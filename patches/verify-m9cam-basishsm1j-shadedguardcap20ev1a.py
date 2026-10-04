#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-basishsm1j-shadedguardcap20ev1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
for p in (renderer_path, gradle_path, frames_path):
    if not p.exists():
        raise SystemExit('BASISHSM1J verifier missing: ' + str(p))

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()
frames = frames_path.read_text()

required_renderer = [
    'm9cam.renderer.basishsm.shadedguardcap20ev.finalclipaudit.v1a.main',
    'private static JSONObject finalClipAudit1A(',
    'finalClipAudit1AEnabled", true',
    'd.put("finalClipAudit1A", finalClipAudit1A(oriented));',
    'shadedGuardCap20Ev1AEnabled", true',
    'shadedGuardCap20Ev1ARequested',
    'shadedGuardCap20Ev1AMaxReductionEv',
    'shadedGuardCap20Ev1AMinGainRatio',
    'shadedGuardCap20Ev1AFloorGain',
    'shadedGuardCap20Ev1ABound',
    'shadedGuard1ARenderedMeterGain',
    'shadedGuard1AFullRequestedGainDeltaEvVsOldOn',
    'Math.pow(2.0, -shadedGuardCap20Ev1AMaxReductionEv)',
    'Math.max(shadedGuard1AMeterGain, shadedGuardCap20Ev1AFloorGain)',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARD1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARDCAP20EV1A"',
    'boolean[] applyShadedGuard1AFlags = {false, false, true, false};',
    'boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false, true};',
    '"shading_on_guarded_cap20ev1a"',
]
for marker in required_renderer:
    if marker not in renderer:
        raise SystemExit('BASISHSM1J verifier missing renderer marker: ' + marker)

if renderer.count('final double shadedGuardCap20Ev1AMaxReductionEv = 0.20;') != 1:
    raise SystemExit('BASISHSM1J verifier cap value/count mismatch')
if 'Math.min(meter.baseGain, shadedGuard1ACorrectedGuardGain)' not in renderer:
    raise SystemExit('BASISHSM1J verifier full SHADEDGUARD formula missing')
if 'applyShadedGuard1A || applyShadedGuardCap20Ev1A' not in renderer:
    raise SystemExit('BASISHSM1J verifier cap/full eligibility seam missing')

if '-basishsm1j-shadedguardcap20ev1a' not in gradle:
    raise SystemExit('BASISHSM1J verifier build provenance missing')
if '-basishsm1i-finalclipaudit1a' in gradle:
    raise SystemExit('BASISHSM1J verifier stale 1I build provenance')

for marker in [
    'M9_NOHDR1A_SINGLE_FRAME_BOUNDARY',
    'frameCount = 1;',
    'throwCount = 0;',
    'IsoExpoSelector.HDR = false;',
]:
    if marker not in frames:
        raise SystemExit('BASISHSM1J verifier NOHDR boundary missing: ' + marker)

for forbidden in [
    'IsoExpoSelector.HDR = true;',
    'frameCount = 2;',
    'frameCount = 3;',
]:
    if forbidden in frames:
        raise SystemExit('BASISHSM1J verifier forbidden capture marker: ' + forbidden)

print('BASISHSM1J-SHADEDGUARDCAP20EV1A verification OK')
print(' - four prospective products: OFF / ON unguarded / ON full guard / ON cap20EV')
print(' - cap formula bounds whole-frame guard reduction to <=0.20 EV')
print(' - FINALCLIPAUDIT1A remains present for high-vs-low clipping evaluation')
print(' - single RAW and HDR=false boundary present')
