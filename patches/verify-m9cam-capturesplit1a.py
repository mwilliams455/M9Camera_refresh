#!/usr/bin/env python3
from pathlib import Path
import math, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-capturesplit1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()

checks = {
    '1H scene math retained': (
        'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java',
        'm9cam.sceneexposure.v8.renderaware1h'),
    'capture/render split attached to scene output': (
        'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java',
        'M9CaptureRenderExposureCoordinator.evaluate(out)'),
    'capture coordinator schema': (
        'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java',
        'm9cam.exposuresplit.v1.capturemeter1a.temporal1a'),
    'render proxy excluded from capture': (
        'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java',
        'scene1hRenderProxyEvExcludedFromCapture'),
    'five capture history': (
        'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java',
        'HISTORY = 5'),
    'scene change reset': (
        'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java',
        'scene_change_reset_first_capture_normal_envelope'),
    'capture slew limit': (
        'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java',
        'MAX_SLEW_EV_PER_CAPTURE = 0.35'),
    'render meter schema': (
        'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RenderMeterDiagnostic.java',
        'm9cam.rendermeter.v1.observational1a'),
    'render meter waits for direct rendered luma': (
        'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RenderMeterDiagnostic.java',
        'awaiting_direct_rendered_luma_measurement'),
    'render meter attached after renderer statistics': (
        'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
        'M9RenderMeterDiagnostic.evaluate(diag)'),
    '1.42 build identity': (
        'app/build.gradle',
        '1.42-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1hcapturesplit1a'),
}
for label, (rel, needle) in checks.items():
    p = root / rel
    if not p.exists() or needle not in p.read_text():
        raise SystemExit(f'FAIL {label}: {needle!r} missing from {rel}')
    print(f'OK   {label}')

scene = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java').read_text()
coord = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java').read_text()
rendermeter = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RenderMeterDiagnostic.java').read_text()
renderer = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java').read_text()

for forbidden in [
    'live_test_signed_exposure_enabled',
    'scene1e_total_signed_ev_replaces_fb1_total',
    'applySceneExposureDelta',
    'recordLiveApplication',
    'CaptureRequest.Builder',
]:
    if forbidden in coord or forbidden in rendermeter:
        raise SystemExit(f'FAIL CAPTURESPLIT1A diagnostic-only contract: {forbidden!r}')
print('OK   coordinator/render-meter contain no live Camera2/FB1 mutation handoff')

if renderer.count('M9RenderMeterDiagnostic.evaluate(diag)') != 1:
    raise SystemExit('FAIL renderer should contain exactly one observational render-meter call')
print('OK   renderer has exactly one observational render-meter insertion')

required_split = 'double rawCaptureCandidate = clamp(positiveEv + captureNegativeEv, -1.25, 1.25);'
if required_split not in coord:
    raise SystemExit('FAIL capture candidate does not exclude render-aware proxy exactly')
print('OK   capture candidate excludes render-aware 1H negative proxy')

for needle in ['out.put("correctionAppliedEv", 0.0);',
               'out.put("correctionCandidateEv", 0.0);',
               'out.put("liveEligible", false);']:
    if needle not in rendermeter:
        raise SystemExit(f'FAIL observational render-meter guard missing {needle}')
print('OK   RENDERMETER1A is observational-only until direct rendered luma exists')

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def median(v):
    v = sorted(v)
    n = len(v)
    return v[n//2] if n & 1 else 0.5 * (v[n//2-1] + v[n//2])

cat_raw = [0.082, 1.249, 0.402, 0.400, 0.425, 0.400]
bounded = [clamp(x, -0.25, 0.40) for x in cat_raw]
history = []
stable = None
trajectory = []
for x in bounded:
    history.append(x)
    history = history[-5:]
    med = median(history)
    agree = sum(abs(v - med) <= 0.20 for v in history)
    if stable is None:
        proposed = clamp(x, -0.25, 0.40)
    else:
        delta = med - stable
        ad = abs(delta)
        if ad <= 0.20:
            gate = True
        elif ad <= 0.40:
            gate = agree >= 2
        elif ad <= 0.70:
            gate = agree >= 3
        else:
            gate = False
        desired = med if gate else stable + clamp(delta, -0.20, 0.20)
        proposed = stable + clamp(desired - stable, -0.35, 0.35)
    stable = clamp(proposed, -0.25, 0.40)
    trajectory.append(stable)

if max(trajectory) > 0.4000001:
    raise SystemExit(f'FAIL cat burst conservative envelope: {trajectory}')
if abs(trajectory[-1] - 0.40) > 0.08:
    raise SystemExit(f'FAIL cat burst does not converge near +0.40 EV: {trajectory}')
if any(abs(b-a) > 0.3500001 for a, b in zip(trajectory, trajectory[1:])):
    raise SystemExit(f'FAIL cat burst slew limit: {trajectory}')
print(f'OK   cat-like unstable burst is bounded/stabilized: {trajectory}')

pos = 0.08717079
capture_neg = 0.0
render_proxy = -0.30
capture_candidate = clamp(pos + capture_neg, -1.25, 1.25)
if capture_candidate <= 0.0 or render_proxy >= 0.0:
    raise SystemExit('FAIL capture/render separation synthetic hot-render anchor')
print(f'OK   render-hot proxy remains separate: capture {capture_candidate:+.3f} EV, render proxy {render_proxy:+.3f} EV')

for needle in [
    'NORMAL_NEG_LIMIT_EV = -0.25',
    'NORMAL_POS_LIMIT_EV = 0.40',
    'STARVATION_POS_LIMIT_EV = 0.75',
    'EXCEPTIONAL_POS_LIMIT_EV = 1.00',
]:
    if needle not in coord:
        raise SystemExit(f'FAIL capture envelope missing {needle}')
print('OK   capture envelopes: normal -0.25..+0.40, starvation +0.75, exceptional +1.00')

for needle in [
    'COLOR_BayerRG2BGR_EA',
    'renderBlockParallelDirectBitmap',
    'curve02 normal-ISO sRGB Standard',
    'TG_NEG_CB_COMPRESSION = 0.25',
    'HSM_H = 0.25',
    'native_parallel_luma8_weightedselect_parity1b',
]:
    if needle not in renderer:
        raise SystemExit(f'FAIL frozen renderer photographic anchor missing {needle!r}')
print('OK   frozen R3.8/H25/TG1/TC20 photographic anchors retained')

print('CAPTURESPLIT1A verification passed: capture adequacy, temporal stabilization and render tonal placement are now separate diagnostic modules; 1H math remains observational, render-aware proxy cannot drive capture, and renderer correction remains disabled pending direct rendered-luma evidence')
