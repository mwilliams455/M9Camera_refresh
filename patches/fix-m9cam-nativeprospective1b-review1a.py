#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: fix-m9cam-nativeprospective1b-review1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeProspective1A.java'
if not p.exists():
    raise SystemExit('NATIVEPROSPECTIVE1B REVIEW1A requires generated NATIVEPROSPECTIVE1A helper')
text = p.read_text()

# 1) Correct DNG ColorMatrix convention. ForwardMatrix normalization remains intentional.
old_cm = '''        float[] ncm1 = cm1.clone();
        float[] ncm2 = cm2.clone();
        float[] nfm1 = fm1.clone();
        float[] nfm2 = fm2.clone();
        Converter.normalizeFM(ncm1);
        Converter.normalizeFM(ncm2);
        Converter.normalizeFM(nfm1);
        Converter.normalizeFM(nfm2);

        double factor = Converter.findDngInterpolationFactor(
                ref1, ref2, cal1, cal2, ncm1, ncm2, neutral);
'''
new_cm = '''        // NATIVEPROSPECTIVE1B CMCONVENTION1A: preserve DNG ColorMatrix1/2 exactly
        // as XYZ -> reference-camera matrices. normalizeFM() is a ForwardMatrix
        // normalization and must not alter camera-channel relationships used for white inference.
        float[] nfm1 = fm1.clone();
        float[] nfm2 = fm2.clone();
        Converter.normalizeFM(nfm1);
        Converter.normalizeFM(nfm2);

        double factor = Converter.findDngInterpolationFactor(
                ref1, ref2, cal1, cal2, cm1, cm2, neutral);
'''
if text.count(old_cm) != 1:
    raise SystemExit('NATIVEPROSPECTIVE1B CM normalization block missing/non-unique')
text = text.replace(old_cm, new_cm, 1)

# 2) Make current scope explicit: scientifically valid main/RGGB experiment only.
cfa_old = '''            if (params.cfaPattern != 0) {
                throw new IllegalStateException(
                        "NATIVEPROSPECTIVE1A follows frozen RGGB CFA=0 path; got " + params.cfaPattern);
            }
'''
cfa_new = cfa_old + '''            out.put("cfaPattern", params.cfaPattern & 0xff);
            out.put("cfaScope", "RGGB_main_only_until_CFA_aware_shading_and_demosaic_are_validated");
            out.put("fourRearCameraRendererClaimed", false);
'''
if text.count(cfa_old) != 1:
    raise SystemExit('NATIVEPROSPECTIVE1B CFA scope anchor missing/non-unique')
text = text.replace(cfa_old, cfa_new, 1)

# 3) Preserve single-frame shading headroom inside the U16 transport by scaling the
# corrected Bayer plane down by the frame map maximum, then compensate that scalar at
# the final fixed M9 render gain. This avoids pre-demosaic clipping caused solely by
# Camera2 LensShadingMap gains > 1 while retaining the exact same primary TC20 decision.
map_decl_old = '''        float[] map = null;
        int mapCols = 0;
        int mapRows = 0;
'''
map_decl_new = map_decl_old + '''        double lensShadingLinearStorageScale = 1.0;
'''
if text.count(map_decl_old) != 1:
    raise SystemExit('NATIVEPROSPECTIVE1B lens-map declaration anchor missing/non-unique')
text = text.replace(map_decl_old, map_decl_new, 1)

map_copy_old = '''            map = new float[lensMap.getGainFactorCount()];
            lensMap.copyGainFactors(map, 0);
            out.put("camera2LensShadingMapApplied", true);
'''
map_copy_new = '''            map = new float[lensMap.getGainFactorCount()];
            lensMap.copyGainFactors(map, 0);
            double maxMapGainForStorage = 1.0;
            for (float g : map) {
                if (Float.isFinite(g) && g > maxMapGainForStorage) maxMapGainForStorage = g;
            }
            lensShadingLinearStorageScale = 1.0 / maxMapGainForStorage;
            out.put("lensShadingMaxMapGainForStorage", maxMapGainForStorage);
            out.put("lensShadingLinearStorageScale", lensShadingLinearStorageScale);
            out.put("lensShadingHeadroomPolicy",
                    "scale_corrected_linear_Bayer_to_U16_then_inverse_scale_at_fixed_M9_render_gain");
            out.put("camera2LensShadingMapApplied", true);
'''
if text.count(map_copy_old) != 1:
    raise SystemExit('NATIVEPROSPECTIVE1B lens-map copy anchor missing/non-unique')
text = text.replace(map_copy_old, map_copy_new, 1)

unit_old = '''                double corrected = Math.max(0.0, rawValue - bl) * gain;
                double unit = Math.max(0.0, Math.min(1.0, corrected / denominator));
                normalized[index] = (short) Math.round(unit * 65535.0);
'''
unit_new = '''                double corrected = Math.max(0.0, rawValue - bl) * gain;
                double correctedUnit = (corrected / denominator) * lensShadingLinearStorageScale;
                boolean storageClipped = correctedUnit > 1.0;
                double unit = Math.max(0.0, Math.min(1.0, correctedUnit));
                if (storageClipped) shadingStorageClipCount++;
                normalized[index] = (short) Math.round(unit * 65535.0);
'''
if text.count(unit_old) != 1:
    raise SystemExit('NATIVEPROSPECTIVE1B old shading clamp anchor missing/non-unique')
# Add counter before pixel loop.
loop_anchor = '''        long[] gainCount = new long[4];

        for (int y = 0, index = 0; y < height; y++) {
'''
loop_new = '''        long[] gainCount = new long[4];
        long shadingStorageClipCount = 0L;

        for (int y = 0, index = 0; y < height; y++) {
'''
if text.count(loop_anchor) != 1:
    raise SystemExit('NATIVEPROSPECTIVE1B shading clip-counter anchor missing/non-unique')
