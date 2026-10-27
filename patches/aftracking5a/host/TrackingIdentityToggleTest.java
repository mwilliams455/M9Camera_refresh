import com.particlesdevs.photoncamera.control.tracking.TrackingTogglePolicy;
public final class TrackingIdentityToggleTest {
 static int n;
 static void ok(boolean b,String why){n++;if(!b)throw new AssertionError(why);}
 static void check(String k,boolean val,boolean init,boolean track,boolean subject,boolean noChildren,boolean noIdentity){
   TrackingTogglePolicy.Correction c=TrackingTogglePolicy.onPersist(k,val,init);
   ok(c.enableTracking==track,"parent "+k);ok(c.enableSubject==subject,"subject "+k);
   ok(c.disableDependents==noChildren,"children "+k);
   ok(c.disableIdentity==noIdentity,"identity "+k);
 }
 public static void main(String[] args){
   check(TrackingTogglePolicy.IDENTITY,true,false,true,true,false,false);
   check(TrackingTogglePolicy.IDENTITY,true,true,true,true,false,false);
   check(TrackingTogglePolicy.IDENTITY,false,false,false,false,false,false);
   check(TrackingTogglePolicy.SUBJECT,false,false,false,false,false,true);
   check(TrackingTogglePolicy.SUBJECT,false,true,false,false,false,false);
   check(TrackingTogglePolicy.SUBJECT,true,false,true,false,false,false);
   check(TrackingTogglePolicy.TRACKING,false,false,false,false,true,false);
   check(TrackingTogglePolicy.TRACKING,false,true,false,false,false,false);
   check(TrackingTogglePolicy.PREDICTIVE,true,false,true,false,false,false);
   check("other",false,false,false,false,false,false);
   System.out.println("PASS " +n+" tracking dependency assertions");
 }
}
