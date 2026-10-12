# 2.84 MONOAEREF1B

The 2.83 device report establishes why the prior fallback still refused MOTION on
camera `2/2`: `active_ae_state_unavailable`. Result AE mode, compensation and state
are all absent. The exact request matches the result and explicitly requests AE ON,
zero compensation, AUTO control and PREVIEW intent. The result also reports AUTO
control. Measured ISO 1504 and 20,000,000 ns exposure are valid and only 21.7 ms old.
The additional mandatory AE-state requirement in 2.83 is too strict for this case.

This candidate accepts a missing AE state when the result explicitly reports AUTO
control and the existing exact neutral preview-request checks pass. This uses the
associated request as the source of AE mode/compensation, corroborated by reported
AUTO control. It does not claim that AE convergence was measured. Explicit INACTIVE,
unknown AE state, AE OFF, nonzero compensation and conflicting control mode remain
rejected. Missing state plus missing reported control also remains unqualified.
Logical requests cannot substitute for unproven physical-camera override values.

Android documents AE state as optional on some devices. AUTO control enables the
individual algorithm controls, including the associated request's AE mode. Missing
AE mode remains a device metadata omission; this compatibility policy is based on
request/result association and reported AUTO control, not an invented result value.

References:
https://developer.android.com/reference/android/hardware/camera2/CaptureResult#CONTROL_AE_STATE
https://developer.android.com/reference/android/hardware/camera2/CaptureResult#getRequest()
https://developer.android.com/reference/android/hardware/camera2/CaptureRequest#CONTROL_MODE

Only the qualifier, its regression tests and app version change. Numerical exposure
allocation, frame registry, 250 ms age limit, timestamp/session/camera checks, capture
lifecycle, rendering, save/export pipelines, native libraries and assets are unchanged.
The copyable report preserves nulls and records the distinct reason
`exact_neutral_request_with_reported_auto_control` with revision `MONOAEREF1B`.

Parent: `a70daac2bab7c910b7748948bfe446d7344f8f92` (2.83).
Three scoped files change; 1,360 remain byte-identical. The reverse patch restores the
parent exactly. Six new integration regressions exercise the actual phone metadata,
PHOTO/MOTION exposure energy at -1/0/+1 EV, explicit conflicts, incomplete evidence,
request association, measured sensor values and freshness/session boundaries.
The Android workflow requires 128 focused tests including the named phone regression,
then preserves the accepted 2.83 native libraries/assets, signs and independently
reopens the installer. CI passed all 128 tests with zero failures, errors or skips.
Phone validation remains pending. Draft only; no merge.

## Phone check

Install the APK from **M9Cam-2.84-READY-TO-INSTALL** over the existing app. Retry
Monochrom MOTION on the affected lens. If the warning returns, use **Copy details**
and paste that report. If capture succeeds, check that brightness and user EV behave
normally. No exported JSON file is required to report another shutter refusal.

Verified download: [M9Cam-2.84-READY-TO-INSTALL](https://github.com/mwilliams455/M9Camera_refresh/actions/runs/38161340196/artifacts/11710487871).

CI run 38161340196 built commit `7dd0eca52ce1fe6a37f2762ee3e757d301132cd7`.
The downloaded archive was independently checked again for recorded SHA-256, CRCs,
package/version, accepted Android v2 signature, alignment and byte-identical 27 native
libraries/285 assets. See CI_VERIFICATION.json, PACKAGED_VERIFICATION.json and
GITHUB_DELIVERY_VERIFICATION.json.

APK SHA-256: `e6818198bec1178caee8630322a4bbe6a832041c94635b3ef35298fec0e09868`.
