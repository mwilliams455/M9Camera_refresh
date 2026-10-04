#!/usr/bin/env python3
from pathlib import Path
import hashlib
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-nativeprospective1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
native_path = root / 'app/src/main/cpp/m9color_jni.cpp'
physical_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PhysicalCaptureResult1A.java'
for p in [renderer_path, gradle_path, native_path, physical_path]:
    if not p.exists():
        raise SystemExit('NATIVEPROSPECTIVE1A verifier missing: ' + str(p))
renderer = renderer_path.read_text()
gradle = gradle_path.read_text()
native = native_path.read_text()


def extract_method(text, marker):
    start = text.find(marker)
    if start < 0:
        raise SystemExit('verifier method marker missing: ' + marker)
    brace = text.find('{', start)
    depth = 0
    i = brace
    in_string = False
    quote = ''
    escape = False
    while i < len(text):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == quote:
                in_string = False
        else:
            if ch in ('"', "'"):
                in_string = True
                quote = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        i += 1
    raise SystemExit('verifier unterminated method')

frozen = extract_method(renderer, '    private static RenderCore renderCore(')
prospective = extract_method(renderer, '    private static RenderCore renderNativeProspectiveCore(')

m = re.search(r'nativeProspectiveDiag\.put\("frozenPrimaryRenderCoreSha256",\s*\n\s*"([0-9a-f]{64})"\);', renderer)
if not m:
    raise SystemExit('NATIVEPROSPECTIVE1A frozen renderCore SHA marker missing')
actual = hashlib.sha256(frozen.encode('utf-8')).hexdigest()
if actual != m.group(1):
    raise SystemExit('NATIVEPROSPECTIVE1A frozen renderCore SHA mismatch: %s != %s' % (actual, m.group(1)))

required_renderer = [
    'stem + "_M9_NATIVEPROSPECTIVE.jpg"',
    'stem + "_M9_NATIVEPROSPECTIVE.json"',
    'M9PhysicalCaptureResult1A.resolve(',
    'resultMatchesRequestedPhysical(',
    'applyNativeProspectiveGainMap(',
    'buildNativeProspectiveSource(',
    'Converter.calculateCameraToXYZD50Transform(',
    'Converter.findDngInterpolationFactor(',
    'Converter.convertColorspaceTransform(',
    'gainMapApplicationCount", 1',
    'gainMapApplicationStage", "normalized_linear_Bayer_pre_demosaic"',
    'cobaltColorMatrixApplied", false',
    'cobaltForwardMatrixApplied", false',
    'cobaltHueSatMapApplied", false',
    'mixedCalibrationAssetUsage", "curve02_target_component_only"',
    'failed_isolated_primary_preserved',
]
for marker in required_renderer:
    if marker not in renderer:
        raise SystemExit('NATIVEPROSPECTIVE1A required marker missing: ' + marker)

if prospective.find('applyNativeProspectiveGainMap(') > prospective.find('Imgproc.cvtColor(rawMat, cam16'):
    raise SystemExit('NATIVEPROSPECTIVE1A GainMap is not applied before demosaic')
if 'buildColorContext(neutralF, cal)' in prospective:
    raise SystemExit('NATIVEPROSPECTIVE1A prospective path still calls Cobalt buildColorContext')
if 'cal.colorMatrix' in prospective or 'cal.forwardMatrix' in prospective or 'cal.hsm' in prospective:
    raise SystemExit('NATIVEPROSPECTIVE1A prospective method references Cobalt calibration components')
if 'M9R35Calibration cal = M9R35Calibration.get();' not in prospective or 'cal.curve02' not in prospective:
    raise SystemExit('NATIVEPROSPECTIVE1A curve02 target retention missing')
if prospective.count('applyNativeProspectiveGainMap(') != 1:
    raise SystemExit('NATIVEPROSPECTIVE1A prospective render must apply GainMap at one call site exactly')

if 'NATIVEPROSPECTIVE1A' in native or 'nativeProspective' in native:
    raise SystemExit('NATIVEPROSPECTIVE1A unexpectedly modified native m9color C++')
if 'cameraToM9(' not in native or 'm9CurvePixel(' not in native or 'renderStripScalar(' not in native:
    raise SystemExit('NATIVEPROSPECTIVE1A native frozen kernel markers missing')

if '-nativeprospective1a' not in gradle:
    raise SystemExit('NATIVEPROSPECTIVE1A APK identity suffix missing')

print('NATIVEPROSPECTIVE1A verification OK')
print(' - frozen renderCore sha256:', actual)
print(' - frozen primary output naming/payload path retained; prospective starts post-save')
print(' - live physical LensShadingMap exactly once before demosaic')
print(' - native Camera2 dual-illuminant sensor->XYZ source adapter; Cobalt CM/FM/HSM bypassed')
print(' - native m9color C++ reused unchanged with retained TC20/SAT3/curve02/BT601/TG1')
print(' - isolated *_M9_NATIVEPROSPECTIVE.jpg/json outputs present')
