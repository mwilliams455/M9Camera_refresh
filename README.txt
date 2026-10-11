2.80 MONOPLANWAIT1B readiness correction: preserve valid physical exposure metadata on colour-preview failure and check once more at the unchanged retry deadline. One rejection record is exported only when diagnostics are enabled. See patches/monoplanwait1b/README.md. Source verification passed; Android build and phone validation pending. Recording 52650 shows the 2.79 readiness warning after six photos were reported saved; its exact metadata trigger is not yet established. The bounded 2.79 save pipeline is retained.

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
