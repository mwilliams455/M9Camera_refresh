# M9 Project Handoff v2.80 — METADATAFIX1A complete / bounded edge-placement lift next

Date: 2026-09-05

## Current branch / repository

- Repository: `mwilliams455/M9Camera_refresh`
- Active branch: `m9metadatafix1a`
- Parent research branch: `m9edgeplacement1a-offline1`
- METADATAFIX1A build commit: `2c67415c005e4e295a99268242bf7b1b12974a8b`
- GitHub Actions run: `33961948707`
- Result: **SUCCESS**
- Artifact: `M9Cam-METADATAFIX1A`
- Artifact id: `9968248462`
- Artifact digest: `sha256:68fd8a371d2b60a73e302c25ea8ae937e6d636789b65dd111dc014c73c90e413`

## Project priorities remain frozen

Do not trade photographic quality for speed. The current renderer is broadly successful and should remain the photographic baseline.

Frozen unless an explicitly isolated experiment says otherwise:

- R3.8-H25/TG1
- Cobalt Xiaomi 15 Ultra main-camera calibration
- M9 bridge/HSM
- SAT3 M06/M07
- firmware curve02
- exact BT.601 4:2:2
- 12 MP output
- JPEG quality 95
- DNG output
- current capture/TC20 behaviour

The remaining work is bounded edge-case correction, not a global redesign.

---

# 1. METADATAFIX1A — implementation complete

## Why it was needed

The M9 JPEG EXIF path inherited Photon's generic ISO handling. `ParseExif.parse()` takes Camera2 `SENSOR_SENSITIVITY` and multiplies it by `IsoExpoSelector.getMPY()`. That caused the JPEG EXIF ISO to appear approximately 2× the physical sensor ISO in the M9 path even though renderer math and DNG capture values were using the physical Camera2 ISO correctly.

The metadata work was deliberately separated from exposure and colour changes so that it is pixel-neutral.

## Implemented changes

### JPEG ISO / PhotographicSensitivity

For M9 primary JPEGs only:

- take physical `CaptureResult.SENSOR_SENSITIVITY`;
- overwrite the copied JPEG EXIF `PHOTOGRAPHIC_SENSITIVITY` with that value;
- do not modify upstream/non-M9 Photon metadata behaviour.

Expected example:

- Camera2 physical ISO = 50
- `_M9.json` ISO = 50
- JPEG EXIF PhotographicSensitivity = 50
- not 100 from the Photon internal multiplier.

### DNG ISO

No DNG ISO patch was applied.

The current DNG path already:

1. reads `CaptureResult.SENSOR_SENSITIVITY`;
2. passes it into `Parameters.FillDynamicParameters()`;
3. stores the physical sensitivity as `parameters.iso`;
4. writes that value with `DngCreator.setIso()`.

The DNG path is therefore deliberately left frozen unless on-device verification proves otherwise.

### JPEG ApertureValue

Photon had effectively duplicated the physical f-number into both `FNumber` and `ApertureValue`.

M9 JPEG finalisation now:

- keeps `FNumber` as the physical lens f-number;
- computes EXIF `ApertureValue` as APEX Av:
  `Av = 2 * log2(f-number)`.

### JPEG Orientation

The M9 JPEG renderer already writes physically rotated output pixels.

M9 JPEG EXIF is therefore normalised to:

- `Orientation = 1` / normal.

This prevents metadata-driven double rotation in viewers.

### JPEG capture date/time

The asynchronous EXIF finaliser previously risked representing finalisation wall-clock time rather than the actual capture identity.

M9 finalisation now extracts `YYYYMMDD_HHMMSS` from the `IMG_YYYYMMDD_HHMMSS_...` filename when available and writes it to:

- DateTime
- DateTimeOriginal
- DateTimeDigitized

Fallback remains the existing EXIF timestamp if filename recovery is unavailable.

### JPEG Compression tag

The M9 JPEG helper previously assigned JPEG quality (95) to the EXIF/TIFF Compression field.

That field is not a JPEG quality field.

For M9 primary JPEGs:

- EXIF Compression is omitted;
- actual JPEG encoding remains `Bitmap.compress(... JPEG_QUALITY=95 ...)` unchanged.

