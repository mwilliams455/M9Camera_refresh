M9Cam 2.62 SHUTTEREXPORT1A — recover and prioritize shutter-trace exports

Current phone manifests confirm that shutter traces were staged internally, but their public export was queued behind roughly 1,700 historical diagnostics. Burst manifests are indexes and do not contain the trace payloads.

This candidate gives shutter traces a dedicated single-writer exporter. It selects the newest eligible trace first, coalesces repeated updates, recovers existing staged traces, retries failed writes and preserves payloads during active export. No new backlog purge is introduced. Diagnostic saving and foreground visibility still gate export.

The production spool passes 225 host assertions with real files/executors and a controlled storage provider. A 12-MB recovered trace exports despite a blocked historical ordinary export. Failure/retry, sixty in-flight updates, lifecycle transitions and PRIMARY export pass. Only the diagnostic spool and version metadata change; all other 1,330 scoped files match 2.61. Reconstruction, Android build and APK package checks pass.

Start here:
- patches/shutterexport1a/README.md — evidence, recovery instructions and build steps
- patches/shutterexport1a/EVIDENCE.json — supplied diagnostic-manifest observations
- patches/shutterexport1a/HOST_VERIFICATION.json — production spool results
- patches/shutterexport1a/SOURCE_VERIFICATION.json — source boundaries
- patches/shutterexport1a/assemble.py — pinned source recovery
- patches/shutterexport1a/PACKAGED_VERIFICATION.json — final APK checks

This is an incremental source assembly/recovery repository, not an assembled Android project. Candidate APK: M9Cam_2.62_SHUTTEREXPORT1A.apk.
Parent: 2.61 at 87a62f9a1a51dd12fb3510df921e8cfe88c17728, draft PR #79. Main remains unchanged. Phone delivery validation and brightness-pumping diagnosis are pending; exposure and AF are unchanged.
