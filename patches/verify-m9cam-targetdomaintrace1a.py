#!/usr/bin/env python3
from pathlib import Path
import sys, re
if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-targetdomaintrace1a.py <PhotonCamera-root>')
root=Path(sys.argv[1]).resolve()
rp=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
cp=root/'app/src/main/cpp/m9color_jni.cpp'
if not rp.exists() or not cp.exists():
    raise SystemExit('TARGETDOMAINTRACE1A assembled sources missing')
s=rp.read_text(); c=cp.read_text()
checks={
 'trace_schema': 'm9cam.targetdomaintrace.v1a.readonly' in s,
 'trace_attached': 'd.put("targetDomainTrace1A", targetDomainTrace1AJson);' in s,
 'read_only_marker': 'targetDomainTrace1APixelMutation", false' in s,
 'no_cobalt_hsm_dependency': 'targetDomainTrace1ACobaltHsmDependency", false' in s,
 'source_xyz_stage': 'B_sourceXyzD50' in s,
 'target_preclamp_stage': 'C_currentTargetInputRgbPreClamp' in s,
 'm9_prewhite_stage': 'D_m9BridgeRgbBeforeWhiteNormalization' in s,
 'm9_postwhite_stage': 'E_m9BridgeRgbAfterWhiteNormalization' in s,
 'sat2_input_stage': 'F_sat2Input14' in s,
 'm04_m05_branch': 'M04_r_ge_g' in s and 'M05_r_lt_g' in s,
 'signed_accumulator': 'H_signedSat2Accumulator' in s,
 'shift_before_clamp': 'I_postShift16BeforeClamp' in s,
 'curve_indices': 'J_curve02Indices' in s,
 'curve_output': 'K_curve02Rgb8' in s,
 'bt601_pair_output': 'L_exactBt601PairOutput' in s,
 'semantic_roles': all(x in s for x in ['blue_sky','white_grey_building','bright_grass','shaded_grass','foliage','asphalt']),
 'tonebound_retained': 'm9cam.tonebound.v1a.050ev' in s,
 'sat2_selector_retained': 'SATURATION_BANK == 2 ? 9' in s,
 'identity_hsm_retained': 'identity_90x30' in s,
}
expected=[13659,-4457,-1004,-2244,13469,-3033,-199,-6014,14398,
          14811,-5604,-1004,-2455,13688,-3033,393,-6588,14398]
for x in expected:
    if str(x) not in s and str(x) not in c:
        checks['sat2_coefficients_present']=False
        break
else:
    checks['sat2_coefficients_present']=True
start=s.find('    // TARGETDOMAINTRACE1A: read-only target-domain forensics.')
end=s.find('    // BASISHSM1I-FINALCLIPAUDIT1A', start)
helper=s[start:end] if start>=0 and end>start else ''
forbidden=['ctx.camToPp =','ctx.hsm =','cam16.put(','cam16.convertTo(','setPixels(','renderBlockParallel','meter.gain =','effectiveRenderGain =']
checks['helper_region_found']=bool(helper)
checks['helper_has_no_state_mutation_anchors']=bool(helper) and not any(x in helper for x in forbidden)
checks['bt601_exact_coefficients']=all(x in helper for x in ['4899*r0','9617*g0','1868*b0','-2765*rs','5427*gs','8192*bs','6860*gs','1332*bs'])
pos_gain=s.find('final double effectiveRenderGain = toneBoundUnboundedEffectiveGain1A * toneBoundScale1A;')
pos_trace=s.find('final JSONObject targetDomainTrace1AJson = targetDomainTrace1A(', pos_gain)
checks['trace_after_bounded_gain']=pos_gain>=0 and pos_trace>pos_gain
failed=[k for k,v in checks.items() if not v]
for k,v in checks.items(): print(k, 'PASS' if v else 'FAIL')
if failed: raise SystemExit('TARGETDOMAINTRACE1A VERIFY FAIL: '+', '.join(failed))
print('TARGETDOMAINTRACE1A VERIFY PASS')
