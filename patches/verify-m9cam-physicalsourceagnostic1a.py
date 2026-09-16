#!/usr/bin/env python3
from pathlib import Path
import re, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-physicalsourceagnostic1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
s = p.read_text()
checks = {
    'origin_resolver_present': 'resolveSourceRawOrigin1A(' in s,
    'origin_pixel_array': 'raw_dimensions_match_full_pixel_array' in s,
    'origin_precorrection_array': 'raw_dimensions_match_pre_correction_active_array' in s,
    'origin_active_array': 'raw_dimensions_match_active_array' in s,
    'ambiguous_origin_fails_closed': 'cannot prove RAW sensor origin' in s,
    'old_origin0_assumption_removed': 'Current Xiaomi 15 Ultra full-frame RAW validation is origin0' not in s,
    'nativeab_camera2_gate_removed': '"2".equals(requestedPhysicalId)' not in s,
    'nativeab_main2_error_removed': 'main camera 2' not in s and 'main physical 2' not in s,
    'no_literal_characteristics_lookup': re.search(r'getCameraCharacteristics\(\s*"[0-9]+"\s*\)', s) is None,
    'semantic_id_false': 'sourceCameraIdUsedAsSemanticRole", false' in s,
    'array_topology_false': 'sourceCameraArrayTopologyUsedForRendering", false' in s,
    'focal_role_false': 'sourceFocalLengthUsedForRendering", false' in s,
    'target_adapter_retained': 'targetInputAdapter1AProduction", true' in s,
    'active_sensor_preserved': 'targetInputAdapterActiveSensorPreserved", true' in s,
    'setuptrace_retained': 'm9cam.setuptrace.v1a.readonly' in s,
}
failed = [k for k,v in checks.items() if not v]
for k,v in checks.items(): print(('PASS' if v else 'FAIL'), k)
if failed:
    raise SystemExit('PHYSICALSOURCEAGNOSTIC1A verification failed: ' + ', '.join(failed))
print('PHYSICALSOURCEAGNOSTIC1A VERIFY PASS')
print('source_unit', 'physical_RAW_camera_metadata_capabilities')
print('camera_array_topology_dependency', False)
print('camera_role_dependency', False)
