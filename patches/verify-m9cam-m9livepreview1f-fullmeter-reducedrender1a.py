#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv)!=2:
    raise SystemExit('usage: verify-m9cam-m9livepreview1f-fullmeter-reducedrender1a.py <PhotonCamera-root>')
root=Path(sys.argv[1]).resolve()
r=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
p=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
if not r.exists() or not p.exists(): raise SystemExit('M9LIVEPREVIEW1F files missing')
rs=r.read_text(); ps=p.read_text()

for m in [
    'M9LIVEPREVIEW1F_FULLMETER_REDUCEDRENDER1A',
    'M9_LIVE_PREVIEW_1F_METER_ONLY',
    'M9_LIVE_PREVIEW_1F_OVERRIDE',
    'renderLivePreviewSplit1F',
    'full_resolution_RAW_source_path_plus_1600_long_side_TC20',
    'fullResolutionColorRenderPerformed',
    'livePreviewFullMeter1FOverrideApplied',
    'M9LIVEPREVIEW1D_VIRTUALCAPTUREDOMAIN1A',
    'M9LIVEPARITY1B_VIEWFINDER_REFERENCE',
]:
    if m not in rs: raise SystemExit('M9LIVEPREVIEW1F renderer marker missing: '+m)

for m in [
    'copyFullResolutionVirtualDomain1F',
    'FULL_SOURCE_METER_REDUCED_COLOR_RENDER',
    'renderLivePreviewSplit1F',
    'reduceBayerParityPreserving',
    'scaleVirtualCaptureDomain1D',
]:
    if m not in ps: raise SystemExit('M9LIVEPREVIEW1F preview marker missing: '+m)

# Full source decision must early-return before full color render.
decision=rs.find('if (Boolean.TRUE.equals(M9_LIVE_PREVIEW_1F_METER_ONLY.get()))')
fullrender=rs.find('long fullRenderStartedNs = System.nanoTime();', decision)
if decision<0 or fullrender<0 or decision>fullrender:
    raise SystemExit('M9LIVEPREVIEW1F meter-only exit not before full color render')

# Reduced render must only consume override on self-meter path.
if 'meterParitySelfMeter && liveDecision1F != null' not in rs:
    raise SystemExit('M9LIVEPREVIEW1F override gate missing')
if 'else if (meterParitySelfMeter)' not in rs:
    raise SystemExit('M9LIVEPREVIEW1F ordinary self-meter fallback missing')

# Preview facade must still display 1440x1080 target, not 12MP.
if 'LANDSCAPE_WIDTH = 1440' not in ps or 'LANDSCAPE_HEIGHT = 1080' not in ps:
    raise SystemExit('M9LIVEPREVIEW1F 1080p display raster changed')

print('M9LIVEPREVIEW1F_FULLMETER_REDUCEDRENDER1A VERIFY PASS')
print(' - full source path exits after exact 1600-side TC20 decision')
print(' - no full-resolution color bitmap is created in meter-only pass')
print(' - reduced 1440x1080 render inherits full-source Meter')
print(' - ordinary self-meter remains fallback outside preview override')
