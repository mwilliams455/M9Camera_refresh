package com.particlesdevs.photoncamera.processing;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.security.MessageDigest;
import java.util.Arrays;

/** Capture-owned colour/tone approximation of the accepted SAT2/curve02 renderer.
 * Input is the active renderer's common-scene matrix, never another sensor's calibration.
 * No Android state, RAW mutation, device names, or installed external profiles are used.
 */
public final class M9DngProfile {
    public static final int H = 180, S = 65, V = 129, N = 129;
    public final byte[] tone, look;
    public final double gain;
    public final long elapsedMs;
    private static final double[] PCS = {
        1.0000931767609489,1.579227539207758e-5,7.925465633029314e-6,
        -3.769477054823951e-5,.9999936112160234,-3.192011719311565e-6,
        0,0,.9998985904066523};
    private static final double[] SRGB_PP = {
        .5292993150422636,.33005076065375855,.14064992430397805,
        .0984128566140505,.8734844959421335,.028102647443815888,
        .016846442855411464,.11768270512665131,.8654708520179372};
    private static final int[][] EVEN = {{13659,-4457,-1004},{-2244,13469,-3033},{-199,-6014,14398}};
    private static final int[][] ODD = {{14811,-5604,-1004},{-2455,13688,-3033},{393,-6588,14398}};
    private static final String CURVE_SHA = "5b303ff7d9d47ecb8e193a648ddf0570fef46ad29a62d112993d37d52f8c135c";
    private final double[] matrix;
    private final byte[] curve;

    public M9DngProfile(double[] commonSceneToM9, double renderGain, byte[] firmwareCurve) {
        long start=System.nanoTime();
        if (commonSceneToM9==null || commonSceneToM9.length!=9 || !Double.isFinite(renderGain)
                || renderGain<1.0/256 || renderGain>256) throw new IllegalArgumentException("Invalid M9 profile inputs");
        for (int row=0;row<3;row++) {
            double sum=0;
            for (int col=0;col<3;col++) {
                double value=commonSceneToM9[row*3+col];
                if (!Double.isFinite(value) || Math.abs(value)>20) throw new IllegalArgumentException("Invalid M9 matrix");
                sum+=value;
            }
            if (Math.abs(sum-1)>1e-5) throw new IllegalArgumentException("M9 matrix must preserve the neutral axis");
        }
        if (firmwareCurve==null || firmwareCurve.length!=2048 || !sha(firmwareCurve).equals(CURVE_SHA))
            throw new IllegalArgumentException("Unexpected M9 firmware curve");
        matrix=multiply(commonSceneToM9,PCS); gain=renderGain; curve=firmwareCurve.clone();
        double[] x=new double[N], wanted=new double[N];
        double[] rgb=new double[3];
        for (int i=0;i<N;i++) {
            x[i]=decode((double)i/(N-1)); reference(x[i],x[i],x[i],rgb);
            wanted[i]=(decode(rgb[0])+decode(rgb[1])+decode(rgb[2]))/3;
        }
        wanted[0]=0; wanted[N-1]=1;
        double[] y=fitTone(x,wanted);
        ByteBuffer tones=le(N*8);
        // QP roundoff at a black plateau can be slightly negative. DNG readers
        // reject the entire curve if any coordinate falls outside [0,1].
        for (int i=0;i<N;i++) { x[i]=(float)x[i]; y[i]=(float)clip(y[i]); tones.putFloat((float)x[i]).putFloat((float)y[i]); }
        tone=tones.array();
        Spline spline=new Spline(x,y);
        final int invCount=131073;
        double[] inverseX=new double[invCount], inverseY=new double[invCount];
        double previous=0;
        for (int i=0;i<invCount;i++) {
            inverseX[i]=decode((double)i/(invCount-1));
            double value=clip(spline.at(inverseX[i]));
            if (value<previous-1e-7) throw new IllegalStateException("Nonmonotone DNG tone curve");
            inverseY[i]=Math.max(previous,value); previous=inverseY[i];
        }
        ByteBuffer data=le(H*S*V*12);
        double[] encoded=new double[256];
        for (int i=0;i<256;i++) encoded[i]=decode(i/255.0);
        for (int v=0;v<V;v++) {
            double vv=(double)Math.max(1,v)/(V-1), value=decode(vv);
            for (int h=0;h<H;h++) {
                double hue=(double)h*6/H;
                double wr=triangle(hue),wg=triangle(hue+4),wb=triangle(hue+2);
                for (int s=0;s<S;s++) {
                    if (s==0) { data.putFloat(0).putFloat(1).putFloat(1); continue; }
                    double sat=(double)s/(S-1);
                    reference(value*(1-sat+sat*wr),value*(1-sat+sat*wg),value*(1-sat+sat*wb),rgb);
                    double r=encoded[(int)Math.rint(rgb[0]*255)],g=encoded[(int)Math.rint(rgb[1]*255)],b=encoded[(int)Math.rint(rgb[2]*255)];
                    double pr=clip(SRGB_PP[0]*r+SRGB_PP[1]*g+SRGB_PP[2]*b);
                    double pg=clip(SRGB_PP[3]*r+SRGB_PP[4]*g+SRGB_PP[5]*b);
                    double pb=clip(SRGB_PP[6]*r+SRGB_PP[7]*g+SRGB_PP[8]*b);
                    double lo=Math.min(pr,Math.min(pg,pb)),hi=Math.max(pr,Math.max(pg,pb));
                    double a=inverse(lo,inverseY,inverseX),z=inverse(hi,inverseY,inverseX);
                    double scale=hi-lo>1e-14?(z-a)/(hi-lo):0;
                    pr=a+(pr-lo)*scale;pg=a+(pg-lo)*scale;pb=a+(pb-lo)*scale;
                    lo=Math.min(pr,Math.min(pg,pb));hi=Math.max(pr,Math.max(pg,pb));
                    double delta=hi-lo,hs=hi>1e-14?delta/hi:0,hh=0;
                    if (delta>1e-14) {
                        if (pr==hi) hh=(pg-pb)/delta;
                        else if (pg==hi) hh=2+(pb-pr)/delta;
                        else hh=4+(pr-pg)/delta;
                        hh=mod6(hh);
                    }
                    double shift=hs<1e-9?0:mod6(hh-hue+3)-3;
                    float dh=(float)(shift*60),ds=(float)(hs/sat),dv=(float)(encode(hi)/vv);
                    if (!Float.isFinite(dh)||!Float.isFinite(ds)||!Float.isFinite(dv))
                        throw new IllegalStateException("Nonfinite look table");
                    data.putFloat(dh).putFloat(ds).putFloat(dv);
                }
            }
        }
        look=data.array(); elapsedMs=(System.nanoTime()-start)/1_000_000L;
    }

