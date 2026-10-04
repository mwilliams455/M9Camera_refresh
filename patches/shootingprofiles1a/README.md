# M9Cam 2.30 SHOOTINGPROFILES1A

Parent: `869f9540907b80353d5e8c77f65f2e598f56ae1e`, M9Cam 2.29 MENUORGANISE1A, accepted by Malcolm on 4 October 2026 ("It works!"). The next agreed task is named shooting profiles. The accepted M9 photographic rendering remains the baseline; display/clipping aids and preview-to-JPEG consistency follow later.

## User flow

Settings > Image > Shooting profiles shows the current four photographic settings and saved profiles. Save current settings creates a named snapshot. Tap a saved profile to inspect and Apply it. Manage provides Update from current settings, Rename and Delete. Update and Delete require confirmation within the app. Current status names the selected profile or shows "(modified)" when the current values differ from it. No built-in photographic presets are invented or applied on upgrade.

The collection supports up to 20 profiles, each with a trimmed, unique name of 1–40 characters. Duplicate names are compared without case sensitivity. Names may contain Unicode. Blank/control-character names are rejected. The profile layout allows all four settings to remain readable without a three-line summary limit.

## Settings and persistence contract

| Profile field | Existing stored preference | Type/range |
| --- | --- | --- |
| Saturation | `pref_m9_saturation` | String, 0–4 |
| Contrast | `pref_m9_contrast` | String, 0–4 |
| Sharpness | `pref_m9_sharpness` | String, 0–4 |
| Exposure compensation | `pref_expocompensation_seekbar_key` | String, finite −4 to +4 EV |

EV text is retained exactly, including precise values between slider steps. Recall writes the four existing preferences and the active-profile marker through one SharedPreferences editor. It does not change output mode, diagnostics, comparison DNG, exposure mode, ISO, shutter, white balance, focus, timer, lens or display choices. Their existing consumers and semantics continue to apply. Profile EV is the existing compensation control, not a new auto-exposure engine or an override of manual exposure behavior.

Profile records are schema-versioned JSON in `pref_m9_shooting_profiles_v1`; the selected ID is `pref_m9_shooting_profile_active`. Both live in default preferences, so existing full settings backup/restore includes them. These two metadata keys are excluded from per-lens snapshots and ignored if encountered in imported per-lens data. Existing per-lens behavior for the photographic settings is retained. Switching lenses does not automatically reapply a profile; the status compares current values with the selected profile.

The profile store refuses malformed or unsupported collections without replacing them. Recall uses an explicit four-field allowlist, so extra fields in imported profile JSON cannot enable unrelated controls. Deleting or renaming a profile never changes the current image settings. A save/update records current settings; it does not recall another profile.

Settings parent fragments retain ListPreference objects on the back stack. The UI refreshes their cached values after recall, avoiding stale saturation/contrast/sharpness summaries when returning to Image. The settings fragment unregisters its preference listener on destruction and dismisses its profile dialog.

## Rendering boundary

Existing capture planning, JPEG/DNG processing and queue capture-freeze source are unchanged from 2.29. The profile feature writes only the same preferences used by those existing consumers. It does not modify queued job snapshots or introduce a second renderer. All assets and 25 native libraries are preserved byte-for-byte from the accepted 2.29 APK.

Preview sharpness simulation, saved-JPEG histogram parity and DNG spatial sharpening are not added. No HDR/stacking, device-specific look tuning or renewed fringing investigation is included.

## Verification

- `verify_source.py` checks 1,127 unchanged existing app source files, unchanged existing menu routes/classes/defaults, new Image profile route, the per-lens metadata exclusions and the existing EV range.
- The nine-file source patch was applied to temporary copies of the baseline files and reproduced every output hash exactly.
- Android assembleDebug succeeded. Fifteen selected suites: 96 tests total, 95 passed, one skipped, zero failures/errors. Thirteen new profile tests cover read-only defaults, exact EV, one-editor recall, excluded controls, reload/backup-style persistence, modified state, stable IDs, rename/update/delete, invalid names/duplicates, limits, corrupt/future data, invalid values and untrusted extra fields.
- Package verification checks the exact 2.29 control hash, asset identity, all native library identity, signing certificate, 16 KiB alignment, version/package identity, compiled profile screen and ZIP integrity.
- There was no phone/emulator UI run. Phone acceptance should save and recall two distinct profiles, check the Image and Capture values after returning, and confirm persistence after reopening the app. Existing manual/per-lens behavior remains subject to the usual phone behavior.

## Rebuild/recovery

1. `python3 patches/shootingprofiles1a/assemble.py <fresh-tree>` chains the pinned 2.29 assembly and applies this patch.
2. Use the inherited `patches/sharpnessmenu1a/build_native.py <tree> <NDK-27.0.12077973>` and build with Java 17 and the Android SDK.
3. Run the profile and existing affected unit tests, then `package.py <tree> <built-apk> <accepted-2.29-apk> <build-tools-35.0.0> <delivery>`.

Source is committed locally and retained in the recovery bundle. No public push was attempted; the existing publication restriction on the inherited firmware bank remains applicable.

After phone acceptance: display aids and clipping warnings based on displayed preview data, then preview-to-JPEG consistency. Preserve this accepted image path and keep the fringing study parked.
