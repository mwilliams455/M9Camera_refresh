# M9Cam 2.23 — Optional extra files

Adds two independent switches under **Settings → Photo settings**:

- **Save unfiltered DNG** — creates the additional `_RAW_UNFILTERED.dng` comparison file.
- **Save diagnostic files** — enables JSON sidecars, diagnostic images and exported logs.

Both default to off, including upgrades from 2.22. Existing public files are kept.
The normal JPEG and processed DNG, including its selected Leica saturation profile,
remain enabled. The Leica saturation preference retains its existing value.

The unfiltered choice is frozen at RAW enqueue and carried into both the asynchronous
DNG path and synchronous fallback. Disabling it avoids raw-buffer hashing, temporary
files and the extra native DNG writer call. Diagnostic exports check the current setting
at staging and again at delayed/public persistence, including the legacy fallback and
PhotonLog exporter. Enabling diagnostics takes effect without restarting the app.

Internal capture snapshots are retained because the renderer depends on them. Only their
optional persistence is skipped. App-private log/crash recovery remains internal; public
sidecars, burst manifests and exported logs follow the switch. Already saved files are
not deleted. Diagnostic backlog retained before disabling may resume when re-enabled.

Validation covers all four combinations, unchanged primary files/source buffers,
disabled output with invalid input (no buffer/file work), deferred exports disabled after
enqueue, legacy fallback suppression, and immutable render metadata with diagnostics off.
Existing RAW pairing, profile/storage, metadata, saturation and request-isolation gates
remain in the workflow. Tests use synthetic data only.

Packaging preserves all 23 native entries and all M9 assets from the verified 2.22 APK.
No changes to colour arithmetic, source calibration, metering, tone, demosaic, sharpening,
or normal RAW processing are introduced. Installation and handset output counts remain
the final device check.
