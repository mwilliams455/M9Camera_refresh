package com.particlesdevs.photoncamera.m9.preview;


public class FaceHighlightTest {
    static long t;
    static int checks;
    static void expect(double expected) {
        double actual = M9TrackedSubjectMeter.faceTrim("wide","MOTION", t);
        if (Math.abs(expected-actual) > 1.e-10) throw new AssertionError(t+" expected "+expected+" got "+actual);
        checks++;
    }
    static void vote(int ms, int hot, int near) { vote(ms, 1, hot, near); }
    static void vote(int ms, int id, int hot, int near) {
        t = 1_000_000_000L + ms*1_000_000L;
        M9TrackedSubjectMeter.update("wide","MOTION",id,t,150,180,hot,near);
    }
    public static void main(String[] args) throws Exception {
        M9TrackedSubjectMeter.clear();
        vote(0,1,3); expect(0);
        vote(100,7,10); expect(0);
        vote(100,7,10); expect(0);
        vote(200,7,10); expect(-.25);
        vote(300,7,10); expect(-.25);
        vote(640,7,10); expect(-.25);
        vote(700,7,10); expect(-.25);
        M9TrackedSubjectMeter.missed(t+1);
        vote(820,8,10); expect(-.25);
        vote(990,7,10); expect(-.50);
        vote(1100,0,6); expect(-.50);
        vote(1240,0,1); expect(-.50);
        vote(1300,5,10); expect(-.50);
        vote(1400,0,1); expect(-.50);
        vote(1500,0,1); expect(-.25);
        vote(1600,0,1); expect(0);
        vote(1850,6,8); vote(2000,6,8); expect(-.25);
        vote(2500,6,8); vote(2650,6,8); expect(-.50);
        if (M9TrackedSubjectMeter.faceTrim("tele","MOTION",t)!=0 || M9TrackedSubjectMeter.faceTrim("wide","PHOTO",t)!=0) throw new AssertionError();
        t+=775_000_000; expect(-.25);
        t+=225_000_000; expect(0);
        vote(3700,2,9,15); expect(0);
        vote(3850,2,9,15); expect(-.25);
        vote(4000,2,-1,-1); expect(0);
        M9TrackedSubjectMeter.update("wide","MOTION",2,t+1,12,210,-1,-1);
        if (M9TrackedSubjectMeter.requested("wide","MOTION",t+1)!=.25) throw new AssertionError();
        System.out.println(checks+" exposure state assertions passed, plus camera/mode isolation and dark-subject lift.");
    }
}
