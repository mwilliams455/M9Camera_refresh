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

# Compile closure: Camera2 nativeSource.neutral is float[].
old1 = 'private static double[] sourceBoundarySensorNeutralized1A(double[] cameraRgb, double[] neutral)'
new1 = 'private static double[] sourceBoundarySensorNeutralized1A(double[] cameraRgb, float[] neutral)'
old2 = '''double[] sensorNeutral,\n                                                     double effectiveRenderGain'''
new2 = '''float[] sensorNeutral,\n                                                     double effectiveRenderGain'''
if old1 not in s:
    raise SystemExit('neutralized helper signature anchor missing')
if old2 not in s:
    raise SystemExit('probe neutral signature anchor missing')
s = s.replace(old1, new1, 1).replace(old2, new2, 1)

# SENSORGENERIC1A: the source boundary is selected by physical RAW characteristics,
# never by a zoom/lens label such as main, ultrawide, 3x or 4.1x. Camera ID and
# focal length remain provenance/diagnostic fields only.
old_purpose = 'locate_green_magenta_contamination_relative_to_SOURCECAL2A_common_scene_boundary'
new_purpose = 'locate_physical_sensor_domain_divergence_relative_to_SOURCECAL2A_common_scene_boundary'
if old_purpose not in s:
    raise SystemExit('generic probe purpose anchor missing')
s = s.replace(old_purpose, new_purpose, 1)

old_decision = 'first_stage_with_material_3x_vs_main_jump_in_adjacentPairChromaVectorDelta_or_greenMagenta_axis_is_first_suspect_boundary'
new_decision = 'for_any_physical_sensor_pair_first_stage_with_material_between_sensor_jump_in_neutralAxisDistance_adjacentPairChromaVectorDelta_or_greenMagenta_axis_is_first_suspect_boundary'
if old_decision not in s:
    raise SystemExit('3x-specific decision-rule anchor missing')
s = s.replace(old_decision, new_decision, 1)

policy_anchor = '        out.put("targetRendererMutation", false);\n'
policy_insert = '''        out.put("targetRendererMutation", false);\n        out.put("physicalSensorGeneric", true);\n        out.put("sourceAdapterSelectionPolicy",\n                "physical_RAW_characteristics_and_measured_sensor_parameters_not_zoom_or_lens_label");\n        out.put("cameraIdUsedForBehavior", false);\n        out.put("focalLengthUsedForBehavior", false);\n        out.put("zoomLabelUsedForBehavior", false);\n        out.put("geometryDerivedFromActiveInput", true);\n        out.put("intendedSensorScope", "any_supported_physical_Bayer_sensor");\n'''
if policy_anchor not in s:
    raise SystemExit('generic source policy insertion anchor missing')
s = s.replace(policy_anchor, policy_insert, 1)

renderer.write_text(s)
print('SOURCEBOUNDARYPROBE1A_NEUTRALTYPE1A applied: float[] neutral + physical-sensor-generic contract')