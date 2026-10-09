# M9Cam 2.68 MONODIAG1A candidate

Parent: 2.67 REGIONALCLIP1A, commit `5774ba40d640495d226a1500f35abbe3d5ccb219`.

The shared ManagedSwitchPreference stores enabled/disabled values as the strings
`1` and `0`. Monochrom's capture snapshot only recognized native Boolean objects,
so its enabled diagnostic switch was read as false. Its live reader instead called
SharedPreferences.getBoolean on a String; the exporters caught that type exception
and silently treated diagnostics as disabled. The same reader also controls the
independent Original Sensor RAW option.

Both live and frozen reads now use one decoder matching SettingsManager's numeric
string behavior, with native Boolean compatibility. Malformed/missing values keep
the supplied fallback. Capture settings remain immutable and worker-local.

Enabling the previously suppressed imported Mono spool would also run its old
one-time cleanup against the shared m9diag_spool directory. The Mono adapter now
uses the current shared streaming/recoverable exporter, without that imported purge
or its heap-retained payload queue. The `monochrom_primary` role receives the same
priority as the existing primary timing reports. Output names remain unchanged.

This repairs diagnostic admission and delivery. It does not diagnose or change the
reported Mono preview/JPEG brightness mismatch. Renderer, exposure, tone, AF, WB,
native code and assets are byte-identical to 2.67. Four production Java files,
version metadata and two test files differ; 1,332 scoped files remain identical.

## Verification

- Parent host reproduction: enabled frozen diagnostic reads false; live read throws.
- Corrected preference host checks: 69 assertions pass. These use complete production
  capture classes, the unchanged relevant PreferenceKeys methods and a typed store
  adapter, not the Android settings widget.
- All 225 inherited real-file/executor spool assertions pass with Android/JSON stubs.
- Mono transport test covers priority despite a blocked ordinary exporter, existing
  report preservation, disabled behavior, background/resume and no retained byte array.
- Source fingerprint and reverse patch checks pass. Android widget tests and build
  status are recorded separately; no phone validation is claimed.

## Reproduce

```sh
python3 patches/monodiag1a/assemble.py /absolute/PhotonCamera_268 --parent /absolute/PhotonCamera_267
python3 patches/monodiag1a/host_test.py /absolute/PhotonCamera_267 --expect-parent-bug
python3 patches/monodiag1a/host_test.py /absolute/PhotonCamera_268
python3 patches/monodiag1a/transport_test.py /absolute/PhotonCamera_268 --output /absolute/mono-host
python3 patches/monodiag1a/verify_source.py /absolute/PhotonCamera_267 /absolute/PhotonCamera_268
python3 patches/monodiag1a/build.py /absolute/PhotonCamera_268 --sdk /absolute/android-sdk --output /absolute/build268
python3 patches/monodiag1a/package.py /absolute/PhotonCamera_268 /absolute/build268/app/outputs/apk/debug/M9Cam_2.68_MONODIAG1A-debug.apk /absolute/M9Cam_2.67_REGIONALCLIP1A.apk /absolute/android-sdk/build-tools/35.0.0 /absolute/deliverables268
```

Omit `--parent` for full reconstruction. Use the parent's JDK 17 / SDK 36 /
build-tools 35.0.0 / NDK 27.0.12077973 / CMake 3.22.1 toolchain.
The final packager verifies the exact parent APK and preserves all 27 native
libraries and 285 assets. The raw Gradle APK must not be distributed.

## Phone check after a packaged APK is available

Keep Save diagnostic files enabled and Original Sensor RAW off unless desired.
Take one Mono Motion 3x photo of the same scene, remain in the camera briefly,
and check DCIM/Camera for the matching `_MONO_PRIMARY.json` and available
`_MONO_LIVEPAIR.json`. Compare preview and saved brightness again. M9 shutter-trace
coverage is a separate path; this change does not add M9's trace collector to Mono.
