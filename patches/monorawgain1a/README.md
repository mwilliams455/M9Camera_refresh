# Mono Motion RAW exposure correction — 2.70 candidate

The 2.69 cat capture has exact camera/RAW-timestamp association. Its preview target is 329 × 10,000,000 ns = 3.29 ISO-seconds. The submitted request is ISO 1600 × 2,056,250 ns, preserving that target. The camera returns ISO 1119 at unchanged shutter, losing 0.515862 EV. Both preview and still use the same Medium high contrast curve and Sepia Weak toning.

Two earlier uploaded capture records from camera 4, 11.5mm f/1.8, 4096×3072 RAW, report sensitivity range 50–6400 and maximum analogue sensitivity 1118: `IMG_20260915_192303_1789496583508_00_M9.json` and `IMG_20260915_204031_1789501231637_00_M9.json`. The earlier dark bottle capture returned ISO 1116; the cat returned 1119. This strongly supports gain saturation around that analogue limit. The current cat primary omitted sensor limits, so the historical metadata is corroboration rather than a current-characteristics dump. New primary reports include the capture-owned RAW sensor metadata.

The application defect is reproducible: Mono's automatic allocator permits gain up to the full advertised sensitivity range and Motion bypasses its immutable preview/capture plan. The separate colour M9 path already reconciles automatic exposure to an analogue RAW budget. Android permits digital RAW gain above the analogue limit, so this correction is a conservative portable Auto policy, not a claim that all cameras cannot exceed their analogue maximum.

## Correction

- Enable the existing Mono shared plan in Photo and Motion, retaining flash/recording/dual-session exclusions and Motion's faster preferred shutter.
- Reconcile fully automatic exposure to the original metered target plus user/placement EV, using the active physical camera's valid analogue limit, selected Auto ISO maximum and applicable explicit bounds. Missing/invalid analogue metadata falls back to the sensor range.
- Extend automatic shutter when the ISO budget would otherwise lose exposure. Explicit manual ISO remains authoritative; explicit manual shutter is not lengthened. Unattainable targets remain limited and their actual plan drives preview.
- Preserve Photo-only placement eligibility. No new Motion subject lift, renderer gain, HDR, stacking, sharpening, toning or AF changes.
- Record Motion accurately in embedded diagnostics, removing an old hardcoded Photo label, and include capture-owned sensor limits.

For the recorded target and preferred shutter, the corrected allocation is ISO 1118 at 2,942,755 ns (about 1/340s). Host replay confirms energy preservation. This may increase motion blur at the gain ceiling, as brightness-preserving shutter allocation necessarily gathers more light.

## Validation

`host_test.py` compiles the actual new pure allocator and the unchanged production legacy shutter curve. It reproduces ISO 1600 / 2,056,250 ns from the recorded energy/cap, verifies the corrected allocation, and sweeps ISO floors, analogue metadata, user caps, preferred shutters, EV and physical boundaries. The simulated ceiling is not phone validation.

`MonoRawGainTest` exercises the actual Mono allocator, routing gate, immutable plan and request setter with Android metadata mocks. `MonoPrimaryEvidenceTest` verifies the embedded Motion identity and capture-owned sensor budget. CI performs Android compilation and these tests plus inherited diagnostic preference/output tests.

The exact patch changes nine scoped files. All rendering, shaders, firmware assets, native libraries, AF/WB logic and colour M9 allocation code remain unchanged. Package against the verified 2.69 APK to retain all 27 accepted native libraries and 285 assets. Phone validation remains pending; no full WYSIWYG parity claim is made.

## Completed candidate verification

- Android run 37947936866 at source commit `d06bb65f88f0bf5200b50092d2d7a161d9af0aef`: build PASS, 29 tests PASS, no failures/errors/skips.
- Host allocator replay and bounds sweep: 12,795 checks PASS.
- Exact source reconstruction and reverse-patch audit PASS; source fingerprint `c962691aa14d43d3ce532c42cf704566ad832c29acce81ff36fc701af15236dd`.
- Signed APK: `M9Cam_2.70_MONORAWGAIN1A.apk`, version code 27270, SHA-256 `b40e1ae85d99a175c42bde8f0547a8fb8108f023687f609487dfad189a8f57fe`.
- Package signature matches the accepted app; all 27 native libraries and 285 assets are byte-identical to 2.69; compiled menus and 16 KiB alignment pass.

The first CI attempt compiled successfully but one test could not mock Android's final `CaptureRequest.Builder`. The passing revision creates a real Robolectric camera request builder and verifies its submitted ISO, shutter, AE, compensation and immutable plan tag. This was a test-harness repair, not a skipped test.

Phone acceptance is still pending. Install this candidate over 2.69, select Mono / Motion / 3× with Auto ISO and Auto shutter at EV 0, and provide the saved JPEG and embedded primary JSON for a dim scene. Inspect requested/result energy agreement, sensor budget, plan identity and preview/save brightness. A longer automatic shutter near the gain ceiling can introduce more motion blur. Keep PR #88 as a draft until device validation.
