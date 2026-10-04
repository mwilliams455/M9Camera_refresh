#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: fix-m9cam-sourcecal1b-embeddedcalibrationroles1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9SourceCalibrationAudit1A.java'
if not p.exists():
    raise SystemExit('SOURCECAL1B requires generated SOURCECAL1A audit helper')
text = p.read_text()

anchor = '''            out.put("nativeTransformAppliedToRender", false);
            out.put("cobaltRuntimeDependencyChanged", false);
            out.put("phase", "A_native_metadata_and_transform_audit");
'''
insert = '''            out.put("nativeTransformAppliedToRender", false);
            out.put("cobaltRuntimeDependencyChanged", false);
            out.put("phase", "A_native_metadata_and_transform_audit_plus_embedded_calibration_role_split");

            // SOURCECAL1B: make the current mixed calibration asset explicit. The loader itself
            // documents that ColorMatrix/ForwardMatrix/HSM originate in the Xiaomi 15 Ultra
            // Rear Wide Cobalt Modular DCP while curve02 originates in Leica M9 firmware.
            // This audit does not change either component; it only records their separate roles
            // so the Cobalt source adapter can later be replaced without discarding M9 firmware.
            M9R35Calibration embeddedCal = M9R35Calibration.get();
            JSONObject embedded = new JSONObject();
            embedded.put("schema", "m9cam.sourcecal.v1b.embeddedcalibrationroles1a");
            embedded.put("asset", "m9/m9_r35_calibration.bin");
            embedded.put("magic", "M9R35CAL");
            embedded.put("sourceAdapterProvider", "Cobalt_Xiaomi_15_Ultra_Rear_Wide_Camera_Modular_DCP");
            embedded.put("sourceAdapterPhysicalCameraScope", "Xiaomi_15_Ultra_rear_wide_profile_only");
            embedded.put("sourceAdapterComponents", "ColorMatrix_A_D65,ForwardMatrix_A_D65,ProfileHueSatMap_A_D65");
            embedded.put("sourceAdapterCurrentlyAppliedToRender", true);
            embedded.put("targetProvider", "Leica_M9_firmware");
            embedded.put("targetComponentsInThisAsset", "curve02");
            embedded.put("targetCurveCurrentlyAppliedToRender", true);
            embedded.put("mixedSourceAndTargetAsset", true);
            embedded.put("replacementPolicy", "replace_source_adapter_only_keep_firmware_target_components_frozen");
            embedded.put("hueDivisions", embeddedCal.hueDivisions);
            embedded.put("satDivisions", embeddedCal.satDivisions);
            embedded.put("valueDivisions", embeddedCal.valueDivisions);
            embedded.put("colorMatrixA", matrix(embeddedCal.colorMatrixA));
            embedded.put("colorMatrixD65", matrix(embeddedCal.colorMatrixD65));
            embedded.put("forwardMatrixA", matrix(embeddedCal.forwardMatrixA));
            embedded.put("forwardMatrixD65", matrix(embeddedCal.forwardMatrixD65));
            embedded.put("hsmAFloatCount", embeddedCal.hsmA != null ? embeddedCal.hsmA.length : 0);
            embedded.put("hsmD65FloatCount", embeddedCal.hsmD65 != null ? embeddedCal.hsmD65.length : 0);
            embedded.put("curve02Length", embeddedCal.curve02 != null ? embeddedCal.curve02.length : 0);
            embedded.put("nativeReplacementApplied", false);
            embedded.put("comparisonMeaning", "embedded_Cobalt_source_profile_logged_beside_native_Camera2_source_characterization");
            out.put("embeddedCalibrationRoleAudit1B", embedded);
'''
if anchor not in text:
    raise SystemExit('SOURCECAL1B phase anchor missing')
text = text.replace(anchor, insert, 1)

matrix_anchor = '''    private static JSONArray matrix(float[] a) throws Exception {
        if (a == null || a.length != 9) return null;
        JSONArray rows = new JSONArray();
        for (int r = 0; r < 3; r++) {
            JSONArray row = new JSONArray();
            for (int c = 0; c < 3; c++) {
                float v = a[r * 3 + c];
                row.put(Float.isFinite(v) ? v : JSONObject.NULL);
            }
            rows.put(row);
        }
        return rows;
    }
'''
if matrix_anchor not in text:
    raise SystemExit('SOURCECAL1B float matrix helper anchor missing')
matrix_double = matrix_anchor + '''
    private static JSONArray matrix(double[] a) throws Exception {
        if (a == null || a.length != 9) return null;
        JSONArray rows = new JSONArray();
        for (int r = 0; r < 3; r++) {
            JSONArray row = new JSONArray();
            for (int c = 0; c < 3; c++) {
                double v = a[r * 3 + c];
                row.put(Double.isFinite(v) ? v : JSONObject.NULL);
            }
            rows.put(row);
        }
        return rows;
    }
'''
text = text.replace(matrix_anchor, matrix_double, 1)

for marker in [
    'm9cam.sourcecal.v1b.embeddedcalibrationroles1a',
    'Cobalt_Xiaomi_15_Ultra_Rear_Wide_Camera_Modular_DCP',
    'Leica_M9_firmware',
    'replace_source_adapter_only_keep_firmware_target_components_frozen',
    'embedded.put("colorMatrixA", matrix(embeddedCal.colorMatrixA))',
    'embedded.put("forwardMatrixD65", matrix(embeddedCal.forwardMatrixD65))',
    'embedded.put("curve02Length"',
    'nativeReplacementApplied", false',
    'private static JSONArray matrix(double[] a) throws Exception',
]:
    if marker not in text:
        raise SystemExit('SOURCECAL1B marker missing after patch: ' + marker)

p.write_text(text)
print('M9SOURCECAL1B EMBEDDEDCALIBRATIONROLES1A applied')
print(' - current M9R35CAL asset split into explicit source-adapter vs target-firmware roles')
print(' - Cobalt CM/FM/HSM matrices logged beside native Camera2 source characterization')
print(' - Leica firmware curve02 explicitly retained as target component')
print(' - no native replacement applied; no RAW/JPEG/TC20/M9 render pixel behavior changed')
