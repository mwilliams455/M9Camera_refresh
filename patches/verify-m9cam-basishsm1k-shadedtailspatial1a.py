#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-basishsm1k-shadedtailspatial1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
for p in (renderer_path, gradle_path, frames_path):
    if not p.exists():
        raise SystemExit('BASISHSM1K verifier missing: ' + str(p))

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()
frames = frames_path.read_text()

required_renderer = [
    'm9cam.renderer.basishsm.shadedtailspatial.finalclipaudit.v1a.main',
    'm9cam.renderer.shadedtailspatial.v1a',
    'private static JSONObject shadedTailSpatialAudit1A(',
    'private static JSONObject shadedTailSpatialAudit1ASkipped(',
    'shadedTailSpatial1AEnabled", true',
    'shadedTailSpatial1AExecuted',
    'd.put("shadedTailSpatial1A", shadedTailSpatial1AJson);',
    'sameRawSharedAcrossShadingOnVariants", true',
    'executedOnlyOnRole", "shading_on_unguarded_control"',
    'photographicDecisionMutation", false',
    'tailSupportThresholdLinear',
    'tailSupportFractionOfTotal',
    'tailSupportExcessEnergyFractionOfTotal',
    'correctedLinearAboveOneFractionOfOriginalUnclipped',
    'tailSupportMax3x3CellShare',
    'tailSupport3x3Herfindahl',
    'aboveOneMax3x3CellShare',
    'aboveOne3x3Herfindahl',
    'display3x3',
    'tailSupportBoundingBoxDisplay',
    'center_50_percent_width_height_display_orientation',
    'outside_center_50_percent_width_height_display_orientation',
    'clockwise_cameraRotation_0_90_180_270',
    'applyNativeShading',
    '&& !applyShadedGuard1A',
    '&& !applyShadedGuardCap20Ev1A',
    'private static JSONObject finalClipAudit1A(',
    'finalClipAudit1AEnabled", true',
    'shadedGuardCap20Ev1AEnabled", true',
    'shadedGuardCap20Ev1ABound',
    'Math.pow(2.0, -shadedGuardCap20Ev1AMaxReductionEv)',
    'Math.max(shadedGuard1AMeterGain, shadedGuardCap20Ev1AFloorGain)',
    'Math.min(meter.baseGain, shadedGuard1ACorrectedGuardGain)',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARD1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARDCAP20EV1A"',
    'boolean[] applyShadedGuard1AFlags = {false, false, true, false};',
    'boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false, true};',
]
for marker in required_renderer:
    if marker not in renderer:
        raise SystemExit('BASISHSM1K verifier missing renderer marker: ' + marker)

if renderer.count('private static JSONObject shadedTailSpatialAudit1A(') != 1:
    raise SystemExit('BASISHSM1K verifier spatial helper count mismatch')
if renderer.count('final double shadedGuardCap20Ev1AMaxReductionEv = 0.20;') != 1:
    raise SystemExit('BASISHSM1K verifier cap20 value/count mismatch')
if renderer.count('d.put("shadedTailSpatial1A", shadedTailSpatial1AJson);') != 1:
    raise SystemExit('BASISHSM1K verifier spatial diagnostic seam count mismatch')

if '-basishsm1k-shadedtailspatial1a' not in gradle:
    raise SystemExit('BASISHSM1K verifier build provenance missing')
if '-basishsm1j-shadedguardcap20ev1a' in gradle:
    raise SystemExit('BASISHSM1K verifier stale 1J build provenance')

for marker in [
    'M9_NOHDR1A_SINGLE_FRAME_BOUNDARY',
    'frameCount = 1;',
    'throwCount = 0;',
    'IsoExpoSelector.HDR = false;',
]:
    if marker not in frames:
        raise SystemExit('BASISHSM1K verifier NOHDR boundary missing: ' + marker)

for forbidden in [
    'IsoExpoSelector.HDR = true;',
    'frameCount = 2;',
    'frameCount = 3;',
]:
    if forbidden in frames:
        raise SystemExit('BASISHSM1K verifier forbidden capture marker: ' + forbidden)

print('BASISHSM1K-SHADEDTAILSPATIAL1A verification OK')
print(' - 1J four-way photomath controls retained')
print(' - read-only pre-render corrected-tail spatial audit added')
print(' - spatial audit executes only on shading-ON unguarded same-RAW control')
print(' - center50/edge plus display-oriented 3x3 concentration diagnostics present')
print(' - full SHADEDGUARD1A and cap20EV formulas remain intact')
print(' - FINALCLIPAUDIT1A retained for downstream correlation')
print(' - single RAW and HDR=false boundary present')
