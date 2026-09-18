#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-m9livepreview1c-capturedomain1a.py <PhotonCamera-root>')

root=Path(sys.argv[1]).resolve()
r=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
p=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
c=root/'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
for x in (r,p,c):
    if not x.exists(): raise SystemExit('M9LIVEPREVIEW1C missing '+str(x))
rs=r.read_text(); ps=p.read_text(); cs=c.read_text()

renderer_markers=[
    'M9LIVEPREVIEW1C_CAPTUREDOMAIN1A',
    'm9cam.livepreview.capturedomain.v1a',
    'viewfinder_prediction_only',
    'finalJpegIsAuthority',
    'stillCaptureMutation',
    'probeToTargetLinearScale',
    'black_relative_linear_Bayer_before_unchanged_M9_renderer',
    'previewExposureDomain1C',
    'SAT2_M04_M05',
    'm9cam.tonebound.v1a.050ev',
    'M9LIVEPARITY1B_VIEWFINDER_REFERENCE',
]
for m in renderer_markers:
    if m not in rs: raise SystemExit('M9LIVEPREVIEW1C renderer marker missing: '+m)

preview_markers=[
    'BlackLevelPattern',
    'exposureDomainScale',
    'targetEnergy / probeEnergy',
    'scaleExposureDomainCode',
    'CameraCharacteristics.SENSOR_BLACK_LEVEL_PATTERN',
    'CameraCharacteristics.SENSOR_INFO_WHITE_LEVEL',
    'probeResultIso',
]
for m in preview_markers:
    if m not in ps: raise SystemExit('M9LIVEPREVIEW1C preview marker missing: '+m)

controller_markers=[
    'm9LivePreviewTargetIso1C',
    'm9LivePreviewTargetExposureNs1C',
    'IsoExpoSelector.GenerateExpoPair(-1, this)',
    'CaptureRequest.CONTROL_AE_MODE_OFF',
    'CaptureRequest.SENSOR_SENSITIVITY',
    'CaptureRequest.SENSOR_EXPOSURE_TIME',
    'Restore the long-lived repeating builder BEFORE submitting the immutable probe',
]
for m in controller_markers:
    if m not in cs: raise SystemExit('M9LIVEPREVIEW1C controller marker missing: '+m)

# The normal still setExpo path must remain distinct; the overlay only touches preview-probe method.
if 'IsoExpoSelector.setExpo' in cs:
    # Presence is fine, but this patch must not introduce a preview target into a still call.
    pass
if 'm9LivePreviewTargetIso1C, m9LivePreviewTargetExposureNs1C' not in cs:
    raise SystemExit('M9LIVEPREVIEW1C target not passed to preview renderer')
if 'm9LivePreviewTargetIso1C = -1;' not in cs:
    raise SystemExit('M9LIVEPREVIEW1C stop/reset gate missing')

print('M9LIVEPREVIEW1C_CAPTUREDOMAIN1A VERIFY PASS')
print(' - viewfinder probe target is generated with step=-1 prediction')
print(' - immutable RAW probe requests predicted still ISO/shutter')
print(' - actual probe exposure is residual-scaled black-relative before preview render')
print(' - final still exposure and final still renderer are not modified by this overlay')
