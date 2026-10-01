# M9Cam 2.18 DNGPROFILE1B

Fixes profile export being bypassed in shared DCIM storage. The 2.17 writer used a
`.tmp` sibling; a device capture reported `Operation not permitted` at that path.
The writer now stages an app-owned `M9_PROFILE_PENDING_*.dng` in the same directory,
then validates and atomically replaces the original. Normal failure cleanup removes
the staging file. A failed replacement retains the complete original RAW.

The profile algorithm and rendering are inherited unchanged from 2.17. New embedded
profiles are named `M9 App1B ...`. PRIMARY diagnostics retain the `dngProfile1A` key
for compatibility, with revision `M9DNGPROFILE1B` and an explicit `storagePolicy`.
No extra storage permission is requested. Source reconstruction and packaging pin
the three changed files and retain all native libraries from accepted 2.16.

`verify_storage.py` compiles both the old and corrected production writers. A Java
17 host policy reproduces non-DNG staging rejection, permits DNG staging, and injects
a final replacement failure to check byte-for-byte original preservation and cleanup.
This is a focused host simulation, not an Android FUSE emulator. Existing profile,
RAW and physical-calibration regression gates also run in CI. Phone capture and
Lightroom selection still require validation on the updated APK.

Limits from 2.17 remain: profile colour/tone is an editable approximation of the JPEG
look; demosaicing, detail and spatial shading can differ. No shared-target cross-lens
experiment is enabled. Abrupt process termination may leave an uncommitted staging
DNG; normal handled failures clean it up. Private capture files stay outside this repo.
