#!/usr/bin/env python3
from pathlib import Path
import math, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-m9negative1c-signedcal1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
negative = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java').read_text()
coord = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java').read_text()
gradle = (root / 'app/build.gradle').read_text()
backlight = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java').read_text()
compact_version = '1.47-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1a-sc1a-cm1b'

checks = {
    'M9NEGATIVE1C schema': 'm9cam.m9negative.v3.capturemeter1b.scenefingerprint1a.signedcal1a' in negative,
    'SIGNEDCAL1A schema': 'm9cam.signedcal.v1.completedraw_coordinates1a' in negative,
    'self completed RAW calibration emitted': 'buildSignedCalibration(raw, "completed_raw_self")' in negative,
    'matched source calibration emitted': 'buildSignedCalibration(best, "matched_completed_raw_source")' in negative,
    'diagnostic-only signed calibration': 'diagnostic_only_counterfactual_raw_scaling' in negative,
    'signed calibration cannot mutate': 'out.put("usedToMutateCaptureTarget", false)' in negative,
    'scene fingerprint explicitly frozen': 'out.put("sceneAssociationFrozen", "SCENEFINGERPRINT1A")' in negative,
    'recommendation formula explicitly frozen': 'out.put("recommendationFormulaFrozen", "M9NEGATIVE1A")' in negative,
    'capture recommendation model label frozen': 'frozen_m9negative1a_formula' in negative,
    'q25 low coordinate': 'evToQ25_0p006' in negative,
    'q25 high coordinate': 'evToQ25_0p025' in negative,
    'q50 low coordinate': 'evToQ50_0p025' in negative,
    'q50 middle coordinate': 'evToQ50_0p055' in negative,
    'q50 high coordinate': 'evToQ50_0p080' in negative,
    'q998 0.88 coordinate': 'evToQ99_8_0p880' in negative,
    'q998 0.92 coordinate': 'evToQ99_8_0p920' in negative,
    'q998 0.98 coordinate': 'evToQ99_8_0p980' in negative,
    'minus half stop projection': 'new double[] {-0.50, -0.25, 0.0, 0.25, 0.50}' in negative,
    'linear projection caveat': 'hard_clip_fraction_and_scene_response_are_not_predicted' in negative,
    'negative clip gate observable': 'negativeClipGatePass' in negative,
    'negative body gate observable': 'negativeBodyGatePass' in negative,
    'negative gate margin observable': 'negativeClipGateMargin' in negative and 'negativeBodyGateMargin' in negative,
    'pre-gate negative candidate observable': 'negativeCandidateBeforeGateEv' in negative,
    'frozen positive bound preserved': 'MAX_POSITIVE_DELTA_EV = 0.50' in negative,
    'frozen negative bound preserved': 'MAX_NEGATIVE_DELTA_EV = -0.50' in negative,
    'frozen q998 headroom target preserved': 'log2(0.92 / Math.max(best.q998, 1e-6))' in negative,
    'frozen positive equation preserved': 'additionalCaptureHeadroomEv\n                    * negativeShadowStarvationEvidence' in negative,
    'frozen negative equation preserved': '-0.35 * meaningfulClipRiskEvidence' in negative,
    'frozen negative clip gate preserved': 'meaningfulClipRiskEvidence > 0.45 && negativeShadowStarvationEvidence < 0.55' in negative,
    'frozen deadband preserved': 'Math.abs(recommendation) < 0.05' in negative,
    'SCENEFINGERPRINT threshold frozen': 'SIMILAR_SCENE_DISTANCE = 1.0' in negative,
    'SCENEFINGERPRINT recency frozen': 'MAX_FEEDBACK_AGE_MS = 60_000L' in negative,
    'SCENEFINGERPRINT energy scale frozen': 'previewEnergyIsoSeconds / other.previewEnergyIsoSeconds' in negative,
    'coordinator identifies signed calibration': 'm9cam.exposuresplit.v4.capturemeter1b.m9negative1c.scenefingerprint1a.signedcal1a' in coord,
    'compact version exact': ("versionName '" + compact_version + "'") in gradle,
    'compact version safely short': len(compact_version) < 96,
    'full forensic marker retained': 'm9negative1csignedcal1ascenefingerprint1acapturemeter1b' in backlight,
}
for name, ok in checks.items():
    print(('OK   ' if ok else 'FAIL ') + name)
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit('M9NEGATIVE1C / SIGNEDCAL1A structural check failed: ' + ', '.join(failed))

