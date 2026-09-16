#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-targethsm1a-rescue.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
if not p.exists():
    raise SystemExit('TARGETHSM1A missing renderer')
s = p.read_text()

def method_span(text, signature):
    start = text.index(signature)
    brace = text.index('{', start)
    depth = 0
    state = 'code'; quote = ''; escape = False
    i = brace
    while i < len(text):
        ch = text[i]; nxt = text[i+1] if i+1 < len(text) else ''
        if state == 'line':
            if ch == '\n': state = 'code'
        elif state == 'block':
            if ch == '*' and nxt == '/': state = 'code'; i += 1
        elif state == 'string':
            if escape: escape = False
            elif ch == '\\': escape = True
            elif ch == quote: state = 'code'
        else:
            if ch == '/' and nxt == '/': state = 'line'; i += 1
            elif ch == '/' and nxt == '*': state = 'block'; i += 1
            elif ch in ('"', "'"): state = 'string'; quote = ch
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: return start, i + 1
        i += 1
    raise SystemExit('TARGETHSM1A unterminated method')

start, end = method_span(s, 'private static RenderCore renderNativeSourceProduction1P(')
prod = s[start:end]
if 'm9cam.renderer.nativefirmware.v1a.production' not in prod:
    raise SystemExit('TARGETHSM1A requires COBALTROLEPURGE1A production baseline')
mode0 = '                0,\n                true,\n                false, false,'
mode3 = '                3,\n                true,\n                false, false,'
if prod.count(mode0) != 1:
    raise SystemExit('TARGETHSM1A expected exactly one production identity-HSM mode0 call')
prod = prod.replace(mode0, mode3, 1)

# Only patch semantic/telemetry fields that live inside this method. The explanatory
# route comment sits immediately before the method signature, so it is deliberately
# not an anchor: comments must never decide whether the photographic rescue applies.
replacements = {
    'd.put("schema", "m9cam.renderer.nativefirmware.v1a.production");':
        'd.put("schema", "m9cam.renderer.targethsm.v1a.sourceadapterrescue.production");',
    'd.put("architectureRevision", "COBALTROLEPURGE1A_NATIVEFIRMWARE1A");':
        'd.put("architectureRevision", "SOURCEADAPTER_RESCUE1A_TARGETHSM1A_PERF1A");',
    'd.put("cobaltRuntimeProductionDependency", false);':
        'd.put("cobaltRuntimeProductionDependency", true);\n        d.put("cobaltRuntimeDependencyRole", "frozen_shared_target_H25_HSM_only_not_source_CM_FM");',
    'd.put("cobaltHueSatMapApplied", false);':
        'd.put("cobaltHueSatMapApplied", true);\n        d.put("cobaltHueSatMapRole", "shared_target_H25_HSM_after_native_common_scene");',
    'd.put("cobaltHistoricalLinearBasisApplied", false);':
        'd.put("cobaltHistoricalLinearBasisApplied", true);',
    'd.put("historicalBasisHsmTargetBehaviorApplied", false);':
        'd.put("historicalBasisHsmTargetBehaviorApplied", true);',
    'd.put("historicalBasisHsmRole", "disabled_removed_from_production");':
        'd.put("historicalBasisHsmRole", "frozen_shared_target_behavior_after_native_SOURCECAL2A");',
    'd.put("historicalBasisDataProvenance", "none_production");':
        'd.put("historicalBasisDataProvenance", "legacy_profile_target_role_control_pending_firmware_replacement");',
    'd.put("identityHsmApplied", true);':
        'd.put("identityHsmApplied", false);',
    'd.put("mixedCalibrationAssetUsedByProduction", false);':
        'd.put("mixedCalibrationAssetUsedByProduction", true);\n        d.put("mixedCalibrationProductionRole", "target_H25_HSM_plus_byte_identical_curve02_only_source_CM_FM_disabled");',
    'd.put("tc20DecisionSource", "native_source_identity_hsm_same_frame_tc20");':
        'd.put("tc20DecisionSource", "native_source_shared_target_H25_HSM_same_frame_tc20");',
    'd.put("bridgeProbeName", "production_source_only_identity_hsm");':
        'd.put("bridgeProbeName", "production_native_source_shared_target_H25_HSM");',
    'd.put("historicalLinearBasisDiagnosticApplied", false);':
        'd.put("historicalLinearBasisDiagnosticApplied", true);',
    'd.put("historicalLinearBasisDerivedFromCobaltSourceProfile", false);':
        'd.put("historicalLinearBasisDerivedFromCobaltSourceProfile", true);',
    'd.put("basisHsm1A", false);':
        'd.put("basisHsm1A", true);',
    'd.put("basisHsmCombinedApplied", false);':
        'd.put("basisHsmCombinedApplied", true);',
    'd.put("basisHsmOrdering", "not_in_production");':
        'd.put("basisHsmOrdering", "native_SOURCECAL2A_then_historical_linear_basis_then_H25_HSM");',
    'd.put("basisHsmHistoricalBasisBeforeHsm", false);':
        'd.put("basisHsmHistoricalBasisBeforeHsm", true);',
    'd.put("basisHsmHsmTableIdentity", "identity");':
        'd.put("basisHsmHsmTableIdentity", "historical_H25_S85_V100");',
    'd.put("mixedCalibrationAssetUsage", "none_production");':
        'd.put("mixedCalibrationAssetUsage", "target_role_only_no_source_CM_FM");',
    'd.put("fullColorRenderStages", "active physical Camera2 SOURCECAL2A -> common scene space -> identity HSM -> shared M9 bridge/SAT3/curve02/BT601/TG1");':
        'd.put("fullColorRenderStages", "active physical Camera2 SOURCECAL2A -> common scene space -> frozen shared H25/HSM target role -> M9 bridge/TC20/SAT3/curve02/BT601/TG1");',
    'd.put("pipeline", "NORM030 physical LensShadingMap -> DEMOSAICMHCNEUTRAL1A -> active physical-sensor SOURCECAL2A -> common scene space -> shared M9 bridge -> TC20 -> SAT3 M06/M07 -> firmware curve02 -> exact BT601 4:2:2 -> M9Modern TG1");':
        'd.put("pipeline", "NORM030 physical LensShadingMap -> DEMOSAICMHCNEUTRAL1A -> active physical-sensor SOURCECAL2A -> common scene space -> frozen shared H25/HSM target role -> M9 bridge -> TC20 -> SAT3 M06/M07 -> firmware curve02 -> exact BT601 4:2:2 -> M9Modern TG1");'
}
for old, new in replacements.items():
    if old not in prod:
        raise SystemExit('TARGETHSM1A telemetry anchor missing: ' + old[:80])
    prod = prod.replace(old, new, 1)

# Source calibration remains native: explicitly guard the forbidden source-role regression.
for forbidden in [
    'd.put("cobaltSourceAdapterApplied", true);',
    'd.put("cobaltSourceColorMatrixApplied", true);',
    'd.put("cobaltSourceForwardMatrixApplied", true);',
]:
    if forbidden in prod:
        raise SystemExit('TARGETHSM1A would re-enable forbidden Cobalt source role: ' + forbidden)

s = s[:start] + prod + s[end:]
p.write_text(s)
print('TARGETHSM1A applied')
print(' - active physical SOURCECAL2A remains production source transform')
print(' - frozen shared historical H25/HSM target role restored after common scene')
print(' - Cobalt CM/FM source transforms remain disabled')
