#!/usr/bin/env python3
from pathlib import Path
import math
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-nohdr1a-sourcecal2a-fixedgain1a-nativeab1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit('verifier: not a PhotonCamera root')

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit('verifier missing expected file: ' + rel)
    return p.read_text()

def require(text, marker, label):
    if marker not in text:
        raise SystemExit('verifier missing ' + label + ': ' + marker)

def forbid(text, marker, label):
    if marker in text:
        raise SystemExit('verifier forbidden ' + label + ': ' + marker)

def extract_top_method(text, marker):
    start = text.find(marker)
    if start < 0:
        raise SystemExit('verifier method marker missing: ' + marker)
    end = text.find('\n    private static ', start + len(marker))
    if end < 0:
        raise SystemExit('verifier next method marker missing: ' + marker)
    return text[start:end]

frames = read('app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java')
iso = read('app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java')
source = read('app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9SourceCalibrationAudit1A.java')
renderer = read('app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java')
gradle = read('app/build.gradle')

# NOHDR1A hard boundary.
for marker in [
    'M9_NOHDR1A_SINGLE_FRAME_BOUNDARY',
    'frameCount = 1;',
    'throwCount = 0;',
    'IsoExpoSelector.HDR = false;',
    'return 1;',
]:
    require(frames, marker, 'NOHDR1A FrameNumberSelector boundary')
for marker in [
    'M9_NOHDR1A_EXPOSURE_ALLOCATOR',
    'if (M9Config.usesM9Pipeline()) HDR = false;',
]:
    require(iso, marker, 'NOHDR1A exposure allocator')
for marker in [
    'd.put("captureMode", "single_frame_raw")',
    'd.put("requestedFrameCount", 1)',
    'd.put("contributingRawFrameCount", 1)',
    'd.put("multiFrameFusion", false)',
    'd.put("temporalMerge", false)',
    'd.put("hdrToneMapper", false)',
    'd.put("ultraHdrOutput", false)',
    'd.put("androidHdrGainmapUsed", false)',
    'd.put("outputEncoding", "SDR_JPEG")',
]:
    require(renderer, marker, 'NOHDR1A diagnostics')

# SOURCECAL2A-CMFIX matrix semantics.
require(source, 'SOURCECAL2A_CMFIX', 'SOURCECAL2A identity')
require(source,
        'nativeColorMatrixNormalization", "none_preserve_DNG_XYZ_to_reference_camera"',
        'ColorMatrix preservation diagnostic')
require(source,
        'nativeForwardMatrixNormalization", "D50_forward_matrix_only"',
        'ForwardMatrix normalization diagnostic')
require(source,
        'matrixStorageConvention", "android_ColorSpaceTransform_copyElements_row_major"',
        'Android-safe row-major matrix diagnostic')
for marker in [
    'Converter.normalizeFM(ncm1);',
    'Converter.normalizeFM(ncm2);',
]:
    forbid(source, marker, 'ColorMatrix normalization')
for marker in [
    'Converter.normalizeFM(nfm1);',
    'Converter.normalizeFM(nfm2);',
]:
    require(source, marker, 'ForwardMatrix normalization')

# NATIVEAB1A static isolation and fixed-gain invariants.
prospective = extract_top_method(renderer, '    private static RenderCore renderNativeProspectiveCore(')
for marker in [
    'double fixedPrimaryGain',
    'boolean applyNativeShading',
    'tc20DecisionSource", "frozen_primary_same_frame"',
    'prospectiveMeterRecomputed", false',
    'final double effectiveRenderGain = fixedPrimaryGain * nativeShading.representationScale;',
]:
    require(prospective, marker, 'FIXEDGAIN1A prospective method')
for marker in [
    'tc20MeterNative(',
    'tc20MeterNativeDirect(',
    'METER_TARGET /',
]:
    forbid(prospective, marker, 'prospective re-metering')
for marker in [
    '"_M9_NATIVE_SOURCE_ONLY"',
    '"_M9_NATIVE_SOURCE_SHADING"',
    'if (!"2".equals(requestedPhysicalId))',
    'sameRawAsPrimary", true',
    'fixedPrimaryLinearGain',
    'primaryTc20BaselineGain',
]:
    require(renderer, marker, 'NATIVEAB1A controlled output hook')

# Shading must not clip valid post-gain samples to nominal 1 before preserving scale.
for marker in [
    'final double representationScale = maxGain;',
    'double correctedLinear = normalized * gain;',
    'double represented = correctedLinear / representationScale;',
    'aboveNominalBeforeScale',
    'postScaleClipCount',
    'singleFrameLinearHeadroomPreserved',
    'postScaleClip != 0L',
]:
    require(renderer, marker, 'RAWSHADING2A headroom preservation')
forbid(renderer,
       'clamp(v, 0.0, 1.0) * 65535.0',
       'old post-shading nominal clamp')

# Correct Camera2 matrix extraction in both the experimental source adapter and
# SOURCECAL audit. Android ColorSpaceTransform.getElement is column,row; using
# copyElements() removes that argument-order ambiguity and yields documented row-major.
for marker in [
    'Rational[] elements = new Rational[9];',
    'transform.copyElements(elements, 0);',
    'out[i] = v != null ? v.floatValue() : Float.NaN;',
    'colorMatrixConvention", "row_major_DNG_XYZ_to_reference_camera_unchanged"',
    'forwardMatrixConvention", "D50_normalized_only"',
    'nativeMatrixExtractionPolicy", "NATIVEAPIORDER1A_ColorSpaceTransform_copyElements_row_major"',
    'converterConvertColorspaceTransformUsed", false',
]:
    require(renderer, marker, 'NATIVEAPIORDER1A renderer source adapter')
