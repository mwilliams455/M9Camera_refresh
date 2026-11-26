package com.particlesdevs.photoncamera.m9.preview;

import android.graphics.Bitmap;

public class PreviewFeedbackTest {
    static int channel(double linear) {
        double unit = Math.min(1,linear);
        return (int)Math.round(255 * (unit <= .0031308 ? 12.92*unit : 1.055*Math.pow(unit,1/2.4)-.055));
    }
    static double sample(int frame, double intensity, double applied) {
        double factor = Math.pow(2,applied) * intensity;
        int rgb=0xff000000 | channel(1.25*factor)<<16 | channel(.95*factor)<<8 | channel(.65*factor);
        long t=1_000_000_000L+frame*200_000_000L;
        M9TrackedSubjectMeter.observe("wide","MOTION",1,t,t,new Bitmap(rgb),.25f,.2f,.75f,.8f,true);
        return M9TrackedSubjectMeter.faceTrim("wide","MOTION",t);
    }
    public static void main(String[] args) {
        double previous=0;
        for (int n=0;n<45;n++) {
            double light=n<5 || n>=35 ? .45 : 1.;
            previous=sample(n,light,previous);
            if ((n<5 || n>=39) && previous!=0) throw new AssertionError("Ordinary light "+n);
            if (n>=10 && n<35 && previous!=-.50) throw new AssertionError("Sustained bright light "+n);
        }
        System.out.println("Synthetic 45-frame feedback sequence passed. Settled at -0.50 EV under sustained bright light and released after light fell.");
    }
}
