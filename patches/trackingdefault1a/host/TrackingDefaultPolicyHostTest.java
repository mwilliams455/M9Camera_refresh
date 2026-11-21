import com.particlesdevs.photoncamera.control.tracking.TrackingDefaultPolicy;

public final class TrackingDefaultPolicyHostTest {
    private static int assertions;
    private static void check(boolean ok, String reason) {
        assertions++;
        if (!ok) throw new AssertionError(reason);
    }
    public static void main(String[] args) {
        check(TrackingDefaultPolicy.eligible(true,true,true,true,true,false),
                "new install in Wide AF-C eligible");
        check(!TrackingDefaultPolicy.eligible(true,true,false,true,true,false),
                "saved explicit OFF remains OFF");
        check(!TrackingDefaultPolicy.eligible(true,true,true,false,true,false),
                "AF-S and manual never hijacked");
        check(!TrackingDefaultPolicy.eligible(true,true,true,true,false,false),
                "Spot/Expand/Custom use their existing tap owner");
        check(!TrackingDefaultPolicy.eligible(true,true,true,true,true,true),
                "dedicated pet AF owns regions");
        check(!TrackingDefaultPolicy.eligible(true,false,true,true,true,false),
                "unsupported mode");
        check(!TrackingDefaultPolicy.eligible(false,true,true,true,true,false),
                "non-M9 rendering mode");
        check(!TrackingDefaultPolicy.warmSemantic(false,true),
                "no semantic warm-up on idle preview");
        check(!TrackingDefaultPolicy.warmSemantic(true,false),
                "subject recognition switch OFF");
        check(TrackingDefaultPolicy.warmSemantic(true,true),
                "warm-up occurs only after explicit tap");
        System.out.println("PASS " + assertions + " tracking-default eligibility checks");
    }
}
