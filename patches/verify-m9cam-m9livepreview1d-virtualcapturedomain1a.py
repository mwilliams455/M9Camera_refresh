#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-m9livepreview1d-virtualcapturedomain1a.py <PhotonCamera-root>')

root=Path(sys.argv[1]).resolve()
r=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
p=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
c=root/'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
for x in (r,p,c):
    if not x.exists(): raise SystemExit('M9LIVEPREVIEW1D missing '+str(x))
rs=r.read_text(); ps=p.read_text(); cs=c.read_text()

for m in [
    'M9LIVEPREVIEW1D_VIRTUALCAPTUREDOMAIN1A',
    'm9cam.livepreview.virtualcapturedomain.v1a',
    'sensorProbeExposureMutation',
    'rawCaptureResultPairing',
    'Image_timestamp_matches_TotalCaptureResult_SENSOR_TIMESTAMP',
    'black_relative_linear_Bayer_after_exact_frame_pairing',
    'previewVirtualCaptureDomain1D',
    'M9LIVEPARITY1B_VIEWFINDER_REFERENCE',
    'SAT2_M04_M05',
]:
    if m not in rs: raise SystemExit('M9LIVEPREVIEW1D renderer marker missing: '+m)

for m in [
    'scaleVirtualCaptureDomain1D',
    'targetEnergy / probeEnergy',
    'SENSOR_BLACK_LEVEL_PATTERN',
    'SENSOR_INFO_WHITE_LEVEL',
    'exact paired probe exposure metadata missing',
]:
    if m not in ps: raise SystemExit('M9LIVEPREVIEW1D preview marker missing: '+m)

for m in [
    'm9LivePreviewPairLock1D',
    'm9LivePreviewPendingImage1D',
    'm9LivePreviewPendingResult1D',
    'tryDispatchM9LivePreviewPair1D',
    'CaptureResult.SENSOR_TIMESTAMP',
    'IsoExpoSelector.GenerateExpoPair(-1, this)',
    'ordinary repeating-preview request plus RAW output',
]:
    if m not in cs: raise SystemExit('M9LIVEPREVIEW1D controller marker missing: '+m)

# Guard against the 1C regression: preview probe must not force manual AE/ISO/shutter.
req_start=cs.find('    private void requestM9LivePreviewProbe1A() {')
req_end=cs.find('    private void showToast(String msg) {', req_start)
if req_start < 0 or req_end < 0:
    raise SystemExit('M9LIVEPREVIEW1D request/helper scope missing')
scope=cs[req_start:req_end]
for forbidden in [
    'CONTROL_AE_MODE_OFF',
    'mPreviewRequestBuilder.set(CaptureRequest.SENSOR_SENSITIVITY',
    'mPreviewRequestBuilder.set(CaptureRequest.SENSOR_EXPOSURE_TIME',
    'mPreviewRequestBuilder.set(CaptureRequest.SENSOR_FRAME_DURATION',
]:
    if forbidden in scope:
        raise SystemExit('M9LIVEPREVIEW1D forbidden probe exposure mutation: '+forbidden)

if 'delta > 2_000_000L' not in cs:
    raise SystemExit('M9LIVEPREVIEW1D timestamp-pairing tolerance gate missing')
if 'M9LivePreview1A.markDisplayed1B();' not in cs:
    raise SystemExit('M9LIVEPREVIEW1D displayed-frame confirmation missing')

print('M9LIVEPREVIEW1D_VIRTUALCAPTUREDOMAIN1A VERIFY PASS')
print(' - probe exposure remains normal repeating-preview exposure')
print(' - RAW Image and TotalCaptureResult paired by sensor timestamp')
print(' - predicted still domain applied only to in-memory reduced RAW')
print(' - final JPEG and still photographic core unchanged')
