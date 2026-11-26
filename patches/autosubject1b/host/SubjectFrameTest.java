import com.particlesdevs.photoncamera.control.subject.AutomaticSubjectSelection;
import com.particlesdevs.photoncamera.control.subject.AutomaticSubjectSelection.Box;
import com.particlesdevs.photoncamera.control.subject.SubjectFocusPolicy.Face;
import com.particlesdevs.photoncamera.control.subject.SubjectFrame;
import com.particlesdevs.photoncamera.control.tracking.SubjectAnchorPolicy.Candidate;
import java.util.Collections;

public final class SubjectFrameTest {
    private static void check(boolean ok, String message) {
        if (!ok) throw new AssertionError(message);
    }

    private static void near(float result, float expected) {
        check(Math.abs(result-expected)<.001f, result+" expected "+expected);
    }

    public static void main(String[] args) {
        AutomaticSubjectSelection policy = new AutomaticSubjectSelection();
        Face profile = new Face(3,.12f,.28f,.48f,.64f,.23f,.40f,Float.NaN,Float.NaN,
                .25f,.46f,.26f,.55f);
        Box clockwise = Box.fromFace(profile,true,90);
        near(clockwise.left,.28f); near(clockwise.top,.52f);
        near(clockwise.right,.64f); near(clockwise.bottom,.88f);
        near(clockwise.aimX,.40f); near(clockwise.aimY,.77f);
        Box counter = Box.fromFace(profile,true,-90);
        near(counter.left,.36f); near(counter.top,.12f);
        near(counter.right,.72f); near(counter.bottom,.48f);
        near(counter.aimX,.60f); near(counter.aimY,.23f);
        check(Box.fromFace(new Face(3,.12f,.28f,.48f,.64f,.23f,.40f,Float.NaN,
                Float.NaN,.25f,.46f,Float.NaN,Float.NaN),false)==null,"unverified fragment");
        policy.faceScanComplete(false); check(policy.faceRotation()==-90,"first sideways attempt");
        policy.faceScanComplete(true); check(policy.faceRotation()==-90,"retain successful angle");
        policy.faceScanComplete(false); check(policy.faceRotation()==90,"opposite angle");
        policy.faceScanComplete(false); check(policy.faceRotation()==0,"upright retry");
        long start=1_000_000_000L;
        policy.observe(start,start,Collections.singletonList(clockwise));
        long id=policy.selectionId();
        SubjectFrame frame = new SubjectFrame();
        frame.update(id,clockwise,400,600);
        float initial=frame.side;
        policy.observe(start+200_000_000L,start+200_000_000L,Collections.emptyList());
        check(policy.visibleAt(start+400_000_000L) && !policy.mayAim(),"visual hold only");
        check(!policy.visibleAt(start+AutomaticSubjectSelection.HOLD_NS+1),"hold expires without callbacks");
        Box body=Box.fromBody(new Candidate("person",.88f,.10f,.15f,.95f,.95f));
        check(policy.observe(start+450_000_000L,start+450_000_000L,Collections.singletonList(body))==body,
                "same subject after a short gap");
        check(id==policy.selectionId() && !policy.mayAim(),"handover needs confirmation");
        frame.update(id,body,400,600);
        check(frame.side>initial && frame.side<body.squareSide(400,600),"gradual size change");
        near(body.squareSide(400,600),224f);
        long later=start+2_000_000_000L;
        policy.observe(later,later,Collections.singletonList(counter));
        check(policy.selectionId()!=id,"new subject starts a new frame");
        frame.update(policy.selectionId(),counter,600,400);
        near(frame.side,counter.squareSide(600,400));
        policy.reset();
        check(!policy.visibleAt(later) && policy.faceRotation()==0,"session resets immediately");
        System.out.println("PASS rotated face and AF coordinates, hold deadline, framing and reacquisition");
    }
}
