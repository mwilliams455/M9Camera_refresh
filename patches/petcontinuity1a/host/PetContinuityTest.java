import com.particlesdevs.photoncamera.control.subject.AutomaticSubjectSelection;
import com.particlesdevs.photoncamera.control.subject.AutomaticSubjectSelection.Box;
import com.particlesdevs.photoncamera.control.subject.PetDetailInput;
import com.particlesdevs.photoncamera.control.tracking.SubjectAnchorPolicy.Candidate;
import java.util.Arrays;
import java.util.Collections;

public final class PetContinuityTest {
    static final long MS=1000000L;
    static void check(boolean v,String message) { if(!v)throw new AssertionError(message); }
    static Box sample(AutomaticSubjectSelection policy,long time,Box... boxes) {
        return policy.observe(time*MS,time*MS,Arrays.asList(boxes));
    }
    public static void main(String[] args) {
        AutomaticSubjectSelection policy=new AutomaticSubjectSelection();
        Box cat=Box.fromBody(new Candidate("cat",.78f,.42f,.48f,.64f,.68f));
        sample(policy,5,cat);
        check(policy.confirmedPet(5*MS)==null,"Cannot seed local searches from one sighting");
        sample(policy,205,cat);
        sample(policy,405);
        Box anchor=policy.confirmedPet(405*MS);
        check(policy.lastObservationMissed() && anchor!=null,"Recent confirmed pet must survive one miss");
        PetDetailInput local=PetDetailInput.forTracking(600,800,Collections.emptyList(),cat,anchor,true);
        check(local!=null,"Missing primary hint should permit one bounded local search");
        Candidate pet=new Candidate("cat",.68f,.36f,.24f,.80f,.76f);
        check(local.confirm(Collections.singletonList(new Candidate("dog",.93f,.36f,.24f,.80f,.76f)))==null,
                "A different species cannot maintain this selection");
        check(local.confirm(Collections.singletonList(new Candidate("cat",.53f,.36f,.24f,.80f,.76f)))==null,
                "Weak local evidence must not renew a lock");
        check(local.confirm(Arrays.asList(pet,pet))==null,"Two matches are ambiguous");
        check(local.confirm(Collections.singletonList(new Candidate("cat",.91f,0f,0f,.2f,.2f)))==null,
                "An unrelated animal cannot renew a lock");
        Box fresh=local.confirm(Collections.singletonList(pet));
        check(fresh!=null && fresh.cx()>cat.cx(),"A fresh match must follow motion");
        check(sample(policy,605,fresh)==fresh && !policy.mayAim(),"First frame back should only move the square");
        check(sample(policy,805,fresh)==fresh && policy.mayAim(),"Second fresh match should permit autofocus");
        check(policy.confirmedPet(1500*MS)==null && !policy.visibleAt(1500*MS),"Expired anchor cannot extend itself");
        System.out.println("Pet continuity and fresh autofocus confirmation passed");
    }
}
