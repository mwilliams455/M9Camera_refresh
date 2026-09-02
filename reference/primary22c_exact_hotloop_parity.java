import java.util.Random;

public class primary22c_exact_hotloop_parity {
    static final int RAW_MAX=16383, LUT_MAX=2047;
    static final double HSM_H=.25, HSM_S=.85, HSM_V=1.0;
    static final long[] QE={16754,-7632,-922,-3124,14774,-3458,-567,-9579,18330};
    static final long[] QO={18160,-9034,-922,-3422,15080,-3458,137,-10264,18330};
    static final double[] UNIT16=buildUnit16();
    static double[] buildUnit16(){ double[] o=new double[65536]; for(int i=0;i<o.length;i++)o[i]=i/65535.0; return o; }
    static long clipLong(long v,long lo,long hi){return v<lo?lo:(v>hi?hi:v);}
    static double clamp(double v,double lo,double hi){return v<lo?lo:(v>hi?hi:v);}

    static int oldCurve(double[] m9,double gain,byte[] curve,int[] rgb){
        long r=clipLong((long)Math.rint(m9[0]*gain*RAW_MAX),0,RAW_MAX);
        long g=clipLong((long)Math.rint(m9[1]*gain*RAW_MAX),0,RAW_MAX);
        long b=clipLong((long)Math.rint(m9[2]*gain*RAW_MAX),0,RAW_MAX);
        long[] q=r>=g?QE:QO;
        long a0=q[0]*r+q[1]*g+q[2]*b;
        long a1=q[3]*r+q[4]*g+q[5]*b;
        long a2=q[6]*r+q[7]*g+q[8]*b;
        int i0=(int)clipLong(a0>>16,0,LUT_MAX),i1=(int)clipLong(a1>>16,0,LUT_MAX),i2=(int)clipLong(a2>>16,0,LUT_MAX);
        int rr=curve[i0]&255,gg=curve[i1]&255,bb=curve[i2]&255; rgb[0]=rr;rgb[1]=gg;rgb[2]=bb;
        int edge=0;if(rr==0||rr==255)edge++;if(gg==0||gg==255)edge++;if(bb==0||bb==255)edge++;
        return (r>=g?4:0)|edge;
    }
    static int oldBridgeCurve(double pr,double pg,double pb,double[] m,double gain,byte[] curve){
        double[] m9=new double[3];
        m9[0]=Math.max(m[0]*pr+m[1]*pg+m[2]*pb,0.0);
        m9[1]=Math.max(m[3]*pr+m[4]*pg+m[5]*pb,0.0);
        m9[2]=Math.max(m[6]*pr+m[7]*pg+m[8]*pb,0.0);
        int[] rgb=new int[3]; int f=oldCurve(m9,gain,curve,rgb);
        return (((f>>>2)&1)<<26)|((f&3)<<24)|(rgb[0]<<16)|(rgb[1]<<8)|rgb[2];
    }
    static int fused(double pr,double pg,double pb,double[] m,double gain,byte[] curve){
        double m9r=Math.max(m[0]*pr+m[1]*pg+m[2]*pb,0.0);
        double m9g=Math.max(m[3]*pr+m[4]*pg+m[5]*pb,0.0);
        double m9b=Math.max(m[6]*pr+m[7]*pg+m[8]*pb,0.0);
        long r=clipLong((long)Math.rint(m9r*gain*RAW_MAX),0,RAW_MAX);
        long g=clipLong((long)Math.rint(m9g*gain*RAW_MAX),0,RAW_MAX);
        long b=clipLong((long)Math.rint(m9b*gain*RAW_MAX),0,RAW_MAX);
        boolean even=r>=g; long a0,a1,a2;
        if(even){a0=16754*r-7632*g-922*b;a1=-3124*r+14774*g-3458*b;a2=-567*r-9579*g+18330*b;}
        else{a0=18160*r-9034*g-922*b;a1=-3422*r+15080*g-3458*b;a2=137*r-10264*g+18330*b;}
        int i0=(int)clipLong(a0>>16,0,LUT_MAX),i1=(int)clipLong(a1>>16,0,LUT_MAX),i2=(int)clipLong(a2>>16,0,LUT_MAX);
        int rr=curve[i0]&255,gg=curve[i1]&255,bb=curve[i2]&255; int edge=0;
        if(rr==0||rr==255)edge++;if(gg==0||gg==255)edge++;if(bb==0||bb==255)edge++;
        return (even?(1<<26):0)|(edge<<24)|(rr<<16)|(gg<<8)|bb;
    }

