import com.particlesdevs.photoncamera.control.subject.AutomaticSubjectSelection;
import com.particlesdevs.photoncamera.control.subject.AutomaticSubjectSelection.Box;
import com.particlesdevs.photoncamera.control.subject.SceneHeads;
import com.particlesdevs.photoncamera.control.tracking.SubjectAnchorPolicy.Candidate;
import java.util.List;

public class HeadBodyAcquisitionTest {
    private static final long STEP = 200_000_000L;
    private static void check(boolean value,String why) {
        if (!value) throw new AssertionError(why);
    }
    private static Box face(int x, int y, int size) {
        float[] row={x,y,size,size,x+.3f*size,y+.35f*size,x+.7f*size,y+.35f*size,
                x+.5f*size,y+.55f*size,x+.35f*size,y+.75f*size,x+.65f*size,y+.75f*size,.9f};
        return SceneHeads.decode(row,400,400,0);
    }
    public static void main(String[] args) {
        Box head=face(80,80,140);
        Candidate body=new Candidate("person",.77f,.1f,.12f,.9f,.96f);
        Candidate weak=new Candidate("person",.4f,.1f,.12f,.9f,.96f);
        Candidate cat=new Candidate("cat",.96f,.1f,.12f,.9f,.96f);
        Candidate elsewhere=new Candidate("person",.88f,.55f,.3f,.99f,.99f);
        check(SceneHeads.supportedByOnePerson(head,List.of(body,cat,elsewhere)),"Single enclosing person");
        check(!SceneHeads.supportedByOnePerson(head,List.of(body,body)),"Ambiguous people");
        check(!SceneHeads.supportedByOnePerson(head,List.of(weak,cat,elsewhere)),"Independent evidence required");
        check(!SceneHeads.supportedByOnePerson(face(100,100,40),List.of(body)),"Tiny head on unrelated torso");
        check(!SceneHeads.supportedByOnePerson(Box.fromBody(body),List.of(body)),"Body cannot corroborate itself");
        check(!SceneHeads.supportedByOnePerson(null,List.of(body)),"Missing head");

        AutomaticSubjectSelection policy=new AutomaticSubjectSelection();
        check(policy.observe(STEP,STEP,List.of(head))==head && !policy.mayAim(),"First sample frames the head");
        check(policy.observe(2*STEP,2*STEP,List.of(head))==head && policy.mayAim() && !head.eye,"Head-centre AF on confirmation");
        policy.reset();
        check(policy.observe(STEP,STEP+AutomaticSubjectSelection.MAX_AGE_NS+1,List.of(head))==null,"Stale sample");
        System.out.println("PASS single close head supported by one same-frame person");
    }
}
