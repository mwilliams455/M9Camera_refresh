# M9 Project — 3.12 merged; 3.13 tracking-default handoff

**Handoff date:** 27 October 2026  
**Project:** M9Cam — Leica M9 + Monochrome in one Android app  
**Current signed, phone-reviewed baseline:** M9Cam **3.12 `FOCUSOVERLAY1B`**, version code **27312**  
**Repository:** https://github.com/mwilliams455/M9Camera_refresh  
**Accepted merge:** https://github.com/mwilliams455/M9Camera_refresh/pull/123  
**Merge commit:** `424380e54c7df53961eb44e9cd43b8214adb7236` (the exact 3.12 merge; subsequent documentation commits, if any, are not camera changes).  
**Next proposed implementation:** `TRACKINGDEFAULT1A` / potential 3.13. **Not implemented or user-approved as a settings change yet.**

> **Resume instruction:** Start from the merged M9Cam 3.12 source on `main`, not the older 3.10/3.11 experimental branches. The Balanced Extended Ticks visual design is locked and visually accepted. The next issue is whether and how **tap-initiated subject tracking** should be enabled by default in **AF-C**, while preserving automatic Eye AF, normal AF-S/manual tap behaviour, existing user settings, and performance. Do not make an unrelated AF or rendering rewrite. The user expressly approved merging 3.12; PR #123 is merged.

## 1. Confirmed completed work

### 3.10 `AUTOEYE1A`

- Human eye recognition runs automatically by default in **Wide / Continuous Picture AF**, within Photo, Night, and Motion modes. The user initially reported that this seemed to work on device.
- Validated full-face landmarks and a separate four-fresh-frame one-eye/profile gate; no generic face-rectangle fallback was added.
- Existing explicit user-tap priority, subject/pet ownership, AF requests, exposure and rendering preserved. Eye recognition is not proof of optical sharpness.

### 3.11 `FOCUSOVERLAY1A`

- Introduced the user-selected **Balanced Extended Ticks**: four separate right-angle corner segments, white/slightly warm-white active state, restrained amber pending/hold/lost states, no full box, no eye dot or crosshair.
- Removed the additional black-backed Eye AF plaque, retained accessible status descriptions and the existing `TrackingFocusView` state interfaces.
- First on-phone recording `63341.mp4` showed a visually oversized eye bracket: it drew using full AF-region dimensions and extended onto forehead/cheek. This was a display-sizing issue, not a demonstrated wrong Camera2 AF region.
- 3.11 signed build was successful; it remains a rollback reference.

### 3.12 `FOCUSOVERLAY1B` — accepted and merged

- Fixed **only the visible Eye AF marker extent**. In `HumanSubjectFocusController`, render the eye marker with a maximum of **17 dp horizontal half-width and 13 dp vertical half-height** (34 × 26 dp overall) using `FocusTickGeometry.eyeDisplayHalfWidth/Height`. The shared geometry still has a display-only minimum for visibility.
- **The selected eye centre, original normalized target, Camera2 AF-region dimensions and update calls did not change.** Neither person-tracking markers nor manual focus/area markers were shrunk.
- Recording `63345.mp4` (about 33 seconds) showed a compact eye-local marker, no duplicate Eye AF plaque, and larger **`Tracking person`** brackets later in the video. The larger person bracket is intentional: it is not a regression of the compact eye marker.
- **Important resolved point:** the user explicitly stated **“I intentionally tapped.”** The apparent alternation between adult and child at roughly 19, 22 and 26 seconds was user-directed retargeting, **not evidence of subject-identity theft or a tracking regression**. Do not reopen this diagnosis or modify tracker identity logic on the basis of that clip.
- User then explicitly instructed **“Merge it as we can improve if necessary.”** PR **#123** was merged successfully into `main`; final merge verified (`merged=true`), with no divergent `main` history overwritten. Merge commit `424380e54c7df53961eb44e9cd43b8214adb7236`.

**Signed 3.12 installer**

| Property | Verified value |
| --- | --- |
| APK | `M9Cam_3.12_FOCUSOVERLAY1B.apk` |
| App package | `com.m9project.m9cam.photon` |
| Version | `3.12-focusoverlay1b`; code `27312` |
| Bytes | `206520623` (~197 MiB) |
| SHA-256 | `434fb4a6de2e87aa883fe841db1d8abed5c38785e574a756020d8b6aa818a4ee` |
| GitHub Actions run | https://github.com/mwilliams455/M9Camera_refresh/actions/runs/40468484229 |
| Signing | Original certificate matched; APK signature verified |
| Package integrity | 16 KiB alignment verified; all **37 original native libraries** and **301 assets** preserved byte-for-byte; M9 and Monochrome menus verified |
| Test result | Source reconstruction, new and inherited host geometry/AF tests, Android build and focus/shutter regressions **PASS** |
| Delivery | Signed APK and ZIP containing installer plus verification reports generated in the previous conversation; artifact name `M9Cam-3.12-FOCUSOVERLAY1B-READY-TO-INSTALL` |

