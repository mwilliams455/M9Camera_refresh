package com.particlesdevs.photoncamera.m9.preview;
import java.lang.reflect.Method;

public final class TargetStabilityTest {
    private static int checks;
    private static Method reset,stabilize;
    private static void yes(boolean v,String m){if(!v)throw new AssertionError(m);checks++;}
    private static void eq(double a,double b,String m){yes(Math.abs(a-b)<1e-9,m+": "+a+" != "+b);}
    private static double step(double raw,double current,boolean fresh,boolean safety)throws Exception {
        return (double)stabilize.invoke(null,raw,current,fresh,safety);
    }
    private static void reset()throws Exception{reset.invoke(null,true);}
    public static void main(String[] args)throws Exception {
        reset=M9AutoExposure2D.class.getDeclaredMethod("resetTargetStability1A",boolean.class);
        stabilize=M9AutoExposure2D.class.getDeclaredMethod("stabilizePhotographicTarget1A",
                double.class,double.class,boolean.class,boolean.class);
        reset.setAccessible(true);stabilize.setAccessible(true);

        reset();
        eq(step(1.0,0,true,false),1.0,"initial target accepted immediately");
        eq(step(1.25,.25,true,false),1.0,"quarter-stop jitter held sample 1");
        eq(step(1.25,.50,true,false),1.0,"quarter-stop jitter held sample 2");
        eq(step(1.25,.75,true,false),1.25,"quarter-stop persists on sample 3");

        eq(step(1.0,1.0,true,false),1.25,"small reverse held sample 1");
        eq(step(1.25,1.0,true,false),1.25,"return to accepted cancels pending change");

        eq(step(1.75,1.25,true,false),1.25,"half-stop change held sample 1");
        eq(step(1.75,1.25,true,false),1.75,"half-stop accepted sample 2");

        eq(step(.75,1.75,true,false),.75,"one-stop scene transition bypasses persistence");
        eq(step(.25,.75,true,true),.25,"hard safety reduction is immediate");
        eq(step(.50,.25,false,false),.25,"no fresh sample cannot move target");

        reset();
        eq(step(.50,0,true,false),.50,"new ownership starts from new target");
        eq(step(.75,.25,true,false),.50,"new small change waits");
        eq(step(1.50,.25,true,false),1.50,"large transition replaces pending small change");

        reset();
        eq(step(1.0,0,true,false),1.0,"second sequence initial");
        eq(step(1.25,.25,true,false),1.0,"oscillation A held");
        eq(step(.75,.50,true,false),1.0,"opposite jitter replaces pending but holds accepted");
        eq(step(1.25,.75,true,false),1.0,"repeated alternating jitter never accumulates");

        System.out.println("AETARGETSTABILITY_ASSERTIONS="+checks);
    }
}
