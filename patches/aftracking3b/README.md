# M9Cam 3.07 AFTRACKING3B — subject-aware arbitrary tracking assist

**Parent:** signed 3.06 AFTRACKING3A, still the tested installed baseline. The uploaded `62889.mp4` (26 October 2026; 25.8 seconds) shows repeated `Tracking obscured - AF area held` and `Tracking lost - tap again` during ordinary child and dog movement. Camera2's `AF reported focused` is independent of whether the correct visual subject is retained. The recording does **not** demonstrate a firmware fault or establish saved-image sharpness.

## Diagnosis

3.06 matches a single immutable 21×21 luminance template with three nearby scales (0.82, 1.0, 1.22), a ±22-pixel local search, and strict correlation/ambiguity gates. A person rotating from face to back necessarily changes that template. A long enough run of low correlation becomes `Tracking lost` even with the person still visible. Increasing an occlusion timeout alone risks following furniture/other subjects and is not an identity solution.

## Experimental correction

**Opt-in** Settings → Capture → **Subject-aware tracking (experimental)**, default OFF, requires the existing **Focus tracking** toggle + continuous-picture AF. This is not Hasselblad vendor code. It reuses the existing pinned offline COCO EfficientDet-Lite0 model already included for Cat/Dog AF and keeps the 3.05 Camera2 tracking handle/cadence.

- **People, cats and dogs:** two coherent detector frames of a tap-containing class (minimum confidence 0.45) establish a spatially pinned identity anchor. The chosen point retains its relative position on the target's detected body as appearance and body orientation change. A person turning away need not visually match the original 21×21 tap patch. Face/eye and Pet AF dedicated modes are not modified and remain mutually exclusive with generic patch tracking.
- **Arbitrary objects:** keep the existing 3.06 local 21×21 multi-scale patch tracker. With assist OFF, the preview sample is still **256-pixel long edge** and original frame/AF request logic remains the fallback. When assist is ON, the same single-flight PixelCopy reads a 448-pixel-long-edge sample for the on-device model and 2×2 downsamples to 256 pixels for patch correlation.
- **Occlusion, no theft:** don't follow a different recognised class or a distant person/pet. If detector results become ambiguous or the selected subject disappears, hold the previous AF area without sending a new AF request for up to 1150 ms. No stable identity match means the user must tap again. Model observations must be fresh (500 ms maximum action age). Existing 3.05 AF-region throttling remains.
- **Preview semantics:** amber *Identifying subject - AF area held* distinguishes model warm-up from genuine temporary occlusion. The white box is *tracking* rather than proof of optical sharpness. Pixel-copy failures and stale/lens/profile/session callbacks still never mutate Camera2 after retirement.
- **No new model or native dependencies:** reuse pinned `efficientdet-lite0.tflite`, MediaPipe 0.10.35 and accepted native payload; MediaPipe receives an isolated bitmap copy because `MPImage.close()` recycles its bitmap.

## Source verification

`SubjectAnchorPolicyTest` exercises tap ownership, person turns/movement, relative point retention, two-frame acquisition, visible target loss/return, wrong-class/wrong-person rejection, repeated/stale frames, timeout/retirement, pet classes and non-semantic fallback (34 host assertions). Inherited 3.06 PatchTracker3A, TrackingFrameDecision3A and 3.05 autofocus-gate host suites remain required. Android CI must build the full M9 and Monochrome app, run focus lifecycle/shutter tests, package the signed APK using **the exact signed 3.06 APK as parent**, and assert all 37 inherited native libraries and 301 original assets are identical. Diagnostics, colour, exposure, DNG/JPEG and other focus modes must not be changed.

## Device acceptance

1. Start with subject-aware tracking **OFF** and confirm existing 3.06 still behaves the same (safe rollback comparator).
2. Turn both **Focus tracking** and **Subject-aware tracking** ON. Using AF-C, tap the child's head/upper body and have them turn from face to side/back while moving. The region should remain with the chosen person, with no random background jumps. Repeat in M9 and Monochrome.
3. Include dog foreground crossings; the selected person must not switch to the dog. Next, explicitly tap the dog and test pet tracking. Then tap a textured toy/furniture item and ensure the arbitrary patch path still works.
4. Occlude the selected person briefly, then more than ~1 second. A brief obstruction should HOLD then recover if the same subject is recognised; a longer absence should retire without stealing another target. Verify every mode after zoom, lens switches, orientation changes and pause/resume. Confirm AF remains active and saved JPEGs are actually sharp.
5. A single 25.8-second screen recording does not establish optical AF convergence, detector CPU cost, temperature, battery or wide-device compatibility. Test these separately. Do not merge into `main` before device validation.

**Known limits:** COCO bounding boxes have no persistent person ID or formal re-identification embedding. Spatial/temporal gating cannot guarantee identity among overlapping similar-looking people or under lengthy full occlusion. Detector false negatives may still cause *hold/lost*. Only supported Camera2 AF-region devices can perform moving-region AF. This stage is experimental, not Hasselblad AF-T firmware equivalence.

