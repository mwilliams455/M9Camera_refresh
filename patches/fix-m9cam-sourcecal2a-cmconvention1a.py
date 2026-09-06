#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: fix-m9cam-sourcecal2a-cmconvention1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9SourceCalibrationAudit1A.java'
if not p.exists():
    raise SystemExit('SOURCECAL2A CMCONVENTION1A requires generated SOURCECAL helper')
text = p.read_text()

old = '''                float[] ncm1 = cm1.clone();
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
new = '''                // SOURCECAL2A CMCONVENTION1A: DNG ColorMatrix is XYZ -> reference-camera.
                // Do not row-normalize it using ForwardMatrix normalization. ForwardMatrix
                // normalization is retained because the DNG forward route is defined in the
                // D50 output convention expected by Converter.calculateCameraToXYZD50Transform().
                float[] nfm1 = fm1.clone();
                float[] nfm2 = fm2.clone();
                Converter.normalizeFM(nfm1);
                Converter.normalizeFM(nfm2);

                double factor = Converter.findDngInterpolationFactor(
                        ref1, ref2, cal1, cal2, cm1, cm2, neutral);
'''
if text.count(old) != 1:
    raise SystemExit('SOURCECAL2A CMCONVENTION1A expected legacy CM/FM normalization block once')
text = text.replace(old, new, 1)

anchor = '''                out.put("nativeTransformCalculation",
                        "Photon_Converter_DNG_dual_illuminant_math_using_only_CameraCharacteristics_and_live_neutral");
'''
insert = anchor + '''                out.put("nativeColorMatrixConvention", "DNG_XYZ_to_reference_camera_unmodified");
                out.put("nativeColorMatrixRowNormalizationApplied", false);
                out.put("nativeForwardMatrixNormalizationApplied", true);
                out.put("nativeTransformConventionFix", "SOURCECAL2A_CMCONVENTION1A");
'''
if anchor not in text:
    raise SystemExit('SOURCECAL2A CMCONVENTION1A diagnostic anchor missing')
text = text.replace(anchor, insert, 1)

for forbidden in ['Converter.normalizeFM(ncm1)', 'Converter.normalizeFM(ncm2)']:
    if forbidden in text:
        raise SystemExit('SOURCECAL2A CMCONVENTION1A forbidden ColorMatrix normalization remains: ' + forbidden)
for required in [
    'Converter.findDngInterpolationFactor(\n                        ref1, ref2, cal1, cal2, cm1, cm2, neutral)',
    'nativeColorMatrixRowNormalizationApplied", false',
    'nativeForwardMatrixNormalizationApplied", true',
]:
    if required not in text:
        raise SystemExit('SOURCECAL2A CMCONVENTION1A required marker missing: ' + required)

p.write_text(text)
print('M9SOURCECAL2A CMCONVENTION1A applied')
print(' - native DNG ColorMatrix1/2 preserved in XYZ->reference-camera convention')
print(' - ForwardMatrix normalization retained')
print(' - previous SOURCECAL1A native transform should be considered superseded')
