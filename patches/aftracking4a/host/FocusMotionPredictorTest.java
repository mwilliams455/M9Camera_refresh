import com.particlesdevs.photoncamera.control.tracking.FocusMotionPredictor;
import com.particlesdevs.photoncamera.control.tracking.FocusMotionPredictor.Source;

public final class FocusMotionPredictorTest {
  static int checks;
  private static void yes(boolean test){checks++;if(!test)throw new AssertionError("check "+checks);}
  private static void near(float expected,float actual){yes(Math.abs(expected-actual)<.0001f);}
  public static void main(String[] ignored) {
    FocusMotionPredictor p=new FocusMotionPredictor();p.begin(1);
    FocusMotionPredictor.Aim a=p.observe(1,1000,1030,.2f,.3f,Source.PATCH);
    yes(!a.predicted);near(.2f,a.x);near(.3f,a.y);
    a=p.observe(1,1100,1140,.26f,.3f,Source.PATCH);
    yes(a.predicted);yes(a.x>.26f);yes(a.x<.306f);near(.3f,a.y);yes(a.leadMs<=140);
    a=p.observe(1,1200,1240,.34f,.3f,Source.PATCH);
    yes(a.predicted);yes(a.x>.34f);yes(a.x<=.385001f);
    a=p.observe(1,1300,1340,.34f,.301f,Source.PATCH);
    yes(!a.predicted);near(.34f,a.x);
    a=p.observe(1,1400,1440,.34f,.301f,Source.PATCH);
    yes(!a.predicted);
    a=p.observe(1,1500,1540,.36f,.3f,Source.PATCH);
    yes(a.predicted);yes(a.x>.36f);
    p.hold(1);
    a=p.observe(1,1600,1630,.37f,.3f,Source.PATCH);
    yes(!a.predicted);near(.37f,a.x);
    a=p.observe(1,1750,1780,.39f,.3f,Source.SUBJECT);
    yes(!a.predicted);near(.39f,a.x);
    a=p.observe(1,1900,1930,.42f,.3f,Source.SUBJECT);
    yes(a.predicted);yes(a.x>.42f);
    a=p.observe(1,2050,2600,.44f,.3f,Source.SUBJECT);
    yes(!a.predicted);near(.44f,a.x); // old detector results cannot produce lead
    a=p.observe(1,2150,2200,.46f,.3f,Source.SUBJECT);
    yes(!a.predicted); // stale invalidation removed old velocity
    a=p.observe(2,2300,2340,.5f,.5f,Source.PATCH);
    yes(!a.predicted);near(.5f,a.x); // wrong session rejected
    p.begin(2);
    a=p.observe(2,2300,2340,.5f,.5f,Source.PATCH);
    yes(!a.predicted);
    a=p.observe(2,2300,2340,.55f,.55f,Source.PATCH);
    yes(!a.predicted);near(.55f,a.x); // duplicate timestamp rejected
    a=p.observe(2,2400,2420,.95f,.7f,Source.PATCH);
    yes(!a.predicted);near(.95f,a.x); // huge jump no leading
    a=p.observe(2,2500,2550,1f,.75f,Source.PATCH);
    yes(a.x<=1f);yes(a.y<=1f);
    a=p.observe(2,2600,2650,Float.NaN,.4f,Source.PATCH);
    yes(!a.predicted);near(.5f,a.x); // invalid input has harmless centre fallback
    p.begin(3);
    a=p.observe(3,1000,1010,.1f,.1f,Source.PATCH);
    a=p.observe(3,1020,1030,.12f,.1f,Source.PATCH);
    yes(!a.predicted); // too-short time gap
    a=p.observe(3,2000,2010,.15f,.1f,Source.PATCH);
    yes(!a.predicted); // too-long time gap
    a=p.observe(3,2100,2110,.2f,.1f,Source.PATCH);
    yes(a.predicted);
    p.hold(99); // different epoch cannot change state
    a=p.observe(3,2200,2220,.25f,.1f,Source.PATCH);
    yes(a.predicted);
    a=p.observe(3,2300,2300,.28f,.08f,Source.SUBJECT);
    yes(!a.predicted); // source change resets velocity
    System.out.println("PASS " + checks + " motion prediction safety checks");
  }
}
