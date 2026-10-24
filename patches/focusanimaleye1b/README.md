# FOCUSANIMALEYE1B — repair 3.02 animal-eye AF (3.03, 24 Oct 2026)

## User video `61834.mp4` and established behaviour

The 37.3-second Xiaomi 15 Ultra M9 recording shows both **Dog AF** and **Cat AF** bounding boxes operating normally, with repeated status messages `Pet DOG body age=65ms pose_GPU` and `Pet CAT body age=82ms pose_GPU` (typical body detection 65–100 ms). The scene includes a white dog and a long-haired cat, with both appearing on screen at different times. There is **no verified Dog Eye AF or Cat Eye AF transition**.

The `pose_GPU` status reported that `AnimalEyePoseEstimator` loaded a GPU model, **not that a valid keypoint observation was returned**. The body-first inference path was functioning.

## Proven primary cause: shared preview bitmap recycled

`PetObjectDetector.detect(bitmap)` in 3.02 wrapped the caller-owned PixelCopy `Bitmap` directly with `new BitmapImageBuilder(image).build()` and then called `mpImage.close()` in its `finally` block. The upstream MediaPipe 0.10.35 class `BitmapImageContainer.close()` unconditionally calls `bitmap.recycle()`:

https://github.com/google-ai-edge/mediapipe/blob/v0.10.35/mediapipe/java/com/google/mediapipe/framework/image/BitmapImageContainer.java

Next, `AnimalEyePoseEstimator.estimate(bitmap,...)` immediately returns null when `preview.isRecycled()`, so animal-eye inference never begins. This explains the persistent `pose_GPU` + body focus messages, even when Cat/Dog AF performs normally.

## Secondary decoder defect: wrong SimCC confidence

The 3.02 adapter computed confidence by applying softmax to each axis of 512 SimCC logits, then multiplying their peak normalized probabilities. The official MMPose decoder `get_simcc_maximum`, default `apply_softmax=False`, instead uses the **raw score `min(max(simcc_x), max(simcc_y))`** and coordinates `argmax/2`, as documented and implemented here:

https://github.com/open-mmlab/mmpose/blob/main/mmpose/codecs/utils/post_processing.py

The former calculation could falsely reject even strongly peaked raw predictions due to normalization across 512 bins.

## 3.03 changes, tightly scoped

1. **Detector owns a separate bitmap**: `PetObjectDetector` passes a dedicated `Bitmap.copy(ARGB_8888,false)` to `BitmapImageBuilder`. Closing the MediaPipe image recycles that detector-only copy; it must never recycle the shared PixelCopy bitmap that the AP10K pose model needs.
2. New pure Java `AnimalSimccDecoder` implements MMPose's raw min-of-peaks score, argmax/2 coordinates, bounded valid indices, rejecting invalid/nonpositive/nonfinite responses.
3. UI/Logcat marks `pose_null_recycled` vs `pose_null_invalid_input` when the pose estimator still returns null. Genuine `eye_unverified`, `nose_unverified`, `eye_confirming` and `eye_ready` gates are preserved.
4. **No change** to existing Human Eye AF, Cat/Dog identification, PetTargetPolicy, AP10K weights, M9/Monochrome RAW, colour, AE/AWB, crop transforms, Camera2 focus request ownership, HDR or native processing.
5. The separate Animal Eye AF preference remains off by default. Invalid poses fall back to body focus.

## Tests and release criteria

`host/AnimalSimccDecoderHostTest.java` demonstrates why a meaningful raw 0.68 SimCC response becomes a spurious ~0.004 peak after the previous 512-bin softmax, and verifies exact coordinate mapping, nonfinite response rejection and missing keypoints. Inherited AP10K acceptance, pet tracking, and MediaPipe copy/ownership source assertions must pass. Android and focus lifecycle regressions must pass. Signed package uses the exact signed **3.02** as parent, retaining all **37** native libraries and all **301** assets byte-for-byte, package certificate and compile menus.

The model-inference numerical score, camera focus convergence and optical animal-eye sharpness still require phone evidence.

## Proposed phone check

Install signed **3.03** over 3.02 without clearing data, enable *both* Cat/Dog AF and Animal Eye AF, keep AF-C. Revisit the same dog/cat under good light. The badge should show `Dog Eye AF`/`Cat Eye AF` once two coherent eye observations are accepted. If not, the new status should distinguish pose-null failures from eye/nose geometry rejection. Record short footage and capture a JPEG for sharpness. Keep the PR draft until confirmed.

This is a source-level root-cause fix, not a claim that 3.03 has already been optically validated on device.
