# M9Cam 2.11 PERF2S

The full-resolution saturation audit was forced on for every ordinary M9 photo.
It evaluates three saturation families and extra colour transforms for a JSON
research report, but does not contribute pixels to the saved photograph.

PERF2S makes this audit optional and off by default. Settings > Advanced >
Extended M9 colour diagnostics restores it for troubleshooting. Explicit legacy
SKYSAT control probes retain their previous behaviour and memory-layout guards.
The PRIMARY JSON reports the new policy, user preference and whether it ran.

Exposure, white balance, AMaZE, chroma preparation, firmware Standard SAT2,
curve02, sharpening policy, JPEG encoding and the FIX1 RAW16 protections retain
their accepted implementations. Among the 111 previously frozen M9 source and
asset files, only the renderer's diagnostic orchestration changes; all other
110 remain byte-identical. No native source or colour asset changes.

## Reproduce

Use JDK 17 and the Android toolchain documented in `../upstream2r/README.md`.
From the wrapper root:

```sh
python3 patches/perf2s_auditopt1a/assemble.py PhotonCamera
python3 patches/perf2s_auditopt1a/parity.py PhotonCamera NATIVE_PARITY
cd PhotonCamera
chmod +x gradlew
./gradlew :app:assembleDebug :app:testDebugUnitTest --tests '*M9RenderDiagnosticsTest' --tests '*M9Upstream2RRawPackingTest'
cd ..
python3 patches/perf2s_auditopt1a/package.py PhotonCamera CONTROL.apk "$ANDROID_HOME/build-tools/35.0.0" DELIVERY
```

The host parity test compiles the unchanged production native code with `g++`
and OpenMP. It compares audit-on/off input, context, prepared RGB, final ARGB and
render statistics, including a deterministic 4096x3072 frame. Android bitmap/JNI
entry points are not exercised by this host test. It uses synthetic data and
does not measure handset performance.

Five unit tests cover default-off, explicit opt-in, disabling without restart,
malformed optional settings, legacy controls and layout guards. The 14 existing
RAW16 regressions are retained. Their optional private fixture test skips unless
`M9_RAW16_FIXTURE` points to a 4096x3072 RAW16 file. No photos or photo-derived
fixtures are included. Restricted hosts that prohibit Mockito agent attachment
can preload the cached Byte Buddy agent through `JAVA_TOOL_OPTIONS=-javaagent:...`.

Packaging accepts the verified 2.10 control, or the previously accepted 2.07/2.08
controls whose M9 native libraries and assets are identical. It reuses those two
M9 colour binaries and verifies all other output entries against the new build.
With the 2.10 control it additionally requires every native library to match
2.10. The app ID and signing certificate stay unchanged; version code is 27211.
The output is `M9Cam_2.11_PERF2S.apk`.

Install over 2.10 and leave extended diagnostics off for normal shooting. A phone
test is still required to confirm save behaviour and actual elapsed time. Check
that PRIMARY JSON reports `diagnosticPerformanceRevision=M9PERF2S_AUDITOPT1A`,
`satDomainAuditPolicy=opt_in_default_off` and `satDomainAuditExecuted=false`.
There is no claim of a new photographic rendering or fringing improvement here.