text = text.replace(loop_anchor, loop_new, 1)
text = text.replace(unit_old, unit_new, 1)

return_anchor = '''        out.put("bayerCorrectionOrder",
                "max(raw-encoded_black,0)*Camera2_LensShadingMap_then_whiteLevel_normalize");
        return normalized;
'''
return_new = '''        out.put("bayerCorrectionOrder",
                "max(raw-encoded_black,0)*Camera2_LensShadingMap_then_linear_storage_scale_then_whiteLevel_normalize");
        out.put("lensShadingStorageClipCount", shadingStorageClipCount);
        out.put("lensShadingStorageClipFraction", pixels > 0 ? shadingStorageClipCount / (double)pixels : 0.0);
        if (!useMap) {
            out.put("lensShadingLinearStorageScale", 1.0);
            out.put("lensShadingHeadroomPolicy", "no_map_identity_scale");
        }
        return normalized;
'''
if text.count(return_anchor) != 1:
    raise SystemExit('NATIVEPROSPECTIVE1B Bayer return anchor missing/non-unique')
text = text.replace(return_anchor, return_new, 1)

# 4) Fixed exposure comparison must fail closed if the primary TC20 result is absent.
gain_old = '''            double tc20BaselineGain = frozenRendererDiagnostics != null
                    ? frozenRendererDiagnostics.optDouble("gain", 1.0) : 1.0;
            String treatment = edge != null ? edge.optString("treatment", "FROZEN") : "FROZEN";
            double renderGainEv = "DARK_EXACT_RERENDER_GAIN_OFFSET".equals(treatment)
                    ? edge.optDouble("appliedEv", 0.0) : 0.0;
            double fixedRenderGain = tc20BaselineGain * Math.pow(2.0, renderGainEv);
'''
gain_new = '''            if (frozenRendererDiagnostics == null || !frozenRendererDiagnostics.has("gain")) {
                out.put("tc20ComparisonEligible", false);
                throw new IllegalStateException("frozen primary TC20 gain unavailable; prospective comparison refused");
            }
            double tc20BaselineGain = frozenRendererDiagnostics.optDouble("gain", Double.NaN);
            if (!Double.isFinite(tc20BaselineGain) || tc20BaselineGain <= 0.0) {
                out.put("tc20ComparisonEligible", false);
                throw new IllegalStateException("invalid frozen primary TC20 gain: " + tc20BaselineGain);
            }
            out.put("tc20ComparisonEligible", true);
            String treatment = edge != null ? edge.optString("treatment", "FROZEN") : "FROZEN";
            double renderGainEv = "DARK_EXACT_RERENDER_GAIN_OFFSET".equals(treatment)
                    ? edge.optDouble("appliedEv", 0.0) : 0.0;
            double linearStorageScale = out.optDouble("lensShadingLinearStorageScale", 1.0);
            if (!Double.isFinite(linearStorageScale) || linearStorageScale <= 0.0 || linearStorageScale > 1.0) {
                throw new IllegalStateException("invalid prospective linear storage scale: " + linearStorageScale);
            }
            double fixedRenderGain = tc20BaselineGain * Math.pow(2.0, renderGainEv) / linearStorageScale;
'''
if text.count(gain_old) != 1:
    raise SystemExit('NATIVEPROSPECTIVE1B frozen TC20 anchor missing/non-unique')
text = text.replace(gain_old, gain_new, 1)

# Diagnostics that distinguish the source transform convention from shading.
diag_anchor = '''            out.put("prospectiveEffectiveRenderGain", fixedRenderGain);
'''
diag_new = diag_anchor + '''            out.put("prospectiveLinearStorageScaleCompensation", 1.0 / linearStorageScale);
            out.put("nativeColorMatrixConvention", "DNG_XYZ_to_reference_camera_unmodified");
            out.put("nativeColorMatrixRowNormalizationApplied", false);
            out.put("nativeForwardMatrixNormalizationApplied", true);
            out.put("experimentConfoundingWarning",
                    "combined_native_source_plus_lens_shading_result_do_not_promote_without_source_only_control");
'''
if text.count(diag_anchor) != 1:
    raise SystemExit('NATIVEPROSPECTIVE1B gain diagnostic anchor missing/non-unique')
text = text.replace(diag_anchor, diag_new, 1)

for forbidden in ['Converter.normalizeFM(ncm1)', 'Converter.normalizeFM(ncm2)']:
    if forbidden in text:
        raise SystemExit('NATIVEPROSPECTIVE1B forbidden ColorMatrix normalization remains')
for required in [
    'cfaScope", "RGGB_main_only',
    'tc20ComparisonEligible", false',
    'lensShadingLinearStorageScale',
    'lensShadingStorageClipFraction',
    'nativeColorMatrixRowNormalizationApplied", false',
]:
    if required not in text:
        raise SystemExit('NATIVEPROSPECTIVE1B required marker missing: ' + required)

p.write_text(text)
print('M9 NATIVEPROSPECTIVE1B REVIEW1A applied')
print(' - DNG ColorMatrix convention corrected; no FM-style CM row normalization')
print(' - primary TC20/edge-placement result is mandatory and reused, never defaulted/re-metered')
print(' - LensShadingMap U16 transport preserves linear headroom by scale+inverse-gain compensation')
print(' - current photographic experiment explicitly scoped to RGGB main camera only')
print(' - combined source+shading image remains diagnostic until a source-only control is added')
