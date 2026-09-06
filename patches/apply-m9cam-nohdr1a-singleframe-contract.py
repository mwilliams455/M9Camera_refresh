#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-nohdr1a-singleframe-contract.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit('NOHDR1A: not a PhotonCamera root')

iso_rel = 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
ui_rel = 'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/CameraUIController.java'
frame_rel = 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit('NOHDR1A missing expected file: ' + rel)
    return p.read_text()

def write(rel, text):
    (root / rel).write_text(text)

iso = read(iso_rel)
if 'import com.particlesdevs.photoncamera.m9.M9Config;' not in iso:
    raise SystemExit('NOHDR1A requires M9Config import in IsoExpoSelector from recovery foundation')

sig = '''    public static ExpoPair GenerateExpoPair(int step, CaptureController captureController) {
'''
insert = sig + '''        // M9 NOHDR1A: capture-boundary contract. M9 is one Bayer RAW photograph,
        // never a bracket/HDR exposure allocator. Reset the inherited static flag on every
        // exposure request so a persisted/UI bracketing preference cannot perturb step 0.
        if (M9Config.usesM9Pipeline()) {
            HDR = false;
        }
'''
if 'M9 NOHDR1A: capture-boundary contract' not in iso:
    if iso.count(sig) != 1:
        raise SystemExit('NOHDR1A GenerateExpoPair signature missing/non-unique')
    iso = iso.replace(sig, insert, 1)
write(iso_rel, iso)

ui = read(ui_rel)
import_anchor = 'import com.particlesdevs.photoncamera.processing.parameters.IsoExpoSelector;\n'
if 'import com.particlesdevs.photoncamera.m9.M9Config;' not in ui:
    if import_anchor not in ui:
        raise SystemExit('NOHDR1A CameraUIController import anchor missing')
    ui = ui.replace(import_anchor,
                    import_anchor + 'import com.particlesdevs.photoncamera.m9.M9Config;\n', 1)
old = '                        IsoExpoSelector.HDR = (Integer) value > 0;\n'
new = '''                        // M9 NOHDR1A: bracketing preference may remain visible/stored, but it
                        // cannot arm Photon's HDR exposure allocator while the M9 route is active.
                        IsoExpoSelector.HDR = !M9Config.usesM9Pipeline() && (Integer) value > 0;
'''
if new not in ui:
    if ui.count(old) != 1:
        raise SystemExit('NOHDR1A BRACKETING UI anchor missing/non-unique')
    ui = ui.replace(old, new, 1)
write(ui_rel, ui)

frame = read(frame_rel)
if 'if (M9Config.isCaptureTest()) { frameCount = 1; throwCount = 0; return 1; }' not in frame:
    raise SystemExit('NOHDR1A one-frame FrameNumberSelector invariant missing')

iso = read(iso_rel)
ui = read(ui_rel)
if 'if (M9Config.usesM9Pipeline()) {\n            HDR = false;\n        }' not in iso:
    raise SystemExit('NOHDR1A capture-boundary HDR reset missing')
if 'IsoExpoSelector.HDR = !M9Config.usesM9Pipeline() && (Integer) value > 0;' not in ui:
    raise SystemExit('NOHDR1A UI arming guard missing')

print('M9 NOHDR1A SINGLEFRAME contract applied')
print(' - M9 FrameNumberSelector remains exactly one RAW frame')
print(' - inherited HDR/bracketing exposure flag is forced false at GenerateExpoPair')
print(' - BRACKETING UI cannot re-arm IsoExpoSelector.HDR in M9 route')
print(' - no multi-frame merge, HDR tone mapper or Ultra HDR output path added')
