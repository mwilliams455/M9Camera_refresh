import com.particlesdevs.photoncamera.control.subject.FocusControlPolicy;

public final class FocusControlPolicyTest {
    private static void check(boolean yes,String why){if(!yes)throw new AssertionError(why);}
    private static void near(float a,float b){check(Math.abs(a-b)<.0001f,a+" not "+b);}
    public static void main(String[] x) {
        FocusControlPolicy p=new FocusControlPolicy();p.beginSession(17L);
        check(p.mode()==FocusControlPolicy.Mode.WIDE,"wide default");
        check(p.mayAcquire(.9f,.9f,1f,1f),"wide searches frame");
        FocusControlPolicy.Region a=p.area(.9f,.8f,.2f,.1f);
        near(a.width,.2f);near(a.height,.1f);
        p.configure(FocusControlPolicy.Mode.SPOT,.20f,.18f);
        a=p.area(Float.NaN,Float.NaN,0,0);
        near(a.width,.07f);near(a.x,.5f);
        check(!p.mayAcquire(.01f,.01f,.12f,.12f),"spot must not auto-steal distant subjects");
        check(p.mayAcquire(.46f,.46f,.54f,.54f),"spot accepts local face");
        check(p.tap(17L,.99f,.02f),"tap anchors region");
        a=p.area(.99f,.02f,0,0);
        near(a.right(),1f);near(a.top(),0f);
        check(!p.tap(18L,.3f,.4f),"stale lens tap rejected");
        p.configure(FocusControlPolicy.Mode.CUSTOM,.33f,.16f);
        a=p.area(Float.NaN,Float.NaN,0,0);
        near(a.width,.33f);near(a.height,.16f);
        p.configure(FocusControlPolicy.Mode.CUSTOM,99f,-99f);
        a=p.area(Float.NaN,Float.NaN,0,0);
        near(a.width,.5f);near(a.height,.05f);

        p.configure(FocusControlPolicy.Mode.EXPAND_SPOT,.20f,.20f);
        a=p.area(.5f,.5f,0,0);near(a.width,.07f);
        p.observeAf(17L,FocusControlPolicy.AF_PASSIVE_UNFOCUSED,1000);
        check(!p.expanded(),"first failed AF estimate cannot expand prematurely");
        p.observeAf(17L,FocusControlPolicy.AF_PASSIVE_UNFOCUSED,1600);
        check(!p.expanded(),"600ms still spot");
        p.observeAf(17L,FocusControlPolicy.AF_PASSIVE_UNFOCUSED,1690);
        check(p.expanded(),"AF unable to focus triggers expanded region");
        near(p.area(.5f,.5f,0,0).width,.19f);
        check(p.afStatus(1800)==FocusControlPolicy.FocusStatus.HAL_UNFOCUSED,
                "HAL reports not focused");
        p.observeAf(17L,FocusControlPolicy.AF_PASSIVE_FOCUSED,1850);
        check(!p.expanded(),"successful passive AF retracts to spot");
        near(p.area(.5f,.5f,0,0).width,.07f);
        check(p.afStatus(1900)==FocusControlPolicy.FocusStatus.HAL_FOCUSED,
                "focus feedback needs HAL state");
        check(p.afStatus(2600)==FocusControlPolicy.FocusStatus.UNKNOWN,
                "stale HAL state must not claim focused");
        p.observeAf(16L,FocusControlPolicy.AF_FOCUSED_LOCKED,2650);
        check(p.afStatus(2700)==FocusControlPolicy.FocusStatus.UNKNOWN,
                "previous lens state ignored");
        p.beginSession(18L);
        check(p.afStatus(10000)==FocusControlPolicy.FocusStatus.UNKNOWN,"session clears AF state");
        check(!p.pinned(),"new session clears tap pin");
        check(p.tap(18L,.4f,.3f),"new tap valid");
        p.releasePin(18L);
        check(!p.pinned(),"pin release");
        check(FocusControlPolicy.parseMode("Expand Spot")==FocusControlPolicy.Mode.EXPAND_SPOT,
                "human-readable mode parsed");
        check(FocusControlPolicy.parseMode("nonsense")==FocusControlPolicy.Mode.WIDE,
                "bad settings fail to default wide");
        System.out.println("PASS FocusControlPolicyTest (4 areas, subject scope, tap/lens, AF feedback and expansion)");
    }
}
