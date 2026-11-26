package com.particlesdevs.photoncamera.m9.preview;

import com.particlesdevs.photoncamera.control.tracking.TrackingGeometry;

public class M9SubjectMeterFramesTest {
    private static final Object OWNER = new Object();
    private static final long T = 1_000_000_000L;
    private static TrackingGeometry geometry(long t, boolean mirror) {
        return new TrackingGeometry(OWNER,"0","MOTION",1080,1920,0,240,1080,1440,1,0,mirror,t,t);
    }
    private static void detect(TrackingGeometry g, long t) {
        M9SubjectMeterFrames.observe(g,7,t,t,.02f,.04f,.20f,.24f,true);
    }
    public static void main(String[] args) {
        int w=M9SubjectMeterFrames.WIDTH,h=M9SubjectMeterFrames.HEIGHT;
        byte[] pixels = new byte[M9SubjectMeterFrames.BYTES];
        // GL stores the bright upper-left face near the end of the buffer.
        for(int y=0;y<h/4;y++) for(int x=0;x<w/4;x++) {
            int at=4*((h-1-y)*w+x);
            pixels[at]=pixels[at+1]=pixels[at+2]=(byte)255;
        }
        M9TrackedSubjectMeter.clear();
        M9SubjectMeterFrames.clear();
        for(int i=0;i<8;i++) {
            long t=T+i*250_000_000L;
            TrackingGeometry g=geometry(t,false);
            M9SubjectMeterFrames.request(g,t);
            if(i%2==0) detect(g,t);
            M9SubjectMeterFrames.publish(g,pixels,t);
            if(i%2!=0) detect(g,t);
            assert M9TrackedSubjectMeter.trace(t).contains("faceHotSamples=37");
        }
        long t=T+7*250_000_000L;
        assert M9TrackedSubjectMeter.faceTrim("0","MOTION",t)==-.5;
        detect(geometry(t,false),t+1);
        assert M9TrackedSubjectMeter.trace(t+1).isEmpty();
        t+=300_000_000L;
        TrackingGeometry g=geometry(t,true);
        M9SubjectMeterFrames.request(g,t);
        M9SubjectMeterFrames.publish(geometry(t,false),pixels,t);
        detect(g,t);
        assert M9TrackedSubjectMeter.trace(t).isEmpty();
        M9SubjectMeterFrames.publish(geometry(t-200_000_000L,true),pixels,t);
        assert M9TrackedSubjectMeter.trace(t).isEmpty();
        M9SubjectMeterFrames.missed(t);
        M9SubjectMeterFrames.publish(g,pixels,t);
        assert M9TrackedSubjectMeter.trace(t).isEmpty();
        System.out.println("Pre-falloff region, arrival order, stale, duplicate, miss and geometry checks passed");
    }
}
