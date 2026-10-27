import com.particlesdevs.photoncamera.control.tracking.TrackingTogglePolicy;
public final class TrackingTogglePolicyTest {
  static int checks;
  static void yes(boolean ok){checks++;if(!ok)throw new AssertionError("check "+checks);}
  static void expect(String k, boolean v, boolean init, boolean parent,boolean children){
    TrackingTogglePolicy.Correction d=TrackingTogglePolicy.onPersist(k,v,init);
    yes(d.enableTracking==parent);yes(d.disableDependents==children);
  }
  public static void main(String[] args){
    expect(TrackingTogglePolicy.SUBJECT,true,false,true,false);
    expect(TrackingTogglePolicy.SUBJECT,true,true,true,false);
    expect(TrackingTogglePolicy.SUBJECT,false,false,false,false);
    expect(TrackingTogglePolicy.PREDICTIVE,true,false,true,false);
    expect(TrackingTogglePolicy.PREDICTIVE,true,true,true,false);
    expect(TrackingTogglePolicy.PREDICTIVE,false,false,false,false);
    expect(TrackingTogglePolicy.TRACKING,false,false,false,true);
    expect(TrackingTogglePolicy.TRACKING,false,true,false,false);
    expect(TrackingTogglePolicy.TRACKING,true,false,false,false);
    expect("other_pref",false,false,false,false);
    System.out.println("PASS " + checks + " preference dependency checks");
  }
}
