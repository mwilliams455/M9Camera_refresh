import com.particlesdevs.photoncamera.control.subject.AnimalEyeTargetPolicy;
import com.particlesdevs.photoncamera.control.subject.PetTargetPolicy;
import java.util.Arrays;

public final class AnimalEyeTargetPolicyHostTest {
    static final long EPOCH=48,BASE=8_000_000_000L;
    static void ck(boolean result,String why) {if(!result)throw new AssertionError(why);}
    static PetTargetPolicy.Candidate dog(float shift) {
        return new PetTargetPolicy.Candidate("dog",.9f,.10f+shift,.08f,.75f+shift,.92f);
    }
    static PetTargetPolicy.Target pet(PetTargetPolicy p,long time,float shift) {
        return p.update(EPOCH,time,time,Arrays.asList(dog(shift)));
    }
    static AnimalEyeTargetPolicy.Observation observation(long time,float dx,
            float leftEyeScore,float rightEyeScore,float noseScore){
        return new AnimalEyeTargetPolicy.Observation(PetTargetPolicy.Species.DOG,
                .10f+dx,.08f,.75f+dx,.92f,
                new AnimalEyeTargetPolicy.Point(.35f+dx,.31f,leftEyeScore),
                new AnimalEyeTargetPolicy.Point(.43f+dx,.30f,rightEyeScore),
                new AnimalEyeTargetPolicy.Point(.25f+dx,.46f,noseScore),
                time,EPOCH);
    }
    public static void main(String[] args) {
        PetTargetPolicy p=new PetTargetPolicy();
        AnimalEyeTargetPolicy eyes=new AnimalEyeTargetPolicy();
        p.beginSession(EPOCH);eyes.beginSession(EPOCH);
        ck(pet(p,BASE,0f)==null,"unconfirmed pet must not eye-focus");
        ck(pet(p,BASE+100_000_000L,0f)==null,"pet still unconfirmed");
        long t=BASE+200_000_000L;
        PetTargetPolicy.Target body=pet(p,t,0f);
        ck(body!=null,"confirmed body target");
        ck(eyes.update(EPOCH,t,observation(t,0f,.86f,.64f,.73f),body)==null,
                "single keypoint observation never drives AF");
        long u=t+250_000_000L;
        body=pet(p,u,.005f);
        AnimalEyeTargetPolicy.Target eye=eyes.update(EPOCH,u,
                observation(u,.005f,.83f,.67f,.77f),body);
        ck(eye!=null&&eye.eyeIndex==AnimalEyeTargetPolicy.EYE_LEFT,
                "two consistent dog keypoint frames acquire left eye");
        ck(Math.abs(eye.x-.355f)<.0001f,"coordinates in preview must be used unchanged");

        long v=u+250_000_000L;
        body=pet(p,v,.01f);
        ck(eyes.update(EPOCH,v,new AnimalEyeTargetPolicy.Observation(
                PetTargetPolicy.Species.DOG,.11f,.08f,.76f,.92f,
                new AnimalEyeTargetPolicy.Point(.36f,.31f,.85f),
                new AnimalEyeTargetPolicy.Point(.44f,.30f,.8f),
                new AnimalEyeTargetPolicy.Point(.26f,.46f,.3f),v,EPOCH),body)==null,
                "nose below score threshold must fall back to body");
        ck("nose_unverified".equals(eyes.lastReason()),"specific fallback reason");

        eyes.beginSession(EPOCH);
        body=pet(p,v+250_000_000L,.01f);
        ck(eyes.update(EPOCH,v+250_000_000L,observation(v+250_000_000L,.01f,
                .1f,.15f,.9f),body)==null,"no eyes never takes AF");
        ck("eye_unverified".equals(eyes.lastReason()),"unverified reason");

        eyes.beginSession(EPOCH);
        long w=v+500_000_000L;
        body=pet(p,w,0f);
        ck(eyes.update(EPOCH,w+1_000_000_000L,
                observation(w,0f,.9f,.9f,.9f),body)==null,
                "stale keypoints never alter focus");
        ck("stale_pose".equals(eyes.lastReason()),"stale reason");

        eyes.beginSession(EPOCH+1);
        ck(eyes.update(EPOCH,w,observation(w,0f,.9f,.9f,.9f),body)==null,
                "wrong session cannot read old pose");
        eyes.beginSession(EPOCH);
        ck(eyes.update(EPOCH,w,
                new AnimalEyeTargetPolicy.Observation(PetTargetPolicy.Species.CAT,
                    .1f,.1f,.7f,.9f,new AnimalEyeTargetPolicy.Point(.3f,.3f,.9f),
                    null,new AnimalEyeTargetPolicy.Point(.24f,.44f,.9f),w,EPOCH),body)==null,
                "cat eye cannot steal confirmed dog focus");

        eyes.beginSession(EPOCH);
        ck(eyes.update(EPOCH,w,observation(w,0f,.85f,.1f,.9f),body)==null,
                "one visible eye may acquire only after temporal agreement");
        long w2=w+200_000_000L;
        body=pet(p,w2,.01f);
        eye=eyes.update(EPOCH,w2,observation(w2,.01f,.81f,.11f,.85f),body);
        ck(eye!=null&&eye.eyeIndex==0,"profile view with one visible eye may work");

        eyes.beginSession(EPOCH);
        long z=w2+250_000_000L;
        body=pet(p,z,.01f);
        ck(eyes.update(EPOCH,z,new AnimalEyeTargetPolicy.Observation(
                PetTargetPolicy.Species.DOG,.11f,.08f,.76f,.92f,
                new AnimalEyeTargetPolicy.Point(.73f,.88f,.99f),null,
                new AnimalEyeTargetPolicy.Point(.26f,.46f,.95f),z,EPOCH),body)==null,
                "hind-leg/edge hallucinations cannot count as eyes");
        ck("eye_unverified".equals(eyes.lastReason()),"bad anatomy should fail");

        System.out.println("PASS: AnimalEyeTargetPolicyHostTest "+
                "(confirmed body, eye/nose, one-eye profile, stale, identity, pose geometry)");
    }
}
