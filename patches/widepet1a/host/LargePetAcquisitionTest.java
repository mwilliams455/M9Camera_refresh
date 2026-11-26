import com.particlesdevs.photoncamera.control.subject.AutomaticSubjectSelection;
import com.particlesdevs.photoncamera.control.subject.AutomaticSubjectSelection.Box;
import com.particlesdevs.photoncamera.control.subject.LargePetAcquisition;
import com.particlesdevs.photoncamera.control.subject.PetDetailInput;
import com.particlesdevs.photoncamera.control.tracking.SubjectAnchorPolicy.Candidate;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

public final class LargePetAcquisitionTest {
    private static final long STEP = 200_000_000L;
    private static final Box CAT = body("cat",.05f,.2f,.75f,.6f);
    private static final Box DOG = body("dog",.05f,.2f,.75f,.6f);
    private static final Box PERSON = body("person",.3f,.3f,.7f,.8f);
    private static final Box SMALL = body("dog",.4f,.4f,.6f,.6f);

    private static Box body(String label,float l,float t,float r,float b) {
        return Box.fromBody(new Candidate(label,.75f,l,t,r,b));
    }
    private static void check(boolean value,String message) {
        if (!value) throw new AssertionError(message);
    }
    private static List<Box> filter(LargePetAcquisition gate, Box current, long frame, long now, Box... boxes) {
        List<Box> result = new ArrayList<>(Arrays.asList(boxes));
        gate.filter(result,current,frame,now);
        return result;
    }
    public static void main(String[] args) {
        PetDetailInput crop=PetDetailInput.wide(540,720);
        check(crop.side==540 && crop.top==90 && crop.left==0,"Portrait wide square");
        PetDetailInput landscape=PetDetailInput.wide(720,540);
        check(landscape.left==90 && landscape.top==0 && landscape.side==540,"Landscape wide square");
        Candidate label=new Candidate("cat",.48f,.1f,.25f,.9f,.75f);
        List<Candidate> labels=Collections.singletonList(label);
        Box proposal=crop.poseCandidate(labels);
        check(proposal!=null && proposal.left==.1f && proposal.top==.3125f,"Wide coordinates");
        check(crop.confirm(labels)==null,"A label alone cannot verify a new wide pet");
        check(crop.poseCandidate(Arrays.asList(label,label))==null,"Ambiguous animals");
        check(crop.poseCandidate(Collections.singletonList(new Candidate("cat",.8f,.4f,.4f,.6f,.6f)))==null,
                "Small animals use their own detail search");

        LargePetAcquisition gate=new LargePetAcquisition();
        check(filter(gate,null,STEP,STEP,CAT,PERSON).equals(Collections.singletonList(PERSON)),"First observation");
        check(gate.awaiting(2*STEP),"Request wide confirmation");
        check(filter(gate,null,2*STEP,2*STEP,CAT).contains(CAT),"Consistent second frame");
        gate.reset();
        filter(gate,null,STEP,STEP,CAT);
        check(filter(gate,null,STEP,STEP,CAT).isEmpty(),"Duplicate frame");
        check(filter(gate,null,2*STEP,2*STEP,DOG).isEmpty(),"Species disagreement");
        filter(gate,null,3*STEP,3*STEP);
        check(filter(gate,null,4*STEP,4*STEP,DOG).isEmpty(),"Interrupted confirmations");
        check(filter(gate,null,5*STEP,5*STEP,DOG,CAT).isEmpty(),"Multiple new large pets");
        filter(gate,null,6*STEP,6*STEP,CAT);
        check(filter(gate,null,7*STEP,9*STEP,CAT).isEmpty(),"Stale result");
        check(filter(gate,null,10*STEP,10*STEP,CAT).isEmpty(),"Expired confirmation");
        check(filter(gate,CAT,11*STEP,11*STEP,CAT,SMALL).size()==2,"Current animal and separate small pet");
        check(AutomaticSubjectSelection.needsPetDetail(null,Collections.singletonList(
                body("person",.78f,.02f,.98f,.25f))),"Peripheral person does not preclude a pet search");
        check(!AutomaticSubjectSelection.needsPetDetail(null,Collections.singletonList(PERSON)),"Centred person");
        System.out.println("Large pet acquisition, independent evidence, timing and geometry passed");
    }
}
