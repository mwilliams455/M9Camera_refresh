# M9Cam 2.48 — Monochrom image profiles

Monochrom previously had individual image controls but no saved looks in the merged M9 app. MONOPROFILES1A adds Settings > Image > Monochrom profiles, using the familiar M9 profile workflow with a separate collection and active marker.

Profiles store contrast, sharpness, toning hue and toning strength. Up to 20 named profiles can be saved, applied, updated from current settings, renamed and deleted. Manual edits mark the active profile as modified without overwriting it. Reset current look restores standard contrast/sharpness, remembers Sepia and turns toning off; it retains saved profiles. Reset, overwrite and delete require explicit confirmation in the app.

Profiles affect the existing preview/JPEG preferences. They do not change exposure/Auto ISO, output selection, diagnostics, M9 profiles or the linear Monochrom DNG. The remembered toning hue is retained when strength is Off, and the hue picker is then disabled. Per-lens saving excludes the profile collection and active marker; importing a stale per-lens snapshot cannot overwrite them or the four Monochrom image values.

The existing immutable shutter snapshot protects photographs already queued for processing. Renderer, capture, save and native processing code are unchanged. There is no performance change in this release.

## Recovery, build and package

Parent: M9 main `7ba30325fb42a28d11dc2b5b6e232c0d8cc96613` (2.47, PR #65).

```sh
python3 patches/monoprofiles1a/assemble.py /absolute/new/PhotonCamera --parent /absolute/verified/PhotonCamera_247
# Omit --parent to reconstruct the earlier patch chain as well.
python3 patches/monoprofiles1a/verify_source.py /absolute/verified/PhotonCamera_247 /absolute/new/PhotonCamera
python3 patches/monoprofiles1a/build.py /absolute/new/PhotonCamera --sdk /absolute/android-sdk --output /absolute/build --offline
python3 patches/monoprofiles1a/test.py /absolute/new/PhotonCamera --sdk /absolute/android-sdk --output /absolute/build --offline
python3 patches/monoprofiles1a/package.py /absolute/new/PhotonCamera /absolute/build/app/outputs/apk/debug/M9Cam_2.48_MONOPROFILES1A-debug.apk /absolute/M9Cam_2.47_MONOLABEL1A.apk /absolute/android-sdk/build-tools/35.0.0 /absolute/deliverables
```

Use JDK 17, SDK 36, build-tools 35.0.0 and NDK 27.0.12077973 with the provisioned dependency cache. Run builds serially. If the test runtime requires an explicitly provisioned Byte Buddy agent, pass its absolute JAR path using `test.py --java-agent`. Robolectric needs its SDK runtime cached or network access.

Packaging preserves all 27 native libraries and all 285 assets from the accepted 2.47 package. The output has the same app ID/signing certificate and a higher versionCode, so it installs over 2.47. Do not distribute the raw Gradle APK.

## Phone checks

1. Choose Mono, open Settings > Image > Monochrom profiles, and save your current look.
2. Change contrast and toning, save a second look, then apply the first. Check both the controls and the preview/JPEG.
3. Try Update, Rename and Delete. Cancel and confirm Reset current look; confirm saved looks remain.
4. Switch to M9 and back, change lenses, then restart the app. Check both renderers retain their own profiles.

Automated evidence is in TEST_VERIFICATION.json, SOURCE_VERIFICATION.json, RECONSTRUCTION_VERIFICATION.json and PACKAGED_VERIFICATION.json. Phone confirmation of this new feature is still pending.
