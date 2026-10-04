#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: fix-m9cam-rawshading1a-minmax1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RawShadingAudit1A.java'
if not path.exists():
    raise SystemExit('RAWSHADING1A MINMAX1A requires M9RawShadingAudit1A.java')
text = path.read_text()

old = '''                out.put("gainMapMinPerChannel", stats(factors, cols, rows, 0));
                out.put("gainMapStatsPerChannel", allChannelStats(factors, cols, rows));'''
new = '''                out.put("gainMapMinPerChannel", channelExtrema(factors, cols, rows, true));
                out.put("gainMapMaxPerChannel", channelExtrema(factors, cols, rows, false));
                out.put("gainMapStatsPerChannel", allChannelStats(factors, cols, rows));'''
if new not in text:
    if old not in text:
        raise SystemExit('RAWSHADING1A MINMAX1A stats anchor missing')
    text = text.replace(old, new, 1)

anchor = '''    private static JSONArray allChannelStats(float[] factors, int cols, int rows) throws Exception {
'''
helper = '''    private static JSONArray channelExtrema(float[] factors, int cols, int rows, boolean wantMin) throws Exception {
        JSONArray out = new JSONArray();
        for (int c = 0; c < 4; c++) {
            JSONObject s = stats(factors, cols, rows, c);
            if (!s.optBoolean("valid", false)) out.put(JSONObject.NULL);
            else out.put(wantMin ? s.optDouble("min") : s.optDouble("max"));
        }
        return out;
    }

'''
if helper not in text:
    if anchor not in text:
        raise SystemExit('RAWSHADING1A MINMAX1A helper anchor missing')
    text = text.replace(anchor, helper + anchor, 1)

path.write_text(text)
print('M9RAWSHADING1A MINMAX1A applied')
print(' - gainMapMinPerChannel is now [R, Geven, Godd, B]')
print(' - gainMapMaxPerChannel is now [R, Geven, Godd, B]')