The recorded device review is maintained in `docs/M9_FOCUSOVERLAY1B_DEVICE_REVIEW_63345_20261027.md` and includes the user's tap clarification. Its original “merge approval pending” text is **historical**; subsequent user approval and PR #123 supersede that limitation.

## 2. The question that starts the next workstream

User asked: **“By default should that tracking be on?”** The assistant recommended **yes for tap-initiated tracking in Continuous AF**, not automatic tracking of every recognised object. The user next asked to create this handoff; **no separate 3.13 default-switch change has yet been authorised or implemented**.

### Recommended initial 3.13 behaviour (proposal, not shipped)

| Feature | Existing 3.12 behaviour | Proposed 3.13 default |
| --- | --- | --- |
| Automatic human Eye AF | Default ON in supported Wide AF-C modes | **ON** — preserve current behaviour |
| Base `Focus tracking` (`pref_focus_tracking`) | Opt-in / effective default OFF | **ON when AF-C is eligible**, enabling tap-to-track |
| `Subject-aware tracking` (`pref_focus_tracking_semantic`) | Opt-in / default OFF | **ON in eligible AF-C after deliberate tap**, person/cat/dog model; arbitrary object uses patch fallback |
| `Predictive AF-C` (`pref_focus_tracking_predictive`) | Opt-in / default OFF | **OFF initially**, retain optional advanced switch |
| `Persistent subject identity` (`pref_focus_tracking_identity`) | Opt-in / default OFF | **OFF initially**, retain optional advanced switch |
| AF-S / manual focus / unsupported AF lens | Normal focus interactions must work | **No persistent tracking interception**; preserve existing tap-focus/manual behaviour |
| Cat/Dog dedicated AF | Has independent ownership and higher priority | Unchanged; avoid new conflict |

**Interpretation:** A user can point the camera and automatic human Eye AF still works. After a deliberate tap on a different object/person, the camera may maintain the selected target and AF-C region until cancellation, retirement or an explicit change. **Do not start an arbitrary-object tracker or place persistent person boxes merely because the camera sees a subject.**

### Critical design/engineering caveats

1. **Not a one-line preference change.** `FocusTrackingController.enabled()` currently reads `pref_focus_tracking` with `false` fallback. `FocusTrackingController.tap()` can consume an ordinary tap once tracking is enabled, including paths that later report `focus_tracking_auto_required` if `autofocus` is false. Gating tap interception by AF-C support and maintaining ordinary tap-focus behaviour is a release blocker for any default-on change.
2. **Intentional target selection must remain explicit.** Current `tap()` starts `newTrackingFocus()`, sets `selected=true`, and tapping the current selected region can cancel/clear. Preserve predictable retap/cancel semantics, and permit deliberate refocusing without forcing persistent tracking in AF-S/manual modes.
3. **Protect autofocus ownership.** Automatic Eye AF's verified-eye handler must outrank ordinary object tracking when an eye is deliberately selected. A deliberate non-eye tap must override automatic Eye AF. Pet AF, Spot/Expand Spot/Custom, manual/AF-S, focus area rules and capture handover must remain deterministic; no simultaneous competing Camera2 handles or overlay boxes.
4. **Preserve saved preferences.** On fresh installs, the proposed experience can default ON; on upgrades, do **not** silently overwrite an existing explicit OFF setting. Review how the settings manager distinguishes missing keys from saved `false` before implementing migration. Verify dependencies so `Subject-aware ON` enables parent tracking, and disabling the parent retires dependent settings without unexpectedly changing the user's other options.
5. **Avoid idle recognition overhead.** The existing controller calls `warmSemantic()` on startup and in its tick loop when subject recognition is enabled. If default-on recognition would initialise ML models despite no selected subject, measure the cost; consider delayed/lazy initialization until a deliberate tap, without impacting the separate automatic Eye AF worker. Keep single-flight preview capture, offline models and bounded inference cadence; avoid doubling idle readbacks.
6. **No UI redesign.** Retain locked Balanced Extended Ticks and the compact eye marker. Larger brackets for person tracking are intentionally different. White means tracking/acquired, not guaranteed optical focus; amber hold/pending/lost must remain truthful.
7. **M9 + Monochrome parity.** Both profiles must honour the same default/migration/AF-mode policy. Keep this device-independent across Camera2-capable Android phones, not Xiaomi-specific.

