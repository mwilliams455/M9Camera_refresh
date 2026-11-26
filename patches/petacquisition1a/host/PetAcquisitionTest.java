import com.particlesdevs.photoncamera.control.subject.AnimalEyeTargetPolicy;
import com.particlesdevs.photoncamera.control.subject.AnimalEyeTargetPolicy.Observation;
import com.particlesdevs.photoncamera.control.subject.AnimalEyeTargetPolicy.Point;
import com.particlesdevs.photoncamera.control.subject.AutomaticSubjectSelection;
import com.particlesdevs.photoncamera.control.subject.AutomaticSubjectSelection.Box;
import com.particlesdevs.photoncamera.control.subject.PetDetailInput;
import com.particlesdevs.photoncamera.control.subject.PetTargetPolicy.Species;
import com.particlesdevs.photoncamera.control.tracking.SubjectAnchorPolicy.Candidate;
import java.util.Arrays;
import java.util.Collections;

public final class PetAcquisitionTest {
    static void check(boolean result,String message) { if(!result)throw new AssertionError(message); }
    static boolean supported(Point eye,Point nose,Point neck,Point tail) {
        return AnimalEyeTargetPolicy.supportsAnimal(new Observation(Species.DOG,.2f,.2f,.8f,.8f,
                eye,null,nose,neck,tail,1,1));
    }
    public static void main(String[] args) {
        Point nose=new Point(.47f,.48f,.71f);
        check(!supported(nose,nose,null,null),"Coincident landmarks are insufficient");
        check(!supported(new Point(.1f,.43f,.86f),nose,null,null),"Eye outside body");
        check(!supported(new Point(.42f,.43f,.49f),nose,null,null),"Weak evidence");
        check(supported(new Point(.43f,.41f,.62f),nose,null,null),"Credible face");
        check(supported(null,null,new Point(.54f,.39f,.69f),new Point(.36f,.64f,.73f)),"Turned animal");
        check(!supported(null,null,nose,nose),"Coincident torso points");

        PetDetailInput search=PetDetailInput.centre(540,720,0);
        Candidate label=new Candidate("dog",.39f,.22f,.20f,.75f,.79f);
        Box proposed=search.poseCandidate(Collections.singletonList(label));
        check(proposed!=null && Math.abs(proposed.cx()-.495f)<.01f,"Mapped centred proposal");
        check(search.confirm(Collections.singletonList(label))==null,"Discovery must require independent evidence");
        check(search.poseCandidate(Arrays.asList(label,label))==null,"Ambiguous animal proposal");
        check(search.poseCandidate(Collections.singletonList(new Candidate("person",.95f,.22f,.20f,.75f,.79f)))==null,
                "No relabelling people as pets");
        check(search.poseCandidate(Collections.singletonList(new Candidate("cat",Float.NaN,.22f,.20f,.75f,.79f)))==null,
                "Finite scores required");
        PetDetailInput upper=PetDetailInput.centre(720,540,2), lower=PetDetailInput.centre(720,540,1);
        check(upper.top<lower.top && lower.top+lower.side<=540 && upper.left+upper.side<=720,"Preview bounds");
        Box real=Box.fromBody(new Candidate("dog",.8f,.42f,.39f,.62f,.61f));
        check(AutomaticSubjectSelection.samePet(real,proposed),"Continue a matching species and position");
        check(!AutomaticSubjectSelection.samePet(Box.fromBody(new Candidate("cat",.8f,.42f,.39f,.62f,.61f)),proposed),
                "Different species needs verification");
        check(PetDetailInput.secondView(540,720,real)!=null,"Optional-backend fallback crop");
        System.out.println("Pet pose admission, ambiguity, discovery geometry and species checks passed");
    }
}
