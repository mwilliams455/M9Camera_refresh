# FOCUSANIMAL1B — Pet AF failure investigation, 24 October 2026

## Phone observation: `61804.mp4`

The user's 29.7-second, 1440 × 3200 screen recording of signed M9Cam 2.99 shows a large, clearly visible long-haired cat in the live M9 viewfinder, with M9/Motion, 1×/24 mm and the camera's `AF-C LOCK` status. The cat is visible standing, sitting and moving and later approaches the camera. Yellow/magenta guide lines appear over the preview, but no `Cat AF`/ `Dog AF` subject box is visibly acquired throughout the recording. The recording briefly shows the Settings landing page, **not** the Capture submenu, so the pet preference's stored enabled state is not directly proved by the video. The absence of a pet-focus box is confirmed; the internal rejection reason is not.

## Actual 2.99 source defects/limitations

- `PetTargetPolicy.MAX_FRAME_AGE_NS=300_000_000`: the model result is rejected more than 300 ms after the sample was *requested*, counting PixelCopy, any model initialization and CPU inference. Results are silent when they exceed this; repeated frames can all fail.
- `MAX_GAP_NS=850 ms`, spatial overlap `> .18`, and three confirmation frames: moving pets can continuously restart confirmation, even with valid cat/dog classification.
- Two nested detector thresholds (.60 MediaPipe, .64 policy) and `setMaxResults(8)` mean low-to-medium indoor confidence is discarded before any pet-specific diagnostics are exposed.
- All model initialization, copy, detection, class filtering, policy rejection and AF-C eligibility failures are effectively invisible on the UI. The video by itself does not demonstrate which one failed.
- The prior model SHA-256 and embedded labels were rechecked: the bundled COCO model has `cat` and `dog` labels in `labelmap.txt`. Package integrity alone does not prove live inference.

## v3.00 bounded correction

- Analyse a 448-pixel-long-edge viewfinder bitmap instead of 640; native EfficientDet-Lite0 input is 320×320.
- Raw detector threshold .15 (for diagnostics), preserve explicit cat/dog class filtering in `PetObjectDetector`, require confidence ≥ .50 in `PetTargetPolicy`, plus three temporally/spatially coherent hits before automatic acquisition.
- Admission can use a detector result up to 1200 ms after the sample request, but **actual Camera2 AF-region movement remains blocked beyond 900 ms**, with `slow result` status. These are deliberately different thresholds: classify first, act only on sufficiently current coordinates.
- Allow bounded inter-frame gaps up to 2 seconds and reduce required candidate overlap to IoU .13, keeping pin/epoch/old-session/subject-class protection.
- Add a small on-screen **Pet AF:** status label only while experimental Cat/Dog AF is enabled. It shows whether detection is running, copy/model failure, model class/score summary, confirmation progress, age and Camera2 eligibility. No photographs or raw image pixels are written to diagnostics.
- Keep the signed 2.99 model, every native library and all existing assets unchanged. The user-confirmed working 2.98 human-eye path, exposure, WB, JPEG/DNG and colour rendering are unchanged.

These changes address credible gate failures and expose the true run-time failure if they are insufficient; they do **not** establish on-phone detection performance before testing.

## Verification

The fixed policy must pass the inherited Cat/Dog class, confidence, subject motion, tap and stale-session cases as well as `PetRuntimeTimingTest` for delayed 600–750 ms model results, 1400 ms staleness, wrong physical-camera epoch and household-object rejection. Android must compile and run inherited focus/handover and capture regressions. Repackaging must preserve all 31 native libraries, all 300 assets, accepted certificate and compatible 16 KiB native alignment.

## Recommended next phone test

Install verified 3.00 over 2.99 without clearing data. Keep **Settings → Capture → Cat / Dog AF** ON and AF-C. Show the exact Capture setting once, then pan the same cat at 1× in Motion and Photo. The visible small diagnostic text should distinguish `no_matching_pet`, `confirming_1/3`, `ready_cat`, `inference_too_old`, `model error` or `AF-C region unavailable`. If the pet target is acquired, follow the cat and capture a sharp still. Do not use cat-eye success claims; this is whole-body AF. Retain the older 2.98 Eye AF phone-positive checkpoint as rollback.

**Keep draft/unmerged** until live model recognition, actual focus sharpness and no-regression across M9 and Monochrome are demonstrated.
