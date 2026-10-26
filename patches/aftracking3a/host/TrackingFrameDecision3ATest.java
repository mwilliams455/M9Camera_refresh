import com.particlesdevs.photoncamera.control.tracking.PatchTracker;
import com.particlesdevs.photoncamera.control.tracking.TrackingFrameDecision;
import static com.particlesdevs.photoncamera.control.tracking.TrackingFrameDecision.Action;

public final class TrackingFrameDecision3ATest {
    private static int checks;
    static void check(boolean ok, String message) {
        checks++; if (!ok) throw new AssertionError(message);
    }
    public static void main(String[] args) {
        PatchTracker tracker = new PatchTracker();
        final int width = 96, height = 80;
        int[] pixels = new int[width*height];
        java.util.Random rand = new java.util.Random(990);
        for (int i=0;i<pixels.length;i++) {
            int v = 16 + rand.nextInt(223);
            pixels[i] = 0xff000000 | (v<<16) | (v<<8) | v;
        }
        PatchTracker.Result first=tracker.select(pixels,width,height,.5f,.5f,1000);
        check(first.tracking,"target admitted for policy test");
        check(TrackingFrameDecision.classify(first,0)==Action.APPLY,"accepted tracker may target AF");
        check(TrackingFrameDecision.classify(first,500)==Action.APPLY,"500 ms is bounded action limit");
        check(TrackingFrameDecision.classify(first,501)==Action.RETIRE,"stale target cannot move AF");
        check(TrackingFrameDecision.classify(first,-1)==Action.RETIRE,"future clock not valid");
        check(TrackingFrameDecision.classify(null,0)==Action.RETIRE,"missing observation retired");
        int[] covered=new int[pixels.length];java.util.Arrays.fill(covered,0xff777777);
        PatchTracker.Result hidden=tracker.update(covered,width,height,1100);
        check(hidden.holding&&!hidden.tracking,"occlusion indicated");
        check(TrackingFrameDecision.classify(hidden,0)==Action.HOLD,"occlusion freezes AF");
        check(TrackingFrameDecision.classify(hidden,501)==Action.RETIRE,"old hold is unsafe");
        PatchTracker.Result lost=tracker.update(covered,width,height,1900);
        check(!lost.tracking&&!lost.holding,"timeout permanently loses subject");
        check(TrackingFrameDecision.classify(lost,0)==Action.RETIRE,"expired hold must release AF");
        System.out.println("PASS: "+checks+" AF frame-decision checks");
    }
}
