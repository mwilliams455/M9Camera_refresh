# M9Cam 2.37 AELOCKTIMER1A

Parent: `f15e38c20b55879e8a8321435c8c72e8207ac989`, M9Cam 2.36 AUTOISO1A. On 4 October 2026 Malcolm confirmed that 2.36 worked and requested AE lock and the self-timer next. This build implements both. On the same date Malcolm reported “Both worked”, accepting AE lock and the self-timer in 2.37 on the phone.

## Photographer controls

AE-L is a labelled button above the viewfinder in Photo and Motion, highlighted when held. With shutter on Auto, tap it to hold the physical ISO/shutter exposure currently displayed; recompose, focus and take repeated pictures at that exposure. Tap again to unlock. Manual ISO with automatic shutter can be locked. Manual shutter is deliberately excluded, following the Monochrom adaptation of Leica's aperture-priority metering-memory control. Unavailable/stale preview shows an explanatory message rather than inventing a lock.

Taps while AE-L is held remain focus-only. Lock clears on camera close/pause, physical session/lens changes, mode changes, EV/manual ISO/shutter edits, Auto ISO maximum/slowest edits, explicit exposure-balance changes or torch changes. Merely moving/recomposing, changing focus or taking a picture does not clear it. AE-L is session state, not a saved shooting-profile preference.

The self-timer is Off / 2 seconds / 12 seconds in the existing timer button, quick settings and Settings → Capture menu. Stored indices remain 0/1/2: a previous 3-second choice becomes 2 seconds and a previous 10-second choice becomes 12 seconds. Timer icons and accessibility labels match. The chosen delay persists across cancellation and lens changes; profiles retain their existing six photographic controls and do not change the timer.

Tap the shutter again to cancel. Leaving the camera, changing camera mode/lens, opening settings/gallery or changing timer selection cancels the pending release. Automatic physical-lens restarts cancel too. A generation/context gate rejects already-queued callbacks after cancel/restart and permits only one release. The chosen timer preference is retained. Invalid stored timer indices resolve to Off. At countdown completion, the existing focus/capture flow resolves the current displayed exposure; the scene is not latched when the countdown starts. An explicit AE-L remains in force through the countdown. Focusing and camera readiness can add time after the nominal countdown.

## Leica reference and Monochrom comparison

Leica M9 Instructions, printed pp. 136 and 157, describes aperture-priority metering memory lock while holding the shutter pressure point; the exposure remains fixed for recomposition until released. Its self-timer offers 2 or 12 seconds, preserves the selection after cancellation, and normally determines exposure immediately before the picture. Primary manual content reproduced at https://manualzz.com/doc/11569313/leica-m9-user-manual .

The phone's persistent AE-L toggle adapts the physical half-press, as in Monochrom `monoleicasettings1f`. Timer choices and numeral vectors follow `monoleicasettings1i`. Reference commit: `1716e806cc66ec999faff4e820c0f6927d92ab3a`. Explicit AE-L plus delayed capture is a phone adaptation; this does not claim that every mechanical Leica switch combination is reproduced. No front-camera feature, face detection or automatic selfie triggering is introduced.

## M9 exposure authority

The seed is the last displayed, validated M9 exposure plan, not a newer unseen sensor plan. Immutable generation/source-plan identity travels through every plan copy. Current-plan access, displayed-plan access and publication validate the generation, age, camera/session, mode and exposure-control context. A lock/unlock/control change invalidates in-flight computations and old draws. Missing preview observations cannot extend a locked capture plan's freshness indefinitely.

Held ISO, shutter, user EV and source automatic-placement decision are preserved. Fresh real neutral Camera2 observations update preview simulation. Crucially, the neutral reference is reallocated from the current scene through the existing accepted physical allocator, with zero user/automatic placement and no new automatic-placement decision. The saved M9 renderer normalizes its measurement domain using actual RAW energy relative to this reference. Freezing the reference along with ISO/shutter would allow TC20 to compensate away lighting changes despite the physical lock. Keeping the neutral reference live preserves the intended locked exposure response without changing JPEG/render math, shaders or tone curves.

