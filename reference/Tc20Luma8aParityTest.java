package com.particlesdevs.photoncamera.m9.render;

import java.util.Arrays;

public final class Tc20Luma8aParityTest {
    private static final double HSM_H = 0.25;
    private static final double HSM_S = 0.85;
    private static final double HSM_V = 1.00;
    private static final double METER_CW = 0.75;

    private static double clamp(double v, double lo, double hi) {
        return Math.max(lo, Math.min(v, hi));
    }

    private static void hsv6ToRgbWrapped(double h, double s, double v, double[] out) {
        int i = (int)h;
        double f = h - i;
        double p = v * (1.0 - s);
        double q = v * (1.0 - s * f);
        double t = v * (1.0 - s * (1.0 - f));
        switch (i) {
            case 0: out[0] = v; out[1] = t; out[2] = p; break;
            case 1: out[0] = q; out[1] = v; out[2] = p; break;
            case 2: out[0] = p; out[1] = v; out[2] = t; break;
            case 3: out[0] = p; out[1] = q; out[2] = v; break;
            case 4: out[0] = t; out[1] = p; out[2] = v; break;
            default: out[0] = v; out[1] = p; out[2] = q; break;
        }
    }

    private static void applyHsm(double r, double g, double b, double[] hsm, int hd, int sd, double[] out) {
        double v = Math.max(r, Math.max(g, b));
        double mn = Math.min(r, Math.min(g, b));
        double gap = v - mn;
        double h = 0.0, s = 0.0;
        if (gap > 1e-12) {
            if (r == v) { h = (g - b) / gap; if (h < 0.0) h += 6.0; }
            else if (g == v) h = 2.0 + (b - r) / gap;
            else h = 4.0 + (r - g) / gap;
            s = gap / v;
        }
        double hp = h * (hd / 6.0);
        double sp = s * (sd - 1);
        int h0 = (int)hp, s0 = (int)sp;
        if (s0 > sd - 2) s0 = sd - 2;
        int h1 = h0 + 1;
        if (h0 >= hd - 1) { h0 = hd - 1; h1 = 0; }
        double hf = hp - h0, sf = sp - s0;
        double oneMinusHf = 1.0 - hf, oneMinusSf = 1.0 - sf;
        int e00 = (h0 * sd + s0) * 3;
        int e01 = (h1 * sd + s0) * 3;
        int e10 = e00 + 3;
        int e11 = e01 + 3;
        double a0 = oneMinusHf * hsm[e00] + hf * hsm[e01];
        double c0 = oneMinusHf * hsm[e10] + hf * hsm[e11];
        double d0 = oneMinusSf * a0 + sf * c0;
        double a1 = oneMinusHf * hsm[e00 + 1] + hf * hsm[e01 + 1];
        double c1 = oneMinusHf * hsm[e10 + 1] + hf * hsm[e11 + 1];
        double d1 = oneMinusSf * a1 + sf * c1;
        double a2 = oneMinusHf * hsm[e00 + 2] + hf * hsm[e01 + 2];
        double c2 = oneMinusHf * hsm[e10 + 2] + hf * hsm[e11 + 2];
        double d2 = oneMinusSf * a2 + sf * c2;
        double hue = h + HSM_H * d0 * (6.0 / 360.0);
        if (hue < 0.0) hue += 6.0; else if (hue >= 6.0) hue -= 6.0;
        double sat0 = s * (1.0 + HSM_S * (d1 - 1.0));
        double sat = Math.min(sat0, 1.0);
        double val = clamp(v * (1.0 + HSM_V * (d2 - 1.0)), 0.0, 1.0);
        hsv6ToRgbWrapped(hue, sat, val, out);
    }

