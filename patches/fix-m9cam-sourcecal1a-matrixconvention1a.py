#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: fix-m9cam-sourcecal1a-matrixconvention1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9SourceCalibrationAudit1A.java'
if not p.exists():
    raise SystemExit('SOURCECAL1A MATRIXCONVENTION1A requires generated audit helper')
text = p.read_text()
old = '''    private static float[] transform(ColorSpaceTransform t) {
        if (t == null) return null;
        float[] out = new float[9];
        int k = 0;
        for (int r = 0; r < 3; r++) {
            for (int c = 0; c < 3; c++) {
                Rational v = t.getElement(r, c);
                out[k++] = v != null ? v.floatValue() : Float.NaN;
            }
        }
        return out;
    }
'''
new = '''    private static float[] transform(ColorSpaceTransform t) {
        if (t == null) return null;
        // Match Parameters.ReCalcColor()/Converter.convertColorspaceTransform exactly:
        // Photon stores Camera2 ColorSpaceTransform in its internal transposed layout.
        float[] out = new float[9];
        Converter.convertColorspaceTransform(t, out);
        return out;
    }
'''
if old not in text:
    raise SystemExit('SOURCECAL1A MATRIXCONVENTION1A transform anchor missing')
text = text.replace(old, new, 1)

# Android's org.json implementation on this baseline declares JSONArray.put as checked.
# These helpers are only called inside captureAndWrite's broad try/catch, so propagate it.
array_old = '    private static JSONArray array(float[] a) {\n'
array_new = '    private static JSONArray array(float[] a) throws Exception {\n'
if array_old not in text:
    raise SystemExit('SOURCECAL1A JSONEXCEPTION1A array helper anchor missing')
text = text.replace(array_old, array_new, 1)

matrix_old = '    private static JSONArray matrix(float[] a) {\n'
matrix_new = '    private static JSONArray matrix(float[] a) throws Exception {\n'
if matrix_old not in text:
    raise SystemExit('SOURCECAL1A JSONEXCEPTION1A matrix helper anchor missing')
text = text.replace(matrix_old, matrix_new, 1)

for marker in [
    'Converter.convertColorspaceTransform(t, out);',
    'private static JSONArray array(float[] a) throws Exception',
    'private static JSONArray matrix(float[] a) throws Exception',
]:
    if marker not in text:
        raise SystemExit('SOURCECAL1A hardening marker missing: ' + marker)

p.write_text(text)
print('M9SOURCECAL1A MATRIXCONVENTION1A/JSONEXCEPTION1A applied')
print(' - native Camera2 matrices use the same internal layout as Parameters.ReCalcColor')
print(' - native-vs-active comparisons and native sensor->XYZ calculation are convention-aligned')
print(' - diagnostic JSONArray helpers propagate checked JSONException to existing audit try/catch')
print(' - diagnostic only; no render input changed')
