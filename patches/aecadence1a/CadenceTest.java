package com.particlesdevs.photoncamera.m9.preview;
import android.opengl.GLES30;
import android.os.SystemClock;
import com.particlesdevs.photoncamera.m9.M9ExposurePlan1A;

/** Synthetic clock/GL contract tests. This is not a GPU/Android performance benchmark. */
public final class CadenceTest {
    static int checks;
    static void yes(boolean value,String why) { if(!value)throw new AssertionError(why); checks++; }
    static void eq(long a,long b,String why) { yes(a==b,why+": "+a+" != "+b); }
    static void scheduler() {
        M9AeProbeCadence1A c=new M9AeProbeCadence1A(); long t=1_000_000_000L;
        yes(c.due(t,100,"A","PHOTO",0,true),"initial probe immediate");c.submitted(t,100);
        eq(c.lastIntervalNs(),-1,"no fabricated first interval");
        yes(!c.due(t+124_999_999L,101,"A","PHOTO",0,true),"fast rate limit");
        yes(c.due(t+125_000_000L,101,"A","PHOTO",0,true),"125ms fast cadence");
        c.submitted(t+125_000_000L,101);
        eq(c.lastIntervalNs(),125_000_000L,"measured interval");
        yes(!c.due(t+400_000_000L,101,"A","PHOTO",0,true),"duplicate texture denied");
        yes(!c.due(t+400_000_000L,99,"A","PHOTO",0,true),"older texture denied");
        yes(!c.due(t,102,"A","PHOTO",0,true),"clock reversal denied");
        yes(!c.due(t+400_000_000L,0,"A","PHOTO",0,true),"invalid texture denied");
        yes(!c.due(t+400_000_000L,102,null,"PHOTO",0,true),"null camera denied");
        // Let the bounded fast tail expire, then prove the 250ms idle interval.
        t+=2_000_000_000L;yes(c.due(t,102,"A","PHOTO",0,false),"idle first read");c.submitted(t,102);
        yes(!c.due(t+125_000_000L,103,"A","PHOTO",0,false),"idle not forced to 8Hz");
        yes(c.due(t+250_000_000L,103,"A","PHOTO",0,false),"idle 4Hz");c.submitted(t+250_000_000L,103);
        yes(!c.due(t+260_000_000L,104,"A","PHOTO",1,false),"retap cannot bypass physical rate limit");
        yes(c.due(t+375_000_000L,104,"A","PHOTO",1,false),"tap event speeds next probe");c.submitted(t+375_000_000L,104);
        yes(c.due(t+500_000_000L,105,"A","PHOTO",2,false),"tap clear also requests quick evidence");c.submitted(t+500_000_000L,105);
        yes(c.due(t+625_000_000L,10,"B","PHOTO",2,false),"new lens has independent texture clock");c.submitted(t+625_000_000L,10);
        yes(c.due(t+750_000_000L,9,"B","MOTION",2,false),"mode ownership transition");
        // Simulated 60Hz draws: a frozen texture never manufactures confirmations.
        c=new M9AeProbeCadence1A();int accepted=0;long last=-1;
        for(int i=0;i<240;i++) {
            long now=10_000_000_000L+i*16_666_667L;
            if(c.due(now,777,"A","PHOTO",i/20,true)){c.submitted(now,777);accepted++;}
        }
        eq(accepted,1,"repeated taps cannot turn one frozen frame into fresh evidence");
        c=new M9AeProbeCadence1A();accepted=0;
        for(int i=0;i<240;i++) {
            long now=20_000_000_000L+i*16_666_667L;
            if(c.due(now,now,"A","PHOTO",i/20,true)) {
                if(last>=0)yes(now-last>=125_000_000L,"burst respects max submission rate");
                c.submitted(now,now);last=now;accepted++;
            }
        }
        yes(accepted>=29&&accepted<=32,"fast cadence under simulated 60Hz stream");
        System.out.println("SIMULATED_FAST_SUBMISSIONS_4S="+accepted);
    }
    static M9PreviewFrameState1W frame(long t,int manualIso,double userEv) {
        M9ExposurePlan1A p=new M9ExposurePlan1A(t,t/1_000_000L,t,"A","PHOTO",100,10_000_000L,
            100,10_000_000L,100,10_000_000L,userEv,0,"synthetic",0,manualIso,100);
        return new M9PreviewFrameState1W(p,t);
    }
    static boolean sample(M9PreviewMeter2D m,long t,int iso,double ev) {
        SystemClock.now=t;return m.sample(frame(t,iso,ev),t,1,2,0,3,1);
    }
    static void glContracts() {
        M9AutoExposure2D.reset();GLES30.reset();M9PreviewMeter2D m=new M9PreviewMeter2D();long t=50_000_000_000L;
        yes(sample(m,t,0,0),"actual meter queues initial probe");yes(m.isBusy(),"fence is outstanding");
        eq(GLES30.draws,11,"all eleven probes retained");eq(GLES30.reads,1,"one readback");
        GLES30.signalled=false;
        yes(!sample(m,t+125_000_000L,0,0),"busy fence cannot queue another readback");
        eq(GLES30.reads,1,"no queue accumulation");eq(GLES30.maps,0,"unsignalled fence never mapped");
        GLES30.signalled=true;
        yes(sample(m,t+160_000_000L,0,0),"completion can be followed by due probe");
        eq(GLES30.maps,1,"completed probe mapped exactly once");eq(GLES30.maxLive,1,"single in-flight readback");
        yes(!sample(m,t+170_000_000L,0,0),"completed readback still respects cadence");
        eq(GLES30.maps,2,"second completion read once");yes(!m.isBusy(),"fence released");
        eq(GLES30.boundDraw,71,"draw framebuffer restored");eq(GLES30.boundRead,72,"read framebuffer restored");
        eq(GLES30.boundPack,73,"pixel pack buffer restored");eq(GLES30.active,74,"active texture restored");
        eq(GLES30.boundTex,75,"texture binding restored");
        yes(GLES30.scissor,"scissor state restored");
        yes(!sample(m,t+300_000_000L,200,0),"manual ISO remains ineligible");
        yes(!sample(m,t+300_000_000L,0,.5),"manual EV remains ineligible");
        eq(GLES30.reads,2,"manual controls create no hidden auto probes");
        // Denied old texture cannot consume a new submission slot.
        SystemClock.now=t+400_000_000L;
        yes(!m.sample(frame(t+160_000_000L,0,0),t+160_000_000L,1,2,0,3,1),"actual GL meter rejects frozen texture");
        yes(sample(m,t+410_000_000L,0,0),"fresh texture resumes normally");
        // The latest published bracket is the actual measured synthetic buffer.
        M9AutoExposure2D.Decision d=M9AutoExposure2D.decide("A","PHOTO",t+420_000_000L,1e9,0,0,0,0,true);
        yes(d.diagnostics.contains("M9AECADENCE1A"),"cadence marker reaches real decision");
        yes(d.diagnostics.contains("aeLastProbeReadbackMs"),"readback timing reaches decision");
        // Readback timeout fails closed; no blocking wait or additional buffer is introduced.
        GLES30.signalled=false;
        yes(!sample(m,t+2_000_000_000L,0,0),"timeout disables meter as before");
        yes(!m.isBusy(),"timed-out fence cleaned up");eq(GLES30.live,0,"no leaked fence");
        eq(GLES30.blockingWaits,0,"all fence waits use zero timeout");
    }
    public static void main(String[] args) { scheduler();glContracts();System.out.println("CADENCE_ASSERTIONS="+checks); }
}
