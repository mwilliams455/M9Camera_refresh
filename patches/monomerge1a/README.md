# M9Cam 2.45 — Monochrom integration candidate

MONOMERGE1A integrates the recovered Monochrom renderer into the accepted M9 2.44 interface. The renderer picker selects M9 or Monochrom; M10-R and M11 remain unavailable. Rendering is independent of Photo/Motion selection. This is a phone-test candidate, not a new photographic acceptance baseline.

## Settings and behavior

There is one settings hierarchy. M9 retains its existing Image page and presets. Monochrom's Image page contains contrast, sharpness, toning hue (Sepia/Cool/Selenium), and strength (Off/Weak/Strong). Their keys are independent of M9. The Capture page shows the selected renderer's Auto ISO and bracket settings. Display, output, timer, focus, lens switching, and the camera overlay retain their shared locations.

Monochrom histograms and clipping warnings use luminance. Stored M9 RGB histogram selections are presented as their luminance equivalents without rewriting that preference. Monochrom AE-L and its planned bracketing are Photo-mode features, matching the imported planner; Motion retains its existing faster allocation path.

A renderer change recreates the camera view and clears exposure/tap/AE-lock state. Selection is gated through timer, capture, bracketing, and final-save completion. Every queued Monochrom photograph owns a settings snapshot and physical-camera parameter snapshot. Brackets advance from final-output completion, including verified linear DNG publication.

Save modes are JPEG, DNG+JPEG, and DNG. Monochrom DNG is the original linear SOURCE1D luminance export; JPEG contrast, sharpness and toning are not baked into its pixels. Monochrom Original Sensor RAW is independent of that selection and defaults off. The existing M9 optional unfiltered-DNG semantics remain unchanged. The shared diagnostics switch defaults off. Monochrom renderer and final-output evidence is included in `_MONO_PRIMARY.json` when enabled.

The imported dark-frame policy requests supported Camera2 hot-pixel metadata and applies the original guarded derived-path correction. It adds no second exposure, no delay, no HDR, and no modification to preserved sensor RAW.

## Source and reproduction

- M9 parent: `212e8857aa1fc7840cc307a875693070e3c5480c` (2.44 UI; accepted photographic baseline remains 2.38).
- Monochrom source: `cf5e00e23ea47920fb863eb7abb0fa423885786a`, `research/mono-darkframe1a`.
- The full Monochrom recovery chain was reconstructed and its original policy/source checks passed before integration.
- `manifest.json` pins every changed/new source and binary payload. `monomerge1a.patch.gz` is deterministic. `assemble.py` verifies inputs and outputs.

```sh
python3 patches/monomerge1a/assemble.py /absolute/new/PhotonCamera
# Or reuse an already assembled 2.44 source:
python3 patches/monomerge1a/assemble.py /absolute/new/PhotonCamera --parent /absolute/PhotonCamera_244
python3 patches/monomerge1a/build.py /absolute/new/PhotonCamera --sdk /absolute/android-sdk --output /absolute/build --offline
python3 patches/monomerge1a/package.py /absolute/new/PhotonCamera /absolute/build/app/outputs/apk/debug/M9Cam_2.45_MONOMERGE1A-debug.apk /absolute/M9Cam_2.38_BRACKET1A.apk /absolute/android-sdk/build-tools/35.0.0 /absolute/deliverables
```

Provision the same JDK 17, Android SDK 36/build-tools 35.0.0 and NDK 27.0.12077973 as the parent. Offline builds require the parent Gradle dependencies and test runtime to be cached. Do not distribute the raw Gradle APK: packaging deliberately restores all 25 accepted 2.38 native libraries and adds only the two `libmonocolor.so` ABI libraries.

`SOURCE_VERIFICATION.json`, `TEST_VERIFICATION.json`, and `PACKAGED_VERIFICATION.json` record the exact checks and package hash. Existing M9 photographic Java, native source, and assets are unchanged except for explicitly identified shared routing/UI helpers. The imported Monochrom native math, LUTs, shader, and allocator match their source after namespace relocation.

## Device validation still required

On the target phone, check M9 → Monochrom → M9, independent Image settings across restarts/lenses, preview-to-JPEG exposure/toning, physical ISO metadata, every output mode with Original Sensor RAW on/off, AE-L, tap metering, timer cancellation, and a serial bracket. Verify Photo/Motion and all used physical lenses. The latest imported dark-frame policy is included as a candidate, not newly claimed phone-accepted.
