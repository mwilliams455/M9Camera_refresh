#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-m9livepreview1e-fullresoracle1a.py <PhotonCamera-root>')

root=Path(sys.argv[1]).resolve()
p=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
r=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
for x in (p,r):
    if not x.exists(): raise SystemExit('M9LIVEPREVIEW1E missing '+str(x))
ps=p.read_text(); rs=r.read_text()

for m in [
    'M9LIVEPREVIEW1E_FULLRESORACLE1A',
    'copyFullResolutionBayerVirtualDomain1E',
    'final int dstW = srcW;',
    'final int dstH = srcH;',
    'Bitmap.createScaledBitmap',
    'FULL_RES_M9_THEN_DISPLAY_DOWNSCALE',
    'scaleVirtualCaptureDomain1D',
]:
    if m not in ps: raise SystemExit('M9LIVEPREVIEW1E preview marker missing: '+m)

for m in [
    'm9cam.livepreview.fullresoracle.v1a',
    'M9LIVEPREVIEW1E_FULLRESORACLE1A',
    'ORIGINAL_FULL_RESOLUTION_RAW',
    'spatialReductionBeforeM9Renderer',
    'displayReductionAfterM9Renderer',
    'previewFullResOracle1E',
]:
    if m not in rs: raise SystemExit('M9LIVEPREVIEW1E renderer marker missing: '+m)

# Critical oracle property: the ordinary parity reducer must not be used for the live render.
render_start=ps.find('public static Bitmap render(Image raw,')
render_end=ps.find('private static ByteBuffer copyFullResolutionBayerVirtualDomain1E', render_start)
if render_start < 0 or render_end < 0:
    raise SystemExit('M9LIVEPREVIEW1E render scope missing')
scope=ps[render_start:render_end]
if 'reduceBayerParityPreserving(raw' in scope:
    raise SystemExit('M9LIVEPREVIEW1E still reduces Bayer before renderer')
if 'copyFullResolutionBayerVirtualDomain1E(' not in scope:
    raise SystemExit('M9LIVEPREVIEW1E full-resolution copy not used by render')

print('M9LIVEPREVIEW1E_FULLRESORACLE1A VERIFY PASS')
print(' - original RAW dimensions feed the M9 renderer')
print(' - no spatial Bayer reduction occurs before M9 source/tone decisions')
print(' - only the final M9 Bitmap is reduced for display')
print(' - 1D exact-frame pairing and virtual exposure mapping retained')