def clamp01(x): return max(0.0, min(1.0, x))
def clamp(x, lo, hi): return max(lo, min(hi, x))
def smoothstep(x, lo, hi):
    t = clamp01((x-lo)/(hi-lo))
    return t*t*(3.0-2.0*t)
def model(q25, q50, q998, clip):
    tail = smoothstep(q998, .88, .98)
    clip_risk = smoothstep(clip, .005, .030)
    meaningful = clamp01(clip_risk * max(.35, smoothstep(q998, .72, .96)))
    highlight = clamp01(max(tail * (.35 + .65*meaningful), meaningful))
    q50a = smoothstep(q50, .025, .080)
    q25a = smoothstep(q25, .006, .025)
    body = clamp01(.68*q50a + .32*q25a)
    starvation = clamp01(1.0-body)
    head = math.log(.92/max(q998,1e-6), 2.0)
    add = clamp(head, 0.0, .50) * (1.0-.80*meaningful)
    pos = add * starvation * (1.0-.65*highlight)
    neg_before = -.35 * meaningful * (1.0-starvation)
    clip_gate = meaningful > .45
    body_gate = starvation < .55
    neg = neg_before if clip_gate and body_gate else 0.0
    combined = clamp(pos+neg, -.50, .50)
    rec = 0.0 if abs(combined) < .05 else combined
    return dict(body=body, starvation=starvation, meaningful=meaningful, highlight=highlight,
                head=head, pos=pos, neg_before=neg_before, clip_gate=clip_gate,
                body_gate=body_gate, neg=neg, combined=combined, rec=rec)

def near(actual, expected, tol=2e-3):
    return abs(actual-expected) <= tol

# Real completed-RAW vectors from the 2026-09-03 SCENEFINGERPRINT1A validation batch.
# Window: highlight stressed but lower body starved; must NOT recommend negative exposure.
window = model(.0031282586027111575, .010427528675703858,
               .9332638164754953, .038721561431884766)
print('WINDOW', window)
if not window['clip_gate'] or window['body_gate'] or window['rec'] != 0.0:
    raise SystemExit('SIGNEDCAL1A regression: backlit window should expose clip pressure but block negative EV')
if not near(window['head'], -0.0206511, 5e-4):
    raise SystemExit('SIGNEDCAL1A regression: backlit window q998 headroom coordinate drifted')

# Bike: lower body is already adequate but there is abundant highlight headroom; frozen deadband remains zero.
bike = model(.0334, .0699, .4265, .0003)
print('BIKE', bike)
if bike['rec'] != 0.0 or not (0.02 < bike['combined'] < 0.05):
    raise SystemExit('SIGNEDCAL1A regression: healthy bike scene should remain inside frozen zero deadband')

# Dark bottle/detergent control: starved lower body with headroom should remain a strong positive diagnostic.
detergent = model(.0052, .0136, .6709, 0.0)
print('DETERGENT', detergent)
if not near(detergent['rec'], .4555361, 3e-3):
    raise SystemExit('SIGNEDCAL1A regression: dark-headroom positive control drifted')

# Synthetic negative control proves the frozen negative branch remains measurable in diagnostics.
negative_control = model(.030, .080, .990, .040)
print('NEGATIVE_CONTROL', negative_control)
if not negative_control['clip_gate'] or not negative_control['body_gate']:
    raise SystemExit('SIGNEDCAL1A regression: synthetic adequate-body highlight stress should pass both negative gates')
if not near(negative_control['rec'], -.35, 1e-9):
    raise SystemExit('SIGNEDCAL1A regression: frozen negative branch equation drifted')

# Counterfactual math is deliberately simple linear RAW scaling, not a clip-fraction predictor.
q998 = .9332638164754953
minus_quarter = q998 * (2.0 ** -0.25)
plus_quarter = q998 * (2.0 ** .25)
print(f'PROJECTION q998 -0.25EV={minus_quarter:.6f} +0.25EV={plus_quarter:.6f}')
if not near(minus_quarter, .7847, 2e-3) or not near(plus_quarter, 1.1098, 2e-3):
    raise SystemExit('SIGNEDCAL1A regression: linear RAW projection math unexpected')

print('M9NEGATIVE1C / SIGNEDCAL1A verification passed')
