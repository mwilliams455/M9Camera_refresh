# M9Cam 2.36 AUTOISO1A

Parent: `83b446fefc11b2a4303b504f331e5df6ef3f7ea6`, M9Cam 2.35 ORIENTATIONFIX1A. On 4 October 2026 Malcolm confirmed “That works” and requested Auto ISO and slowest shutter, followed by AE lock and self-timer. This accepts 2.35's orientation fix. This build implements the first stage. In the next turn on 4 October 2026 Malcolm confirmed “That worked” and requested AE lock and the self-timer. 2.36 is now phone-accepted; see `../aelocktimer1a/README.md`. This confirmation supersedes pending status in the original delivery reports.

## Controls and exposure behavior

Settings → Capture and preview → Auto ISO setup contains:

- Maximum ISO: 160, 200, 250, 320, 400, 500, 640, 800, 1000, 1250, 1600, 2000, 2500.
- Slowest shutter: Lens dependent, 1/125, 1/60, 1/30, 1/15, 1/8 second.
- New app defaults: ISO 2500 and Lens dependent. These are chosen application defaults, not an assertion about Leica factory defaults.

The menu follows the Leica M9 Instructions, printed page 128: normal ISO 160–2500, Max ISO and Slowest speed controls, a lens-dependent 1/f rule and fixed whole-stop choices from 1/125 to 1/8. Pull 80 is a special setting and is excluded from the automatic maximum list. Primary manual content is reproduced at https://manualzz.com/doc/11569313/leica-m9-user-manual .

The implementation adapts Monochrom `monoleicasettings1d` and `monoleicasettings1e` at reference commit `1716e806cc66ec999faff4e820c0f6927d92ab3a`, using M9 values and the accepted M9 physical energy allocator. It does not copy Monochrom's ISO 320–10000 menu or replace M9 metering/rendering.

In Photo and Motion, the existing allocator still supplies a preferred shutter and unchanged target energy (sensor observation × user EV × automatic placement). The physical final allocation intersects the selected ceiling with the active sensor range, reported analog ceiling and existing explicit ISO balance limit. A hardware minimum above the selected ceiling wins and is diagnosed. Manual ISO bypasses the ceiling and slowest preference. Manual shutter remains exact within hardware bounds, with automatic ISO capped; insufficient light can therefore underexpose at that cap. Fully manual ISO/shutter remains authoritative.

With both controls automatic, a preferred shutter beyond the slowest threshold is shortened and ISO rises to retain the target energy. At the effective ISO ceiling, shutter duration may exceed the threshold to retain exposure. Existing hard exposure-balance time limits and physical limits remain hard. The legacy tripod override of the exposure-balance time limit is retained; the explicitly selected Auto ISO preference still applies. This is a physical ISO/time allocation, not JPEG brightness compensation. The existing phone mode allowing manual shutter with Auto ISO is retained as an adaptation, not a claim of identical M9 manual-exposure behavior.

Lens dependent uses active Camera2 focal length and sensor width to estimate 35mm equivalent focal length, then the nearest 8/15/30/60/125 reciprocal whole stop, matching the Monochrom policy. The equivalent focal estimate is bounded to 8–200mm. Missing/invalid metadata uses a documented 35mm reference (1/30), flagged in diagnostics. It uses the first available focal length of the selected camera; digital zoom is not a new multiplier. No device/lens identifiers or sensor ISO calibration claims are introduced.

## Persistence and capture identity

Both preferences are global across lenses, including protection from imported per-lens snapshots. A single immutable preference/lens snapshot is used by the neutral and intended allocation. Its identity is attached to the immutable exposure plan and retained by every diagnostic-copy method. Both current-plan and displayed-plan accessors reject changed controls/lens metadata, alongside their existing camera/mode/EV/manual/age validation. Capture still uses the displayed plan and its existing shutter-time evidence.

Profiles save both settings atomically with saturation, contrast, sharpness and EV. Editing either marks the active profile as modified. Existing schema-1 profiles remain readable without an on-read rewrite; absent new fields use the documented 2500/Lens dependent defaults when recalled. Malformed new fields cannot silently overwrite the collection. Menus and profile summaries refresh through the existing listener flow.

Exposure diagnostics include selected/effective ISO ceiling, selected/effective slowest time, lens estimate/fallback, manual bypass, sensor-floor exception, ceiling-triggered shutter slowdown, target/allocated energy and error EV. No HDR or stacking path is enabled.

## Verification

- Debug APK build passed. 19 selected Android suites: 147 tests, 146 passed, one existing skip, no failures/errors.
- New production-allocation tests cover 7,800 feasible exposure cases across every ISO/slowest combination, plus the full 19-step EV range, physical/analog/explicit limits, all manual/automatic combinations, lens fallback, identity preservation and rejection, atomic profile recall, legacy profiles and malformed data.
- Hash-checked incremental patch round trip covers 16 changed/new files. 1,188 parent source files remain exact, including all preview/orientation/shader and saved rendering code. The decimal EV controls remain unchanged.
- Packaging checks all assets against accepted 2.35, preserves all 25 native libraries, verifies compiled controls/defaults and upgrade identity/certificate, ZIP integrity and 16 KiB alignment.
- These checks do not substitute for a handset trial or establish actual sensor result/request parity for new settings. No emulator/handset visual validation was performed.

## Recovery and next work

`assemble.py <fresh-tree>` chains the accepted 2.35 reconstruction and applies the hash-checked patch. Build inherited native sharpness with `../sharpnessmenu1a/build_native.py`, NDK 27.0.12077973 and Java 17. The supplied build runner uses a dedicated Gradle output directory and the existing test runtime agent.

`verify_source.py <accepted-2.35-tree> <2.36-tree> <report.json>` checks the entire source scope, patch round trip and integration/menu guards. `package.py <2.36-tree> <built-apk> <accepted-2.35-apk> <build-tools-35.0.0> <delivery>` signs the upgrade while retaining accepted natives. Accepted 2.35 APK SHA256: `d847e3631eee61faf74b95275129d834f0b8c9f4240eba8e5e01bb5711c0d9f2`.

Next user-requested stages: AE lock, then Leica self-timer. Review the Monochrom plan-lock implementation against M9's displayed-plan capture authority before changing AE lock. Timer changes must retain the selected delay and resolve exposure at the intended release point. Review remaining colour/framing items and then the proposed M9 Colour / M Monochrom single-app architecture. 2.34's producer-transform framing integration remains withdrawn; it must not be reintroduced as part of these controls. Bracketing and cross-lens colour/fringing work remain deferred.

Source and recovery bundle remain private. The inherited firmware publication restriction applies; no public push is attempted.