    private void reference(double r,double g,double b,double[] out) {
        int qr=quant(matrix[0]*r+matrix[1]*g+matrix[2]*b);
        int qg=quant(matrix[3]*r+matrix[4]*g+matrix[5]*b);
        int qb=quant(matrix[6]*r+matrix[7]*g+matrix[8]*b);
        int[][] m=qr>=qg?EVEN:ODD;
        for (int c=0;c<3;c++) {
            int index=Math.max(0,Math.min(2047,(m[c][0]*qr+m[c][1]*qg+m[c][2]*qb)>>16));
            out[c]=(curve[index]&255)/255.0;
        }
    }
    private int quant(double x) { return (int)Math.max(0,Math.min(16383,Math.rint(x*gain*16383))); }
    static double clip(double x) { return Math.max(0,Math.min(1,x)); }
    static double encode(double x) { x=Math.max(x,0);return x<=.0031308?12.92*x:1.055*Math.pow(x,1/2.4)-.055; }
    static double decode(double x) { x=Math.max(x,0);return x<=.04045?x/12.92:Math.pow((x+.055)/1.055,2.4); }
    private static double mod6(double x) { return x-6*Math.floor(x/6); }
    private static double triangle(double x) { return clip(Math.abs(mod6(x)-3)-1); }
    static ByteBuffer le(int length) { return ByteBuffer.allocate(length).order(ByteOrder.LITTLE_ENDIAN); }
    static String sha(byte[] data) {
        try { return hex(MessageDigest.getInstance("SHA-256").digest(data)); }
        catch (Exception e) { throw new IllegalStateException(e); }
    }
    static String hex(byte[] data) {
        StringBuilder b=new StringBuilder(data.length*2);
        for(byte value:data) b.append(Character.forDigit((value&255)>>>4,16)).append(Character.forDigit(value&15,16));
        return b.toString();
    }
    private static double[] multiply(double[] a,double[] b) {
        double[] out=new double[9];
        for(int r=0;r<3;r++) for(int c=0;c<3;c++) for(int k=0;k<3;k++) out[r*3+c]+=a[r*3+k]*b[k*3+c];
        return out;
    }
    private static double inverse(double value,double[] y,double[] x) {
        int l=0,r=y.length-1;
        while(l<r) { int mid=(l+r)>>>1;if(y[mid]<value) l=mid+1;else r=mid; }
        if(l==0) return x[0];
        double dy=y[l]-y[l-1];
        return dy>0?x[l-1]+(x[l]-x[l-1])*(value-y[l-1])/dy:x[l];
    }

