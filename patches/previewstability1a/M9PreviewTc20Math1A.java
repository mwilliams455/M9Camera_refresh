package com.particlesdevs.photoncamera.m9.preview;

import java.util.Arrays;

/**
 * Allocation-stable preview-only negative TC20 math.
 * Keeps the NEUTRAL1A photographic behavior while removing per-sample object sorting.
 */
public final class M9PreviewTc20Math1A {
    public static final String REVISION="M9PREVIEWSTABILITY1A";
    public static final String PARENT_REVISION="M9PREVIEWTC20NEUTRAL1A";
    public static final double METER_TARGET=0.107*(8192.0/10000.0);
    public static final double CENTER_WEIGHT_WIDTH=.75;
    public static final double MIN_EV=-.5;
    public static final double MAX_EV=0.0;
    public static final double MAX_SLEW_EV=.125;
    public static final double DEADBAND_EV=.04;
    private static final int HIST_BITS=12;
    private static final int HIST_BINS=1<<HIST_BITS;
    private static final int HIST_SHIFT=16-HIST_BITS;

    /** One persistent histogram per calling thread; live use is the GL thread. */
    private static final ThreadLocal<Scratch> SCRATCH =
            ThreadLocal.withInitial(Scratch::new);

    private static final class Scratch {
        final double[] weightedHistogram=new double[HIST_BINS];
    }

    private M9PreviewTc20Math1A(){}

    public static final class Result {
        public final boolean valid;
        public final int validCount;
        public final double weightedMedian,requestedGain,requestedEv,boundedGain,boundedEv;
        Result(boolean valid,int count,double median,double requestedGain,double requestedEv,
               double boundedGain,double boundedEv){
            this.valid=valid;validCount=count;weightedMedian=median;
            this.requestedGain=requestedGain;this.requestedEv=requestedEv;
            this.boundedGain=boundedGain;this.boundedEv=boundedEv;
        }
        static Result invalid(){return new Result(false,0,Double.NaN,1,0,1,0);}
    }

    /**
     * Analyze a packed 16-bit linear-luma panel. A 12-bit weighted histogram gives
     * sub-0.001-code precision here without allocating Integer wrappers or sort arrays.
     */
    public static Result analyzePackedPanel(byte[] rgba,int width,int height,int panels,int panel) {
        if(rgba==null||width<=0||height<=0||panels<=0||panel<0||panel>=panels
                ||rgba.length<width*height*panels*4)return Result.invalid();

        Scratch scratch=SCRATCH.get();
        double[] hist=scratch.weightedHistogram;
        Arrays.fill(hist,0.0);

        int valid=0;
        double totalWeight=0.0;
        double h2=height/2.0,w2=width/2.0;
        double den=2.0*CENTER_WEIGHT_WIDTH*CENTER_WEIGHT_WIDTH;

        for(int y=0;y<height;y++)for(int x=0;x<width;x++){
            int off=((y*width*panels)+(panel*width)+x)*4;
            int q=((rgba[off]&255)<<8)|(rgba[off+1]&255);
            if(q<=1)continue;
            double ry=(y-h2)/h2,rx=(x-w2)/w2;
            double weight=Math.exp(-(ry*ry)/den)*Math.exp(-(rx*rx)/den);
            int bin=Math.min(HIST_BINS-1,q>>>HIST_SHIFT);
            hist[bin]+=weight;
            totalWeight+=weight;
            valid++;
        }
        if(valid==0||!(totalWeight>0))return Result.invalid();

        double half=totalWeight*.5,cumulative=0.0;
        int medianBin=HIST_BINS-1;
        for(int i=0;i<HIST_BINS;i++){
            cumulative+=hist[i];
            if(cumulative>=half){medianBin=i;break;}
        }
        // Bin centre in the original U16 domain.
        double median=((medianBin<<HIST_SHIFT)+(1<<(HIST_SHIFT-1)))/65535.0;
        median=Math.max(0.0,Math.min(1.0,median));

        double requested=clamp(METER_TARGET/Math.max(median,1e-6),.5,16.0);
        double negativeOnly=Math.min(1.0,requested);
        double requestedEv=log2(negativeOnly);
        double boundedEv=clamp(requestedEv,MIN_EV,MAX_EV);
        return new Result(true,valid,median,negativeOnly,requestedEv,
                Math.pow(2.0,boundedEv),boundedEv);
    }

    public static double slewEv(double current,double target) {
        current=clamp(current,MIN_EV,MAX_EV);
        target=clamp(target,MIN_EV,MAX_EV);
        double delta=target-current;
        if(Math.abs(delta)<=DEADBAND_EV)return current;
        if(delta>MAX_SLEW_EV)return current+MAX_SLEW_EV;
        if(delta<-MAX_SLEW_EV)return current-MAX_SLEW_EV;
        return target;
    }
    private static double clamp(double x,double lo,double hi){return Math.max(lo,Math.min(hi,x));}
    private static double log2(double x){return Math.log(x)/Math.log(2.0);}
}