for marker in [
    'Rational[] elements = new Rational[9];',
    't.copyElements(elements, 0);',
    'out[i] = v != null ? v.floatValue() : Float.NaN;',
]:
    require(source, marker, 'NATIVEAPIORDER1A SOURCECAL audit')
forbid(renderer, 'Rational v = transform.getElement(r, c);',
       'wrong getElement(row,column) renderer extraction')
forbid(source, 'Rational v = t.getElement(r, c);',
       'wrong getElement(row,column) SOURCECAL extraction')
forbid(prospective, 'Converter.normalizeFM(ncm1);', 'prospective CM1 normalization')
forbid(prospective, 'Converter.normalizeFM(ncm2);', 'prospective CM2 normalization')

# Distinct build identity.
require(gradle, '-nohdr1a-sourcecal2a-cmfix-fixedgain1a-nativeab1a',
        'corrected APK version suffix')
require(gradle, '-nativeapiorder1a', 'NATIVEAPIORDER1A version suffix')

# Numerical sanity using reviewed Xiaomi main-camera matrices from the v2.89 handoff.
CM_D65 = [
    0.67664, -0.217803, 0.000916,
    -0.158325, 1.075623, 0.089294,
    0.05809, 0.153564, 0.496475,
]
CM_A = [
    0.813507, -0.292191, -0.000885,
    -0.123856, 1.072311, 0.05397,
    0.085602, 0.190414, 0.409332,
]
FM_D65 = [
    0.624100, 0.292114, 0.048004,
    0.226761, 0.733521, 0.039719,
    0.001740, 0.041626, 0.781525,
]
FM_A = [
    0.575424, 0.341614, 0.047180,
    0.213623, 0.749039, 0.037338,
    -0.004593, 0.118500, 0.710983,
]
CAL_D65 = [
    0.997269, 0.0, 0.0,
    0.0, 1.000000, 0.0,
    0.0, 0.0, 0.971268,
]
CAL_A = [
    0.982056, 0.0, 0.0,
    0.0, 1.000000, 0.0,
    0.0, 0.0, 0.965775,
]
D50 = [0.9642, 1.0, 0.8249]

def det3(m):
    return (m[0]*(m[4]*m[8]-m[5]*m[7])
            - m[1]*(m[3]*m[8]-m[5]*m[6])
            + m[2]*(m[3]*m[7]-m[4]*m[6]))

def map3(m, v):
    return [
        m[0]*v[0] + m[1]*v[1] + m[2]*v[2],
        m[3]*v[0] + m[4]*v[1] + m[5]*v[2],
        m[6]*v[0] + m[7]*v[1] + m[8]*v[2],
    ]

def normalize_fm(m):
    xyz = map3(m, [1.0, 1.0, 1.0])
    if min(abs(x) for x in xyz) < 1e-12:
        raise SystemExit('verifier ForwardMatrix normalization singular white')
    row_scale = [D50[i]/xyz[i] for i in range(3)]
    out = m[:]
    for r in range(3):
        for c in range(3):
            out[r*3+c] *= row_scale[r]
    return out

for name, m in [('CM_D65', CM_D65), ('CM_A', CM_A),
                ('FM_D65', FM_D65), ('FM_A', FM_A),
                ('CAL_D65', CAL_D65), ('CAL_A', CAL_A)]:
    d = det3(m)
    if not math.isfinite(d) or abs(d) < 1e-4:
        raise SystemExit(f'verifier {name} determinant implausible: {d}')

for name, fm in [('FM_D65', FM_D65), ('FM_A', FM_A)]:
    n = normalize_fm(fm)
    white = map3(n, [1.0, 1.0, 1.0])
    if max(abs(white[i]-D50[i]) for i in range(3)) > 2e-6:
        raise SystemExit(f'verifier {name} D50 normalization failed: {white}')

# CameraCalibration is meaningfully non-identity, so it must remain in the transform.
if abs(CAL_D65[8]-1.0) < 1e-3 or abs(CAL_A[0]-1.0) < 1e-3:
    raise SystemExit('verifier expected non-identity Xiaomi CameraCalibration endpoints')

# Negative control: treating ColorMatrix as ForwardMatrix materially changes it.
cm_bad = normalize_fm(CM_D65)
if max(abs(cm_bad[i]-CM_D65[i]) for i in range(9)) < 1e-3:
    raise SystemExit('verifier ColorMatrix normalization negative control unexpectedly negligible')

print('M9 NOHDR1A / SOURCECAL2A-CMFIX / FIXEDGAIN1A / NATIVEAB1A / NATIVEAPIORDER1A verified')
print(' - M9 still capture requests exactly one RAW and disables bracket exposure allocation')
print(' - SDR JPEG / no fusion / no Ultra HDR contract is explicit')
print(' - Xiaomi ColorMatrix rows are preserved; ForwardMatrix-only D50 normalization')
print(' - Camera2 matrices use copyElements() row-major in both renderer and SOURCECAL audit')
print(' - native A/B reuses same-frame primary gain and contains no prospective TC20 meter')
print(' - main physical camera 2 only; source-only and source+shading outputs are isolated')
print(' - shading preserves >1.0 single-frame linear headroom by global representation scaling')