### Software identity

M9 JPEG EXIF now writes:

- `Software = M9Cam`

Make/Model remain the actual Xiaomi/device identity. The application does not falsely claim that the file was physically captured by a Leica M9.

### Metadata diagnostics

PRIMARY diagnostics now expose metadata verification evidence under schema:

- `m9cam.metadata.v1a`

including fields for:

- JPEG PhotographicSensitivity
- capture DateTime
- ApertureValue
- Software
- Orientation
- Compression-tag omission

## CI result

Actions run `33961948707` passed all stages:

- checkout
- frozen M9 cumulative patch chain
- METADATAFIX1A apply + verifier
- JDK / Android setup
- APK build
- artifact upload

Therefore **metadata implementation/build verification is complete**.

## Important remaining runtime check

Do not claim full metadata closure until an actual APK-produced JPEG is inspected.

Use only two shots:

1. low/base ISO daylight shot;
2. higher-ISO indoor shot.

For each, compare JPEG EXIF to `_M9.json` / Camera2 values:

- ISO
- ExposureTime
- FNumber
- FocalLength
- Orientation
- DateTimeOriginal
- Software

Expected result: metadata-only change; JPEG pixels/rendering visually identical to the frozen baseline.

If those two shots match, METADATAFIX1A can be considered runtime-validated and frozen.

---

# 2. Exposure / edge placement — current conclusion

The recent prospective visual-first test strongly changed the interpretation of the remaining exposure problem.

The system does **not** have a general capture-exposure calibration failure.

Ordinary successful M9-like photographs can be:

- globally dark;
- locally very dark;
- TC20 guard-limited;
- TC20 median-limited;
- captured at zero assist;
- captured with positive assist;
- associated with a diagnostic meter requesting substantial positive EV;
- associated with a diagnostic meter requesting negative EV.

Therefore none of the following is a valid standalone DARK selector:

- low finished JPEG median;
- high dark fraction;
- TC20 guard binding;
- large median-vs-guard suppression;
- positive MFM capture assist;
- positive diagnostic exposure recommendation;
- RENDERMETER1C starvation/lift signals.

## Prospective readiness

Latest accepted visual-first controls:

- `084106` GOOD
- `084129` GOOD
- `084146` GOOD
- `084154` BOUNDARY
- `084224` GOOD
- `084303` GOOD
- `084325` GOOD hard negative
- `084328` GOOD hard negative
- `084333` GOOD hard negative (visual-only)
- `084513` GOOD
- `084525` GOOD hard negative
- `084712` GOOD
- `084858` GOOD hard negative

Current global readiness count before any further incoming JPEGs:

- GOOD: **28 / 30**
- BOUNDARY: **6**
- BRIGHT_FAIL: **6**
- DARK_FAIL: **3**

Only two further ordinary GOOD controls are needed to clear the global GOOD-count guard.

## Strongest new hard negative

`084858` is especially important:

- visually GOOD;
- extremely dark finished image;
- zero actual capture offset;
- diagnostic meter requested roughly +0.9 EV;
- severe TC20 median demand / highlight-guard restriction;
- finished global median around 14;
- nevertheless photographically coherent and should not be automatically lifted.

This proves that a future lift cannot simply react to darkness or exposure demand.

## Exposure direction now agreed

Do **not** redesign capture AE.

Do **not** globally lift shadows or black point.

Do **not** alter TC20 globally.

Do **not** apply a universal +0.5 / +0.75 / +1.0 EV correction.

The next exposure change should be a **bounded finished-placement lift** that activates only on rare, visually under-placed failures.

Desired behaviour:

- preserve M9 density and contrast principles;
- preserve intentional silhouettes and deep foregrounds;
- preserve black-subject scenes such as the dog controls;
- preserve canopy and strong backlight hard negatives;
- only genuine under-placed edge cases receive a slight lift.

Initial treatment magnitude should remain small, approximately **+0.15 to +0.35 EV equivalent** as a working investigation range, not yet frozen.

The exact activation rule and amount must be validated against GOOD hard negatives before promotion.

Historical useful DARK anchor:

- `IMG_20260904_164048_1788536448208_00` — confirmed DARK example / likely former visual #73, sculpture/statue against bright field/sky.