    static void hsv(double h,double s,double v,double[] out){int i=(int)h;double f=h-i,p=v*(1-s),q=v*(1-s*f),t=v*(1-s*(1-f));switch(i){case 0:out[0]=v;out[1]=t;out[2]=p;break;case 1:out[0]=q;out[1]=v;out[2]=p;break;case 2:out[0]=p;out[1]=v;out[2]=t;break;case 3:out[0]=p;out[1]=q;out[2]=v;break;case 4:out[0]=t;out[1]=p;out[2]=v;break;default:out[0]=v;out[1]=p;out[2]=q;}}
    static void hsmOld(double r,double g,double b,double[] hsm,int hd,int sd,double[] out){
        double v=Math.max(r,Math.max(g,b)),mn=Math.min(r,Math.min(g,b)),gap=v-mn,h=0,s=0;
        if(gap>1e-12){if(r==v){h=(g-b)/gap;if(h<0)h+=6;}else if(g==v)h=2+(b-r)/gap;else h=4+(r-g)/gap;s=gap/v;}
        double hp=h*(hd/6.0),sp=s*(sd-1);int h0=(int)hp,s0=(int)sp;if(s0>sd-2)s0=sd-2;int h1=h0+1;boolean wrap=h0>=hd-1;if(wrap){h0=hd-1;h1=0;}
        double hf=hp-h0,sf=sp-s0,omh=1-hf,oms=1-sf;int e00=(h0*sd+s0)*3,e01=(h1*sd+s0)*3,e10=e00+3,e11=e01+3;
        double a0=omh*hsm[e00]+hf*hsm[e01],c0=omh*hsm[e10]+hf*hsm[e11],d0=oms*a0+sf*c0;
        double a1=omh*hsm[e00+1]+hf*hsm[e01+1],c1=omh*hsm[e10+1]+hf*hsm[e11+1],d1=oms*a1+sf*c1;
        double a2=omh*hsm[e00+2]+hf*hsm[e01+2],c2=omh*hsm[e10+2]+hf*hsm[e11+2],d2=oms*a2+sf*c2;
        double hue=h+HSM_H*d0*(6.0/360.0);if(hue<0)hue+=6;else if(hue>=6)hue-=6;double sat=Math.min(s*(1+HSM_S*(d1-1)),1),val=clamp(v*(1+HSM_V*(d2-1)),0,1);hsv(hue,sat,val,out);
    }
    static void hsmNew(double r,double g,double b,double[] hsm,double[] out){
        double v=Math.max(r,Math.max(g,b)),mn=Math.min(r,Math.min(g,b)),gap=v-mn,h=0,s=0;
        if(gap>1e-12){if(r==v){h=(g-b)/gap;if(h<0)h+=6;}else if(g==v)h=2+(b-r)/gap;else h=4+(r-g)/gap;s=gap/v;}
        double hp=h*15.0,sp=s*29.0;int h0=(int)hp,s0=(int)sp;if(s0>28)s0=28;int h1=h0+1;boolean wrap=h0>=89;if(wrap){h0=89;h1=0;}
        double hf=hp-h0,sf=sp-s0,omh=1-hf,oms=1-sf;int e00=(h0*30+s0)*3,e01=(h1*30+s0)*3,e10=e00+3,e11=e01+3;
        double a0=omh*hsm[e00]+hf*hsm[e01],c0=omh*hsm[e10]+hf*hsm[e11],d0=oms*a0+sf*c0;
        double a1=omh*hsm[e00+1]+hf*hsm[e01+1],c1=omh*hsm[e10+1]+hf*hsm[e11+1],d1=oms*a1+sf*c1;
        double a2=omh*hsm[e00+2]+hf*hsm[e01+2],c2=omh*hsm[e10+2]+hf*hsm[e11+2],d2=oms*a2+sf*c2;
        double hue=h+HSM_H*d0*(6.0/360.0);if(hue<0)hue+=6;else if(hue>=6)hue-=6;double sat=Math.min(s*(1+HSM_S*(d1-1)),1),val=clamp(v*(1+HSM_V*(d2-1)),0,1);hsv(hue,sat,val,out);
    }

