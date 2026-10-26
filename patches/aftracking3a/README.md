# M9Cam 3.06 AFTRACKING3A — Multiscale patch tracker and safe occlusion hold

**Parent:** phone-positive signed M9Cam 3.05 AFTRACKING2A, branch `codex/m9-aftracking2a-v3.05`.
**Stage branch:** `codex/m9-aftracking3a-v3.06`; do not merge into `main` without user phone validation.

## What changes

- The optional **Settings → Capture → Focus tracking** mode still depends on a user tap and Camera2 Continuous Picture AF. Normal AF-S/manual, Spot/Expand Spot/Custom, Human Eye and Cat/Dog AF are unchanged.
- `PatchTracker.java` retains an immutable 21×21 grey reference to the tapped object, and searches near the previous location at 0.82×, 1× and 1.22× its latest accepted scale. Search is bounded to ±22 reduced-preview pixels per axis and scale is constrained to 0.62–1.7× the original patch size. Ambiguous/weak matches are never published as valid tracking.
- On a weak/ambiguous match the tracker now enters a maximum **850 ms hold** instead of irreversibly losing the target. Hold never updates Camera2 AF regions; it keeps the last region temporarily and shows an amber **Tracking obscured - holding focus** box. Automatic recovery requires two distinct, high-confidence, spatially consistent local appearances of the *original* template before focus updates resume. A long occlusion or stale frame requires another tap; it will not claim semantic re-identification.
- `TrackingFrameDecision` independently checks result age and explicitly maps TRACKING→APPLY, HOLD→no-AF-update, LOST or stale→RETIRE. The inherited 3.05 `ArbitraryAfUpdateGate` cadence remains unchanged at 90/180 ms; no AF trigger pulses, AE/AWB changes, or manual focus modifications.
- The renderer and profiles for M9 and Monochrome, shutter/capture handoff, RAW/DNG/JPEG, exposure, AWB, ISO, lens correction, and all 37 original native libraries/301 baseline assets must remain byte-for-byte identical to 3.05.

## Test evidence boundaries

Local Java tests: `PatchTracker3ATest` exercises scale growth/shrink, translation, partial/full occlusion, two-frame reacquisition, loss timeout, wrong/stale frames, invalid selection; `TrackingFrameDecision3ATest` exercises safe no-AF decisions. Pure Java tests do not verify Camera2 HAL convergence, subject identity under similar-looking occluders or physical optical sharpness.

To reproduce host tests:

```sh
javac -Xlint:all -d /tmp/m9track306 \
  patches/aftracking3a/src/com/particlesdevs/photoncamera/control/tracking/{PatchTracker,TrackingFrameDecision}.java \
  patches/aftracking3a/host/{PatchTracker3ATest,TrackingFrameDecision3ATest}.java
java -ea -cp /tmp/m9track306 PatchTracker3ATest
java -ea -cp /tmp/m9track306 TrackingFrameDecision3ATest
```

Apply after exact 3.05:

```sh
python3 patches/aftracking3a/apply.py /absolute/PhotonCamera_306 --report /tmp/aftracking3a-source.json
```

Source scopes are verified against the 3.05 SHA256 of the inherited tracker. Android CI assembles 3.05, applies this patch, runs host and inherited Android focus/shutter tests, then independently packages and signs 3.06 against exact 3.05 signed installer. Do not call the work phone-validated until a new device capture confirms behaviour.

## Required phone gate

1. Enable Focus tracking and AF-C, tap a high-texture stationary subject. The box should be white; move it horizontally and closer/farther, checking whether the box grows/shrinks without wild jumping and the saved JPEG is sharp.
2. Pass another object briefly across the target and restore it within ~0.8 s. Box should turn **amber with holding message**, lens should not chase the obstruction, and after two stable matches the white box should resume without retap.
3. Cover the target for over a second: tracking must retire to **Tracking lost — tap again**, with no new AF-region commands until retap. Do not auto-select another object in the background.
4. Repeat after M9/Monochrome switch, portrait/landscape orientation, lens/zoom change, shutter capture, and pause/resume. Ensure focus region remains correct and no stale callbacks resurrect it. Keep comparison to 3.05 for AF speed and battery.

**Limitations:** Fixed reference template and local search are not general object re-identification, depth sensing or firmware-equivalent Hasselblad AF-T. Face and pet detectors remain separate. In noisy/low-texture scenes conservative holding/loss is preferable to claiming false focus success. 
