2.81 MONODIAGEXPORT1C: diagnostic-delivery correction after Malcolm confirmed the 2.80 rejection record is absent. Uses the working Raw diagnostics folder, priority export, recovery of private 2.80 records, and bounded evidence in the next successful photo. The diagnostics-enabled warning also shows a reason code. Source verification, Android build, all 104 focused tests and signed-package verification pass. All 27 native libraries and 285 assets are identical to 2.80. Draft PR #99 is not merged. The underlying exposure-preview rejection is unresolved. See patches/monodiagexport1c/README.md. This draft chain is not authorised to merge.

2.80 MONOPLANWAIT1B: the Monochrom exposure-preview warning still occurs on the phone (Malcolm, 11 October 2026 at 14:58 Europe/London). The tested source fixes did not resolve the reported issue. The matching MONO_EXPOSURE_READINESS_*.json is needed to identify the rejected metadata/plan condition. See patches/monoplanwait1b/README.md. Source checks, all 94 focused Android tests and signed-package verification passed; draft PR #98 is not merged. The bounded 2.79 save pipeline is retained.

Current work order (11 October 2026): docs/PROJECT_GOALS.md
Autofocus source audit: docs/AF_LIFECYCLE_AUDIT_20261011.md (six findings).
Lifecycle corrections are next. SL-series firmware-derived tracking is a
future goal blocked by unresolved camera firmware decryption. Experimental 2.72
tracking remains parked on draft PR #90; merged baseline information follows.

M9Cam 2.71 TRACEREWIND1A — retain diagnostic history before screen recording stops

The camera shutter cannot be used during screen recording on the user's phone.
This diagnostic candidate exports up to 30 seconds before a later shutter press
from the existing bounded rings, instead of the former three seconds. Record a
short example, stop recording, then take the photo within about five seconds.

This is a diagnostic workaround, not a fix for preview pumping or shutter refusal.
Only trace serialization, its regression tests and app version metadata change.
All 2.68–2.70 Monochrom work is preserved; photographic policy is unchanged.

Start here: patches/tracerewind1a/README.md
Source checks: patches/tracerewind1a/SOURCE_VERIFICATION.json
Reconstruct: python3 patches/tracerewind1a/assemble.py /absolute/fresh/destination
Android build, all 34 regression tests and signed-package verification pass.
Results: patches/tracerewind1a/BUILD_VERIFICATION.json and PACKAGED_VERIFICATION.json.
Phone validation remains pending.

This is an incremental source-recovery repository, not an assembled Android project.
Parent: 2.70 at 301a80733145f7d88decefdde7fc0388df1210a7, draft PR #88.
Candidate: M9Cam_2.71_TRACEREWIND1A.apk. User requested merging this tested chain on 10 October 2026; phone validation remains pending.
