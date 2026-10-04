# FINISH1N — BODYQUAL1A + SUBJECTHEADROOM1A

Version 2.03 is an experimental single-capture Auto-exposure candidate, not a claim
of photographic acceptance.

BODYQUAL1A qualifies each geometrically eligible connected component before ranking
valid candidates. Geometry, confidence thresholds, tie handling and target formulas
are unchanged. A high-ranked invalid component no longer hides a valid alternative.

SUBJECTHEADROOM1A distinguishes selected-body clipping from background channel
clipping. Only a currently confirmed, severely dark, background-supported body may
use the extended allowance. Only the regional channel-clipping counter outside that
body is deferred, and only while the preceding bracket is below the existing body
target and the next bracket makes useful progress within the existing body safety
rules. The first target-reaching bracket may be used; no new target is added.

Global channel-clip growth, global near-white growth, regional broad near-white
limits, subject-field clipping, BGQUAL1A and open-anchor caps are retained. The
baseline highlight API remains intact for callers without qualified body evidence.
The live controller requires a current valid proposed body overlapping the latched
body; a stale body lock alone cannot authorize the extra allowance.

No renderer, TC20, SAT2, curve02, TG1, colour, noise, DNG, queue or preview shader
change is made. There is no local exposure adjustment or multi-frame HDR.

The host suite runs the complete new Java class against the inherited policy tests
and synthetic candidate-order, subject/background, target-stop and safety tests.
These tests do not establish semantic subject recognition or real RAW/JPEG parity.
The returned private analysis package contains actual-capture replay evidence; no
new private captures, pixel buffers or capture-derived fixtures are committed here.

`ci.py` replays a SHA-256-pinned parent workflow's shell blocks without changing the
inherited test bodies, then preserves its packaged APK/signing checks with updated
candidate identity markers. The outer workflow owns checkout, Java and uploads.
