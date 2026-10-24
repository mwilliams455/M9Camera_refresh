import com.particlesdevs.photoncamera.control.subject.HumanEyeAdmissionGate;
import com.particlesdevs.photoncamera.control.subject.SubjectFocusPolicy;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/** Regression for reported v2.97 non-human tracking in 61791.mp4. */
public final class HumanEyeAdmissionGateHostTest {
    static final long EPOCH=10L;
    static final long BASE=1_000_000_000L;
    static void check(boolean result,String why) {
        if(!result)throw new AssertionError(why);
    }
    static SubjectFocusPolicy.Face face(int id) {
        return new SubjectFocusPolicy.Face(id,.2f,.1f,.6f,.7f,
                .3f,.25f,.5f,.25f,.4f,.38f,.4f,.52f);
    }
    static SubjectFocusPolicy.Face translated(SubjectFocusPolicy.Face f,float dx,float dy) {
        return new SubjectFocusPolicy.Face(f.id,f.left+dx,f.top+dy,
                f.right+dx,f.bottom+dy,
                f.leftEyeX+dx,f.leftEyeY+dy,f.rightEyeX+dx,f.rightEyeY+dy,
                f.noseX+dx,f.noseY+dy,f.mouthX+dx,f.mouthY+dy);
    }
    static List<SubjectFocusPolicy.Face> admit(HumanEyeAdmissionGate gate,
              long time,SubjectFocusPolicy.Face... faces) {
        return gate.admit(EPOCH,time,time,Arrays.asList(faces));
    }
    static void rejectedOverManyFrames(HumanEyeAdmissionGate gate,
               SubjectFocusPolicy.Face bad,String reason) {
        gate.beginSession(EPOCH);
        for(int i=0;i<12;i++)
            check(admit(gate,BASE+i*100_000_000L,bad).isEmpty(),reason);
    }
    public static void main(String[] args) {
        HumanEyeAdmissionGate g=new HumanEyeAdmissionGate();
        g.beginSession(EPOCH);
        SubjectFocusPolicy.Face good=face(7);
        check(HumanEyeAdmissionGate.hasCoherentEyeLandmarks(good),
                "A front-facing eye/nose/mouth configuration must qualify");
        check(admit(g,BASE,good).isEmpty(),"first face must not move the lens");
        check(admit(g,BASE,good).isEmpty(),"same-frame callback must not count twice");
        check(admit(g,BASE+100_000_000L,good).isEmpty(),
                "second hit is still preliminary");
        List<SubjectFocusPolicy.Face> ready=admit(g,BASE+200_000_000L,good);
        check(ready.size()==1 && ready.get(0).id==7,
                "three genuine, sequential detections must qualify");

        SubjectFocusPolicy policy=new SubjectFocusPolicy();
        policy.beginSession(EPOCH);
        SubjectFocusPolicy.Target tracked=policy.update(EPOCH,BASE+200_000_000L,
                BASE+200_000_000L,ready,SubjectFocusPolicy.Kind.HUMAN_EYE);
        check(tracked!=null && tracked.eyeLandmarkFound,
                "confirmed eye target must reach existing AF policy");

        rejectedOverManyFrames(g,new SubjectFocusPolicy.Face(7,.2f,.1f,.6f,.7f,
                Float.NaN,Float.NaN,Float.NaN,Float.NaN),
                "face box without eyes must never be followed");
        rejectedOverManyFrames(g,new SubjectFocusPolicy.Face(7,.2f,.1f,.6f,.7f,
                .3f,.25f,.5f,.25f),
                "two dots alone without nose and mouth must not qualify");
        rejectedOverManyFrames(g,new SubjectFocusPolicy.Face(7,.2f,.1f,.6f,.7f,
                .3f,.25f,Float.NaN,Float.NaN,.4f,.38f,.4f,.52f),
                "single eye cannot auto-acquire a new person");
        rejectedOverManyFrames(g,new SubjectFocusPolicy.Face(7,.2f,.1f,.6f,.7f,
                .3f,.25f,.5f,.25f,.4f,.18f,.4f,.52f),
                "nose on wrong side of eye line must be rejected");
        rejectedOverManyFrames(g,new SubjectFocusPolicy.Face(7,.2f,.1f,.6f,.7f,
                .3f,.25f,.5f,.25f,.4f,.38f,.4f,.19f),
                "mouth above nose must be rejected");
        rejectedOverManyFrames(g,face(-1),
                "missing ML Kit tracking ID cannot qualify");
        SubjectFocusPolicy.Face tiny = new SubjectFocusPolicy.Face(7,
                .2f,.1f,.25f,.15f,.211f,.112f,.239f,.112f,
                .225f,.126f,.225f,.139f);
        rejectedOverManyFrames(g,tiny,"tiny false positive must fail");

        g.beginSession(EPOCH);
        check(admit(g,BASE,good).isEmpty(),"restarted evidence required");
        check(admit(g,BASE+100_000_000L,good).isEmpty(),"second hit required");
        // A jump in apparent face location must invalidate the current run.
        check(admit(g,BASE+200_000_000L,translated(good,.28f,.2f)).isEmpty(),
                "large face-box jump must reset confidence");
        check(admit(g,BASE+300_000_000L,translated(good,.28f,.2f)).isEmpty(),
                "moved face still needs another hit");
        check(admit(g,BASE+400_000_000L,translated(good,.28f,.2f)).size()==1,
                "coherent shifted face can eventually be followed");

        g.beginSession(EPOCH);
        check(admit(g,BASE,good).isEmpty(),"first hit");
        check(admit(g,BASE+700_000_000L,good).isEmpty(),
                "long gap resets confirmation");
        check(admit(g,BASE+800_000_000L,good).isEmpty(),
                "long gap confirmation still incomplete");
        check(admit(g,BASE+900_000_000L,good).size()==1,
                "new continuous 3-hit window qualifies");

        g.beginSession(EPOCH);
        check(admit(g,BASE,good).isEmpty(),"first hit for epoch");
        check(g.admit(EPOCH+1,BASE+100_000_000L,BASE+100_000_000L,
                Collections.singletonList(good)).isEmpty(),
                "wrong camera epoch must reject");
        check(g.admit(EPOCH,BASE+100_000_000L,BASE+400_000_000L,
                Collections.singletonList(good)).isEmpty(),
                "stale 300ms analysis must reject");
        check(admit(g,BASE+200_000_000L,good).isEmpty(),
                "stale result cannot advance confidence");
        check(admit(g,BASE+300_000_000L,good).size()==1,
                "a real next frame can complete confirmation");
        g.beginSession(EPOCH+1);
        check(g.admit(EPOCH,BASE+400_000_000L,BASE+400_000_000L,
                Collections.singletonList(good)).isEmpty(),
                "old session cannot modify new focus target");

        System.out.println("PASS: HumanEyeAdmissionGateHostTest "+
                "(no-landmark objects, 3-hit confirmation, jump, epoch, stale)");
    }
}
