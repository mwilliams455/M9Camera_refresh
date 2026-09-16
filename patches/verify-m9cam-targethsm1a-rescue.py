#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-targethsm1a-rescue.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
s = p.read_text()

def method(text, signature):
    start = text.index(signature); brace = text.index('{', start); depth = 0
    state='code'; quote=''; esc=False
    i=brace
    while i < len(text):
        ch=text[i]; nxt=text[i+1] if i+1 < len(text) else ''
        if state=='line':
            if ch=='\n': state='code'
        elif state=='block':
            if ch=='*' and nxt=='/': state='code'; i+=1
        elif state=='string':
            if esc: esc=False
            elif ch=='\\': esc=True
            elif ch==quote: state='code'
        else:
            if ch=='/' and nxt=='/': state='line'; i+=1
            elif ch=='/' and nxt=='*': state='block'; i+=1
            elif ch in ('"', "'"): state='string'; quote=ch
            elif ch=='{': depth+=1
            elif ch=='}':
                depth-=1
                if depth==0: return text[start:i+1]
        i+=1
    raise SystemExit('unterminated method')

prod = method(s, 'private static RenderCore renderNativeSourceProduction1P(')
core = method(s, 'private static RenderCore renderNativeProspectiveCore(')
checks = {
    'rescue_schema': 'm9cam.renderer.targethsm.v1a.sourceadapterrescue.production' in prod,
    'production_mode3': '                3,\n                true,\n                false, false,' in prod,
    'identity_mode0_removed': '                0,\n                true,\n                false, false,' not in prod,
    'native_source_provider_retained': 'active_physical_Xiaomi_Camera2_DNG_SOURCECAL2A_CMFIX' in prod,
    'source_adapter_cobalt_false': 'd.put("cobaltSourceAdapterApplied", false);' in prod,
    'source_cm_cobalt_false': 'd.put("cobaltSourceColorMatrixApplied", false);' in prod,
    'source_fm_cobalt_false': 'd.put("cobaltSourceForwardMatrixApplied", false);' in prod,
    'shared_target_hsm_true': 'd.put("historicalBasisHsmTargetBehaviorApplied", true);' in prod,
    'identity_hsm_false': 'd.put("identityHsmApplied", false);' in prod,
    'target_role_explicit': 'target_H25_HSM_only_not_source_CM_FM' in prod,
    'pipeline_target_after_common_scene': 'common scene space -> frozen shared H25/HSM target role' in prod,
    'historical_asset_only_nonzero_modes': 'historicalProbeCalibrationRequired = bridgeProbeMode != 0' in core,
    'native_source_builder_retained': 'buildNativeProspectiveSource(' in core,
    'm9_bridge_retained': 'ctx.ppToM9' in core,
    'sat3_retained': 'SAT3' in core,
    'bt601_retained': 'BT601' in core,
}
failed=[k for k,v in checks.items() if not v]
if failed:
    for k in failed: print('FAIL', k)
    raise SystemExit('TARGETHSM1A verification failed')
print('TARGETHSM1A VERIFY PASS')
for k in checks: print('PASS', k)
print('production_source', 'active physical Camera2 SOURCECAL2A')
print('production_target_control', 'frozen shared H25/HSM after common scene')
print('cobalt_source_CM_FM', False)
