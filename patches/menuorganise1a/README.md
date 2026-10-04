# M9Cam 2.29 MENUORGANISE1A

Parent: `72fc1fdc01dc2d68ad0a0edd40cffd3ba4a6cb50`, M9Cam 2.28. On 4 October 2026 Malcolm confirmed it works and approved the displayed photo. The supplied settings screenshot shows saturation Standard, contrast Standard and sharpness Medium high. Preserve those user choices; the fresh-install sharpness default remains the explicitly chosen Standard. This acceptance is not a claim of exhaustive lens/device or all-level validation.

## Scope

Five M9 photo settings screens: Image, Capture, Output, Display and Advanced. The original preference XML remains byte-identical for the inherited video/raw-video modes. SettingsActivity changes only the resource selected for M9 photo mode; all existing click handlers, nested dynamic screens, preference storage and camera processing remain unchanged.

| Screen | Existing controls |
| --- | --- |
| Image | Leica saturation, contrast, sharpness and saved-JPEG detail explanation |
| Capture | Exposure compensation, countdown timer, autofocus, automatic lens switching, preserve manual WB, camera sounds |
| Output | JPEG / RAW+JPEG / RAW, 16:9 crop |
| Display | Grid, focus peaking, HUD/histogram, horizon, lens-bar position, rounded edges, theme, accent, viewfinder background |
| Advanced | Diagnostic files, unfiltered comparison DNG, extended colour audit, capture comparison B, per-lens settings, binning, CFA, colour method, tunables, sensor configuration, video, app launcher icon, backup/restore/reset and About |

The timer is the existing global `pref_countdown_timer_key`, persisted as a String index 0/1/2, corresponding to 0/3/10 seconds. SettingsManager.set(int) already converts to String; getInteger reads and parses it. The new ListPreference therefore uses the same type, default and values as the viewfinder timer. It introduces no new capture implementation.

HUD is labelled "HUD and histogram" so the existing HUD + Histogram entry is discoverable. An informational row accurately describes it as a preview histogram; it does not claim saved-JPEG parity or add clipping warnings.

## Control audit and omissions

The new hierarchy retains every previously visible leaf except three traced controls. Stored preferences are never removed or rewritten:

- Watermark: consumed by the inherited RotateWatermark/PostPipeline route. The M9 DefaultSaver branch enqueues M9PrimaryRenderQueue and returns before the inherited renderer. The M9 renderer has no watermark consumer.
- Battery saver: changes inherited GPU tile size and PostPipeline processing choices; it does not control the current M9 primary photo renderer. Its stored value and inherited quick controls remain unchanged.
- Preview format: the M9 capture path explicitly forces YUV_420_888 in CaptureController, overriding the generic format selector. Retain the stored value for inherited modes.

Previously hidden frame count, HDR, HEIC, legacy generic sharpness/contrast/noise/merge/shadow/compressor/alignment and legacy JPEG-category controls remain omitted. Their XML and stored values remain available to inherited modes.

The 16:9 and binning settings have real consumers in SaverImplementation.getFrame. Exposure compensation is used in IsoExpoSelector. Autofocus, auto lens switching, preserve-WB, timer and sound retain their camera/UI consumers. CFA/colour-method, per-lens configuration and dynamic tunables remain in Advanced with their original keys and defaults; this change makes no new claims about their applicability to every processing path. No shooting profiles, HDR, new preview math or photo processing changes are included.

## Verification

- `verify_menu.py <accepted-2.28-tree> <2.29-tree> <report.json>` checks five root routes, all nested video/About/dynamic routes, unique resolved keys, preserved classes/attributes for 68 moved nodes, the timer index contract, and 1,127 unchanged app source files.
- The four-file source patch was applied to baseline files in a temporary directory and reproduced each output hash exactly.
- Android assembleDebug succeeded. Fourteen selected existing test suites: 83 tests, 82 passed, one skipped, zero failures/errors.
- `package.py` requires the exact accepted 2.28 APK, copies all 25 native libraries from it, and requires all assets to match. It verifies ZIP contents, 16 KiB alignment, signing identity, package/version, and the compiled five-screen resource.
- No phone or emulator navigation run was performed. Opening each menu, back navigation and persistence across an in-place update remain the phone acceptance check.

## Rebuild and recovery

1. `python3 patches/menuorganise1a/assemble.py <fresh-source-directory>` chains the pinned 2.28 assembly and applies this UI patch.
2. Use `patches/sharpnessmenu1a/build_native.py <tree> <NDK-27.0.12077973>` for the inherited sharpness libraries, then build the Android debug APK with Java 17 and the cached SDK.
3. `python3 patches/menuorganise1a/package.py <tree> <built-apk> <accepted-2.28-apk> <build-tools-35.0.0> <delivery-directory>`.

Source is committed locally and included in the recovery bundle. No public push was attempted. The earlier publication restriction on the inherited firmware bank still applies.

After phone acceptance, the roadmap is shooting profiles, then display aids/clipping warnings, then preview-to-JPEG consistency. Keep the accepted 2.28 image path and do not reopen the parked fringing study.
