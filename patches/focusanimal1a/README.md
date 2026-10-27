# FOCUSANIMAL1A — M9Cam 2.99 experimental Cat/Dog AF

## Accepted parent and scope

The user confirmed on 24 October 2026: **"Eye focus works!"** on signed 2.98 FOCUSSUBJECT1B. That is the accepted human-eye checkpoint, not a reason to modify its successful selection mechanism.

This source branch derives from exact 2.98, with no source change to M9/Monochrom RAW capture, renderer, exposure, white balance, or the existing sensor/viewfinder focus coordinate transform.

## What 2.99 adds

- Opt-in **Settings → Capture → Cat / Dog AF** in both M9 and Monochrom.
- Bundled, CPU-run **EfficientDet-Lite0 COCO** object-detection model, with a label allowlist limited to **cat** and **dog**. It is fetched into build assets from Google's official TensorFlow examples source and pinned by SHA-256 before release. **No runtime network, no Play Services model fetch.**
- **MediaPipe Tasks Vision** rather than legacy TensorFlow Task Vision, because newer Android devices require native ELF 16-KiB memory-page compatibility. Package validation explicitly tests every new ARM64 native library.
- One reduced **640-pixel-long-edge PixelCopy** viewfinder sample at a time on a separate inference worker. Automatic acquisition requires **three coherent frames**, sufficient confidence and a contiguous bounding box of the same species; sudden spatial jumps cannot silently switch pets.
- The existing `CaptureController.TrackingFocus` takes the selected target's **whole-body centre** as an AF-C region. **This is not yet eye/head landmark localisation** and the displayed `Cat AF`/`Dog AF` label is not proof that the lens is sharply focused.
- User tap selects a known detected pet; a tap outside a detected cat/dog returns control to ordinary manual tap-to-focus.
- If the target is lost or the camera rotates/switches lens/profile/zoom/capture session, stale detections and AF updates are retired. Unsupported AF-C/fixed-focus lenses safely disable the optional feature.

## Focus priorities

When Cat/Dog AF is on, it takes priority over Human Face/Eye AF and legacy patch tracking, even if their stored settings are also on. Switching Cat/Dog AF off returns control to the earlier selected focus setting. All modes default off until explicitly selected; the normal autofocus and manual tap-focus route remains available.

## Evidence and release gates

`host/PetTargetPolicyHostTest.java` checks ordinary objects and wrong species are rejected, a single-frame detection never controls AF, repeated low-confidence detections never acquire, taps require reconfirmation, tracking retains subject identity across movement, and stale/wrong-session callbacks cannot acquire.

CI reconstructs exact 2.95 then overlays accepted 2.98 and optional 2.99. It downloads and hashes the published model, builds Android, executes inherited eye/tap/AF/shutter regressions, preserves all original 2.98 native libraries/assets, checks new ARM64 native ELF alignment, verifies both compiled settings menus and independently signs and reopens the installer.

**Phone validation is still required**: use a visible cat or dog, repeat against furniture, move near/far and across the screen, tap a second pet, switch between M9 and Mono, check still-image sharpness and shutter reliability. Neither live tracking accuracy nor animal-eye localization has been established on device.

Research references: TensorFlow official Android object-detection sample (EfficientDet-Lite0 COCO), MediaPipe Tasks object detection Android guide, and MediaPipe 0.10.26+ Android 16-KiB compatibility. No Hasselblad vendor code or firmware binaries are imported.
