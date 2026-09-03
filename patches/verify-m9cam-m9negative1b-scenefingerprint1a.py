#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-m9negative1b-scenefingerprint1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
negative = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java').read_text()
coord = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java').read_text()
gradle = (root / 'app/build.gradle').read_text()

checks = {
    'M9NEGATIVE1B schema': 'm9cam.m9negative.v2.capturemeter1b.scenefingerprint1a' in negative,
    'SCENEFINGERPRINT1A schema': 'm9cam.scenefingerprint.v1.previewexistingfields1a' in negative,
    '60s recency gate': 'MAX_FEEDBACK_AGE_MS = 60_000L' in negative,
    'recency filters candidates before distance': 'if (ageMs > MAX_FEEDBACK_AGE_MS)' in negative,
    'full distribution q95': 'normalizedDelta(q95, other.q95' in negative,
    'dark fraction descriptor': 'normalizedDelta(dark64, other.dark64' in negative,
    'bright192 descriptor': 'normalizedDelta(bright192, other.bright192' in negative,
    'bright224 descriptor': 'normalizedDelta(bright224, other.bright224' in negative,
    'axis spread descriptor': 'normalizedDelta(axisSpread, other.axisSpread' in negative,
    'low region descriptor': 'normalizedDelta(lowRegionMedianRatio, other.lowRegionMedianRatio' in negative,
    'top bright descriptor': 'normalizedDelta(topBrightShare, other.topBrightShare' in negative,
    'top row heterogeneity descriptor': 'normalizedDelta(topRowHeterogeneity, other.topRowHeterogeneity' in negative,
    'preview exposure energy moderator': 'previewEnergyIsoSeconds / other.previewEnergyIsoSeconds' in negative,
    'reject expired feedback': 'completed_raw_feedback_expired' in negative,
    'association policy': 'recent_full_preview_fingerprint_then_completed_raw' in negative,
    'live mutation stays false': 'out.put("usedToMutateCaptureTarget", false)' in negative,
    'jpeg not capture input': 'out.put("jpegBrightnessUsedForCapture", false)' in negative,
    'recommendation positive bound preserved': 'MAX_POSITIVE_DELTA_EV = 0.50' in negative,
    'recommendation negative bound preserved': 'MAX_NEGATIVE_DELTA_EV = -0.50' in negative,
    'raw headroom target preserved': 'log2(0.92 / Math.max(best.q998, 1e-6))' in negative,
    'coordinator identifies 1B': 'm9cam.exposuresplit.v3.capturemeter1b.m9negative1b.scenefingerprint1a' in coord,
    'version bumped': "versionName '1.46-" in gradle,
    'version marker': 'm9negative1bscenefingerprint1acapturemeter1b' in gradle,
}
failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(('OK   ' if ok else 'FAIL ') + name)
if failed:
    raise SystemExit('M9NEGATIVE1B self-check failed: ' + ', '.join(failed))
print('M9NEGATIVE1B / SCENEFINGERPRINT1A verification passed')
