import com.particlesdevs.photoncamera.control.subject.PetTargetPolicy;
import java.util.Arrays;
import java.util.Collections;

public final class PetTargetPolicyHostTest {
    private static final long EPOCH=100L;
    private static final long T=5_000_000_000L;
    private static PetTargetPolicy.Candidate c(String species,float score,float x,float y) {
        return new PetTargetPolicy.Candidate(species,score,x,y,x+.24f,y+.27f);
    }
    private static void check(boolean ok,String what) {
        if(!ok)throw new AssertionError(what);
    }
    private static PetTargetPolicy.Target tick(PetTargetPolicy gate,long n,PetTargetPolicy.Candidate... candidates) {
        return gate.update(EPOCH,n,n,Arrays.asList(candidates));
    }
    public static void main(String[] args) {
        PetTargetPolicy gate=new PetTargetPolicy();
        gate.beginSession(EPOCH);
        check(tick(gate,T,c("dog",.94f,.21f,.24f))==null,"one dog frame isn't enough");
        check(tick(gate,T,c("dog",.94f,.21f,.24f))==null,"duplicate cannot confirm");
        check(tick(gate,T+200_000_000L,c("dog",.91f,.22f,.24f))==null,"two frames incomplete");
        PetTargetPolicy.Target got=tick(gate,T+400_000_000L,c("dog",.90f,.23f,.25f));
        check(got!=null && got.species==PetTargetPolicy.Species.DOG,"third dog frame acquires");
        check(got.x>.30f && got.x<.40f,"target position must be normalized body centre");
        check(tick(gate,T+450_000_000L,c("person",.99f,.23f,.25f),
                c("car",.99f,.23f,.25f))==null,"people/cars are not pets");
        check(tick(gate,T+700_000_000L,c("dog",.97f,.75f,.70f))==null,
                "far dog must not steal tracked pet");
        check(tick(gate,T+800_000_000L,c("dog",.96f,.24f,.25f))!=null,
                "returning same dog can retain target");

        gate.beginSession(EPOCH);
        for(int i=0;i<8;i++)check(tick(gate,T+i*200_000_000L,
                c("unknown",.99f,.2f,.2f),c("human face",.99f,.2f,.2f))==null,
                "objects without cat/dog class must never acquire");
        gate.beginSession(EPOCH);
        for(int i=0;i<8;i++)check(tick(gate,T+i*200_000_000L,
                c("cat",.30f,.2f,.2f))==null,"low score must never acquire");
        gate.beginSession(EPOCH);
        check(tick(gate,T,c("cat",.99f,.1f,.1f))==null,"cat stage 1");
        check(tick(gate,T+200_000_000L,c("cat",.99f,.1f,.1f))==null,"cat stage 2");
        got=tick(gate,T+400_000_000L,c("cat",.99f,.1f,.1f));
        check(got!=null&&got.species==PetTargetPolicy.Species.CAT,"cat stage 3");
        check(tick(gate,T+500_000_000L,c("dog",.99f,.1f,.1f))==null,
                "species confusion must never switch automatically");

        gate.beginSession(EPOCH);
        PetTargetPolicy.Candidate small=new PetTargetPolicy.Candidate("cat",.99f,.1f,.1f,.12f,.13f);
        for(int i=0;i<6;i++)check(tick(gate,T+i*200_000_000L,small)==null,
                "small false-positive patch cannot pass");

        gate.beginSession(EPOCH);
        check(!gate.tapSelect(.5f,.5f,Arrays.asList(c("car",.99f,.4f,.4f))),"wrong tap class");
        check(gate.tapSelect(.25f,.3f,Arrays.asList(c("dog",.91f,.21f,.24f))),
                "known pet should be selectable");
        check(tick(gate,T,c("dog",.90f,.21f,.24f))==null,"tap cannot skip confirmation");
        check(tick(gate,T+100_000_000L,c("dog",.90f,.21f,.24f))==null,"tap 2");
        check(tick(gate,T+200_000_000L,c("dog",.90f,.21f,.24f))!=null,"tap 3");
        check(tick(gate,T+300_000_000L,c("dog",.99f,.70f,.70f))==null,"pinned cannot jump");

        gate.beginSession(EPOCH);
        check(tick(gate,T,c("cat",.99f,.1f,.1f))==null,"re-entry");
        check(gate.update(EPOCH+1,T+10_000_000L,T+10_000_000L,
                Arrays.asList(c("cat",.99f,.1f,.1f)))==null,"epoch changed");
        check(gate.update(EPOCH,T+200_000_000L,T+1_700_000_000L,
                Arrays.asList(c("cat",.99f,.1f,.1f)))==null,"stale inference");
        check(tick(gate,T+300_000_000L,c("cat",.99f,.1f,.1f))==null,"no stale promotion");
        check(tick(gate,T+500_000_000L,c("cat",.99f,.1f,.1f))!=null,"three valid after stale");
        check(PetTargetPolicy.speciesFor("  DOG ")==PetTargetPolicy.Species.DOG,"case normalizing");
        check(PetTargetPolicy.speciesFor("plant")==null,"category whitelist");
        System.out.println("PASS: PetTargetPolicyHostTest v3.00 (cat/dog label, score, 3-hit, tap, IoU, epoch, stale)");
    }
}
