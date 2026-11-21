import com.particlesdevs.photoncamera.control.subject.AutomaticSubjectSelection;
import com.particlesdevs.photoncamera.control.subject.AutomaticSubjectSelection.Box;
import com.particlesdevs.photoncamera.control.subject.SceneHeads;
import java.util.*;

public class SceneHeadsTest {
    static void check(boolean ok) { if (!ok) throw new AssertionError(); }
    static float[] face(int x,int y) {
        return new float[]{x,y,50,60,x+12,y+18,x+32,y+18,x+20,y+32,x+14,y+46,x+30,y+46,.9f};
    }
    public static void main(String[] args) {
        long t=1_000_000_000L;
        Box a=SceneHeads.decode(face(50,100),360,480,0), b=SceneHeads.decode(face(79,146),360,480,0);
        Box duplicate=SceneHeads.decode(face(52,98),360,480,0);
        SceneHeads policy=new SceneHeads();
        List<Box> found=new ArrayList<>();
        policy.merge(found,List.of(a),t);
        check(found.isEmpty());
        found.add(a);
        policy.merge(found,List.of(duplicate,b),t+100);
        check(found.size()==2 && found.get(0)==a && found.get(1)==b && !b.eye);
        found.clear();
        policy.merge(found,List.of(b),t+200);
        check(found.size()==1 && found.get(0)==b);
        found.clear();
        policy.merge(found,List.of(b),t+AutomaticSubjectSelection.HOLD_NS+101);
        check(found.isEmpty());
        policy.merge(found,List.of(a,b),t+2_000_000_000L);
        policy.clear(); found.clear();
        policy.merge(found,List.of(b),t+2_100_000_000L);
        check(found.isEmpty());
        float[] raw=face(50,100);
        Box rot=SceneHeads.decode(raw,360,480,90);
        check(Math.abs(rot.cx()-a.cy())<.00001 && Math.abs(rot.cy()-(1-a.cx()))<.00001);
        raw[9]=raw[5];check(SceneHeads.decode(raw,360,480,0)==null);
        raw=face(50,100);raw[14]=.79f;check(SceneHeads.decode(raw,360,480,0)==null);
        System.out.println("PASS overlapping heads, duplicate suppression, rotation and single-head expiry");
    }
}
