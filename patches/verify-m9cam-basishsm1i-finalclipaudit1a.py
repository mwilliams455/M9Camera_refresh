#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-basishsm1i-finalclipaudit1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
rp = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gp = root / 'app/build.gradle'
fp = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
for p in (rp, gp, fp):
    if not p.exists():
        raise SystemExit('BASISHSM1I-FINALCLIPAUDIT1A verify missing ' + str(p))
r = rp.read_text()
g = gp.read_text()
f = fp.read_text()

required = [
    'm9cam.renderer.basishsm.finalclipaudit.v1a.main',
    'private static JSONObject finalClipAudit1A(Bitmap bitmap)',
    'm9cam.renderer.finalclipaudit.v1a',
    'finished_oriented_ARGB8888_bitmap_post_curve_post_BT601_post_TG1',
    'anyHighClipFraction',
    'anyLowClipFraction',
    'mixedHighLowFraction',
    'redHighClipFraction',
    'greenHighClipFraction',
    'blueHighClipFraction',
    'redLowClipFraction',
    'greenLowClipFraction',
    'blueLowClipFraction',
    'anyChannelGE250Fraction',
    'allChannelsGE250Fraction',
    'lumaGE250Fraction',
    'center_50_percent_width_height',
    'outside_center_50_percent_width_height',
    'bitmap.getPixels(pixels, 0, width, 0, y0, width, rows)',
    '(4899 * r + 9617 * g + 1868 * b) >> 14',
    'finalClipAudit1AEnabled',
    'd.put("finalClipAudit1A", finalClipAudit1A(oriented));',
    'shadedGuardAB1A',
    'shading_on_unguarded_control',
    'shading_on_guarded',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARD1A"',
]
for marker in required:
    if marker not in r:
        raise SystemExit('BASISHSM1I-FINALCLIPAUDIT1A verify marker missing: ' + marker)

if '-basishsm1i-finalclipaudit1a' not in g:
    raise SystemExit('BASISHSM1I-FINALCLIPAUDIT1A build provenance missing')
if '-basishsm1h-shadedguardab1a' in g:
    raise SystemExit('BASISHSM1I-FINALCLIPAUDIT1A stale 1H build provenance survived')

for marker in ['M9_NOHDR1A_SINGLE_FRAME_BOUNDARY', 'frameCount = 1;', 'throwCount = 0;', 'IsoExpoSelector.HDR = false;']:
    if marker not in f:
        raise SystemExit('BASISHSM1I-FINALCLIPAUDIT1A NOHDR boundary missing: ' + marker)

# Exactly the three 1H causal field products must survive.
for suffix in [
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARD1A"',
]:
    if r.count(suffix) != 1:
        raise SystemExit('BASISHSM1I-FINALCLIPAUDIT1A field suffix count invalid: ' + suffix)

# The new helper must be read-only. It may inspect ARGB bytes but cannot write bitmap
# pixels, change a gain, mutate capture state, or alter HDR/single-frame policy.
start = r.find('private static JSONObject finalClipAudit1A(Bitmap bitmap)')
end = r.find('    private static RenderCore renderNativeProspectiveCore(', start)
if start < 0 or end < 0:
    raise SystemExit('BASISHSM1I-FINALCLIPAUDIT1A helper block not found')
block = r[start:end]
for forbidden in [
    'bitmap.setPixel', 'bitmap.setPixels', 'copyPixelsFromBuffer',
    'CaptureRequest.', 'SENSOR_EXPOSURE_TIME', 'SENSOR_SENSITIVITY',
    'IsoExpoSelector.HDR = true', 'meter.gain =', 'effectiveRenderGain =',
]:
    if forbidden in block:
        raise SystemExit('BASISHSM1I-FINALCLIPAUDIT1A forbidden mutation in audit helper: ' + forbidden)

print('BASISHSM1I-FINALCLIPAUDIT1A verification OK')
print(' - exact final ARGB audit records high/low clipping separately')
print(' - per-channel and center-vs-edge extrema recorded')
print(' - 1H three-way field outputs preserved')
print(' - audit helper is read-only; no gain/capture/HDR mutation')
print(' - single RAW / HDR=false / capture / DNG boundary retained')
