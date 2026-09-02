public class primary23_java_oracle {
    static final int RAW_MAX = 16383, LUT_MAX = 2047;
    static final double HSM_H = .25, HSM_S = .85, HSM_V = 1.0;
    static final long[] QE={16754,-7632,-922,-3124,14774,-3458,-567,-9579,18330};
    static final long[] QO={18160,-9034,-922,-3422,15080,-3458,137,-10264,18330};
    static final int HD=90, SD=30, WIDTH=257, ROWS=97, PIXELS=WIDTH*ROWS;

    static long clipLong(long v,long lo,long hi){return v<lo?lo:(v>hi?hi:v);}
    static double clamp(double v,double lo,double hi){return v<lo?lo:(v>hi?hi:v);}
    static int roundU8(double v){return (int)(clamp(v/255.0,0,1)*255.0+.5);}
    static int pack(int r,int g,int b){return 0xff000000|(r<<16)|(g<<8)|b;}

    static void hsv(double h,double s,double v,double[] out){
        int i=(int)h; double f=h-i,p=v*(1-s),q=v*(1-s*f),t=v*(1-s*(1-f));
        switch(i){case 0:out[0]=v;out[1]=t;out[2]=p;break;case 1:out[0]=q;out[1]=v;out[2]=p;break;case 2:out[0]=p;out[1]=v;out[2]=t;break;case 3:out[0]=p;out[1]=q;out[2]=v;break;case 4:out[0]=t;out[1]=p;out[2]=v;break;default:out[0]=v;out[1]=p;out[2]=q;}
    }
    static void hsm(double r,double g,double b,double[] table,double[] out){
        double v=Math.max(r,Math.max(g,b)),mn=Math.min(r,Math.min(g,b)),gap=v-mn,h=0,s=0;
        if(gap>1e-12){if(r==v){h=(g-b)/gap;if(h<0)h+=6;}else if(g==v)h=2+(b-r)/gap;else h=4+(r-g)/gap;s=gap/v;}
        double hp=h*(HD/6.0),sp=s*(SD-1);int h0=(int)hp,s0=(int)sp;if(s0>SD-2)s0=SD-2;int h1=h0+1;if(h0>=HD-1){h0=HD-1;h1=0;}
        double hf=hp-h0,sf=sp-s0,omh=1-hf,oms=1-sf;int e00=(h0*SD+s0)*3,e01=(h1*SD+s0)*3,e10=e00+3,e11=e01+3;
        double a0=omh*table[e00]+hf*table[e01],c0=omh*table[e10]+hf*table[e11],d0=oms*a0+sf*c0;
        double a1=omh*table[e00+1]+hf*table[e01+1],c1=omh*table[e10+1]+hf*table[e11+1],d1=oms*a1+sf*c1;
        double a2=omh*table[e00+2]+hf*table[e01+2],c2=omh*table[e10+2]+hf*table[e11+2],d2=oms*a2+sf*c2;
        double hue=h+HSM_H*d0*(6.0/360.0);if(hue<0)hue+=6;else if(hue>=6)hue-=6;
        double sat=Math.min(s*(1+HSM_S*(d1-1)),1),val=clamp(v*(1+HSM_V*(d2-1)),0,1);hsv(hue,sat,val,out);
    }
    static void cameraToM9(short[] cam,int c,double[] cw,double[] camToPp,double[] table,double[] ppToM9,double[] hs,double[] m9){
        double r=(cam[c]&0xffff)/65535.0,g=(cam[c+1]&0xffff)/65535.0,b=(cam[c+2]&0xffff)/65535.0;
        r=Math.min(r,cw[0]);g=Math.min(g,cw[1]);b=Math.min(b,cw[2]);
        double pr=clamp(camToPp[0]*r+camToPp[1]*g+camToPp[2]*b,0,1),pg=clamp(camToPp[3]*r+camToPp[4]*g+camToPp[5]*b,0,1),pb=clamp(camToPp[6]*r+camToPp[7]*g+camToPp[8]*b,0,1);
        hsm(pr,pg,pb,table,hs);double hr=hs[0],hg=hs[1],hb=hs[2];
        m9[0]=Math.max(ppToM9[0]*hr+ppToM9[1]*hg+ppToM9[2]*hb,0.0);m9[1]=Math.max(ppToM9[3]*hr+ppToM9[4]*hg+ppToM9[5]*hb,0.0);m9[2]=Math.max(ppToM9[6]*hr+ppToM9[7]*hg+ppToM9[8]*hb,0.0);
    }
    static int curve(double[] m9,double gain,byte[] lut,int[] rgb){
        long r=clipLong((long)Math.rint(m9[0]*gain*RAW_MAX),0,RAW_MAX),g=clipLong((long)Math.rint(m9[1]*gain*RAW_MAX),0,RAW_MAX),b=clipLong((long)Math.rint(m9[2]*gain*RAW_MAX),0,RAW_MAX);boolean even=r>=g;long[] q=even?QE:QO;
        long a0=q[0]*r+q[1]*g+q[2]*b,a1=q[3]*r+q[4]*g+q[5]*b,a2=q[6]*r+q[7]*g+q[8]*b;int i0=(int)clipLong(a0>>16,0,LUT_MAX),i1=(int)clipLong(a1>>16,0,LUT_MAX),i2=(int)clipLong(a2>>16,0,LUT_MAX);
        int rr=lut[i0]&255,gg=lut[i1]&255,bb=lut[i2]&255;rgb[0]=rr;rgb[1]=gg;rgb[2]=bb;int edge=0;if(rr==0||rr==255)edge++;if(gg==0||gg==255)edge++;if(bb==0||bb==255)edge++;return (even?4:0)|edge;
    }
    static long fnv(long h,int v){for(int i=0;i<4;i++){h^=(v>>>(i*8))&255;h*=0x100000001b3L;}return h;}
    static long fnvLong(long h,long v){for(int i=0;i<8;i++){h^=(v>>>(i*8))&255;h*=0x100000001b3L;}return h;}
    static Result render(short[] cam,double[] cw,double[] ctp,double[] table,double[] ptm,byte[] lut,double gain,double cbg,double crg){
        int[] argb=new int[PIXELS];long even=0,edge=0,nw=0;int w2=WIDTH-(WIDTH&1);double[] h0=new double[3],h1=new double[3],m0=new double[3],m1=new double[3];int[] r0=new int[3],r1=new int[3];
        for(int sy=0;sy<ROWS;sy++){int row=sy*WIDTH;for(int x=0;x<w2;x+=2){int p0=row+x,p1=p0+1,c0=p0*3,c1=p1*3;cameraToM9(cam,c0,cw,ctp,table,ptm,h0,m0);cameraToM9(cam,c1,cw,ctp,table,ptm,h1,m1);int f0=curve(m0,gain,lut,r0),f1=curve(m1,gain,lut,r1);even+=((f0>>>2)&1)+((f1>>>2)&1);edge+=(f0&3)+(f1&3);
            long rr0=r0[0],gg0=r0[1],bb0=r0[2],rr1=r1[0],gg1=r1[1],bb1=r1[2];long y0=(4899*rr0+9617*gg0+1868*bb0)>>14,y1=(4899*rr1+9617*gg1+1868*bb1)>>14,rs=rr0+rr1,gs=gg0+gg1,bs=bb0+bb1;long cbS=((((-2765*rs+1)>>1)-((5427*gs)>>1)+((8192*bs)>>1)))>>14,crS=((((8192*rs)>>1)-((6860*gs)>>1)-((1332*bs)>>1)))>>14;int cb=(int)((cbS+128)&255)-128,cr=(int)((crS+128)&255)-128;double cbm=cb<0?cb*cbg:cb,crm=cr<0?cr*crg:cr;
            int R0=roundU8(y0+1.402*crm),G0=roundU8(y0-.344136*cbm-.714136*crm),B0=roundU8(y0+1.772*cbm),R1=roundU8(y1+1.402*crm),G1=roundU8(y1-.344136*cbm-.714136*crm),B1=roundU8(y1+1.772*cbm);argb[p0]=pack(R0,G0,B0);argb[p1]=pack(R1,G1,B1);if(Math.max(R0,Math.max(G0,B0))>=250)nw++;if(Math.max(R1,Math.max(G1,B1))>=250)nw++;}
            if(w2!=WIDTH){int p=row+w2,c=p*3;cameraToM9(cam,c,cw,ctp,table,ptm,h0,m0);int f=curve(m0,gain,lut,r0);even+=(f>>>2)&1;edge+=f&3;int rr=r0[0],gg=r0[1],bb=r0[2];argb[p]=pack(rr,gg,bb);if(Math.max(rr,Math.max(gg,bb))>=250)nw++;}}
        long hash=0xcbf29ce484222325L;for(int v:argb)hash=fnv(hash,v);hash=fnvLong(hash,even);hash=fnvLong(hash,edge);hash=fnvLong(hash,nw);return new Result(hash,even,edge,nw);
    }
    static class Result{long h,e,d,w;Result(long h,long e,long d,long w){this.h=h;this.e=e;this.d=d;this.w=w;}}
    public static void main(String[] a){
        double[] cw={.78,.92,.84};double[] ctp={1.15,-.08,-.02,-.04,1.07,-.03,.01,-.09,1.12};double[] ptm={1.04,-.08,.03,-.05,1.08,-.02,.02,-.12,1.10};
        double[] table=new double[HD*SD*3];for(int i=0;i<table.length/3;i++){table[i*3]=-25.0+((i*37)%3600)/100.0;table[i*3+1]=.75+((i*53)%600)/1000.0;table[i*3+2]=.8+((i*97)%400)/1000.0;}
        byte[] lut=new byte[2048];for(int i=0;i<lut.length;i++)lut[i]=(byte)Math.min(255,(i*255+1023)/2047);
        short[] cam=new short[PIXELS*3];int state=0x13579bdf;for(int i=0;i<cam.length;i++){state=state*1664525+1013904223;cam[i]=(short)((state>>>8)&0xffff);}
        double[][] scenarios={{.83,1,1},{1.2212466,.875,.92},{1.87,.75,.84},{2.35,.9375,.96}};
        long aggregate=0xcbf29ce484222325L;for(int i=0;i<scenarios.length;i++){Result r=render(cam,cw,ctp,table,ptm,lut,scenarios[i][0],scenarios[i][1],scenarios[i][2]);System.out.printf("case%d hash=%016x even=%d edge=%d nearWhite=%d%n",i,r.h,r.e,r.d,r.w);aggregate=fnvLong(aggregate,r.h);}
        System.out.printf("aggregate=%016x pixels=%d cases=%d%n",aggregate,PIXELS,scenarios.length);
    }
}