## 3. Verified source/build anchors

This repository is **patch/reconstruction-oriented**, not a fully assembled Android Studio application at the Git root. Reuse the pinned source chain and already passing 3.12 GitHub Actions workflow as the construction baseline.

| Source | Purpose / next action |
| --- | --- |
| `main` after merge #123 | Accepted baseline; use for next feature branch; do not retroactively edit the signed 3.12 APK |
| `.github/workflows/build-m9cam-focusoverlay1b.yml` | Known successful full reconstructed Android build, host focus/eye geometry tests, exact prior APK download and signing; adapt for next candidate |
| `patches/aftracking2a/README.md` and patch chain | Existing opt-in tracking behaviour and initial Camera2 tracking handle |
| `patches/aftracking3b/apply.py` | Adds `pref_focus_tracking_semantic` as default false in both profile XML menus |
| `patches/aftracking4a/apply.py` | Adds `pref_focus_tracking_predictive`, default false |
| `patches/aftracking5a/apply.py` | Adds `pref_focus_tracking_identity`, default false |
| `patches/autoeye1a/src/com/particlesdevs/photoncamera/ui/camera/FocusTrackingController.java` | Current (3.10 lineage) tracking controller implementation; `enabled()`, `tap()`, `warmSemantic()`, `reconcileTrackingSwitches()` and `hasExplicitTrackingTarget()` are important |
| `patches/aftracking5a/src/com/particlesdevs/photoncamera/control/tracking/TrackingTogglePolicy.java` | Settings key identities and parent/child enable/disable rules; avoid breaking persistence |
| `patches/autoeye1a/src/com/particlesdevs/photoncamera/ui/camera/HumanSubjectFocusController.java` | Automatic human Eye AF, explicit eye-selection priority and non-face tap override; NOTE this is the **pre-3.11 patch source** and is subsequently presentation-modified by 3.11/3.12 |
| `patches/focusoverlay1a/apply.py` and `patches/focusoverlay1b/apply.py` | Reconstruct the final on-device focus marker without changing actual AF regions |
| `app/src/main/res/xml/preferences_m9.xml`, `preferences_monochrom.xml` **inside reconstructed source** | Actual compiled settings to inspect and change; not necessarily present as final app files at the Git root |
| `CameraFragment.java`, `FocusAreaTouchController.java`, focus/touch views **inside reconstructed source** | Tap routing and focus-area priority. Preserve Monochrome 2.78 tap-coordinate fix |

**Important:** The earlier `patches/aftracking5a/src/.../FocusTrackingController.java` is an *intermediate version*, and still contains an older Eye AF preference check. Inherited `autoeye1a` patches supersede it. Reconstruct the exact **3.12** source and inspect that runtime class rather than editing an older snapshot in isolation.

### Approved staging discipline for 3.13

