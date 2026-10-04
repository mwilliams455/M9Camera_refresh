#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: fix-m9cam-m10r-mfmtest1a-jsonarray1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9M10rMfmTest1A.java'
if not p.exists():
    raise SystemExit('M10RMFMTEST1A JSONARRAY1A target class missing')

s = p.read_text()
old = '''    private static JSONArray toJson(double[] v) {
        JSONArray a = new JSONArray();
        for (double x : v) a.put(x);
        return a;
    }
'''
new = '''    private static JSONArray toJson(double[] v) {
        JSONArray a = new JSONArray();
        for (double x : v) {
            try {
                a.put(x);
            } catch (Exception ignored) {
                // Diagnostic telemetry must never affect capture or rendering.
            }
        }
        return a;
    }
'''
if old not in s:
    if 'Diagnostic telemetry must never affect capture or rendering.' in s:
        print('M10RMFMTEST1A JSONARRAY1A already applied')
        raise SystemExit(0)
    raise SystemExit('M10RMFMTEST1A JSONARRAY1A helper anchor missing')

s = s.replace(old, new, 1)
p.write_text(s)

check = p.read_text()
if 'for (double x : v) a.put(x);' in check:
    raise SystemExit('M10RMFMTEST1A JSONARRAY1A unsafe put remains')
if 'Diagnostic telemetry must never affect capture or rendering.' not in check:
    raise SystemExit('M10RMFMTEST1A JSONARRAY1A source guard missing')

print('M10RMFMTEST1A JSONARRAY1A compile compatibility fix applied')
print(' - JSONArray.put(double) exception is contained in telemetry serialization only')
print(' - no metering equation, exposure bound, TC20, renderer, JPEG or DNG path changed')
