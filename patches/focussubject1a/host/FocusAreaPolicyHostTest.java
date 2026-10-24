import com.particlesdevs.photoncamera.control.subject.SubjectFocusPolicy;
import com.particlesdevs.photoncamera.control.subject.FocusAreaPolicy;
import java.util.Collections;

public final class FocusAreaPolicyHostTest {
    static void check(boolean pass) { if(!pass)throw new AssertionError(); }
    static void close(float a,float b) { check(Math.abs(a-b)<1e-6); }
    public static void main(String[] args) {
        FocusAreaPolicy.Rect r = FocusAreaPolicy.region(FocusAreaPolicy.Mode.SPOT,.02f,.99f,null,.1f,.1f);
        check(r!=null);close(r.left,0f);close(r.bottom,1f);close(r.width(),.07f);
        r = FocusAreaPolicy.region(FocusAreaPolicy.Mode.EXPAND_SPOT,.5f,.5f,null,.1f,.1f);
        close(r.width(),.18f);close(r.centerX(),.5f);
        r = FocusAreaPolicy.region(FocusAreaPolicy.Mode.CUSTOM,.7f,.3f,null,.9f,.001f);
        close(r.width(),.5f);close(r.height(),.05f);
        check(FocusAreaPolicy.region(FocusAreaPolicy.Mode.WIDE,.5f,.5f,null,.1f,.1f)==null);
        check(FocusAreaPolicy.region(FocusAreaPolicy.Mode.CUSTOM,Float.NaN,.5f,null,.3f,.3f)==null);
        SubjectFocusPolicy p=new SubjectFocusPolicy();p.beginSession(9);
        SubjectFocusPolicy.Face f=new SubjectFocusPolicy.Face(1,.1f,.1f,.4f,.5f,Float.NaN,Float.NaN,Float.NaN,Float.NaN);
        SubjectFocusPolicy.Target target=p.update(9,100,100,Collections.singletonList(f),SubjectFocusPolicy.Kind.HUMAN_EYE);
        check(target!=null);
        r=FocusAreaPolicy.region(FocusAreaPolicy.Mode.WIDE,Float.NaN,Float.NaN,target,.1f,.1f);
        check(r!=null);close(r.centerX(),target.x);close(r.centerY(),target.y);
        System.out.println("PASS: FocusAreaPolicyHostTest (all four modes, edge clipping, subject handoff)");
    }
}
