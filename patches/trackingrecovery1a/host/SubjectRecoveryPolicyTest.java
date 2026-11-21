import com.particlesdevs.photoncamera.control.tracking.SubjectAnchorPolicy;
import com.particlesdevs.photoncamera.control.tracking.SubjectAppearanceDescriptor;
import com.particlesdevs.photoncamera.control.tracking.SubjectAnchorPolicy.Candidate;
import com.particlesdevs.photoncamera.control.tracking.SubjectAnchorPolicy.State;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/** Detector sequences exercising the production policy, without Android stubs. */
public final class SubjectRecoveryPolicyTest {
    private static int checks, failures;
    private static void check(boolean condition, String message) {
        checks++;
        if (!condition) { failures++; System.err.println("FAIL: " + message); }
    }
    private static SubjectAppearanceDescriptor colour(int rgb) {
        int[] pixels = new int[128 * 128]; Arrays.fill(pixels, 0xff000000 | rgb);
        return SubjectAppearanceDescriptor.sample(pixels, 128, 128, .1f, .1f, .8f, .9f);
    }
    private static final SubjectAppearanceDescriptor BLUE = colour(0x1450d2);
    private static final Candidate SUBJECT = new Candidate("person", .85f, .15f, .12f, .50f, .90f, BLUE);
    private static final List<Candidate> FOUND = Collections.singletonList(SUBJECT);
    private static SubjectAnchorPolicy acquired(boolean identity) {
        SubjectAnchorPolicy p = new SubjectAnchorPolicy();
        p.begin(7, .30f, .40f, 0); p.useAppearance(identity);
        check(p.observe(7, 10, 20, FOUND).state == State.WAITING, "initial confirmation required");
        check(p.observe(7, 100, 120, FOUND).canMoveAf(), "initial target acquired");
        return p;
    }
    private static void interruptedRecovery(String interruption) {
        SubjectAnchorPolicy p = acquired(true);
        check(p.observe(7, 200, 220, Collections.emptyList()).state == State.HOLD, "initial loss holds");
        check(p.observe(7, 300, 320, FOUND).state == State.HOLD, "first recovery observation holds");
        List<Candidate> data = Collections.emptyList(); long frame = 400, now = 420;
        if (interruption.equals("null")) data = null;
        if (interruption.equals("wrong appearance")) data = Collections.singletonList(
                new Candidate("person", .99f, .15f, .12f, .50f, .90f, colour(0xdc2d19)));
        if (interruption.equals("ambiguous")) data = Arrays.asList(SUBJECT,
                new Candidate("person", .85f, .16f, .12f, .51f, .90f, BLUE));
        if (interruption.equals("stale")) { data = FOUND; frame = 310; now = 820; }
        if (interruption.equals("future")) { data = FOUND; frame = 430; }
        check(p.observe(7, frame, now, data).state == State.HOLD, interruption + " must hold");
        check(p.observe(7, now + 100, now + 120, FOUND).state == State.HOLD,
                interruption + " restarts the consecutive recovery count");
        check(p.observe(7, now + 250, now + 270, FOUND).canMoveAf(),
                interruption + " permits recovery after two new coherent observations");
    }
    private static void deadline(boolean secondHit) {
        SubjectAnchorPolicy p = acquired(true);
        p.observe(7, 200, 220, Collections.emptyList());
        if (secondHit) p.observe(7, 900, 920, FOUND);
        // Last accepted target was at 120 ms: the original budget ends at 1270.
        check(p.observe(7, 1260, 1271, FOUND).state == State.RETIRED,
                "fresh " + (secondHit ? "second" : "first") + " hit after hold deadline cannot revive target");
        check(!p.owns(7), "expired target releases semantic ownership");
        check(!p.observe(7, 1400, 1420, FOUND).canMoveAf(), "expired target requires a new tap");
        p.begin(8, .30f, .40f, 1500);
        check(p.observe(8, 1510, 1520, FOUND).state == State.WAITING, "new tap starts clean");
        check(p.observe(8, 1660, 1680, FOUND).canMoveAf(), "new tap can acquire again");
    }
    private static void boundaryAndDuplicate() {
        SubjectAnchorPolicy p = acquired(true);
        p.observe(7, 200, 220, Collections.emptyList());
        check(p.observe(7, 1000, 1020, FOUND).state == State.HOLD, "first late recovery hit");
        check(p.observe(7, 1000, 1030, FOUND).state == State.HOLD, "duplicate cannot confirm");
        check(p.observe(6, 1100, 1120, FOUND).state == State.RETIRED, "old epoch cannot confirm");
        check(p.observe(7, 1250, 1270, FOUND).canMoveAf(), "second hit exactly at inclusive deadline allowed");
        check(p.observe(7, 1400, 1420, FOUND).canMoveAf(), "normal continuous tracking unchanged");
    }
    private static void legacyOff() {
        SubjectAnchorPolicy p = acquired(false);
        p.observe(7, 200, 220, Collections.emptyList());
        check(p.observe(7, 300, 320, FOUND).canMoveAf(), "identity OFF keeps immediate recovery");
        p.observe(7, 400, 420, Collections.emptyList());
        check(p.observe(7, 1500, 1520, FOUND).canMoveAf(), "identity OFF retains legacy timeout policy");
    }
    public static void main(String[] args) {
        for (String reason : new String[]{"empty", "null", "wrong appearance", "ambiguous", "stale", "future"})
            interruptedRecovery(reason);
        deadline(false); deadline(true); boundaryAndDuplicate(); legacyOff();
        System.out.println((failures == 0 ? "PASS " : "FAILED ") + checks + " recovery checks; failures=" + failures);
        if (failures != 0) throw new AssertionError(failures + " production recovery violations");
    }
}