    private static double cameraToSrgbLuma(short[] cam, int c, double[] cw, double[] camToPp,
                                            double[] hsm, int hd, int sd, double[] ppToXyz,
                                            double[] adapt, double[] xyz2Srgb, double[] out) {
        double r = (cam[c] & 0xffff) / 65535.0;
        double g = (cam[c + 1] & 0xffff) / 65535.0;
        double b = (cam[c + 2] & 0xffff) / 65535.0;
        r = Math.min(r, cw[0]); g = Math.min(g, cw[1]); b = Math.min(b, cw[2]);
        double pr = clamp(camToPp[0]*r + camToPp[1]*g + camToPp[2]*b, 0, 1);
        double pg = clamp(camToPp[3]*r + camToPp[4]*g + camToPp[5]*b, 0, 1);
        double pb = clamp(camToPp[6]*r + camToPp[7]*g + camToPp[8]*b, 0, 1);
        applyHsm(pr, pg, pb, hsm, hd, sd, out);
        double x50 = ppToXyz[0]*out[0] + ppToXyz[1]*out[1] + ppToXyz[2]*out[2];
        double y50 = ppToXyz[3]*out[0] + ppToXyz[4]*out[1] + ppToXyz[5]*out[2];
        double z50 = ppToXyz[6]*out[0] + ppToXyz[7]*out[1] + ppToXyz[8]*out[2];
        double x65 = adapt[0]*x50 + adapt[1]*y50 + adapt[2]*z50;
        double y65 = adapt[3]*x50 + adapt[4]*y50 + adapt[5]*z50;
        double z65 = adapt[6]*x50 + adapt[7]*y50 + adapt[8]*z50;
        double sr = xyz2Srgb[0]*x65 + xyz2Srgb[1]*y65 + xyz2Srgb[2]*z65;
        double sg = xyz2Srgb[3]*x65 + xyz2Srgb[4]*y65 + xyz2Srgb[5]*z65;
        double sb = xyz2Srgb[6]*x65 + xyz2Srgb[7]*y65 + xyz2Srgb[8]*z65;
        return Math.max(.2126*sr + .7152*sg + .0722*sb, 0.0);
    }

    private static void sortIndicesByValue(int[] a, double[] v, int lo, int hi) {
        while (lo < hi) {
            int i=lo,j=hi; double pivot=v[a[lo+((hi-lo)>>>1)]];
            while(i<=j){ while(v[a[i]]<pivot)i++; while(v[a[j]]>pivot)j--; if(i<=j){int t=a[i];a[i]=a[j];a[j]=t;i++;j--;}}
            if(j-lo < hi-i){ if(lo<j)sortIndicesByValue(a,v,lo,j); lo=i; }
            else { if(i<hi)sortIndicesByValue(a,v,i,hi); hi=j; }
        }
    }

    private static double[] javaMeter(short[] cam, int w, int h, double[] rowW, double[] colW,
                                      double[] cw, double[] camToPp, double[] hsm, int hd, int sd,
                                      double[] ppToXyz, double[] adapt, double[] xyz2Srgb) {
        int n=w*h; double[] y=new double[n]; double[] tmp=new double[3]; int valid=0;
        for(int p=0,c=0;p<n;p++,c+=3){y[p]=cameraToSrgbLuma(cam,c,cw,camToPp,hsm,hd,sd,ppToXyz,adapt,xyz2Srgb,tmp); if(y[p]>1e-5)valid++;}
        if(valid==0)return new double[]{0,0,0};
        int[] order=new int[valid]; int k=0; for(int i=0;i<n;i++)if(y[i]>1e-5)order[k++]=i;
        sortIndicesByValue(order,y,0,order.length-1);
        double total=0; for(int idx:order)total += rowW[idx/w]*colW[idx%w];
        double half=total*.5,cum=0,median=y[order[order.length-1]];
        for(int idx:order){cum += rowW[idx/w]*colW[idx%w]; if(cum>=half){median=y[idx];break;}}
        long lowCount=n-order.length; double p=(n-1)*.98,p98=0;
        if(p>=lowCount){double pos=p-lowCount;int lo=Math.min(order.length-1,Math.max(0,(int)Math.floor(pos)));int hi=Math.min(order.length-1,Math.max(0,(int)Math.ceil(pos)));double frac=pos-Math.floor(pos);p98=y[order[lo]]+frac*(y[order[hi]]-y[order[lo]]);}
        return new double[]{median,p98,valid};
    }

