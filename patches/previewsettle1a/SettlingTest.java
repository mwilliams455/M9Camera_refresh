import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D;
import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D.*;
import com.particlesdevs.photoncamera.m9.preview.M9TapMeter1A;
import java.lang.reflect.Field;
import java.util.Arrays;

/** Synthetic reference probes exercise the actual complete Auto decision path. */
public final class SettlingTest {
    static int checks;
    static long now=2_000_000_000L;
    static String mode="PHOTO";
    static boolean candidate;
    static Stats[] clear() {
        Stats[] s=new Stats[11];
        for(int i=0;i<s.length;i++)s[i]=new Stats(90+i*3,.05,.01,.001,
                100+i*3,70+i*3,140+i*3,.05,.01,.01,.001,.001);
        return s;
    }
    static Stats[] highlights() {
        Stats[] s=clear();
        for(int i=1;i<s.length;i++)s[i]=new Stats(160,.01,.65,.6,
                160,120,255,.01,.7,.6,.6,.6);
        return s;
    }
    static void eq(double actual,double expected,String message) {
        checks++;if(Math.abs(actual-expected)>1e-9)
            throw new AssertionError(message+": "+actual+" != "+expected);
    }
    static void yes(boolean ok,String message) { checks++;if(!ok)throw new AssertionError(message); }
    static void publish(Stats[] s) {
        now+=250_000_000L;
        M9AutoExposure2D.publish(new Sample("0",mode,now,now,now,1,s));
    }
    static double decide(double legacy) {
        return M9AutoExposure2D.decide("0",mode,now+1,1,0,0,0,legacy,true).appliedEv;
    }
    static double step(double legacy) {publish(clear());return decide(legacy);}
    static void start() {
        M9AutoExposure2D.reset();
        eq(step(.75),.75,"initial valid baseline");
    }
    static int confirmations() throws Exception {
        Field f=M9AutoExposure2D.class.getDeclaredField("lowerTargetConfirmations");
        f.setAccessible(true);return f.getInt(null);
    }
    static double[] run(double target,int n) {
        start();double[] out=new double[n];double previous=.75;
        for(int i=0;i<n;i++) {
            out[i]=step(target);
            yes(out[i]<=previous+1e-9&&out[i]>=target-1e-9,"monotonic and no overshoot");
            yes(previous-out[i]<=.250000001,"ordinary step remains bounded");
            eq(decide(target),out[i],"same probe cannot step twice");
            previous=out[i];
        }
        return out;
    }
    static void sequence() {
        double[] out=run(0,8);
        double[] expected=candidate?new double[]{.75,.5,.25,0,0,0,0,0}
                :new double[]{.75,.5,.5,.25,.25,0,0,0};
        for(int i=0;i<out.length;i++)eq(out[i],expected[i],"confirmed transition "+i);
        System.out.println("{\"mode\":\""+mode+"\",\"target\":0,\"trajectoryEv\":"+Arrays.toString(out)+"}");
        out=run(-.5,12);
        eq(out[candidate?5:9],-.5,"negative legacy target still reached");
    }
    static void noiseAndChanges() {
        start();
        for(int i=0;i<40;i++)eq(step(i%2==0?0:.25),.75,"alternating lower targets remain rejected");
        eq(step(.5),.75,"changed target starts confirmation");
        eq(step(.5),.5,"one quarter-stop target has identical parent behavior");
        start();eq(step(0),.75,"first lower sample held");eq(step(0),.5,"second confirms");
        eq(step(.25),.5,"new lower target needs confirmation again");
        eq(step(.25),.25,"new target reached without overshoot");
        start();step(0);step(0);
        eq(step(.5),.5,"return to current target stops transition");
        eq(step(0),.5,"subsequent lower target must confirm again");
        eq(step(0),.25,"second subsequent lower sample confirms");
        start();step(0);step(0);
        eq(step(.75),.75,"existing positive rise unchanged");
        eq(step(0),.75,"rise cancels pending lower target");
    }
    static void boundaries() throws Exception {
        start();step(0);step(0);
        publish(highlights());eq(decide(0),0,"new highlight risk releases immediately");
        start();step(0);step(0);
        now+=M9AutoExposure2D.MAX_AGE_NS+1;
        eq(decide(.5),0,"stale positive baseline remains suppressed");
        if(candidate)eq(confirmations(),0,"stale evidence clears confirmed transition");
        start();step(0);step(0);
        M9AutoExposure2D.invalidate("test");eq(decide(-.25),-.25,"invalid fallback unchanged");
        if(candidate)eq(confirmations(),0,"invalid evidence clears confirmation");
        start();step(0);step(0);
        eq(M9AutoExposure2D.decide("0",mode,now+1,1,-.7,0,0,0,true).appliedEv,.5,
                "manual EV preserves held Auto baseline");
        if(candidate) {eq(confirmations(),0,"manual EV clears transition");eq(step(0),.5,"return from EV reconfirms");}
        for(int what=0;what<3;what++) {
            start();step(0);step(0);
            eq(M9AutoExposure2D.decide("0",mode,now+1,1,0,what==0?10_000_000:0,
                    what==1?100:0,0,what!=2).appliedEv,0,"manual/ineligible bypass unchanged");
            eq(confirmations(),0,"manual/ineligible reset");
        }
        start();step(0);step(0);
        eq(M9AutoExposure2D.decide("1",mode,now+1,1,0,0,0,.5,true).appliedEv,0,"camera owner boundary");
        eq(confirmations(),0,"camera reset");
        start();step(0);step(0);
        eq(M9AutoExposure2D.decide("0",mode.equals("PHOTO")?"MOTION":"PHOTO",now+1,1,0,0,0,.5,true).appliedEv,0,"mode owner boundary");
        eq(confirmations(),0,"mode reset");
        start();step(0);step(0);
        M9TapMeter1A.configure("0",mode,now,320,240,new int[]{0,0,320,240},new float[]{1,0,0,1},false);
        yes(M9TapMeter1A.choose(160,120,now),"tap selection created");
        M9TapMeter1A.clear("test_epoch");
        eq(step(0),.5,"tap epoch cancels transition");
        start();step(0);step(0);M9AutoExposure2D.reset();eq(step(0),0,"surface/Auto reset");
        start();step(0);step(0);
        eq(M9AutoExposure2D.decide("0",mode,now+1,2,0,0,0,.5,true).appliedEv,0,"reference energy mismatch fallback");
        if(candidate)eq(confirmations(),0,"foreign reference clears confirmation");
        start();step(0);step(0);
        now+=250_000_000L;
        M9AutoExposure2D.publish(new Sample("0",mode,now,now-150_000_001L,now,1,clear()));
        eq(decide(.5),0,"texture/result mismatch fallback");
        if(candidate)eq(confirmations(),0,"mismatched frame clears confirmation");
    }
    public static void main(String[] args) throws Exception {
        candidate=Boolean.parseBoolean(args[0]);
        for(String m:new String[]{"PHOTO","MOTION"}) {mode=m;sequence();noiseAndChanges();boundaries();}
        System.out.println("{\"assertions\":"+checks+",\"status\":\"PASS\"}");
    }
}
