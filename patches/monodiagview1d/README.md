# 2.82 MONODIAGVIEW1D

Malcolm installed 2.81 from GitHub and encountered the exposure-preview warning again.
The requested latest MONO_PRIMARY file was not visible. The supplied burst manifest
lists its private staging but does not prove a public export: its telemetry shows
2,401 pending individual exports, 61 priority entries pending, zero fresh priority
writes and zero recorded individual failures at that snapshot. This does not identify
the provider operation or prove that backlog caused the shutter rejection.

The 17:56:53 Monochrom LIVEPAIR is a successful MOTION capture with matching exposure.
It contains no earlier readiness failure; the other uploaded PRIMARY files are M9.
The underlying rejection reason remains unknown. Do not request the missing indexed
file again as if its public existence were verified.

This candidate delivers the existing frozen rejection report directly to the camera
UI when Monochrom diagnostics are enabled. A persistent dialog shows the observed
reason, selection reason, mode, camera and app version. **Copy details** puts the
complete JSON on the clipboard, ready to paste into the investigation conversation.
No public diagnostic file, storage permission change or subsequent successful photo
is needed for that route. Dialog arguments preserve the evidence across recreation;
notifications do not stack, and detached/paused hosts do not open a window.

Ordinary shutter cleanup completes before the dialog is shown. Diagnostics-off keeps
the existing plain warning. The 2.81 standalone export and two-minute same-session
photo fallback remain available. Exposure rules, retry deadline, freshness limits,
rendering, save queues and diagnostic spool scheduling are unchanged. This is an
evidence-access correction, not a demonstrated fix for the shutter rejection or
the public export backlog.

Parent: `93e2ca8e40e358e4eec168fe1985d38305945163` (2.81).
Source verification covers exact reconstruction, reverse restoration, seven changed
files and 1,355 unchanged scoped files. Four dialog tests cover exact clipboard
content without file export, duplicate notification suppression, paused/detached
hosts and restored dialog arguments. Existing readiness tests cover delivery of
the typed report despite staging/metadata failures and diagnostics-off behavior.
Android CI and phone validation are pending until their reports are recorded.

The Android workflow builds and tests, preserves all 27 accepted native libraries
and 285 assets from the verified 2.81 installer, signs with the accepted certificate,
then independently reopens and verifies the result before uploading
**M9Cam-2.82-READY-TO-INSTALL**. Draft source only; no merge is authorized.

## Phone check

Install the APK from the successful ready-to-install artifact over the existing app.
Keep Monochrom diagnostics enabled. If the warning recurs, the diagnostic dialog
stays open until dismissed. Tap **Copy details**, then paste the report into the
investigation conversation. A screenshot of the displayed reason is also useful.
Do not require screen recording, an additional successful photo or a missing JSON.
