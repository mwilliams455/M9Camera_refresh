import com.particlesdevs.photoncamera.control.subject.PetTargetPolicy;
import java.util.Arrays;
import java.util.Collections;

/** FOCUSANIMAL1B: regression for real PixelCopy+inference latency budget. */
public final class PetRuntimeTimingTest {
    private static final long E=42L, T=6_000_000_000L;
    private static final PetTargetPolicy.Candidate CAT=
        new PetTargetPolicy.Candidate("cat",.57f,.2f,.2f,.65f,.7f);
    private static void require(boolean okay,String message) {
        if(!okay)throw new AssertionError(message);
    }
    private static PetTargetPolicy.Target update(PetTargetPolicy p,long time,long elapsed,
            PetTargetPolicy.Candidate...candidates) {
        return p.update(E,time,time+elapsed,Arrays.asList(candidates));
    }
    public static void main(String[] args) {
        PetTargetPolicy gate=new PetTargetPolicy();
        gate.beginSession(E);
        require(update(gate,T,600_000_000L,CAT)==null,"a single delayed hit never acquires");
        require("confirming_1_of_3".equals(gate.lastDecision()),gate.lastDecision());
        require(update(gate,T+700_000_000L,660_000_000L,CAT)==null,
                "two measured frames still unconfirmed");
        PetTargetPolicy.Target t=update(gate,T+1_400_000_000L,750_000_000L,CAT);
        require(t!=null && t.species==PetTargetPolicy.Species.CAT,
                "three real delayed COCO pet detections should be admitted");
        require("ready_cat".equals(gate.lastDecision()),gate.lastDecision());
        require(update(gate,T+2_100_000_000L,1_400_000_000L,CAT)==null,
                "1400ms stale results must not update autofocus");
        require("inference_too_old".equals(gate.lastDecision()),gate.lastDecision());
        require(gate.update(E+1,T+2_200_000_000L,T+2_200_000_000L,
                Collections.singletonList(CAT))==null,
                "wrong lens epoch must not update autofocus");
        require(update(gate,T+2_300_000_000L,220_000_000L,
                new PetTargetPolicy.Candidate("plant",.99f,.2f,.2f,.65f,.7f))==null,
                "ordinary household objects never become pet focus targets");
        gate.beginSession(E);
        for(int k=0;k<5;k++)
            require(update(gate,T+k*350_000_000L,140_000_000L,
                new PetTargetPolicy.Candidate("cat",.25f,.2f,.2f,.65f,.7f))==null,
                "weak false detections never automatically focus");
        gate.beginSession(E);
        require(update(gate,T,600_000_000L,CAT)==null,"confirmation restarts on session reset");
        require(update(gate,T+3_000_000_000L,600_000_000L,CAT)==null,
                "time gaps break multi-hit confirmation");
        require("confirming_1_of_3".equals(gate.lastDecision()),gate.lastDecision());
        System.out.println("PASS: PetRuntimeTimingTest (700ms inference, reasons, stale focus, category)");
    }
}
