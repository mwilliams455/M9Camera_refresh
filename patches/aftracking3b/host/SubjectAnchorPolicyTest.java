import com.particlesdevs.photoncamera.control.tracking.SubjectAnchorPolicy;
import com.particlesdevs.photoncamera.control.tracking.SubjectAnchorPolicy.Candidate;
import com.particlesdevs.photoncamera.control.tracking.SubjectAnchorPolicy.Decision;
import com.particlesdevs.photoncamera.control.tracking.SubjectAnchorPolicy.State;
import java.util.Arrays;
import java.util.Collections;

public final class SubjectAnchorPolicyTest {
    static int checks;
    static void ok(boolean value,String message){checks++;if(!value)throw new AssertionError(message);}
    static Candidate c(String label,float confidence,float l,float t,float r,float b){return new Candidate(label,confidence,l,t,r,b);}
    static void childTurningAndMoving(){
        SubjectAnchorPolicy p=new SubjectAnchorPolicy();p.begin(1,.50f,.28f,1000);
        Candidate start=c("person",.86f,.35f,.16f,.65f,.82f);
        ok(p.observe(1,1030,1080,Arrays.asList(start)).state==State.WAITING,"person first detection must confirm");
        Decision locked=p.observe(1,1210,1260,Arrays.asList(c("person",.88f,.38f,.15f,.69f,.82f)));
        ok(locked.state==State.ACQUIRED,"second consistent person acquires");
        ok(Math.abs(locked.y-.28f)<.04f,"tap relative to upper person maintained");
        // Person turns away: patch appearance changes completely, COCO identity holds.
        Decision moved=p.observe(1,1440,1480,Arrays.asList(c("person",.78f,.46f,.14f,.77f,.81f)));
        ok(moved.state==State.ACQUIRED&&moved.x>locked.x,"moving turning body follows");
        ok(moved.canMoveAf(),"only confirmed fresh detection moves AF");
        ok(!p.current(1,1500).canMoveAf(),"no fresh detection: don't repeat stale AF location");
    }
    static void hidesAndReturns(){
        SubjectAnchorPolicy p=new SubjectAnchorPolicy();p.begin(8,.41f,.30f,0);
        p.observe(8,20,40,Arrays.asList(c("person",.8f,.30f,.10f,.60f,.90f)));
        ok(p.observe(8,210,240,Arrays.asList(c("person",.82f,.32f,.12f,.63f,.9f))).canMoveAf(),"initial target");
        ok(p.observe(8,410,440,Collections.emptyList()).state==State.HOLD,"short occlusion holds lens area");
        ok(p.observe(8,660,700,Arrays.asList(c("person",.78f,.38f,.1f,.69f,.86f))).canMoveAf(),"reappearing selected person recovers");
        ok(p.observe(8,1510,1600,Collections.emptyList()).state==State.HOLD,"bounded occlusion");
        ok(p.observe(8,1920,1970,Collections.emptyList()).state==State.RETIRED,"long absence retires");
        ok(!p.observe(8,2140,2170,Arrays.asList(c("person",.99f,.38f,.1f,.69f,.86f))).canMoveAf(),"retired cannot silently reacquire");
    }
    static void noPersonFallsBack(){
        SubjectAnchorPolicy p=new SubjectAnchorPolicy();p.begin(5,.5f,.5f,1000);
        ok(p.observe(5,1080,1100,Arrays.asList(c("chair",.9f,.2f,.2f,.7f,.7f))).state==State.WAITING,"furniture not semantic");
        ok(p.observe(5,1380,1400,Collections.emptyList()).state==State.WAITING,"ordinary patch retains grace period");
        ok(p.observe(5,2570,2600,Collections.emptyList()).state==State.UNAVAILABLE,"no person: fallback to patch tracking");
        p.begin(6,.5f,.5f,2900);
        ok(p.observe(5,3010,3030,Arrays.asList(c("person",.95f,.3f,.2f,.7f,.7f))).state==State.RETIRED,"stale session never commands AF");
    }
    static void noSubjectSteal(){
        SubjectAnchorPolicy p=new SubjectAnchorPolicy();p.begin(1,.2f,.4f,0);
        Candidate a=c("person",.85f,.08f,.15f,.38f,.90f);
        Candidate b=c("person",.96f,.53f,.16f,.86f,.93f);
        ok(p.observe(1,30,50,Arrays.asList(a,b)).state==State.WAITING,"first subject confirmation");
        ok(p.observe(1,210,240,Arrays.asList(a,b)).canMoveAf(),"tap-pinned left person");
        ok(p.observe(1,410,450,Arrays.asList(b)).state==State.HOLD,"right person cannot steal lost target");
        ok(!p.observe(1,610,650,Arrays.asList(c("dog",.99f,.05f,.08f,.39f,.9f))).canMoveAf(),"new dog cannot take person slot");
        ok(p.observe(1,810,845,Arrays.asList(a,b)).state==State.ACQUIRED,"original reacquired even with distractor");
    }
    static void staleAndRepeated(){
        SubjectAnchorPolicy p=new SubjectAnchorPolicy();p.begin(2,.5f,.4f,1000);
        Candidate person=c("person",.9f,.2f,.1f,.8f,.9f);
        p.observe(2,1100,1170,Arrays.asList(person));
        ok(p.observe(2,1100,1171,Arrays.asList(person)).state==State.WAITING,"same frame cannot confirm twice");
        ok(p.observe(2,1200,2000,Arrays.asList(person)).state==State.WAITING,"old detector output doesn't command AF");
        ok(p.observe(2,2050,2080,Arrays.asList(person)).state==State.WAITING,"long gap restarts confirmation");
        ok(p.observe(2,2210,2250,Arrays.asList(person)).canMoveAf(),"second coherent fresh frame reacquires");
        ok(p.observe(2,2080,2800,Arrays.asList(person)).state==State.HOLD,"stale existing detector output holds");
    }
    static void animalsAndInvalid(){
        ok(SubjectAnchorPolicy.classify("DOG")==SubjectAnchorPolicy.ClassId.DOG,"dog class");
        ok(SubjectAnchorPolicy.classify("cat")==SubjectAnchorPolicy.ClassId.CAT,"cat class");
        ok(SubjectAnchorPolicy.classify("person")==SubjectAnchorPolicy.ClassId.PERSON,"person class");
        ok(SubjectAnchorPolicy.classify("car")==null,"vehicles stay patch fallback");
        ok(!c("person",.9f,.7f,.7f,.3f,.9f).valid(),"negative width invalid");
        ok(!c("person",Float.NaN,.2f,.2f,.8f,.8f).valid(),"nonfinite rejected");
        SubjectAnchorPolicy p=new SubjectAnchorPolicy();p.begin(9,.5f,.5f,0);
        ok(p.observe(9,100,140,Arrays.asList(c("dog",.8f,.3f,.25f,.7f,.85f))).state==State.WAITING,"dog first hit");
        ok(p.observe(9,280,300,Arrays.asList(c("dog",.85f,.32f,.24f,.71f,.86f))).canMoveAf(),"dog tap locks");
    }
    public static void main(String[]args){
        childTurningAndMoving();hidesAndReturns();noPersonFallsBack();
        noSubjectSteal();staleAndRepeated();animalsAndInvalid();
        System.out.println("PASS: "+checks+" person/pet semantic-anchor host assertions");
    }
}

