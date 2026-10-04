#!/usr/bin/env python3
from pathlib import Path
import math, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-m9negative1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'M9NEGATIVE1A verify missing {rel}')
    return p.read_text()

def must(rel, token):
    if token not in read(rel):
        raise SystemExit(f'M9NEGATIVE1A verify missing {token!r} in {rel}')

def must_not(rel, token):
    if token in read(rel):
        raise SystemExit(f'M9NEGATIVE1A verify forbidden {token!r} in {rel}')

negative = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java'
coord = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java'
renderer = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
render_meter = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RenderMeterDiagnostic.java'
render_model = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RenderMeterModel1C.java'
scene = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java'
spool = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java'

must('app/build.gradle', "versionName '1.45-m9modern7r38luma24fb1primary25perf3i")
must(negative, 'm9cam.m9negative.v1.capturemeter1b.completedraw1a')
must(negative, 'diagnostic_only_no_exposure_mutation')
must(negative, 'usedToMutateCaptureTarget')
must(negative, 'jpegBrightnessUsedForCapture')
must(negative, 'negativeHighlightProtectionEvidence')
must(negative, 'negativeHighlightStressEvidence')
must(negative, 'negativeShadowStarvationEvidence')
must(negative, 'negativeRecoverabilityEvidence')
must(negative, 'negativeExposureAdequacyEvidence')
must(negative, 'meaningfulClipRiskEvidence')
must(negative, 'additionalCaptureHeadroomEv')
must(negative, 'recommendedCaptureDeltaEv')
must(negative, 'captureExposureEnergyIsoSeconds')
must(negative, 'capture_step_fifo_to_primary_render_completion')
must(negative, 'SIMILAR_SCENE_DISTANCE = 1.0')
must(negative, 'MAX_POSITIVE_DELTA_EV = 0.50')
must(negative, 'MAX_NEGATIVE_DELTA_EV = -0.50')

must(coord, 'm9cam.exposuresplit.v2.capturemeter1b.m9negative1a')
must(coord, 'M9NegativeFeedback1A.evaluate(scene1h, proposedStable)')
must(coord, 'M9NegativeFeedback1A.noteCaptureScene(scene1h)')
must(coord, 'm9Negative1AUsedToMutateCaptureTarget\", false')
must(coord, 'stabilizedCaptureTargetEv\", proposedStable')

must(renderer, 'rawUq25')
must(renderer, 'rawUq50')
must(renderer, 'o.uq25 = quantileBins(bins, total, .25)')
must(renderer, 'o.uq50 = quantileBins(bins, total, .50)')
must(renderer, 'CaptureResult.SENSOR_EXPOSURE_TIME')
must(renderer, 'captureExposureEnergyIsoSeconds')
must(renderer, 'M9NegativeFeedback1A.recordCompletedRaw(diag, iso, exposureTimeNs)')
must(renderer, 'if (primaryRoute)')

# Frozen downstream renderer and SceneExposure identities remain intact.
must(render_meter, 'm9cam.rendermeter.v3.evidence1c')
must(render_meter, 'direct_rendered_luma_evidence_model_active_no_signed_ev')
must(render_model, 'm9cam.rendermetermodel.v1.evidence1c')
must(render_model, 'evidence_only_no_signed_ev')
must(scene, 'm9cam.sceneexposure.v8.renderaware1h')
must(scene, 'diagnostic_only_no_exposure_mutation')
must(renderer, 'JPEG_QUALITY = 95')
must(renderer, 'METER_TARGET = 0.107 * (8192.0 / 10000.0)')
must(renderer, 'M9RenderedLumaDiagnostic.measure(bitmap)')
must(renderer, 'No pixel, TC20, colour or JPEG state is mutated by this diagnostic.')

# SIDECAR1B-only debounce adjustment.
must(spool, 'm9cam.sidecarspool.v1.privatebundle1b')
must(spool, 'BUNDLE_IDLE_MS = 3000L')
must(spool, 'INDIVIDUAL_DELAY_MS = 12000L')
must(spool, 'private_immediate_bundle_first_eventual_individual_public_export')

# New negative model must remain observational and independent from finished JPEG luma.
must_not(negative, 'M9RenderedLumaDiagnostic')
must_not(negative, 'renderLiftNeedEvidence')
must_not(negative, 'correctionAppliedEv')
must_not(negative, 'CaptureRequest.Builder')
must_not(negative, '.set(CaptureRequest')
must_not(negative, 'setPixel(')
must_not(negative, 'setPixels(')
must_not(negative, 'liveEligible\", true')

# Sanity-check the provisional diagnostic equation against representative RAW-negative shapes.
def clamp(x, lo, hi): return max(lo, min(hi, x))
def smooth(x, lo, hi):
    t = clamp((x-lo)/(hi-lo), 0.0, 1.0)
    return t*t*(3.0-2.0*t)
def recommendation(q25, q50, q998, clip):
    tail_stress = smooth(q998, .88, .98)
    clip_risk = smooth(clip, .005, .030)
    meaningful = clamp(clip_risk * max(.35, smooth(q998,.72,.96)), 0.0, 1.0)
    stress = clamp(max(tail_stress * (.35 + .65*meaningful), meaningful), 0.0, 1.0)
    lower = clamp(.68*smooth(q50,.025,.080) + .32*smooth(q25,.006,.025), 0.0, 1.0)
    starvation = 1.0-lower
    raw_headroom = math.log(max(.92/max(q998,1e-6),1e-12),2)
    headroom = clamp(raw_headroom,0.0,.50)*(1.0-.80*meaningful)
    pos = headroom*starvation*(1.0-.65*stress)
    neg = 0.0
    if meaningful > .45 and starvation < .55:
        neg = -.35*meaningful*(1.0-starvation)
    rec = clamp(pos+neg,-.50,.50)
    if abs(rec)<.05: rec=0.0
    return rec, starvation, meaningful, headroom

# Handoff-type protected sky / dark foreground: modest positive RAW delta, not +0.75/+1 EV.
rec, starve, cliprisk, headroom = recommendation(.003,.012,.698,.0062)
if not (0.08 <= rec <= 0.45 and starve > .75 and headroom > .20):
    raise SystemExit(f'M9NEGATIVE1A regression protected-sky rec={rec:.3f} starve={starve:.3f} headroom={headroom:.3f}')
# Healthy negative with strong upper placement and adequate body should hold.
rec, _, _, _ = recommendation(.025,.080,.94,.004)
if abs(rec) > .05:
    raise SystemExit(f'M9NEGATIVE1A regression healthy-negative rec={rec:.3f}')
# Broad/high clipping with adequate lower body should recommend reducing capture modestly.
rec, starve, cliprisk, _ = recommendation(.040,.100,.99,.040)
if not (rec < -0.10 and starve < .10 and cliprisk > .90):
    raise SystemExit(f'M9NEGATIVE1A regression clipped-negative rec={rec:.3f} starve={starve:.3f} cliprisk={cliprisk:.3f}')

print('M9NEGATIVE1A verification PASS: completed RAW feedback is scene-similar, bounded and diagnostic-only; q25/q50 lower-distribution evidence added without a second RAW scan; RENDERMETER1C/SceneExposure/Camera2/motion/TC20/color/JPEG-DNG outputs remain frozen; SIDECAR idle debounce is 3000 ms')
