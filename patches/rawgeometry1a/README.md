# M9Cam 2.89 RAWGEOMETRY1A

Defensive RAW geometry validation on main v2.88. The numeric warning review
identified unchecked `int *= double` conversions in Quad Bayer rectangle scaling.
Zero-bottom source rectangles could divide by zero; out-of-range results could
silently saturate to integer limits. These were synthetic validation failures,
not an established cause of a normal-mode phone crash.

Both source rectangles must be non-null, non-negative and non-empty. Scale must
be finite and positive. Every multiplied coordinate must be finite and within
the integer range, and truncation must leave non-empty rectangles. Both results
are computed on copies and validated before either metadata setter is called.
Original inputs are untouched on rejection. This guarantees validation of the
pair before publication; it does not turn the inherited reflection API into a
transactional or thread-atomic metadata writer.

Valid inputs retain double multiplication, truncation and the existing
`targetHeight / active.bottom` coordinate convention, including non-zero origins.
No change to the renderer, exposure, capture submission, assets or native code.

Invalid geometry clears vendor discovery/trials and maximum-resolution flags,
blocks new vendor hints for that logical/physical camera and format, and selects
an advertised ordinary output size. For RAW, fallback sizes must meet the
existing positive/even/addressable 16-bit buffer rules. Prefer the largest under
the existing normal-resolution threshold, otherwise the smallest advertised size.
If none is valid, reject setup through the existing error path; never substitute
unadvertised preview dimensions. The user's Quad Bayer preference is not changed.

The focused installer gate adds 22 tests (202 total), including real controller
selection and publication checks. Current CI also retains the three upstream
fixture tests (205 total). The 29 existing vendor-size session/recovery tests
remain selected. CI and phone results are pending until recorded below.

Source scope is four files: version metadata, CaptureController, RawGeometry1A
and RawGeometryTest. The readable patch and its compressed reconstruction payload
must match. Reverse application exactly restores v2.88. Packaging preserves all
27 native libraries and 285 assets from the accepted v2.88 installer and checks
the accepted signature, version, alignment and compiled resources.

Phone checks after installation over v2.88: ordinary M9 and Monochrom preview,
capture and lens switching; PHOTO/MOTION/NIGHT where available; gallery entry
with manual controls open/closed; background/return; focus and EV. Optional
vendor high-resolution support still requires its own affected-device evidence.

## Local verification, 15 October 2026

Exact reconstruction, reverse restoration and the CI test-fixture-only overlay
passed. The JDK-only host probe passed 16 unchanged pure geometry test methods
and six checks using verbatim extracted controller methods. Its Android metadata,
reflection and app state are explicit stubs; it does not replace Robolectric,
Android compilation, session integration or phone validation.

Run: `python3 patches/rawgeometry1a/host_probe.py /path/to/PhotonCamera_289`.
See HOST_VERIFICATION.txt for source hashes and results.

The user authorized upload and APK building on 15 October, with image-quality
preservation required. Main stays at v2.88 while this candidate is tested.
The host probe additionally compares 100,000 deterministic valid rectangle pairs
against v2.88's original compound-assignment arithmetic. Pass the parent source as
a second argument to verify the old arithmetic against the actual v2.88 file.
No photograph or device image-quality comparison is implied by these checks.
