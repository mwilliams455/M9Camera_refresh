import com.particlesdevs.photoncamera.control.subject.AutomaticSubjectSelection;
import com.particlesdevs.photoncamera.control.subject.AutomaticSubjectSelection.Box;
import com.particlesdevs.photoncamera.control.subject.SubjectFocusPolicy.Face;
import com.particlesdevs.photoncamera.control.tracking.SubjectAnchorPolicy.Candidate;
import java.util.Arrays;
import java.util.Collections;

public final class AutomaticSubjectSelectionTest {
    private static final long MS=1_000_000L;
    private static Box face(int id, float x, boolean admitted) {
        return Box.fromFace(new Face(id,x,.18f,x+.22f,.5f,x+.12f,.30f,Float.NaN,Float.NaN,
                x+.16f,.36f,x+.14f,.43f),admitted);
    }
    private static Box body(String label, float x) {
        return Box.fromBody(new Candidate(label,.91f,x,.10f,x+.32f,.78f));
    }
    private static void check(boolean ok, String why) {
        if (!ok) throw new AssertionError(why);
    }
    public static void main(String[] args) {
        AutomaticSubjectSelection policy=new AutomaticSubjectSelection();
        Box profile=face(3,.15f,false), eye=face(3,.16f,true), stranger=face(9,.18f,true);
        Box cat=body("cat",.6f), dog=body("dog",.6f), person=body("person",.1f);
        check(Box.fromFace(new Face(3,0,0,1,1,Float.NaN,0,Float.NaN,0),true)==null,"empty landmarks");
        check(body("chair",.2f)==null,"ignore other labels");
        check(Box.fromBody(new Candidate("person",.50f,0,0,1,1))==null,"weak body");
        check(profile!=null && !profile.eye && eye.eye && eye.aimX!=eye.cx(),"profile aim");
        check(profile.squareSide(400,600)>120 && profile.squareSide(600,400)>120,"subject sized square");
        check(policy.facesSuffice(Arrays.asList(profile)),"face fast path");
        check(policy.observe(MS,MS,Arrays.asList(profile))==profile && !policy.mayAim(),"first frame shown");
        check(policy.observe(MS,MS,Arrays.asList(eye))==null && !policy.mayAim(),"duplicate cannot confirm");
        check(policy.observe(201*MS,202*MS,Arrays.asList(stranger,eye))==eye && policy.mayAim(),"same person and eye");
        check(policy.observe(301*MS,302*MS,Arrays.asList(stranger,cat))==null && !policy.mayAim(),"hold identity");
        check(policy.observe(401*MS,402*MS,Arrays.asList(person))==person && !policy.mayAim(),"face to body");
        check(policy.observe(601*MS,602*MS,Arrays.asList(profile))==profile && policy.mayAim(),"body to face");
        check(policy.observe(801*MS,802*MS,Collections.emptyList())==null,"empty scene clears bracket");
        check(policy.observe(1401*MS,1402*MS,Arrays.asList(cat))==cat && !policy.mayAim(),"auto classify cat after loss");
        check(!policy.facesSuffice(Arrays.asList(stranger)),"continue checking for selected pet");
        check(policy.observe(1601*MS,1602*MS,Arrays.asList(stranger,dog,cat))==cat && policy.mayAim(),"pet retains priority");
        check(policy.observe(1801*MS,1802*MS,Arrays.asList(cat,body("cat",.605f)))==null,"ambiguous neighbours");
        check(policy.observe(2001*MS,2400*MS,Arrays.asList(cat))==null,"late callback");
        policy.reset();
        check(policy.observe(MS,MS,Arrays.asList(dog))==dog && !policy.mayAim(),"fresh session picks dog");
        System.out.println("PASS automatic subject acquisition, frame size, focus confirmation and handover");
    }
}
