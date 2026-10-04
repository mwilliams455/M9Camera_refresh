# M9Cam 2.47 — Mono circle label

MONOLABEL1A shortens the camera's circular renderer button from “Monochrom” to “Mono”. The renderer picker and settings retain the full “Monochrom” name. Only this string and the APK version differ from 2.46; settings, profiles, rendering, capture and lifecycle behavior are unchanged.

On 2026-10-04 Malcolm confirmed that 2.46 works after the switch repair and that photos are captured well. Record that as user acceptance of the reported switching/capture behavior. It does not imply additional unreported device or photographic validation.

Follow-up work: explore Monochrom profiles within its existing Image settings, keeping renderer-specific values separate; measure preview and capture-render timing before choosing performance changes. These are future improvements, not changes in 2.47.

## Reconstruct and build

```sh
python3 patches/monolabel1a/assemble.py /absolute/new/PhotonCamera
# Or reuse the exact 2.46 source:
python3 patches/monolabel1a/assemble.py /absolute/new/PhotonCamera --parent /absolute/PhotonCamera_246
python3 patches/monolabel1a/verify_source.py /absolute/PhotonCamera_246 /absolute/new/PhotonCamera
python3 patches/monolabel1a/build.py /absolute/new/PhotonCamera --sdk /absolute/android-sdk --output /absolute/build --offline
python3 patches/monolabel1a/package.py /absolute/new/PhotonCamera /absolute/build/app/outputs/apk/debug/M9Cam_2.47_MONOLABEL1A-debug.apk /absolute/M9Cam_2.46_MONOSWITCH1A.apk /absolute/android-sdk/build-tools/35.0.0 /absolute/deliverables
```

Parent: M9 main `775989a0009faee89104e13e532c14506e39e945` (2.46 / PR 64). Use JDK 17, SDK 36, build-tools 35.0.0 and NDK 27.0.12077973. Run builds serially with the provisioned dependency cache. Packaging preserves all 27 native libraries and all 285 assets from the delivered 2.46 APK. Do not distribute the raw Gradle APK.

Verification: exact reconstruction, source comparison, Android compilation, signed package identity, both compiled settings menus, and native/asset byte preservation. No new unit tests were added or run for this text-only change. The 86 passing tests recorded under `patches/monoswitch1a/TEST_VERIFICATION.json` apply to parent 2.46. The 2.47 label remains to be viewed on the phone.
