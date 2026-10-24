package com.particlesdevs.photoncamera.control.subject;

/**
 * AP-10K RTMPose SimCC [17,512] keypoint decoder, independent of Android.
 *
 * Matches MMPose get_simcc_maximum (apply_softmax=false): point coordinate
 * = argmax / 2 and raw keypoint response = min(max(X), max(Y)).
 * Do not softmax a narrow but finite peak over 512 bins and then mistake its
 * normalized probability for the raw confidence used by the model.
 */
public final class AnimalSimccDecoder {
    private static final int KEYPOINTS=17;
    private static final int BINS=512;
    private static final int INPUT=256;
    private AnimalSimccDecoder(){}

    public static AnimalEyeTargetPolicy.Point decode(float[] sx,float[] sy,int keypoint,
            float cropLeft,float cropTop,float cropSide,int width,int height) {
        if(sx==null||sy==null||sx.length!=KEYPOINTS*BINS||sy.length!=KEYPOINTS*BINS
                ||keypoint<0||keypoint>=KEYPOINTS||width<=0||height<=0
                ||!Float.isFinite(cropSide)||cropSide<=0f)
            return new AnimalEyeTargetPolicy.Point(Float.NaN,Float.NaN,0f);
        int offset=keypoint*BINS;
        int px=0,py=0;
        float bestX=-Float.MAX_VALUE,bestY=-Float.MAX_VALUE;
        for(int i=0;i<BINS;i++) {
            float x=sx[offset+i],y=sy[offset+i];
            if(Float.isFinite(x)&&x>bestX){bestX=x;px=i;}
            if(Float.isFinite(y)&&y>bestY){bestY=y;py=i;}
        }
        float score=Math.min(bestX,bestY);
        if(!(score>0f)||!Float.isFinite(score))
            return new AnimalEyeTargetPolicy.Point(Float.NaN,Float.NaN,0f);
        float screenX=(cropLeft+(px/2f)*cropSide/INPUT)/width;
        float screenY=(cropTop+(py/2f)*cropSide/INPUT)/height;
        if(!Float.isFinite(screenX)||!Float.isFinite(screenY))
            return new AnimalEyeTargetPolicy.Point(Float.NaN,Float.NaN,0f);
        return new AnimalEyeTargetPolicy.Point(screenX,screenY,score);
    }
}
