# SCENEEXPOSURE1A test plan

SCENEEXPOSURE1A is diagnostic-only. It must not change live exposure, FB1, motion caps, renderer math, JPEG quality, or PERF3I behavior.

Expected build identity: `1.34-...exposureaudit1asceneexposure1a`.
Expected metadata section: `m9SceneExposureDiagnostic`.

The new diagnostic records:
- `positiveBodyPressure` and `positiveEvCandidate`
- `negativeHighlightPressure` and `negativeEvCandidate`
- `recommendedSignedEv`
- `direction` = increase / decrease / neutral
- `legacyFb1Reference`

Initial sanity expectations from the two reference scenes that motivated this build:
- ordinary static indoor scene similar to 2026-09-02 12:54:56: modest positive recommendation around +0.3 to +0.4 EV, not applied;
- severe indoor backlight similar to 2026-09-02 12:37:47: strong positive recommendation around +1.0 to +1.25 EV, not applied;
- a broadly bright/high-key scene should be able to generate a negative recommendation rather than being forced to zero or positive.

Device validation set:
1. static ordinary indoor scene;
2. severe indoor backlight;
3. normal outdoor overcast/daylight;
4. broad bright/high-key scene with substantial bright occupancy;
5. intentionally high-contrast scene/silhouette if convenient.

For every frame retain JPEG, `_M9.json`, and `_M9_PRIMARY.json`. Compare `recommendedSignedEv` against visual result, RAW headroom diagnostics, existing FB1 recommendation, and actual Camera2 exposure from `m9ExposureAudit`.

Do not promote this recommendation into live exposure until both positive and negative cases have been reviewed across multiple scenes.
