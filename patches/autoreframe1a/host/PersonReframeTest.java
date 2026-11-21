import com.particlesdevs.photoncamera.control.subject.AutomaticSubjectSelection;
import com.particlesdevs.photoncamera.control.subject.AutomaticSubjectSelection.Box;
import com.particlesdevs.photoncamera.control.subject.SubjectFocusPolicy.Face;
import com.particlesdevs.photoncamera.control.tracking.SubjectAnchorPolicy.Candidate;
import java.util.Arrays;
import java.util.Collections;

public final class PersonReframeTest {
    private static Box body(String label,float x,float y) {
        return Box.fromBody(new Candidate(label,.86f,x-.09f,y-.14f,x+.09f,y+.36f));
    }
    private static Box face(int id,float x) {
        return Box.fromFace(new Face(id,x-.08f,.40f,x+.08f,.60f,x,.469f,Float.NaN,Float.NaN,
                x+.008f,.502f,x+.015f,.546f),false);
    }
    private static void check(boolean condition,String why) {
        if(!condition) throw new AssertionError(why);
    }
    private static Box observe(AutomaticSubjectSelection p,long ms,Box... subjects) {
        long frame=ms*1_000_000L;
        return p.observe(frame,frame,Arrays.asList(subjects));
    }

    public static void main(String[] args) {
        AutomaticSubjectSelection p=new AutomaticSubjectSelection();
        Box edge=face(1,.84f), centre=body("person",.48f,.52f);
        Box other=face(2,.51f), dog=body("dog",.50f,.50f);
        check(p.checkOtherPeople(Collections.singletonList(edge),1),"look for a centred turned-away person");
        check(!p.checkOtherPeople(Arrays.asList(edge,other),1),"fast path when a face is central");
        check(observe(p,1,edge,centre)==centre,"initial composition");
        p.reset();
        observe(p,1,edge); observe(p,201,edge);
        long id=p.selectionId();
        check(observe(p,401,edge,centre)==edge,"brief crossing");
        observe(p,601,edge);
        check(observe(p,801,edge,centre)==edge,"crossing evidence cleared");
        check(observe(p,1001,edge,centre)==edge,"dwell");
        check(observe(p,1201,edge,centre)==centre && p.selectionId()!=id && !p.mayAim(),"deliberate transfer");
        check(observe(p,1401,edge,centre)==centre && p.mayAim(),"fresh confirmation before AF");
        check(observe(p,1601,centre,dog)==centre,"pet does not trigger a person handover");

        p.reset(); Box top=body("person",.48f,.20f);
        observe(p,1,top); observe(p,201,top);
        observe(p,401,top,centre); observe(p,601,top,centre);
        check(observe(p,801,top,centre)==centre,"vertical reframe");
        p.reset(); observe(p,1,edge); observe(p,201,edge);
        Box third=body("person",.61f,.51f), fourth=body("person",.39f,.51f);
        for(int t=401;t<=1201;t+=200)
            check(observe(p,t,edge,third,fourth)==edge,"ambiguous new subjects");
        observe(p,1401,edge,centre);
        check(p.observe(1450_000_000L,1900_000_000L,Arrays.asList(edge,centre))==null,"stale input");
        check(observe(p,1950,edge,centre)==edge,"new confirmation run after a stale result");
        p.reset(); observe(p,1,dog); observe(p,201,dog);
        check(!p.checkOtherPeople(Collections.singletonList(edge),220_000_000L),"pet fast path");
        System.out.println("PASS composition handover, dwell, vertical pans, ambiguity, stale results and AF confirmation");
    }
}
