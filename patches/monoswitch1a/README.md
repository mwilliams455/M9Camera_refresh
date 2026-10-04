# M9Cam 2.46 — renderer switch lifecycle repair

MONOSWITCH1A repairs stale preview work during M9 ↔ Monochrom screen recreation in the 2.45 integration candidate. The supplied recording shows a return to the launcher on both switches and successful startup in the newly selected renderer afterward. The supplied log contains no fatal exception or native backtrace, so the device's exact exception cannot be established from it.

The camera screen now owns a token for each resumed preview. It invalidates the token before pausing or destroying its view. Queued HUD updates, PixelCopy completions, histogram jobs and histogram UI posts check their original token before touching the old controller, executor or views. A later resume receives a new token. This prevents a frame queued before recreation from dereferencing the controller after `onDestroy()` clears it, and prevents late PixelCopy work from submitting to the closed executor.

The selected renderer label now reads “Selected”, including for Monochrom. Settings organization and persistence are unchanged. No rendering math, native source, shaders, LUTs, capture allocator or save pipeline is changed.

## Reproduction and checks

`RendererSwitchLifecycleTest` inflates the real camera fragment, recreates the Android activity in both directions, checks the selected renderer class, and delivers an already-queued preview update after the old controller is destroyed. Camera hardware, GPU execution, continuous blur animation, and the audio/gallery background task are replaced at their boundaries. It does not validate a phone's Camera2 driver or GL output.

The queued-frame test fails against 2.45 with a `NullPointerException` in `MonoIsoExpoSelector.monoHudPair1A()` through `CameraFragment.updateViewfinderHud()`, because the destroyed controller is null. `TEST_VERIFICATION.json` records the before/after result. `SOURCE_VERIFICATION.json` limits source changes to lifecycle handling, the selected label, version and the regression test. `PACKAGED_VERIFICATION.json` records the signed APK and all 27 preserved 2.45 native libraries and all 285 assets.

```sh
python3 patches/monoswitch1a/assemble.py /absolute/new/PhotonCamera
# Or reuse the exact 2.45 source:
python3 patches/monoswitch1a/assemble.py /absolute/new/PhotonCamera --parent /absolute/PhotonCamera_245
python3 patches/monoswitch1a/build.py /absolute/new/PhotonCamera --sdk /absolute/android-sdk --output /absolute/build --offline
python3 patches/monoswitch1a/package.py /absolute/new/PhotonCamera /absolute/build/app/outputs/apk/debug/M9Cam_2.46_MONOSWITCH1A-debug.apk /absolute/M9Cam_2.45_MONOMERGE1A.apk /absolute/android-sdk/build-tools/35.0.0 /absolute/deliverables
```

Parent: M9 main `b84c6ea9bdc8c4b63b80e0f4f38c30487f22d11d` (2.45 / PR 63). Reuse the parent's JDK 17, SDK 36, build-tools 35.0.0 and NDK 27.0.12077973. Run builds serially with the same provisioned dependency cache. Do not distribute the raw Gradle APK.

## Phone check

Install over 2.45, retain the existing settings, and switch M9 → Monochrom → M9 several times with the HUD/histogram enabled. The app should stay open, return to a live preview, and show the relevant Image settings after each switch. Confirm a photograph in each renderer and a background/resume cycle. This remains a phone-test candidate; it is not a new photographic acceptance baseline.