    /** Weighted projection onto nonnegative Bernstein derivative controls.
     * Hildreth dual coordinate descent solves the same convex tone fit used offline.
     * Endpoints are eliminated rather than relaxed. Failure leaves the ordinary RAW intact.
     */
    static double[] fitTone(double[] x,double[] wanted) {
        int n=x.length,k=n-2,m=3*(n-1);
        double[][] slopes=new double[n][n];
        for(int j=0;j<n;j++) { double[] unit=new double[n];unit[j]=1;double[] d=new Spline(x,unit).d;for(int i=0;i<n;i++) slopes[i][j]=d[i]; }
        double[][] a=new double[m][k];double[] bounds=new double[m],weights=new double[k];
        for(int j=0;j<k;j++) weights[j]=Math.pow(.005+wanted[j+1],-.65);
        for(int i=0;i<n-1;i++) for(int part=0;part<3;part++) {
            int row=i*3+part;double dx=x[i+1]-x[i],norm=0;
            for(int j=0;j<n;j++) {
                double c=part==0?dx*slopes[i][j]:part==2?dx*slopes[i+1][j]:
                    3*((j==i+1?1:0)-(j==i?1:0))-dx*(slopes[i][j]+slopes[i+1][j]);
                if(j==n-1) bounds[row]=-c;
                else if(j>0) { a[row][j-1]=c/weights[j-1];norm+=a[row][j-1]*a[row][j-1]; }
            }
            norm=Math.sqrt(norm);if(norm<1e-20) throw new IllegalStateException("Degenerate tone fit");
            bounds[row]/=norm;for(int j=0;j<k;j++) a[row][j]/=norm;
        }
        double[] z=new double[k],lambda=new double[m];for(int j=0;j<k;j++) z[j]=wanted[j+1]*weights[j];
        boolean converged=false;
        for(int sweep=0;sweep<12000;sweep++) {
            double maxMove=0;
            for(int i=0;i<m;i++) {
                double dot=0;for(int j=0;j<k;j++) dot+=a[i][j]*z[j];
                double next=Math.max(0,lambda[i]+bounds[i]-dot),change=next-lambda[i];
                lambda[i]=next;maxMove=Math.max(maxMove,Math.abs(change));
                if(change!=0) for(int j=0;j<k;j++) z[j]+=change*a[i][j];
            }
            if(maxMove<1e-11) { converged=true;break; }
        }
        double[] y=new double[n];y[n-1]=1;for(int j=0;j<k;j++) y[j+1]=z[j]/weights[j];
        if(!converged) {
            // Long clipped plateaus can leave slowly converging dual multipliers.
            // Accept only a feasible primal curve with at most 0.1% regularization
            // toward the identity; larger departures bypass profile export.
            Spline fit=new Spline(x,y);double mix=0;
            for(int i=0;i<n-1;i++) {
                double dx=x[i+1]-x[i];
                double c=Math.min(dx*fit.d[i],Math.min(dx*fit.d[i+1],3*(y[i+1]-y[i])-dx*(fit.d[i]+fit.d[i+1])));
                if(c<0) mix=Math.max(mix,-c/(dx-c));
            }
            if(mix>.001) throw new IllegalStateException("DNG tone fit did not converge within colour tolerance");
            mix=Math.min(.001,mix+1e-8);
            for(int i=1;i<n-1;i++) y[i]=(1-mix)*y[i]+mix*x[i];
        }
        return y;
    }

    static final class Spline {
        final double[] x,y,d;
        Spline(double[] x,double[] y) {
            this.x=x;this.y=y;int n=x.length;double[] dx=new double[n-1],slope=new double[n-1],initial=new double[n],up=new double[n],lo=new double[n];d=new double[n];
            for(int i=0;i<n-1;i++) { dx[i]=x[i+1]-x[i];slope[i]=(y[i+1]-y[i])/dx[i]; }
            for(int i=1;i<n-1;i++) initial[i]=(slope[i-1]*dx[i]+slope[i]*dx[i-1])/(dx[i-1]+dx[i]);
            initial[0]=2*slope[0]-initial[1];initial[n-1]=2*slope[n-2]-initial[n-2];
            up[0]=.5;lo[n-1]=.5;d[0]=.75*(initial[0]+initial[1]);d[n-1]=.75*(initial[n-2]+initial[n-1]);
            for(int i=1;i<n-1;i++) { lo[i]=dx[i]/(2*(dx[i-1]+dx[i]));up[i]=dx[i-1]/(2*(dx[i-1]+dx[i]));d[i]=1.5*initial[i]; }
            for(int i=1;i<n;i++) { double divisor=1-up[i-1]*lo[i];up[i]/=divisor;d[i]=(d[i]-d[i-1]*lo[i])/divisor; }
            for(int i=n-2;i>=0;i--) d[i]-=up[i]*d[i+1];
        }
        double at(double value) {
            if(value<=x[0]) return y[0];if(value>=x[x.length-1]) return y[y.length-1];
            int i=Arrays.binarySearch(x,value);if(i>=0) return y[i];i=-i-2;
            double dx=x[i+1]-x[i],t=(value-x[i])/dx,t2=t*t,t3=t2*t;
            return (2*t3-3*t2+1)*y[i]+(t3-2*t2+t)*dx*d[i]+(-2*t3+3*t2)*y[i+1]+(t3-t2)*dx*d[i+1];
        }
    }
}
