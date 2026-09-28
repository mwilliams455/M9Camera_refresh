# M9AECADENCE1A — exposure response timing, not brightness retuning

Parent: 2.05 EXACTPATCHCLIP1B, commit a00e722bf25b4c609ae9addcc4b612e6d8e434d6.
Candidate: 2.06-m9aecadence1a-exactpatch1b-ae1n-perf3i, version code 26726.

The existing 250ms probe schedule runs at most 4Hz. Normal exposure acquisition is
one 0.25EV step per fresh probe; ordinary release requires two fresh agreeing probes
per step. The first response candidate retains those per-sample decision rules.
It requests a new probe every 125ms while settling, at startup, and on tap/clear/owner
changes, with a 500ms tail before returning to 250ms idle cadence.

The one-readback-in-flight gate, zero-timeout fence polls, complete eleven-step
32x24 probes, full colour/tone shader, manual precedence and highlight thresholds
are unchanged. Repeated or out-of-order textures cannot create extra samples.
A scheduling hint and four timing values are added to diagnostics. These are not
inputs to the photographic target or damage checks.

This is a requested cadence, not a measured device settling-time guarantee. Camera
frame rate, hardware AE, source validity, queued GL work, and the existing evidence
readback serialization can all slow it. Consecutive observations arrive sooner, so
dynamic scene noise/hysteresis stability requires real-device testing.

No +0.50EV tap ceiling, night-scene brightness fix, automatic region-renewal fix,
new autofocus policy, HDR, local tone mapping, renderer change, shutter/ISO allocation
change or reduction in JPEG/DNG quality is bundled here. Existing night-Auto target
behaviour remains deliberately unchanged; faster arrival is not a cure for a bad target.

CI runs all inherited complete-class tests on both versions, compares the 1,152-step
synthetic no-tap differential, then tests the actual GL meter with stubbed Android/GL
services and a synthetic clock. The stub test is not a GPU benchmark. All existing
compilation inputs are checked after build. All lib/, assets/ and res/raw/ APK bytes
must match the actual delivered 2.05 APK. The package, signer and version increment
are checked. No private photographs or capture-derived fixtures are published.
