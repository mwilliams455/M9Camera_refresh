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
if 'Converter.convertColorspaceTransform(t, out);' not in text:
    raise SystemExit('SOURCECAL1A MATRIXCONVENTION1A conversion marker missing')
p.write_text(text)
print('M9SOURCECAL1A MATRIXCONVENTION1A applied')
print(' - native Camera2 matrices use the same internal layout as Parameters.ReCalcColor')
print(' - native-vs-active comparisons and native sensor->XYZ calculation are convention-aligned')
print(' - diagnostic only; no render input changed')
