M9Cam 2.52 DNGNAMEFIX1A — RAW profile-embedding repair

The contrast menu added a colon to embedded profile names, but the DNG writer rejects colons. RAW was saved without its Leica look. This revision changes C: to C-. Profile generation, the writer and all photographic processing are unchanged. The 2.51 diagnostic early exits and lazy fallback allocation are included, along with Monochrom's confirmed speed improvement.

Start here:
- patches/dngnamefix1a/README.md — cause, verification limits, recovery/build and phone checks
- patches/dngnamefix1a/assemble.py — reconstruct the complete pinned source chain
- patches/dngnamefix1a/SOURCE_VERIFICATION.json — exact source-change boundary
- patches/dngnamefix1a/EXPORT_VERIFICATION.json — real exporter/writer: 50 successful setting/output cases plus RAW preservation on failures
- patches/dngnamefix1a/TEST_VERIFICATION.json — 34 app tests in eight suites
- patches/dngnamefix1a/PACKAGED_VERIFICATION.json — signed APK identity and integrity

This is an incremental source assembly/recovery repository, not an already-assembled Android project. The previous contrast test substituted a writer without name validation; the new integration test uses the actual writer. Synthetic host DNGs verify export behaviour. Phone filesystem/editor confirmation remains pending.

Parent source: 2.51, b8a21870f5ff6457b3cf9a347afff14da908cd48 (draft PR #69, stacked on #68 and #67).
Candidate package: M9Cam_2.52_DNGNAMEFIX1A.apk
Install 2.52 directly; there is no need to install 2.51 first. Previously saved RAWs are not automatically rewritten.
