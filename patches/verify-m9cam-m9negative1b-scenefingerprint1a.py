#!/usr/bin/env python3
from pathlib import Path
import math, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-m9negative1b-scenefingerprint1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
negative = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java').read_text()
coord = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java').read_text()
gradle = (root / 'app/build.gradle').read_text()
backlight = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java').read_text()
compact_version = "1.46-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1b-fp1a-cm1b"

checks = {
    'M9NEGATIVE1B schema': 'm9cam.m9negative.v2.capturemeter1b.scenefingerprint1a' in negative,
    'SCENEFINGERPRINT1A schema': 'm9cam.scenefingerprint.v1.scene1h_existingfields1a' in negative,
    '60s recency gate': 'MAX_FEEDBACK_AGE_MS = 60_000L' in negative,
    'recency filters candidates before distance': 'if (ageMs > MAX_FEEDBACK_AGE_MS)' in negative,
    'global median descriptor': 'normalizedDelta(median, other.median, 40.0)' in negative,
    'center median descriptor': 'normalizedDelta(center, other.center, 40.0)' in negative,
    'q95 descriptor': 'normalizedDelta(q95, other.q95, 48.0)' in negative,
    'q99 descriptor': 'normalizedDelta(q99, other.q99, 50.0)' in negative,
    'dark64 descriptor': 'normalizedDelta(dark64, other.dark64, 0.22)' in negative,
    'bright192 descriptor': 'normalizedDelta(bright192, other.bright192, 0.18)' in negative,
    'bright224 descriptor': 'normalizedDelta(bright224, other.bright224, 0.10)' in negative,
    'center delta descriptor': 'normalizedDelta(centerDelta, other.centerDelta, 50.0)' in negative,
    'middle-center q95 descriptor': 'normalizedDelta(middleCenterQ95, other.middleCenterQ95, 50.0)' in negative,
    'starvation descriptor': 'normalizedDelta(starvation, other.starvation, 0.50)' in negative,
    'preview exposure energy moderator': 'previewEnergyIsoSeconds / other.previewEnergyIsoSeconds' in negative,
    'actual SCENE1H dark key': 'darkFractionLE64' in negative,
    'actual SCENE1H bright192 key': 'brightFractionGE192' in negative,
    'actual SCENE1H bright224 key': 'brightFractionGE224' in negative,
    'actual SCENE1H preview energy key': 'previewExposureEnergyIsoSeconds' in negative,
    'reject expired feedback': 'completed_raw_feedback_expired' in negative,
    'association policy': 'recent_scene1h_fingerprint_then_completed_raw' in negative,
    'live mutation stays false': 'out.put("usedToMutateCaptureTarget", false)' in negative,
    'jpeg not capture input': 'out.put("jpegBrightnessUsedForCapture", false)' in negative,
    'recommendation positive bound preserved': 'MAX_POSITIVE_DELTA_EV = 0.50' in negative,
    'recommendation negative bound preserved': 'MAX_NEGATIVE_DELTA_EV = -0.50' in negative,
    'raw headroom target preserved': 'log2(0.92 / Math.max(best.q998, 1e-6))' in negative,
    'positive recommendation equation preserved': 'additionalCaptureHeadroomEv\n                    * negativeShadowStarvationEvidence' in negative,
    'negative recommendation equation preserved': '-0.35 * meaningfulClipRiskEvidence' in negative,
    'coordinator identifies 1B': 'm9cam.exposuresplit.v3.capturemeter1b.m9negative1b.scenefingerprint1a' in coord,
    'compact Android versionName exact': ("versionName '" + compact_version + "'") in gradle,
    'compact Android versionName safely short': len(compact_version) < 96,
    'full forensic build marker retained': 'm9negative1bscenefingerprint1acapturemeter1b' in backlight,
}
failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(('OK   ' if ok else 'FAIL ') + name)
if failed:
    raise SystemExit('M9NEGATIVE1B structural self-check failed: ' + ', '.join(failed))

# Regression labels copied from the 2026-09-03 M9NEGATIVE1A test set.
# Each vector: median, center, q95, q99, dark64, bright192, bright224,
# centerDelta, middleCenterQ95, starvation, previewExposureEnergyIsoSeconds.
def fp(median, center, q95, q99, dark64, b192, b224, center_delta, mcq95, starvation, energy):
    return (median, center, q95, q99, dark64, b192, b224, center_delta, mcq95, starvation, energy)

def nd(a, b, scale):
    return abs(a-b)/scale

def distance(a, b):
    scales = (40.0,40.0,48.0,50.0,0.22,0.18,0.10,50.0,50.0,0.50)
    d = max(nd(a[i], b[i], scales[i]) for i in range(10))
    if a[10] > 0 and b[10] > 0:
        d = max(d, abs(math.log(a[10]/b[10], 2.0))/1.50)
    return d

samples = {
    '120721': fp(97,122,224,249,.291233,.179977,.050347,25,229,1.0,.128455),
    '120723': fp(93,116,223,243,.312645,.174045,.049334,23,243,1.0,.126884),
    '120734': fp(122,85,212,234,.348090,.191985,.020833,-37,205,1.0,.067588),
    '120737': fp(116,81,213,237,.358073,.191262,.021991,-35,208,1.0,.077030),
    '120821': fp(93,93,206,228,.379051,.144676,.021991,0,171,1.0,.169383),
    '121537': fp(75,69,211,225,.427,.173,.011,-6,221,1.0,.0219),
    '121612': fp(80,75,211,217,.382,.308,.002,-5,203,1.0,.0225),
    '121700': fp(63,58,218,228,.509,.295,.022,-5,133,1.0,.0070),
    '121720': fp(72,67,220,230,.446,.288,.029,-5,169,1.0,.0078),
    '121747': fp(74,77,221,229,.439,.257,.032,3,195,1.0,.0099),
    '121751': fp(64,66,221,229,.508,.256,.030,2,194,1.0,.0096),
    '121504': fp(120,133,217,221,.317,.314,.002,13,213,1.0,.0204),
    '122012': fp(76,66,208,213,.405,.128,.004,-10,127,1.0,.0190),
    '122339': fp(174,180,205,237,.242,.139,.019,6,205,1.0,.0091),
}

same_pairs = [('120721','120723'), ('120734','120737'), ('121747','121751')]
false_pairs = [('120737','121537'), ('120737','121612'), ('120821','121700'),
               ('120821','121720'), ('121751','122339'), ('121504','122012')]
for a,b in same_pairs:
    d = distance(samples[a], samples[b])
    print(f'PAIR same {a}->{b} distance={d:.3f}')
    if not d < 1.0:
        raise SystemExit(f'SCENEFINGERPRINT1A regression failed: same-scene pair {a}->{b} rejected at {d:.3f}')
for a,b in false_pairs:
    d = distance(samples[a], samples[b])
    print(f'PAIR false {a}->{b} distance={d:.3f}')
    if not d > 1.0:
        raise SystemExit(f'SCENEFINGERPRINT1A regression failed: false pair {a}->{b} accepted at {d:.3f}')

print('M9NEGATIVE1B / SCENEFINGERPRINT1A verification passed')
