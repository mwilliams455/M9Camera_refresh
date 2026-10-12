# 2.83 MONOAEREF1A

The 2.82 copyable report captured a real MOTION shutter refusal on camera `2/2`:
`neutral_ae_reference_unavailable`, with fresh metadata (30.8 ms), ISO 522 and
19,642,858 ns exposure. Color context was ready. The result omitted AE mode and
compensation. The allocator's mandatory reported-AE-mode check rejected this
observation, so the shutter attempt expired without submission. Missing compensation
alone was already allowed. This report does not contain the associated request or
AE state, so it cannot establish whether the new fallback will qualify on this phone.

This candidate adds a guarded route for missing AE mode on a directly opened camera:

- The callback request must equal the request associated with this exact result.
- That request must explicitly select AE ON, zero compensation, AUTO control and
  PREVIEW capture intent.
- The result must show an active AE state; absent, INACTIVE and unknown states fail.
- Reported AE OFF, nonzero compensation or conflicting control mode still fail.
- Logical-camera requests cannot substitute for missing physical-camera AE metadata.

The decision is frozen with the exact frame and shared by the allocator and diagnostic
report. The report includes request association, requested AE/control fields, AE state
and the qualification reason. The existing in-app Copy details route is retained.
Successful LIVEPAIR preview evidence also records the decision. Exposure always comes
from measured result ISO and shutter, never requested sensor values.

The existing reported-AE route, 250 ms freshness limit, session/timestamp matching,
retry deadline and capture lifecycle are retained. Source verification checks that
all numerical allocation code and color reconstruction are unchanged. No HDR,
rendering, asset, native-library or save-spool changes are included.

Parent: `30c1110f496d5ca39d794a7cc06f0f512b0aacf1` (2.82).
Five scoped files change; 1,358 remain byte-identical. The reverse patch exactly
restores the parent. Fourteen additional registry/allocator regression tests cover
the reported ISO/shutter values, PHOTO/MOTION energy and user EV, explicit conflicts,
missing evidence, logical/physical boundaries, exact request identity, freshness,
session changes and metadata-read failure. Android CI passed all 122 focused tests with zero failures, errors or skips.
Phone validation is pending.

The workflow reconstructs the pinned source chain, runs 122 focused tests, builds the
APK, preserves all 27 native libraries and 285 assets from the accepted 2.82 installer,
signs with the accepted certificate, and independently reopens and verifies the final
APK before uploading **M9Cam-2.83-READY-TO-INSTALL**. Draft source only; no merge.

Android request association and frame-synchronized AE state references:
https://developer.android.com/reference/android/hardware/camera2/CaptureResult#getRequest()
https://developer.android.com/reference/android/hardware/camera2/CaptureResult#CONTROL_AE_STATE

## Phone check

Install the APK from **M9Cam-2.83-READY-TO-INSTALL** over the existing app. Recheck
Monochrom MOTION on the same lens that refused the shutter, with diagnostics enabled.
If the warning returns, use **Copy details** and paste that report; it now includes
`neutralAeReference` with the exact reason and request/result fields. No exported
JSON file or additional successful capture is required to obtain this evidence.

Verified download: [M9Cam-2.83-READY-TO-INSTALL](https://github.com/mwilliams455/M9Camera_refresh/actions/runs/38160453459/artifacts/11710965542).

CI run 38160453459 built commit `044de23ccbe2af9e8ce3ce871bcad195c092de49`.
The downloaded archive was independently checked again for its recorded SHA-256,
CRCs, installer identity, Android v2 signature, accepted certificate, alignment,
and all 27 native libraries/285 assets against 2.82. See CI_VERIFICATION.json,
PACKAGED_VERIFICATION.json and GITHUB_DELIVERY_VERIFICATION.json.

APK SHA-256: `4fad6c38463fd680ca0a621b010dbe507d06ffa56299ed5bedfab01d461fac21`.
