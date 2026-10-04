#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-targethsm1a-rescue.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
s = p.read_text()

def method(text, signature):
    start=text.index(signature); brace=text.index('{',start); depth=0
    state='code'; quote=''; esc=False; i=brace
    while i<len(text):
        ch=text[i]; nxt=text[i+1] if i+1<len(text) else ''
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
            elif ch in ('"',"'"): state='string'; quote=ch
            elif ch=='{': depth+=1
            elif ch=='}':
                depth-=1
                if depth==0: return text[start:i+1]
        i+=1
    raise SystemExit('unterminated method')

prod=method(s,'private static RenderCore renderNativeSourceProduction1P(')
core=method(s,'private static RenderCore renderNativeProspectiveCore(')
adapter=method(s,'private static TargetInputAdapter1A buildTargetInputAdapter1A(')
checks={
 'schema':'m9cam.renderer.targetinputadapter.v1a.xiaomi17u.production' in prod,
 'production_mode4':'                4,\n                true,\n                false, false,' in prod,
 'mode3_not_production':'                3,\n                true,\n                false, false,' not in prod,
 'native_source_provider':'active_physical_Xiaomi_Camera2_DNG_SOURCECAL2A_CMFIX' in prod,
 'active_sensor_preserved':'targetInputAdapterActiveSensorPreserved", true' in prod,
 'physical_id_independent':'targetInputAdapterPhysicalCameraIdIndependent", true' in prod,
 'cobalt_source_false':'d.put("cobaltSourceAdapterApplied", false);' in prod,
 'cobalt_cm_false':'d.put("cobaltSourceColorMatrixApplied", false);' in prod,
 'cobalt_fm_false':'d.put("cobaltSourceForwardMatrixApplied", false);' in prod,
 'formula':'T_scene=C15_historical_scene*inverse(N15_native_scene); output=T_scene*N_active' in prod,
 'mode4_core':'bridgeProbeMode == 4' in core,
 'native_then_basis':'ctx.camToPp = matMul3(bridgeProbeBasis, nativeCamToPpBeforeProbe);' in core,
 'historical_hsm_reference_weight':'targetInput.historical15.wA * cal.hsmA[i]' in core,
 'reference_scene_xy':'activeSource.sceneX' in adapter and 'activeSource.sceneY' in adapter,
 'reference_15_native':'reference15NativeCamToPp' in adapter,
 'delta_formula':'historical15.camToPp,\n                inverse3(reference15NativeCamToPp)' in adapter,
 'no_physical_camera_id_in_adapter':'requestedPhysicalCameraId' not in adapter and 'cameraID' not in adapter,
 'm9_bridge_retained':'ctx.ppToM9' in core,
 'sat3_retained':'SAT3' in core,
 'bt601_retained':'BT601' in core,
}
# SETUPTRACE1A is applied after the first verifier call, so only require it when present.
if 'SETUPTRACE1A' in s or 'setupTrace1A' in s:
    checks['setuptrace_survives']='setupParametersElapsedMs' in s
failed=[k for k,v in checks.items() if not v]
for k,v in checks.items(): print(('PASS' if v else 'FAIL'),k)
if failed: raise SystemExit('TARGETINPUTADAPTER1A verification failed: '+','.join(failed))
print('TARGETINPUTADAPTER1A VERIFY PASS')
print('production_source','active physical Camera2 SOURCECAL2A')
print('target_adapter','T(scene)=C15_historical(scene)*inverse(N15_native(scene))')
print('active_sensor_cancelled',False)
