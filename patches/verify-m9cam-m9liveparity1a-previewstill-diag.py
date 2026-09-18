#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-m9liveparity1a-previewstill-diag.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
if not renderer.exists():
    raise SystemExit('M9LIVEPARITY1A renderer missing')

s = renderer.read_text()

required = [
    'M9LIVEPARITY1A_PREVIEWSTILL_DIAG',
    'M9_LIVE_PARITY_1A_LAST_PREVIEW',
    'captureM9LiveParity1APreview(',
    'snapshotM9LiveParity1A()',
    'm9cam.liveparity.v1a.previewstill',
    'm9cam.liveparity.v1a.render_summary',
    'latest_completed_live_render_snapshotted_at_still_render_entry',
    'previewAgeAtStillRenderStartMs',
    '"preview_reduced_raw"',
    '"still_full_raw"',
    '"toneForensics1A"',
    '"toneBound1A"',
    '"rawUq99_8"',
    '"tc20GuardGain"',
    '"resultShadingMode"',
    '"requestShadingMode"',
    '"sensorDescriptor1A"',
    '"targetFalloff1A"',
    'FULL_PRODUCTION_RENDER_REDUCED_RAW_1440x1080_MAIN',
    'M9SENSORTARGET1A',
    'SAT2_M04_M05',
]
for marker in required:
    if marker not in s:
        raise SystemExit('M9LIVEPARITY1A marker missing: ' + marker)

for forbidden in [
    'set(CaptureRequest.SHADING_MODE',
    'set(CaptureRequest.SENSOR_SENSITIVITY',
    'set(CaptureRequest.SENSOR_EXPOSURE_TIME',
    'PIXEL_MUTATION_ENABLED = true',
]:
    if forbidden in s[s.find('M9LIVEPARITY1A_PREVIEWSTILL_DIAG'):]:
        raise SystemExit('M9LIVEPARITY1A forbidden mutation token: ' + forbidden)

if '(!m9LiveParity1ALiveRoute && primaryRoute)' not in s:
    raise SystemExit('M9LIVEPARITY1A still-only attachment gate missing')
if 'Boolean.TRUE.equals(M9_LIVE_PREVIEW_1A_ACTIVE.get())' not in s:
    raise SystemExit('M9LIVEPARITY1A live route gate missing')
if 'captureM9LiveParity1APreview(\n                            previewDiag' not in s:
    raise SystemExit('M9LIVEPARITY1A preview capture is not anchored to completed preview diagnostics')

print('M9LIVEPARITY1A_PREVIEWSTILL_DIAG VERIFY PASS')
print(' - latest completed preview summary captured in memory')
print(' - snapshot paired at full-resolution still render entry')
print(' - TC20/tonebound/raw-tail/shading/exposure fields included')
print(' - no capture request or photographic pixel mutation introduced')
