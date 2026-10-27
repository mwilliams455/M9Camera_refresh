import com.particlesdevs.photoncamera.control.subject.ProfileEyeAdmissionGate;
import com.particlesdevs.photoncamera.control.subject.SubjectFocusPolicy;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

public final class ProfileEyeAdmissionGateHostTest {
    static int checks;
    static void yes(boolean ok,String why){checks++;if(!ok)throw new AssertionError(why);}
    static final long BASE=1_000_000_000L,EPOCH=22;
    static SubjectFocusPolicy.Face profile(int id){
        return new SubjectFocusPolicy.Face(id,.18f,.12f,.51f,.73f,
                .29f,.26f,Float.NaN,Float.NaN,.38f,.43f,.39f,.57f);
    }
    static List<SubjectFocusPolicy.Face> scan(ProfileEyeAdmissionGate gate,long t,SubjectFocusPolicy.Face f){
        return gate.admit(EPOCH,t,t,Collections.singletonList(f));
    }
    static void never(ProfileEyeAdmissionGate g,SubjectFocusPolicy.Face f,String reason){
        g.beginSession(EPOCH);
        for(int i=0;i<10;i++)yes(scan(g,BASE+i*100_000_000L,f).isEmpty(),reason);
    }
    public static void main(String[] args){
        ProfileEyeAdmissionGate g=new ProfileEyeAdmissionGate();
        g.beginSession(EPOCH);
        SubjectFocusPolicy.Face p=profile(5);
        yes(ProfileEyeAdmissionGate.plausibleProfile(p),"one true side-profile eye with nose/mouth qualifies for temporal check");
        yes(scan(g,BASE,p).isEmpty(),"one hit not enough");
        yes(scan(g,BASE,p).isEmpty(),"duplicate frame refused");
        yes(scan(g,BASE+100_000_000L,p).isEmpty(),"two hits not enough");
        yes(scan(g,BASE+200_000_000L,p).isEmpty(),"three hits not enough");
        List<SubjectFocusPolicy.Face> ready=scan(g,BASE+300_000_000L,p);
        yes(ready.size()==1 && ready.get(0).id==5,"four hits admit profile");
        SubjectFocusPolicy policy=new SubjectFocusPolicy();policy.beginSession(EPOCH);
        SubjectFocusPolicy.Target target=policy.update(EPOCH,BASE+300_000_000L,BASE+300_000_000L,ready,SubjectFocusPolicy.Kind.HUMAN_EYE);
        yes(target!=null&&target.eyeLandmarkFound&&Math.abs(target.x-.29f)<.0001f,"profile focuses actual eye");
        never(g,new SubjectFocusPolicy.Face(5,.18f,.12f,.51f,.73f,
                    Float.NaN,Float.NaN,Float.NaN,Float.NaN,.38f,.43f,.39f,.57f),"no eye");
        never(g,new SubjectFocusPolicy.Face(5,.18f,.12f,.51f,.73f,
                    .29f,.26f,Float.NaN,Float.NaN,Float.NaN,Float.NaN,Float.NaN,Float.NaN),"eye only");
        never(g,new SubjectFocusPolicy.Face(5,.18f,.12f,.51f,.73f,
                    .29f,.26f,Float.NaN,Float.NaN,.38f,.20f,.39f,.57f),"nose above eye");
        never(g,new SubjectFocusPolicy.Face(5,.18f,.12f,.51f,.73f,
                    .29f,.26f,Float.NaN,Float.NaN,.38f,.43f,.39f,.33f),"mouth above nose");
        never(g,new SubjectFocusPolicy.Face(5,.18f,.12f,.51f,.73f,
                    .29f,.26f,.39f,.26f,.38f,.43f,.39f,.57f),"frontal pair excluded from profile path");
        never(g,profile(-1),"missing tracking ID");
        never(g,new SubjectFocusPolicy.Face(5,.18f,.12f,.20f,.18f,
                    .185f,.14f,Float.NaN,Float.NaN,.19f,.16f,.19f,.17f),"tiny face");
        g.beginSession(EPOCH);
        yes(scan(g,BASE,p).isEmpty(),"first hit");
        yes(g.admit(EPOCH+1,BASE+100_000_000L,BASE+100_000_000L,Arrays.asList(p)).isEmpty(),"wrong epoch");
        yes(g.admit(EPOCH,BASE+100_000_000L,BASE+400_000_000L,Arrays.asList(p)).isEmpty(),"stale frame");
        yes(scan(g,BASE+200_000_000L,p).isEmpty(),"stale result does not advance");
        yes(scan(g,BASE+300_000_000L,p).isEmpty(),"still three hits");
        yes(scan(g,BASE+400_000_000L,p).size()==1,"four true hits");
        g.beginSession(EPOCH);
        yes(scan(g,BASE,p).isEmpty(),"initial");
        yes(scan(g,BASE+700_000_000L,p).isEmpty(),"long gap resets");
        yes(scan(g,BASE+800_000_000L,p).isEmpty(),"two after gap");
        yes(scan(g,BASE+900_000_000L,p).isEmpty(),"three after gap");
        yes(scan(g,BASE+1_000_000_000L,p).size()==1,"four after gap");
        g.beginSession(EPOCH);
        yes(scan(g,BASE,p).isEmpty(),"first for displacement");
        SubjectFocusPolicy.Face moved = new SubjectFocusPolicy.Face(5,.54f,.12f,.87f,.73f,
              .65f,.26f,Float.NaN,Float.NaN,.74f,.43f,.75f,.57f);
        yes(scan(g,BASE+100_000_000L,moved).isEmpty(),"large jump invalidates");
        yes(scan(g,BASE+200_000_000L,moved).isEmpty(),"still pending");
        yes(scan(g,BASE+300_000_000L,moved).isEmpty(),"needs fourth coherent");
        yes(scan(g,BASE+400_000_000L,moved).size()==1,"eligible after four same-ID observations");
        System.out.println("PASS: "+checks+" profile-eye false positive / epoch / temporal checks");
    }
}
