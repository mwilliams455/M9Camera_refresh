# M9Cam 2.38 BRACKET1A

Parent: phone-accepted 2.37 AELOCKTIMER1A. Malcolm selected exposure bracketing as the next feature and asked to continue on 4 October 2026. White-balance presets are deferred; automatic image review and JPEG size/quality controls are outside this work. The M9 Colour / M Monochrom app merger remains a later task. Malcolm subsequently confirmed “Exposure bracketing works” on 4 October 2026 and requested a handoff. This makes 2.38 the current phone-accepted baseline.

## Controls

Settings → Capture → Exposure bracketing. Default Off, with 3 / 5 / 7 photographs, 0.5 / 1.0 / 1.5 / 2.0 EV increments, and either centre followed by alternating brighter/darker exposures or darkest to brightest. Seven photographs allow only 0.5 / 1.0 EV; selecting seven normalizes the persisted increment and restricts the visible choices. The quick Bracketing control is Off / On. New global keys prevent a legacy Photon HDR setting enabling this feature after upgrade. The existing six-control shooting profiles are unchanged.

Photo mode and automatic shutter are required. Manual ISO is supported. Flash/torch must be off. Finish saving any prior photograph before starting a sequence. A selected self-timer runs once, before the series. The first physical release uses the latest validated displayed exposure as the centre; an existing AE lock supplies that centre through the accepted 2.37 plan. User EV shifts the centre once. ISO and the centre automatic-placement decision stay fixed; shutter varies within the active physical camera's reported range. Auto ISO's slowest shutter applies to the centre, not subsequent bracket offsets. Sensor limits may cause repeated exposures. No device IDs or lens-specific tables are introduced.

Each exposure uses the existing one-RAW capture and M9 save path. JPEG-only yields N JPEGs; RAW-only yields N DNGs; RAW+JPEG yields N of each. Optional original/unfiltered DNG follows its existing toggle. Output mode and saturation/contrast/sharpness selection are captured for the series. Diagnostics stay optional. No HDR/stacking/merging is enabled.

The preview remains at the ordinary centre exposure; it does not flash through the bracket offsets. Live neutral observations remain current in each capture plan. Saved TC20 normalization uses actual capture energy against that live neutral reference, so it preserves bracket offsets and changes in scene light instead of normalizing every frame back to the centre. No renderer photographic arithmetic, tone, colour, shaders or preview geometry is changed. The renderer's preparation report gains only accurate bracket metadata.

## Sequence boundary and cancellation

Reference: Monochrom `monoleicasettings1h` and corrected `monoleicasettings1hfix1` from commit `1716e806cc66ec999faff4e820c0f6927d92ab3a`. Those use separate saved exposures and fix the premature second capture after JPEG completion. M9 has a different output queue; it uses the per-photo `M9SaveStatus.Ticket` final completion after selected JPEG/DNG writes, EXIF/profile and publication attempts. DefaultSaver's early capture-release event never advances the bracket.

Every frame carries immutable series ID, plan ID, index, requested/achieved EV, base plan and output choices. Only a matching once-only final-output event advances the series. The continuation checks camera readiness, exposure context, current session, mode, AE-lock generation, settings, preview state and renderer capacity. Generation checks reject stale events across cancellation or a new controller. The next capture starts through the existing focus flow after those checks, not on a fixed save delay.

Leaving/closing the camera or changing session/settings cancels remaining releases. Opening settings cancels a series. A submitted photo may finish saving. Save/capture failures stop the remainder; bounded readiness and per-frame exposure-plus-save deadlines avoid an endless disabled state. UI controls remain locked while the series runs. The preference stays enabled until the user switches it off.

## Verification

- Android debug build passed; 22 selected suites, 172 tests, 171 passed, one pre-existing skip, no failures/errors.
- New contracts cover 72 frame-count/increment/order/output combinations, fixed ISO, hardware shutter clipping, final selected-output completion, duplicate/concurrent completion, old-controller events, exposure/session/settings changes, save failure, stale source observations, long exposure deadlines, immutable diagnostic copies and TC20 exposure-intent preservation.
- Existing AE lock, timer, Auto ISO (including 7,800 allocations), EV, preview brightness, profiles, output and rendering diagnostics tests pass.
- 20-file patch round trip passes, with 1,197 parent files exact. All assets, native sources, preview geometry, exposure allocator, AE-lock/timer helpers and photographic renderer arithmetic remain unchanged. Renderer edits are diagnostic only.
- Packaging checks native/asset preservation, compiled controls/defaults, upgrade package/version/signature and 16 KiB ZIP alignment.
- Malcolm confirmed “Exposure bracketing works” on 4 October 2026. No handset or emulator run was performed by the build environment. This is user acceptance, not proof of exhaustive coverage of every bracket length, output mode, lens or failure scenario. The original build/package reports retain their historical pending status; this acceptance supersedes it.

## Recovery

`assemble.py <fresh-tree>` chains accepted 2.37 and applies the hash-checked patch. Build inherited natives using `../sharpnessmenu1a/build_native.py` if not already available; use Java 17, NDK 27.0.12077973 and the supplied build runner/init script with an isolated build directory. Native packaging retains all 25 accepted 2.37 entries.

`verify_source.py <2.37-tree> <2.38-tree> <report.json>` verifies scope, photographic isolation and patch round trip. `package.py <2.38-tree> <built-apk> <accepted-2.37-apk> <build-tools-35.0.0> <delivery>` creates the signed upgrade. Accepted 2.37 APK SHA256: `072afa16465985a70afe5cef39b1f24b4f9adc30bf4740c58cc3cee4a6606b17`.

Do not reintroduce withdrawn 2.34 preview sampling transforms. Source/recovery remains private under the inherited firmware publication restriction; no public push is authorized or performed.
