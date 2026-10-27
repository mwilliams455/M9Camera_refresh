import com.particlesdevs.photoncamera.control.tracking.ArbitraryAfUpdateGate;

public final class ArbitraryAfUpdateGateTest {
    private static int checks;
    private static void check(boolean condition, String message) {
        checks++;
        if (!condition) throw new AssertionError(message);
    }
    public static void main(String[] args) {
        ArbitraryAfUpdateGate g = new ArbitraryAfUpdateGate();
        check(g.shouldSubmit(1000, 100, 100, 280, 280), "first target must focus");
        check(!g.shouldSubmit(1110, 100, 100, 280, 280), "same region must not resubmit");
        check(!g.shouldSubmit(1300, 104, 104, 280, 280), "pixel jitter must not hunt");
        check(!g.shouldSubmit(1070, 300, 100, 280, 280), "no burst under 90 ms");
        check(!g.shouldSubmit(1100, 135, 100, 280, 280), "modest movement waits normal cadence");
        check(g.shouldSubmit(1190, 135, 100, 280, 280), "slow tracking advances after 180 ms");
        check(!g.shouldSubmit(1270, 190, 100, 280, 280), "region throttle applies to every update");
        check(g.shouldSubmit(1290, 320, 100, 280, 280), "large motion can update after 90 ms");
        check(g.shouldSubmit(1390, 320, 100, 350, 300), "area-size switch must be applied");
        check(!g.shouldSubmit(1380, 400, 100, 350, 300), "backwards sample time rejected");
        check(!g.shouldSubmit(1500, -1, 10, 350, 300), "negative coordinates rejected");
        check(!g.shouldSubmit(1500, 0, 0, 0, 300), "invalid region size rejected");
        check(new ArbitraryAfUpdateGate().shouldSubmit(10, 100, 100, 280, 280),
                "new tap/session gets a fresh gate");
        // A very slow subject must eventually cross the gate relative to the last
        // submitted AF region; rejected candidates never redefine the anchor.
        ArbitraryAfUpdateGate slow = new ArbitraryAfUpdateGate();
        check(slow.shouldSubmit(1000, 0, 0, 200, 200), "slow movement start");
        for (int x = 1; x < 18; x++)
            check(!slow.shouldSubmit(1000 + x * 150L, x, 0, 200, 200), "jitter accumulate");
        check(slow.shouldSubmit(3700, 20, 0, 200, 200), "accumulated slow movement updates");
        System.out.println("PASS: " + checks + " arbitrary AF cadence checks");
    }
}
