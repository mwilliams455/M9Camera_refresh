package com.particlesdevs.photoncamera.m9.preview;
import java.util.*;
import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D.*;

/** Temporal scenarios through the complete production controller, not a copied algorithm. */
public final class RecoveryTest {
    static int checks;
    static long now=5_000_000_000L;
    static String mode="PHOTO";
    static boolean candidate;
    static void eq(double a,double b,String msg) {
        checks++;if(Math.abs(a-b)>1e-9)throw new AssertionError(msg+": "+a+" != "+b);
    }
    static void yes(boolean b,String msg) {checks++;if(!b)throw new AssertionError(msg);}
    static Stats[] ordinary() {
        Stats[] s=new Stats[11];
        for(int i=0;i<s.length;i++)s[i]=new Stats(90+i*3,.05,.01,.001,
                100+i*3,70+i*3,140+i*3,.05,.01,.01,.001,.001);
        return s;
    }
    static Stats[] blocked() {
        Stats[] s=ordinary();
        for(int i=1;i<s.length;i++)s[i]=new Stats(160,.01,.65,.6,
                160,120,255,.01,.7,.6,.6,.6);
        return s;
    }
    static void publish(Stats[] s) {
        now+=200_000_000L;
        M9AutoExposure2D.publish(new Sample("T",mode,now,now,now,1,s));
    }
    static double read(double legacy) {
        return M9AutoExposure2D.decide("T",mode,now+1,1,0,0,0,legacy,true).appliedEv;
    }
    static double step(Stats[] s,double legacy) {publish(s);return read(legacy);}
    static void cut() {
        M9AutoExposure2D.reset();
        eq(step(ordinary(),.75),.75,"ordinary baseline");
        eq(step(blocked(),.75),0,"highlight cut is immediate");
    }
    static void flickerAndRecovery() {
        cut();
        List<Double> trace=new ArrayList<>();
        for(int i=0;i<8;i++) {
            double v=step(ordinary(),.75);trace.add(v);
            eq(v,candidate?0:.25,"isolated permissive probe after a safety cut");
            for(int j=0;j<8;j++)eq(read(.75),v,"duplicate read cannot confirm recovery");
            eq(step(blocked(),.75),0,"intervening restrictive probe breaks recovery");
        }
        System.out.println(mode+" alternating recovery EV "+trace);
        List<Double> stable=new ArrayList<>();
        for(int i=0;i<7;i++)stable.add(step(ordinary(),.75));
        double[] expected=candidate?new double[]{0,.25,.5,.75,.75,.75,.75}
                :new double[]{.25,.5,.75,.75,.75,.75,.75};
        for(int i=0;i<7;i++)eq(stable.get(i),expected[i],"stable recovery trajectory");
        System.out.println(mode+" stable recovery EV "+stable);
        // A confirmed rebound must never delay a new safety reduction.
        eq(step(blocked(),.75),0,"second safety cut remains immediate");
    }
    static void targetChanges() {
        cut();step(ordinary(),.75);
        eq(step(ordinary(),0),candidate?0:.25,"non-rising target breaks confirmation");
        eq(step(ordinary(),.75),candidate?0:.5,"new evidence starts over");
        cut();step(ordinary(),.10);
        eq(step(ordinary(),.75),candidate?.10:.35,"first recovery supported by both probes");
        cut();step(ordinary(),.75);
        eq(step(ordinary(),.10),candidate?.10:.25,"second lower target bounds recovery");
        // A normal target reduction with unchanged headroom should not arm recovery.
        M9AutoExposure2D.reset();step(ordinary(),.75);
        for(int i=0;i<5;i++)step(ordinary(),0);
        eq(step(ordinary(),.75),.25,"ordinary settling retains existing positive response");
    }
    static void fieldMap() {
        Stats[] safe=SubjectHeadroomTest.scene(0),unsafe=SubjectHeadroomTest.scene(2);
        M9AutoExposure2D.reset();
        double initial=step(safe,0);
        yes(initial>0,"normal multifield acquisition remains immediate");
        double high=initial;
        for(int i=0;i<12;i++)high=step(safe,0);
        eq(high,1.75,"same inherited subject target");
        eq(step(unsafe,0),.5,"regional near-white limit still releases immediately");
        List<Double> trace=new ArrayList<>();
        for(int i=0;i<6;i++) {
            double v=step(safe,0);trace.add(v);
            if(candidate)eq(v,.5,"one permissive mapped probe cannot rebound");
            else yes(v>.5,"parent reproduces mapped rebound");
            eq(step(unsafe,0),.5,"mapped protective limit maintained");
        }
        System.out.println(mode+" multifield alternating recovery EV "+trace);
        double v=step(safe,0);
        if(candidate)eq(v,.5,"mapped first fresh recovery probe held");
        v=step(safe,0);
        if(candidate)eq(v,.75,"mapped first recovery uses quarter-stop");
        for(int i=0;i<12;i++)v=step(safe,0);
        eq(v,high,"stable field-map target unchanged");
    }
    static void boundaries() {
        for(int which=0;which<7;which++) {
            cut();step(ordinary(),.75);
            switch(which) {
                case 0: M9AutoExposure2D.reset();break;
                case 1: M9AutoExposure2D.invalidate("test");read(0);break;
                case 2: now+=M9AutoExposure2D.MAX_AGE_NS+1;read(0);break;
                case 3: M9AutoExposure2D.decide("T",mode,now+1,1,-.7,0,0,0,true);break;
                case 4: M9AutoExposure2D.decide("T",mode,now+1,1,0,10_000_000L,0,0,true);break;
                case 5: M9AutoExposure2D.decide("T",mode,now+1,1,0,0,100,0,true);break;
                case 6: M9AutoExposure2D.decide("T",mode,now+1,1,0,0,0,0,false);break;
            }
            double v=step(ordinary(),.75);
            yes(v>0,"boundary clears pending recovery: "+which);
        }
        cut();step(ordinary(),.75);
        M9AutoExposure2D.decide("OTHER",mode,now+1,1,0,0,0,0,true);
        yes(step(ordinary(),.75)>0,"camera owner clears recovery");
        cut();step(ordinary(),.75);
        M9AutoExposure2D.decide("T",mode.equals("PHOTO")?"MOTION":"PHOTO",now+1,1,0,0,0,0,true);
        yes(step(ordinary(),.75)>0,"mode owner clears recovery");
        cut();step(ordinary(),.75);
        M9TapMeter1A.configure("T",mode,now,320,240,new int[]{0,0,320,240},new float[]{1,0,0,1},false);
        yes(M9TapMeter1A.choose(160,120,now),"tap selection");
        M9TapMeter1A.clear("test_epoch");
        yes(step(ordinary(),.75)>0,"tap epoch clears recovery");
    }
    public static void main(String[] args) {
        candidate=Boolean.parseBoolean(args[0]);
        for(String m:new String[]{"PHOTO","MOTION"}) {
            mode=m;flickerAndRecovery();targetChanges();fieldMap();boundaries();
        }
        System.out.println("RECOVERY_ASSERTIONS "+checks+" PASS");
    }
}
