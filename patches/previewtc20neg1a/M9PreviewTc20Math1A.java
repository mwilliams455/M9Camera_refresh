package com.particlesdevs.photoncamera.m9.preview;

import java.util.Arrays;

/** Pure math for the preview-only negative TC20 predictor. No capture or still-render authority. */
public final class M9PreviewTc20Math1A {
    public static final String REVISION="M9PREVIEWTC20NEG1A";
    public static final double METER_TARGET=0.107*(8192.0/10000.0);
    public static final double CENTER_WEIGHT_WIDTH=.75;
    public static final double MIN_EV=-.5;
    public static final double MAX_EV=0.0;
    public static final double MAX_SLEW_EV=.25;
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
     * Analyze one horizontally tiled RGBA8 panel whose R/G bytes contain a 16-bit
     * linear-luma code. Layout matches M9PreviewEvidence2E.
     */
    public static Result analyzePackedPanel(byte[] rgba,int width,int height,int panels,int panel) {
        if(rgba==null||width<=0||height<=0||panels<=0||panel<0||panel>=panels
                ||rgba.length<width*height*panels*4)return Result.invalid();
        int n=width*height;
        double[] value=new double[n],weight=new double[n];int valid=0;
        double h2=height/2.0,w2=width/2.0,den=2.0*CENTER_WEIGHT_WIDTH*CENTER_WEIGHT_WIDTH;
        for(int y=0;y<height;y++)for(int x=0;x<width;x++){
            int off=((y*width*panels)+(panel*width)+x)*4;
            int q=((rgba[off]&255)<<8)|(rgba[off+1]&255);
            double v=q/65535.0;
            if(v<=1e-5)continue;
            value[valid]=v;
            double ry=(y-h2)/h2,rx=(x-w2)/w2;
            weight[valid]=Math.exp(-(ry*ry)/den)*Math.exp(-(rx*rx)/den);
            valid++;
        }
        if(valid==0)return Result.invalid();
        Integer[] order=new Integer[valid];
        for(int i=0;i<valid;i++)order[i]=i;
        Arrays.sort(order,(a,b)->Double.compare(value[a],value[b]));
        double total=0;for(int i=0;i<valid;i++)total+=weight[i];
        double half=total*.5,cum=0,median=value[order[valid-1]];
        for(int idx:order){cum+=weight[idx];if(cum>=half){median=value[idx];break;}}
        double requested=clamp(METER_TARGET/Math.max(median,1e-6),.5,16.0);
        // Raw-tail headroom can only limit positive TC20 lift. Negative TC20 is
        // fully determined by this median, so v1A predicts darkening only.
        double negativeOnly=Math.min(1.0,requested);
        double requestedEv=log2(negativeOnly);
        double boundedEv=clamp(requestedEv,MIN_EV,MAX_EV);
        return new Result(true,valid,median,negativeOnly,requestedEv,
                Math.pow(2.0,boundedEv),boundedEv);
    }

    public static double slewEv(double current,double target) {
        current=clamp(current,MIN_EV,MAX_EV);target=clamp(target,MIN_EV,MAX_EV);
        if(target>current+MAX_SLEW_EV)return current+MAX_SLEW_EV;
        if(target<current-MAX_SLEW_EV)return current-MAX_SLEW_EV;
        return target;
    }
    private static double clamp(double x,double lo,double hi){return Math.max(lo,Math.min(hi,x));}
    private static double log2(double x){return Math.log(x)/Math.log(2.0);}
}
