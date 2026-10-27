# M9Cam 3.05 AFTRACKING2A — arbitrary-subject AF-C follow-through

## Exact parent

Based on M9Cam **3.04 FocusControl1A** (`codex/focuscontrol1a-areas-subject-afstate`), which inherits the existing 2.72 optional visual-patch tracker, the AF-continuity and lifecycle corrections, plus the user-tested 3.03 human/pet work. No production `main` merge.

## What this stage implements

- **Existing Settings → Capture → Focus tracking remains opt-in/off by default.** Select **Continuous Picture AF**, then tap a textured arbitrary subject; the existing white box follows it through the preview. Semantic face/pet detection is *not* required.
- The arbitrary tracker receives a dedicated Camera2 `TrackingFocus` handle. Human-eye, animal-body/eye, Spot, Expand Spot and Custom area handles remain unchanged.
- A new per-handle `ArbitraryAfUpdateGate` reduces redundant Camera2 AF-region submissions while accepting meaningful movement. First target submission is immediate, further submissions have a 90 ms hard minimum and a 180 ms normal cadence, and small jitter is skipped. This is not a semantic detector or a new focus-distance controller.
- Continuous Picture AF is retained; the existing Camera2 HAL performs lens convergence when the requested focus region moves. No repeated `AF_TRIGGER_START` and **no AE/AWB metering changes** are introduced.
- Tracking identity, confidence, stale-frame/camera/zoom gating, preview rotation/mirror mapping and focus release remain inherited from 2.72/2.75. A lost target still requires retapping; no automatic takeover by another object.
- All M9 and Monochrom RAW, DNG, JPEG, colour, tone, calibration, shading, exposure, optical processing and native libraries are unchanged.

## Verification

The host test checks the first region, stationary/jitter refusal, 90/180 ms cadence, large movement, focus-area sizing, timestamp regression, invalid regions, slow cumulative movement and new-handle reset. Run:

```sh
javac -Xlint:all -d /tmp/m9-aftracking2a \
  patches/aftracking2a/src/com/particlesdevs/photoncamera/control/tracking/ArbitraryAfUpdateGate.java \
  patches/aftracking2a/host/ArbitraryAfUpdateGateTest.java
java -ea -cp /tmp/m9-aftracking2a ArbitraryAfUpdateGateTest
```

`apply.py` validates that 3.04's unique Camera2 and legacy tracker anchors are present, only changes the dedicated tracker handle and adds the gated AF-region decision, then updates app metadata to **3.05**. Android CI must compile the reconstructed app, run focus/shutter regression suites and check the APK before device use. These tests are **not proof of HAL focus accuracy**.

## Required on-phone test

With the signed build (when available), enable **Focus tracking** and **Continuous Picture AF** on an AF-capable lens. Tap a textured object away from faces/pets. Move it laterally and nearer/farther, capture a still as the target moves, and check **both box following and actual JPEG sharpness**. Repeat after orientation/zoom/lens switches, deliberate occlusion, M9↔Mono switch and capture/background recovery. Compare the same scene with the feature disabled. Check that contrast/exposure/white balance do not flicker or drift. Track output can be correct even when AF-C has not achieved focus; never infer focus lock just from a box.

## Limitations

This is **not** firmware-equivalent Hasselblad AF-T. It does not recognise arbitrary objects semantically, predict depth, track severely deforming/rapid targets, or guarantee focus on devices whose Camera2 AF regions are unsupported or ignored. The inherited 2.72 tracker remains a local-template matcher. The new cadence policy deliberately leaves human-eye and pet focus paths alone.
