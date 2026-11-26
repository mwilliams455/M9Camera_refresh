import com.particlesdevs.photoncamera.control.subject.AutomaticSubjectSelection.Box;
import com.particlesdevs.photoncamera.control.subject.HeadContinuity;
import com.particlesdevs.photoncamera.control.tracking.SubjectAnchorPolicy.Candidate;
import java.util.List;

public final class HeadContinuityTest {
    private static final long STEP=200_000_000L;
    private static Candidate rect(float l,float t,float r,float b) {
        return new Candidate("person",.80f,l,t,r,b);
    }
    public static void main(String[] args) {
        Candidate a=rect(.14f,.20f,.26f,.34f), b=rect(.63f,.28f,.75f,.42f);
        Candidate personA=rect(.05f,.17f,.43f,.86f), personB=rect(.51f,.25f,.92f,.89f);
        List<Candidate> heads=List.of(a,b), people=List.of(personA,personB);
        HeadContinuity t=new HeadContinuity();
        assert t.observe(STEP,heads,people,h->null).isEmpty();
        List<Box> pair=t.observe(2*STEP,heads,people,h->null);
        assert pair.size()==2;
        assert HeadContinuity.focusOwner(Box.fromBody(personA),pair)==pair.get(0);
        assert HeadContinuity.focusOwner(Box.fromBody(personB),pair)==pair.get(1);
        assert HeadContinuity.focusOwner(Box.fromBody(rect(0,0,1,1)),pair)==null;
        assert HeadContinuity.focusOwner(Box.fromBody(new Candidate("cat",.9f,0,0,1,1)),pair)==null;
        // A visually matched patch can move after one missing detection.
        Candidate moved=rect(.65f,.29f,.77f,.43f);
        pair=t.observe(3*STEP,List.of(a),List.of(personA),h->h==b?moved:null);
        assert pair.size()==2 && Math.abs(pair.get(1).cx()-moved.cx())<.001f;
        // No image match at a cut. Remembering an identity never draws a stale head.
        assert t.observe(4*STEP,List.of(),List.of(),h->null).isEmpty();
        assert t.observe(5*STEP,heads,people,h->null).size()==2;
        for (int i=6;i<=8;i++) assert t.observe(i*STEP,List.of(),List.of(),h->h).size()==2;
        assert t.observe(9*STEP,List.of(),List.of(),h->h).isEmpty();
        t.reset();
        for (int i=1;i<=3;i++)
            assert t.observe(i*STEP,List.of(a),List.of(personA,personA),h->null).isEmpty();
        t.reset();
        assert t.observe(STEP,heads,people,h->null).isEmpty();
        assert t.observe(5*STEP,heads,people,h->null).isEmpty();
        assert t.observe(5*STEP,heads,people,h->null).isEmpty();
        System.out.println("PASS scene head ownership, motion, cut, expiry and ambiguous people");
    }
}