The held allocation diagnostic retains its source intended allocation and refreshes the neutral reference, explicitly identifying `intendedHeldFromPlanId` and `neutralReferenceLiveDuringAeLock`. Plan diagnostics expose lock state, generation, original displayed-plan ID and authority. Hardware AE stays neutral and live for the reference; a capture-only Camera2 AE_LOCK flag is not used.

Automatic exposure when unlocked is unchanged: `IsoExpoSelector` differs only by two helpers for locked neutral-reference allocation/diagnostics. All accepted Auto ISO settings, profiles, decimal EV, histogram/clipping, output controls, saved rendering, shader assets, native libraries and preview orientation remain in place. No HDR or stacking is enabled.

## Verification and limits

- Debug APK build passed. 21 Android suites: 160 tests, 159 passed, one pre-existing skip, no failures/errors.
- AE-lock tests cover 120 fresh-observation projections, repeated-shot validity, stale observation expiry, rejection of missing/stale/untagged/manual-shutter plans, manual ISO, camera/mode/session/EV/ISO/shutter/Auto ISO/policy changes, in-flight toggle races, copied diagnostic identity and the TC20 one-stop lighting-change regression.
- Timer tests cover all index/duration mappings, invalid indices, one release only, cancellation/restart, stale callbacks, lens/mode/session/pause mismatches and a fresh locked plan at the end of a 12-second timer. The platform countdown scheduler is reused; these tests do not measure physical handset timing.
- All 2.36 selected regression suites remain, including 7,800 physical ISO/shutter allocation cases and profile compatibility.
- A 28-file hash-checked patch round trip passes. 1,185 parent files are exact. The entire unlocked allocator is byte-identical after removing the two new locked-reference helpers. All saved renderer code and preview geometry/shader code are exact parent copies.
- The package verifies all assets against accepted 2.36 and preserves all 25 native entries; compiled AE-L/timer controls, upgrade package/version/certificate, ZIP integrity and 16 KiB alignment pass.
- No handset or emulator UI/photographic validation was performed by the build environment. Malcolm subsequently reported that both features worked on the phone; this is user acceptance, not a claim of exhaustive device or countdown-length coverage. Existing preview gain bounds and phone camera behavior still apply.

## Recovery and next work

`assemble.py <fresh-tree>` chains the accepted 2.36 reconstruction and applies this patch. Build inherited sharpness natives via `../sharpnessmenu1a/build_native.py`, NDK 27.0.12077973, then Java 17/Gradle with the supplied runner and isolated output directory.

`verify_source.py <2.36-tree> <2.37-tree> <report.json>` checks complete scope, round trip, integration and XML controls. `package.py <2.37-tree> <built-apk> <accepted-2.36-apk> <build-tools-35.0.0> <delivery>` signs an in-place upgrade while retaining natives. Accepted 2.36 APK SHA256: `47e2e9a4444c62aee840e2b4cddb9ad29def80aa450eb03ec0844d36accc4d75`.

Next priority, selected by Malcolm on 4 October 2026 after the menu comparison: exposure bracketing. White-balance presets are deferred; automatic image review and JPEG size/quality controls are unnecessary for the current scope. Auto WB already uses the camera's automatic white-balance mode. The Monochrom reference contains `monoleicasettings1h` (LEICABRACKET1A) plus `monoleicasettings1hfix1` (LEICABRACKET1B_ADMISSIONFIX1): separate fully saved single-frame exposures, held base ISO, shutter variation and an output-admission fix that prevents the sequence stopping after its first frame. Use that corrected implementation as the starting reference, preserving M9 exposure intent through saved rendering and respecting the selected JPEG/RAW output mode. M9 bracketing is now implemented in 2.38 BRACKET1A; see `../bracket1a/README.md`. Malcolm confirmed on 4 October 2026 that exposure bracketing works; 2.38 is phone-accepted.

After the remaining agreed controls, plan the requested M9 Colour / M Monochrom single-app architecture. The 2.34 producer-transform integration remains withdrawn; do not reintroduce it during controls work. Cross-lens colour/fringing investigations remain deferred.

Source and recovery stay private under the inherited firmware publication restriction. No public push is attempted.
