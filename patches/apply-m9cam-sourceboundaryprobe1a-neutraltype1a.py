#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-sourceboundaryprobe1a-neutraltype1a.py <PhotonCamera-root>')
root = Path(sys.argv[1])
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
if not renderer.exists():
    raise SystemExit(f'missing renderer: {renderer}')
s = renderer.read_text()
old1 = 'private static double[] sourceBoundarySensorNeutralized1A(double[] cameraRgb, double[] neutral)'
new1 = 'private static double[] sourceBoundarySensorNeutralized1A(double[] cameraRgb, float[] neutral)'
old2 = '''double[] sensorNeutral,\n                                                     double effectiveRenderGain'''
new2 = '''float[] sensorNeutral,\n                                                     double effectiveRenderGain'''
if old1 not in s:
    raise SystemExit('neutralized helper signature anchor missing')
if old2 not in s:
    raise SystemExit('probe neutral signature anchor missing')
s = s.replace(old1, new1, 1).replace(old2, new2, 1)
renderer.write_text(s)
print('SOURCEBOUNDARYPROBE1A_NEUTRALTYPE1A applied: Camera2 nativeSource.neutral float[] accepted directly')
