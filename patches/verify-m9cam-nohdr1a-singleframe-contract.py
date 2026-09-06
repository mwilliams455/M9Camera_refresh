#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-nohdr1a-singleframe-contract.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()

iso = (root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java').read_text()
ui = (root / 'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/CameraUIController.java').read_text()
frame = (root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java').read_text()
queue = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java').read_text()
renderer = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java').read_text()

required = [
    ('FrameNumberSelector one RAW', 'if (M9Config.isCaptureTest()) { frameCount = 1; throwCount = 0; return 1; }', frame),
    ('capture-boundary HDR reset', 'if (M9Config.usesM9Pipeline()) {\n            HDR = false;\n        }', iso),
    ('UI HDR arming guard', 'IsoExpoSelector.HDR = !M9Config.usesM9Pipeline() && (Integer) value > 0;', ui),
    ('single owned frame queue', 'ImageFrame ownedFrame', queue),
    ('single frame primary render call', 'dngPath, ownedFrame, characteristics, captureResult, captureRequest, cameraRotation', queue),
]
for label, marker, text in required:
    if marker not in text:
        raise SystemExit('NOHDR1A verify failed: ' + label)

# Prospective output must remain an ordinary JPEG sidecar and must not call obvious
# Ultra-HDR/display-gainmap or multi-frame merge APIs. Diagnostic strings containing
# explicit false values are allowed.
for forbidden in [
    'HdrxProcessor',
    'UltraHDR',
    'UltraHdr',
    'GainmapEncoder',
    'setGainmap(',
    'mergeFrames(',
    'mergeRaw',
]:
    if forbidden in renderer:
        raise SystemExit('NOHDR1A renderer contains forbidden active-path marker: ' + forbidden)

print('M9 NOHDR1A SINGLEFRAME contract verified')
print(' - one RAW frame selected and handed to primary renderer')
print(' - inherited HDR/bracketing allocator forced off for M9')
print(' - no obvious Ultra HDR / merge API in M9 renderer')
