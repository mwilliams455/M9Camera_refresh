#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-deviceport-perf1a-hotpath.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9DevicePortAudit1A.java'
if not p.exists():
    raise SystemExit('DEVICEPORT-PERF1A missing assembled audit helper')
s = p.read_text()
old = '            out.put("rearRawCameraInventory", enumerateRearRawCameras());\n'
new = '''            // DEVICEPORT-PERF1A: never enumerate every logical/physical camera from the\n            // capture hot path. On Xiaomi this CameraManager traversal (including stream\n            // configuration queries) can stall setupParameters for tens of seconds. The\n            // active PhysicalRawDescriptor already contains the per-capture evidence needed\n            // by SOURCECAL/source-boundary diagnostics. Full inventory is a one-shot/offline job.\n            out.put("rearRawCameraInventory", JSONObject.NULL);\n            out.put("rearRawCameraInventoryPolicy",\n                    "disabled_on_capture_hot_path_use_explicit_one_shot_inventory_if_needed");\n            out.put("captureHotPathCameraManagerEnumeration", false);\n'''
if old not in s:
    raise SystemExit('DEVICEPORT-PERF1A hot-path inventory anchor missing')
s = s.replace(old, new, 1)
p.write_text(s)
print('DEVICEPORT-PERF1A applied')
print(' - per-shot CameraManager rear/physical inventory traversal disabled')
print(' - active physical RAW descriptor and all photographic pixels unchanged')
