import com.particlesdevs.photoncamera.control.subject.SubjectFocusPolicy;
import java.util.Arrays;
import java.util.Collections;

/** JDK-only regression gate; run with -ea. */
public final class SubjectFocusPolicyHostTest {
    private static final SubjectFocusPolicy.Face A = new SubjectFocusPolicy.Face(
            7, .2f,.1f,.6f,.7f,.3f,.25f,.5f,.25f);
    private static final SubjectFocusPolicy.Face B = new SubjectFocusPolicy.Face(
            8, .55f,.2f,.9f,.8f,.65f,.34f,.82f,.34f);
    private static SubjectFocusPolicy.Target update(SubjectFocusPolicy p,
            long t, long now, SubjectFocusPolicy.Kind mode,
            SubjectFocusPolicy.Face... faces) {
        return p.update(10L, t, now, Arrays.asList(faces), mode);
    }
    private static void near(float a,float b) {
        if (Math.abs(a-b)>1e-5) throw new AssertionError(a+" != "+b);
    }
    public static void main(String[] args) {
        SubjectFocusPolicy p=new SubjectFocusPolicy();
        p.beginSession(10L);
        long t=1_000_000_000L;
        SubjectFocusPolicy.Target one=update(p,t,t,SubjectFocusPolicy.Kind.HUMAN_EYE,A);
        assert one!=null && one.id==7 && one.eyeLandmarkFound;
        near(one.x,.5f); near(one.y,.25f);
        assert update(p,t,t+1,SubjectFocusPolicy.Kind.HUMAN_EYE,A)==null;
        assert p.update(11,t+10,t+10,Arrays.asList(A),SubjectFocusPolicy.Kind.HUMAN_EYE)==null;
        assert update(p,t+20,t+20+250_000_001L,SubjectFocusPolicy.Kind.HUMAN_EYE,A)==null;
        assert update(p,t+30,t+30,SubjectFocusPolicy.Kind.HUMAN_FACE,A)!=null;
        assert p.tapSelect(Arrays.asList(A,B),.25f,.25f);
        one=update(p,t+40,t+40,SubjectFocusPolicy.Kind.HUMAN_EYE,A,B);
        assert one!=null && one.id==7;
        assert update(p,t+50,t+50,SubjectFocusPolicy.Kind.HUMAN_EYE,B)==null;
        assert update(p,t+750_000_000L,t+750_000_000L,
                SubjectFocusPolicy.Kind.HUMAN_EYE,B)==null;
        p.clear();
        one=update(p,t+800_000_000L,t+800_000_000L,
                SubjectFocusPolicy.Kind.HUMAN_FACE,B);
        assert one!=null && one.id==8;
        SubjectFocusPolicy.Face eyeMissing=new SubjectFocusPolicy.Face(
                8,.55f,.2f,.9f,.8f,Float.NaN,Float.NaN,2f,-1f);
        one=update(p,t+900_000_000L,t+900_000_000L,
                SubjectFocusPolicy.Kind.HUMAN_EYE,eyeMissing);
        assert one!=null && !one.eyeLandmarkFound;
        near(one.x,.725f);
        p.beginSession(20L);
        assert p.update(10L,t+1_000_000_000L,t+1_000_000_000L,
                Collections.singletonList(A),SubjectFocusPolicy.Kind.HUMAN_FACE)==null;
        assert !p.tapSelect(Collections.singletonList(A),Float.NaN,.5f);
        assert !p.tapSelect(Collections.singletonList(A),.99f,.99f);
        assert p.tapSelect(Collections.singletonList(A),.3f,.3f);
        assert p.update(20L,t+1_000_000_001L,t+1_000_000_001L,
                Collections.singletonList(A),SubjectFocusPolicy.Kind.HUMAN_EYE)!=null;
        System.out.println("PASS: SubjectFocusPolicyHostTest (epochs/stale/eye/fallback/lock)");
    }
}