    public static void main(String[] args){
        long unitMismatch=0;for(int i=0;i<65536;i++)if(Double.doubleToLongBits(i/65535.0)!=Double.doubleToLongBits(UNIT16[i]))unitMismatch++;
        Random rnd=new Random(0x22c5eedL); byte[] curve=new byte[2048];for(int i=0;i<2048;i++)curve[i]=(byte)Math.min(255,(i*255+1023)/2047);
        long fuseMismatch=0; int N=5_000_000; for(int n=0;n<N;n++){
            double pr=rnd.nextDouble(),pg=rnd.nextDouble(),pb=rnd.nextDouble(); double[] m=new double[9]; for(int i=0;i<9;i++)m[i]=rnd.nextDouble()*2-0.7; double gain=.5+rnd.nextDouble()*3;
            if(oldBridgeCurve(pr,pg,pb,m,gain,curve)!=fused(pr,pg,pb,m,gain,curve))fuseMismatch++;
        }
        double[] table=new double[90*30*3];for(int i=0;i<table.length;i++){int ch=i%3;table[i]=ch==0?(rnd.nextDouble()*36-26):(ch==1?(0.75+rnd.nextDouble()*.6):(0.8+rnd.nextDouble()*.4));}
        long hsmMismatch=0; int H=2_000_000; double[] a=new double[3],b=new double[3];for(int n=0;n<H;n++){double r=rnd.nextDouble(),g=rnd.nextDouble(),bl=rnd.nextDouble();hsmOld(r,g,bl,table,90,30,a);hsmNew(r,g,bl,table,b);for(int c=0;c<3;c++)if(Double.doubleToLongBits(a[c])!=Double.doubleToLongBits(b[c])){hsmMismatch++;break;}}
        int M=4096*3072*3;short[] vals=new short[M];for(int i=0;i<M;i++)vals[i]=(short)rnd.nextInt(65536);double sink=0;for(int w=0;w<2;w++){for(short v:vals)sink+=(v&65535)/65535.0;for(short v:vals)sink+=UNIT16[v&65535];}
        long t=System.nanoTime();double sd=0;for(short v:vals)sd+=(v&65535)/65535.0;long td=System.nanoTime()-t;t=System.nanoTime();double sl=0;for(short v:vals)sl+=UNIT16[v&65535];long tl=System.nanoTime()-t;
        System.out.println("PRIMARY2.2C exact hot-loop parity");
        System.out.println("UNIT16 exhaustive mismatches = "+unitMismatch+" / 65536");
        System.out.println("M9 bridge+SAT3 fused packed mismatches = "+fuseMismatch+" / "+N);
        System.out.println("HSM 90x30 constant-dimension bit mismatches = "+hsmMismatch+" / "+H);
        System.out.printf("Directional host UNIT16 conversion: divide %.1f ms / lookup %.1f ms (%.2fx), checksumEqual=%s sink=%.3f%n",td/1e6,tl/1e6,(double)td/tl,Double.doubleToLongBits(sd)==Double.doubleToLongBits(sl),sink);
        if(unitMismatch!=0||fuseMismatch!=0||hsmMismatch!=0)throw new AssertionError("parity failure");
    }
}