1. Create a new branch from current merged `main`, e.g. `codex/m9-trackingdefault1a-v3.13`. Keep accepted 3.12 build, signatures, assets and previous branches as rollback.
2. Reconstruct the exact merged 3.12 Android source via workflow and pin parent source hashes. Introduce only preference defaults, AF-mode-safe tap dispatch/migration and necessary idle-lifecycle changes; **do not modify detector algorithms simply because a feature is now enabled by default**.
3. Decide the precise tap-intent/cancellation rule in code; keep automatic eye and dedicated pet priority, especially between face and non-face taps. No eager arbitrary selection.
4. Add settings default/migration tests for clean install, upgrade with explicit ON/OFF, stale/inconsistent parent+child switches, both profiles, AF-C vs AF-S/manual, camera/lens changes, and disabling the parent.
5. Run the inherited tracking, human Eye AF, profile admission, tap handover, pet, AF lifecycle, shutter, focus layout, and capture tests. Test that no background ML inference starts without a selected subject (apart from automatic Eye AF's existing behaviour).
6. Build signed candidate (working version `3.13`, potential versionCode `27313` **only if not consumed by parallel development**) using exact signed 3.12 APK as parent. Preserve original signing certificate, 16 KiB alignment, exact 37 native libraries/301 assets, and M9/Mono menus; preserve RAW/JPEG/DNG and renderer bytes/behaviour.
7. Deliver installable APK and ZIP directly in chat plus Actions artifact; device-test against 3.12 *before* merging 3.13. Test idle preview responsiveness, handheld moving child/pet, face-to-toy handoff, AF-S/manual, camera changes and a genuinely sharp saved photograph.

## 4. Acceptance criteria for the next candidate

- New installation in AF-C offers **tap-to-track immediately** without opening advanced settings. The camera should **not** display arbitrary tracking on an untouched scene.
- The existing auto Eye AF still selects verified human eyes automatically in Wide AF-C, and the compact eye-local marker remains 34 × 26 dp maximum.
- Tapping a different person, dog, toy or other eligible subject hands off the Camera2 focus region exactly once, maintains the intended subject, and avoids competing AF controllers. Tapping the selected target again can cancel or another equally discoverable cancellation exists.
- Switching to AF-S, manual, unsupported/fixed-focus lens, or a non-Wide focus-area mode does not unexpectedly steal ordinary focus taps. Fixed-focus support reports correctly, rather than falsely claiming AF lock.
- Existing explicit tracking OFF preference stays OFF after upgrading. Enabling/disabling dependent switches preserves coherent state and both profiles agree.
- Predictive and persistent identity remain independently opt-in by default; existing explicitly enabled states remain honoured.
- No new idle CPU / PixelCopy/inference load without selection beyond existing baseline Eye AF. Check viewfinder stutter, preview-to-output consistency and battery/thermal impacts on device rather than assuming zero cost.
- Active white, amber holding/pending/lost, and TalkBack/accessibility descriptions remain accurate; no duplicates, position offsets, or stale overlays after shutter, zoom, rotation, pause/resume or profile changes.
- Full Android CI and package integrity pass. **Measured subject-following and actual focus of saved JPEG/DNG** are distinct acceptance checks.

## 5. Other open items — separate work, not blockers to merged 3.12

- **Optical AF accuracy:** The `Eye AF reported focused` / HAL focus state in recordings alone does not prove a saved eye is optically sharp. A controlled moving-subject photograph comparison remains outstanding.
- **Magenta/yellow lines and red clipping/guide overlays:** Visible across the viewfinder even without the eye marker and sometimes over black preview. Their exact owning component was not proven. Trace UI draw/source before changing any visibility or rendering; this is **not a failure of the 3.12 corner-tick code**.
- **Intermittent `Eye AF` / `No subject` HUD transitions:** Observed as subjects turned or left the frame. Could be natural acquisition/occlusion; no source-level root cause or demonstrated regression yet. Keep separate from default-on object tracking.
- **Imaging priorities remain unchanged:** No HDR, single-frame RAW philosophy, consistent M9/Monochrome rendering, accurate preview, no unnecessary sharpness/exposure changes. This next stage is AF interaction and defaults, not a colour-science or RAW-processing rewrite.

## 6. Reference links

- Main repo: https://github.com/mwilliams455/M9Camera_refresh
- User-approved source merge: https://github.com/mwilliams455/M9Camera_refresh/pull/123
- 3.12 success / signed artifact: https://github.com/mwilliams455/M9Camera_refresh/actions/runs/40468484229
- 3.11 success: https://github.com/mwilliams455/M9Camera_refresh/actions/runs/40389004859
- 3.10 success: https://github.com/mwilliams455/M9Camera_refresh/actions/runs/40370915580
- User-reviewed 3.12 video record: https://github.com/mwilliams455/M9Camera_refresh/blob/main/docs/M9_FOCUSOVERLAY1B_DEVICE_REVIEW_63345_20261027.md
- Locked original design handoff: `M9_HANDOFF_20261026_BALANCED_EXTENDED_TICKS_LOCKED.md` (project upload; concept design **already final**)

---

### Exact instruction for the next chat

> Continue the M9 Project from `M9_PROJECT_HANDOFF_20261027_V3_12_MERGED_V3_13_TRACKING_DEFAULTS.md`. M9Cam 3.12 is **already merged to main** via PR #123 and its eye-local Balanced Extended Ticks are visually accepted; child/adult switching in recording `63345.mp4` was **intentional tapping**, not a bug. Next work is evaluating and (if proceeding) implementing default-on **tap-initiated** object/person tracking only in **eligible AF-C** while automatic Eye AF stays on, subject recognition is tap-scoped, existing user OFF choices are respected, and AF-S/manual remains normal. Keep predictive AF-C and persistent identity opt-in for now. Base implementation on reconstructed 3.12, run tests, sign an installable candidate and obtain device feedback. Do not reopen the 3.12 visual design or rewrite Camera2/RAW/colour pipelines.