    public static void main(String[] args) {
        if (!M9NativeColorCore.ensureLoaded()) throw new AssertionError(M9NativeColorCore.loadError());
        int w=257,h=193,n=w*h,hd=6,sd=4;
        short[] cam=new short[n*3];
        for(int p=0,c=0;p<n;p++,c+=3){
            int r=(p*4051 + (p/17)*97) & 0xffff;
            int g=(p*7919 + 12345) & 0xffff;
            int b=(p*1237 + (p%31)*1111) & 0xffff;
            if((p%101)==0){r=g=b=0;}
            cam[c]=(short)r;cam[c+1]=(short)g;cam[c+2]=(short)b;
        }
        double[] cw={0.63,1.0,0.72};
        double[] camToPp={1.08,-.06,-.02,-.03,1.04,-.01,.01,-.08,1.07};
        double[] ppToM9={1,0,0,0,1,0,0,0,1};
        double[] adapt={1.0479,.0229,-.0502,.0296,.9904,-.0171,-.0092,.0151,.7519};
        double[] ppToXyz={.7977,.1352,.0313,.2880,.7119,.0001,0,0,.8249};
        double[] xyz2Srgb={3.2404542,-1.5371385,-.4985314,-.9692660,1.8760108,.0415560,.0556434,-.2040259,1.0572252};
        double[] hsm=new double[hd*sd*3];
        for(int hh=0;hh<hd;hh++)for(int ss=0;ss<sd;ss++){int e=(hh*sd+ss)*3;hsm[e]=(hh-2.5)*1.75 + ss*.15;hsm[e+1]=.90 + hh*.018 + ss*.012;hsm[e+2]=.94 + hh*.009 - ss*.006;}
        byte[] curve=new byte[2048]; for(int i=0;i<curve.length;i++)curve[i]=(byte)(i>>>3);
        double[] rowW=new double[h],colW=new double[w]; double h2=h/2.0,w2=w/2.0,den=2.0*METER_CW*METER_CW;
        for(int yy=0;yy<h;yy++){double ry=(yy-h2)/h2;rowW[yy]=Math.exp(-(ry*ry)/den);}
        for(int xx=0;xx<w;xx++){double rx=(xx-w2)/w2;colW[xx]=Math.exp(-(rx*rx)/den);}
        long ctx=M9NativeColorCore.createContext(cw,camToPp,hsm,ppToM9,adapt,ppToXyz,xyz2Srgb,curve,hd,sd);
        if(ctx==0)throw new AssertionError("native context creation failed");
        double[] got=new double[13];
        for (int repeat=0; repeat<50; repeat++) {
            M9NativeColorCore.meterTc20WeightedSelect(ctx,cam,n,w,h,rowW,colW,got);
        }
        M9NativeColorCore.destroyContext(ctx);
        double[] exp=javaMeter(cam,w,h,rowW,colW,cw,camToPp,hsm,hd,sd,ppToXyz,adapt,xyz2Srgb);
        System.out.printf("java   median=%.17g p98=%.17g valid=%.0f%n",exp[0],exp[1],exp[2]);
        System.out.printf("native median=%.17g p98=%.17g valid=%.0f%n",got[0],got[1],got[2]);
        double dm=Math.abs(exp[0]-got[0]), dp=Math.abs(exp[1]-got[1]);
        if(exp[2]!=got[2] || dm>1e-13 || dp>1e-13) throw new AssertionError("TC20LUMA8A parity failed dm="+dm+" dp="+dp);
        if ((int)Math.rint(got[12]) != 8) throw new AssertionError("TC20LUMA8A expected 8 luma workers, got "+got[12]);
        if (got[10] <= 0 || got[11] <= 0) throw new AssertionError("TC20LUMA8A timing probes missing");
        System.out.println("TC20LUMA8A 50x Java-vs-JNI parity + 8-worker telemetry PASS");
    }
}
