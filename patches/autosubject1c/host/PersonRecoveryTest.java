import com.particlesdevs.photoncamera.control.subject.AutomaticSubjectSelection;
import com.particlesdevs.photoncamera.control.subject.AutomaticSubjectSelection.Box;
import com.particlesdevs.photoncamera.control.subject.PersonRecoveryInput;
import com.particlesdevs.photoncamera.control.tracking.SubjectAnchorPolicy.Candidate;
import java.util.Arrays;
import java.util.Collections;

public final class PersonRecoveryTest {
    private static void check(boolean ok,String msg) { if (!ok) throw new AssertionError(msg); }
    private static void near(float actual,float expected) { check(Math.abs(actual-expected)<.0001f,"coordinate"); }
    private static Box body(String label,float l,float t,float r,float b) {
        return Box.fromBody(new Candidate(label,.85f,l,t,r,b));
    }
    public static void main(String[] args) {
        PersonRecoveryInput portrait=new PersonRecoveryInput(540,720), landscape=new PersonRecoveryInput(720,540);
        check(portrait.left==100 && portrait.top==80 && portrait.width==120 && portrait.height==160,"portrait");
        check(landscape.top==100 && landscape.left==80 && landscape.height==120 && landscape.width==160,"landscape");
        Box secondary=portrait.toPreview(new Candidate("person",.8f,.35f,.3f,.65f,.7f));
        near(secondary.left,.1f); near(secondary.right,.9f); near(secondary.top,.1f); near(secondary.bottom,.9f);
        check(portrait.toPreview(new Candidate("person",.96f,0,0,.2f,.18f))==null,"padding");
        check(portrait.toPreview(new Candidate("dog",.9f,.35f,.3f,.65f,.7f))==null,"person-only recovery");

        AutomaticSubjectSelection p=new AutomaticSubjectSelection();
        Box person=body("person",.12f,.08f,.92f,.92f), pet=body("cat",.10f,.11f,.91f,.92f);
        Box other=body("person",.02f,.02f,.18f,.18f);
        final long ms=1_000_000L;
        check(p.observe(10*ms,10*ms,Collections.emptyList(),secondary)==null,"no acquisition from fallback");
        p.observe(100*ms,100*ms,Arrays.asList(person));
        check(p.recoveryAnchor(120*ms)==null,"unconfirmed");
        p.observe(300*ms,300*ms,Arrays.asList(person));
        Box anchor=p.recoveryAnchor(310*ms);
        check(anchor==person && !AutomaticSubjectSelection.needsPersonRecovery(anchor,Arrays.asList(person)),"primary path");
        check(AutomaticSubjectSelection.needsPersonRecovery(anchor,Arrays.asList(pet)),"class disagreement");
        check(!AutomaticSubjectSelection.matchesRecovery(anchor,other),"other location");
        check(p.observe(500*ms,520*ms,Arrays.asList(pet),secondary)==secondary && !p.mayAim(),"first visual only");
        check(p.observe(700*ms,710*ms,Arrays.asList(pet),secondary)==secondary && p.mayAim(),"confirmed recovery");
        check(p.observe(900*ms,910*ms,Arrays.asList(person),other)==person,"primary wins");
        check(p.observe(1000*ms,1000*ms,Arrays.asList(person,person),secondary)==null,"ambiguous primary");
        check(p.observe(1200*ms,1560*ms,Collections.emptyList(),secondary)==null,"stale callback");
        check(p.observe(1500*ms,1590*ms,Collections.emptyList(),secondary)==null,"observation after hold deadline");
        check(p.observe(1700*ms,1700*ms,Arrays.asList(pet),secondary)==pet,"new animal after loss");
        p.observe(1900*ms,1900*ms,Arrays.asList(pet));
        check(p.recoveryAnchor(1910*ms)==null,"selected animal uses primary path");
        p.reset();
        check(p.recoveryAnchor(2000*ms)==null,"session reset");
        System.out.println("PASS close person recovery, geometry, AF confirmation, subject change and stale results");
    }
}
