# M9NEGATIVE1C / SIGNEDCAL1A

Purpose: calibrate the signed completed-RAW exposure recommendation without changing live capture exposure or the frozen M9 renderer.

## Frozen

- SCENEFINGERPRINT1A descriptors, max-distance threshold `1.0`, and 60 s completed-RAW age gate.
- M9NEGATIVE1A recommendation equations, bounds and 0.05 EV deadband.
- CAPTUREMETER1A live capture path and Camera2 ISO/shutter allocation.
- SCENEEXPOSURE1H behavior.
- RENDERMETER1C.
- Motion allocator.
- Native M9 renderer, TC20/H25/TG1/SAT3/BT.601, JPEG quality 95, and DNG sample values.

## Added diagnostics

Each completed RAW now emits `signedCalibration1A` with schema
`m9cam.signedcal.v1.completedraw_coordinates1a`.

The same block is also emitted for the matched completed RAW used during capture-step evaluation.
It records:

- RAW q25/q50/q99/q99.5/q99.8 and hard-clip fraction.
- Frozen lower-body adequacy, shadow-starvation, clip-risk and highlight-stress evidence.
- Positive candidate before deadband.
- Negative candidate before its gates, individual negative gate booleans/margins, and the gated negative candidate.
- Frozen combined candidate and frozen final recommendation.
- EV coordinates required to move q25/q50/q99.8 to the existing provisional threshold landmarks.
- Linear RAW percentile projections at -0.50, -0.25, 0, +0.25 and +0.50 EV.

The projections intentionally do **not** predict hard-clip fraction or scene response. They are simple
counterfactual percentile scaling for calibration only.

## 2026-09-03 validation anchors

The SCENEFINGERPRINT1A test batch showed:

- Backlit window: q50 about 0.0104, q99.8 about 0.9333, hard clip about 3.87%. The clip gate is strong but lower-body starvation is complete, so frozen negative EV remains blocked at 0 EV.
- Healthy bike: q50 about 0.0699, q99.8 about 0.4265, negligible clip. Frozen positive candidate remains below the 0.05 EV deadband.
- Dark bottle/detergent control: q50 about 0.0136, q99.8 about 0.6709, no meaningful clip. Frozen model asks for about +0.456 EV.

No real negative-EV case occurred in that batch. SIGNEDCAL1A exists to collect the evidence needed to calibrate that branch without changing capture behavior.

## Requested next test emphasis

Keep a few repeated-scene pairs for association regression, then deliberately include bright/highlight-heavy scenes where the subject/body is already well exposed (white building/clouds, sunlit pale wall, reflective car, bright shopfront/window exterior). Also include a dark/backlit control. The target is a real case where highlight stress and lower-body adequacy coexist, not simply a clipped window with a starved interior.
