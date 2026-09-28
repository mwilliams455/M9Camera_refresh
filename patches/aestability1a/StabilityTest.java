package com.particlesdevs.photoncamera.m9.preview;
import java.lang.reflect.Method;
import static com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D.*;

public final class StabilityTest {
    static int checks; static Method reset,apply;
    static void yes(boolean v,String m){if(!v)throw new AssertionError(m);checks++;}
    static void eq(double a,double b,String m){yes(Math.abs(a-b)<1e-9,m+": "+a+" != "+b);}
    static double step(double t,double c,boolean fresh,boolean safety,long n)throws Exception{
        return (double)apply.invoke(null,t,c,fresh,safety,n);
    }
    static void helper() throws Exception {
        reset=M9AutoExposure2D.class.getDeclaredMethod("resetAeStability1A",boolean.class);reset.setAccessible(true);
        apply=M9AutoExposure2D.class.getDeclaredMethod("applyAeStability1A",double.class,double.class,boolean.class,boolean.class,long.class);apply.setAccessible(true);
        reset.invoke(null,true);double c=0;long n=1_000_000_000L;
        double[] rise={.25,.5,.75,1.0,1.125,1.25,1.375,1.5};
        for(double e:rise){double p=c;c=step(1.5,c,true,false,n+=125_000_000L);eq(c,e,"smooth rise");yes(Math.abs(c-p)<=.25+1e-9,"no >.25 ordinary jump");}
        eq(step(.75,c,true,false,n+=125_000_000L),1.5,"small reversal requires confirmation");
        c=step(.75,c,true,false,n+=125_000_000L);eq(c,1.25,"confirmed reversal uses bounded far step");
        reset.invoke(null,true);c=1.0;
        c=step(1.25,c,true,false,n+=125_000_000L);eq(c,1.125,"near-target rise is eighth stop");
        c=step(.875,c,true,false,n+=125_000_000L);eq(c,1.125,"near reversal held once");
        c=step(.875,c,true,false,n+=125_000_000L);eq(c,1.0,"near reversal accepted at eighth stop");
        reset.invoke(null,true);c=1.25;
        c=step(0,c,true,false,n+=125_000_000L);eq(c,1.0,"large reversal bypasses confirmation but stays bounded");
        c=step(0,c,true,true,n+=125_000_000L);eq(c,0,"hard safety release remains immediate");
    }
    static Stats[] darkBracket(){
        Stats[] a=new Stats[11];
        for(int i=0;i<11;i++){int m=Math.min(255,15+i*10);a[i]=new Stats(m,.8,0,0,m,m,100,.8,0,0,0,0);}
        return a;
    }
    static void transientHold(){
        M9AutoExposure2D.reset();long s=10_000_000_000L;
        M9AutoExposure2D.publish(new Sample("c","PHOTO",s,s,s,100,darkBracket()));
        Decision d=M9AutoExposure2D.decide("c","PHOTO",s+10_000_000L,100,0,0,0,0,true);
        yes(d.appliedEv>0,"valid dark scene establishes positive exposure");
        double held=d.appliedEv;
        Decision h=M9AutoExposure2D.decide("c","PHOTO",s+100_000_000L,200,0,0,0,0,true);
        eq(h.appliedEv,held,"brief energy mismatch holds last good exposure");
        yes(h.reason.equals("rendered_meter_transient_hold"),"transient hold reason");
        yes(h.diagnostics.contains("M9AESTABILITY1A"),"stability marker emitted");
        yes(h.diagnostics.contains("aeTransientMeterHold"),"hold diagnostic emitted");
        Decision expired=M9AutoExposure2D.decide("c","PHOTO",s+500_000_000L,200,0,0,0,0,true);
        yes(!expired.reason.equals("rendered_meter_transient_hold"),"hold expires");
    }
    public static void main(String[] args)throws Exception{
        helper();transientHold();System.out.println("AESTABILITY_ASSERTIONS="+checks);
    }
}