`IMG_20260904_164019_...` remains a DARK candidate only.

No need to recover old archive ordinals before continuing.

---

# 3. Next exposure implementation recommendation

Working name: `EDGEPLACEMENTLIFT1A`

This should be implemented only after:

1. METADATAFIX1A two-shot runtime validation;
2. the final two GOOD controls are received/classified.

Principles:

- classifier/treatment operates on the finished-placement problem, not generic scene darkness;
- no local tone mapping;
- no face detector / semantic detector;
- no global black lift;
- no capture EV rewrite;
- no TC20 rewrite;
- correction is globally applied only after a conservative scene-level gate;
- `GOOD + M9_IMPROVABLE` remains exposure GOOD and never activates the lift.

Candidate research evidence can include RENDERGRID/INTENTCOLLAPSE geometry, but the existing Part-3 descriptive thresholds must not be blindly promoted because they were discovered on a small cohort.

Before live promotion, test any proposed gate against the recent prospective hard negatives, especially:

- `084325`
- `084328`
- `084333`
- `084525`
- `084858`

A gate that activates on these is rejected.

---

# 4. Tungsten green cast — next colour track after exposure

A separate issue has been visually identified under tungsten / mixed warm artificial light:

- green/olive tint in nominal neutrals and skin;
- likely green-magenta-axis issue rather than simple colour temperature error.

Do not address it during exposure work.

After edge placement is stable, open a separate diagnostic/treatment track, working name:

- `TUNGSTENTINT1A`

Likely investigation order:

1. Camera2 neutral point / AWB under low CCT and mixed illumination;
2. Cobalt + M9 bridge/HSM behaviour under tungsten;
3. TG1 activation/strength and negative Cb/Cr response.

Keep daylight M9 colour frozen. The desired fix is bounded to low-CCT / mixed-light failures, not a global colour-science change.

---

# 5. Development order from here

1. Install/test `M9Cam-METADATAFIX1A` from Actions run `33961948707`.
2. Take two metadata-validation photographs: low ISO + higher ISO.
3. Confirm JPEG EXIF against `_M9.json` / physical Camera2 values.
4. Receive/classify the final two ordinary GOOD exposure controls if available.
5. Freeze metadata.
6. Implement/replay conservative `EDGEPLACEMENTLIFT1A` with a slight bounded lift only on genuine DARK_FAIL cases.
7. Validate zero activation on all recent GOOD hard negatives.
8. Re-check BRIGHT_FAIL handling separately; do not assume symmetry with DARK_FAIL.
9. Freeze exposure/placement once specificity is demonstrated.
10. Begin `TUNGSTENTINT1A` green-cast investigation.
11. Only afterward return to downstream M9-character refinement (`M9_IMPROVABLE`) and non-visible cleanup/performance work.

---

# 6. Hard invariants for the next chat

- Current JPEG look is the baseline, not a draft to globally brighten.
- M9 darkness is often correct and must be preserved.
- Rare bad exposure placement should receive only a small bounded correction.
- DNG/Lightroom remains the escape route for ambiguous personal interpretation.
- BRIGHT_FAIL and DARK_FAIL remain asymmetric until evidence proves otherwise.
- M9ness remains a separate downstream axis from exposure placement.
- No live selector should be promoted merely because it fits the old Part-3 cohort.
- Metadata changes must remain pixel-neutral.
- Tungsten work must remain separate from exposure work.
- Preserve quality-95 12 MP JPEG + DNG output.

## Immediate prompt for continuation

> Validate METADATAFIX1A using one low-ISO and one higher-ISO capture. If ISO/shutter/aperture/focal length/orientation/timestamp agree with the physical capture, freeze metadata. Then finish the final GOOD-count exposure controls and begin conservative EDGEPLACEMENTLIFT1A, targeting only genuine under-placed failures with a slight +0.15–0.35 EV-equivalent lift while rejecting all recent dark-but-GOOD hard negatives. Do not alter frozen capture AE, TC20, R3.8-H25/TG1, Cobalt, SAT3, curve02, BT.601, JPEG quality, or DNG output. Tungsten green-cast work follows only after exposure is closed.
