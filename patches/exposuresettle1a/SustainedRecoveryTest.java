package com.particlesdevs.photoncamera.m9.preview;

import java.util.*;
import java.lang.reflect.*;
import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D.*;

/** Complete production controller; synthetic matched probes reproduce the recorded fast rebound. */
public final class SustainedRecoveryTest {
    static int checks;
    static long now=20_000_000_000L;
    static String mode;
    static boolean candidate;
    static void yes(boolean b,String m){checks++;if(!b)throw new AssertionError(m);}
    static void eq(double a,double b,String m){yes(Math.abs(a-b)<1e-8,m+": "+a+" != "+b);}
    static boolean armed()throws Exception {
        Field f=M9AutoExposure2D.class.getDeclaredField("recoveryArmed");f.setAccessible(true);return f.getBoolean(null);
    }
    static double read(){return M9AutoExposure2D.decide("T",mode,now+1,1,0,0,0,0,true).appliedEv;}
    static double step(Stats[] s){now+=250_000_000L;M9AutoExposure2D.publish(new Sample("T",mode,now,now,now,1,s));return read();}
    static Stats[] safe(){
        Stats[] original=SubjectHeadroomTest.scene(0),delayed=new Stats[original.length];
        // Same neutral scene; readability is reached one exposure step later.
        // This creates the recorded +2 EV target while preserving monotonic probes.
        delayed[0]=original[0];for(int i=1;i<delayed.length;i++)delayed[i]=original[i-1];return delayed;
    }
    static Stats[] unsafe(){return SubjectHeadroomTest.scene(2);}
    static void cut(){
        M9AutoExposure2D.reset();double v=0;
        for(int i=0;i<12;i++)v=step(safe());
        eq(v,2,"same settled mapped target");eq(step(unsafe()),.5,"same immediate headroom reduction");
    }
    static void rebound()throws Exception {
        cut();double last=.5;List<Double> values=new ArrayList<>();
        for(int i=0;i<10;i++){
            double v=step(safe());values.add(v);
            if(candidate)yes(v-last<=.25+1e-9,"every recovery rise is bounded, including after first confirmed step");
            for(int r=0;r<20;r++)eq(read(),v,"duplicate callback cannot advance recovery");
            if(candidate && v<2)yes(armed(),"guard retained through entire recovery");
            last=v;
        }
        double[] expected=candidate?new double[]{.5,.5,.5,.75,1,1.25,1.5,1.75,2,2}
                :new double[]{.5,.75,1.5,2,2,2,2,2};
        for(int i=0;i<values.size();i++)eq(values.get(i),expected[i],"rebound trajectory");
        if(candidate)yes(!armed(),"settled target eventually releases guard");
        eq(step(unsafe()),.5,"later restrictive probe still cuts immediately");
        System.out.println(mode+" rebound "+values);
    }
    static void repeatedBursts(){
        cut();List<Double> peaks=new ArrayList<>();
        for(int cycle=0;cycle<10;cycle++){
            double peak=.5;
            for(int i=0;i<3;i++)peak=Math.max(peak,step(safe()));
            peaks.add(peak);eq(peak,candidate?.5:1.5,"three-probe permissive burst peak");
            eq(step(unsafe()),.5,"recurrent safety bound never delayed");
        }
        System.out.println(mode+" repeated three-probe peaks "+peaks);
    }
    static void settledWindow()throws Exception {
        cut();
        // Reach a low ordinary target quickly: reaching it alone must not restore fast acquisition.
        for(int i=0;i<4;i++){
            now+=10_000_000L;
            M9AutoExposure2D.publish(new Sample("T",mode,now,now,now,1,RecoveryTest.ordinary()));
            M9AutoExposure2D.decide("T",mode,now+1,1,0,0,0,.5,true);
        }
        if(candidate)yes(armed(),"four rapid samples cannot replace 750ms stability");
        long submitted=now;
        for(int i=0;i<8;i++){
            now+=100_000_000L;
            M9AutoExposure2D.decide("T",mode,now+1,1,0,0,0,.5,true);
        }
        if(candidate)yes(armed(),"wall time and duplicate evidence cannot complete settled window");
        now=submitted+900_000_000L;
        M9AutoExposure2D.publish(new Sample("T",mode,now,now,now,1,RecoveryTest.ordinary()));
        M9AutoExposure2D.decide("T",mode,now+1,1,0,0,0,.5,true);
        if(candidate)yes(!armed(),"fresh evidence can finish settled time window");
    }
    static void gap()throws Exception {
        cut();step(safe());step(safe());step(safe());eq(step(safe()),.75,"first confirmed step before gap");
        if(candidate)yes(armed(),"guard active before bridge gap");
        double bridge=M9AutoExposure2D.decide("T",mode,now+100_000_000L,Math.pow(2,.3),0,0,0,0,true).appliedEv;
        eq(bridge,.45,"existing energy-capped bridge retained");
        double next=step(safe());eq(next,candidate?.75:1.5,"gap breaks rising confirmation without erasing guard");
    }
    public static void main(String[] args)throws Exception {
        candidate=Boolean.parseBoolean(args[0]);
        for(String m:new String[]{"PHOTO","MOTION"}){mode=m;rebound();repeatedBursts();settledWindow();gap();}
        System.out.println("SUSTAINED_RECOVERY_ASSERTIONS "+checks+" PASS");
    }
}
