#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-sourcecal2a-cmconvention1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9SourceCalibrationAudit1A.java'
if not p.exists():
    raise SystemExit('SOURCECAL2A verify missing generated helper')
text = p.read_text()
for forbidden in ['Converter.normalizeFM(ncm1)', 'Converter.normalizeFM(ncm2)']:
    if forbidden in text:
        raise SystemExit('SOURCECAL2A verify forbidden ColorMatrix normalization remains: ' + forbidden)
for required in [
    'Converter.normalizeFM(nfm1)',
    'Converter.normalizeFM(nfm2)',
    'ref1, ref2, cal1, cal2, cm1, cm2, neutral',
    'nativeColorMatrixConvention", "DNG_XYZ_to_reference_camera_unmodified"',
    'nativeColorMatrixRowNormalizationApplied", false',
    'nativeForwardMatrixNormalizationApplied", true',
    'SOURCECAL2A_CMCONVENTION1A',
]:
    if required not in text:
        raise SystemExit('SOURCECAL2A verify missing marker: ' + required)
print('M9SOURCECAL2A CMCONVENTION1A verification OK')
print(' - DNG ColorMatrix preserved')
print(' - ForwardMatrix normalization retained')
print(' - native interpolation/XYZ transform now uses unmodified ColorMatrix inputs')
