#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m9livepreview1b-fullrender1080p-main.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
preview = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
controller = root / 'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
gradle = root / 'app/build.gradle'
for p in (renderer, preview, controller):
    if not p.exists():
        raise SystemExit('M9LIVEPREVIEW1B missing required file: ' + str(p))

# This overlay intentionally starts from the already-validated 720p full-render preview.
# It changes preview resolution only; the production still-render methods remain untouched.
s = preview.read_text()
required = [
    'public static final int LANDSCAPE_WIDTH = 960;',
    'public static final int LANDSCAPE_HEIGHT = 720;',
    'FULLRENDER720P'
]
for marker in required:
    if marker not in s:
        raise SystemExit('M9LIVEPREVIEW1B expected 720p baseline marker missing: ' + marker)
s = s.replace('public static final int LANDSCAPE_WIDTH = 960;',
              'public static final int LANDSCAPE_WIDTH = 1440;', 1)
s = s.replace('public static final int LANDSCAPE_HEIGHT = 720;',
              'public static final int LANDSCAPE_HEIGHT = 1080;', 1)
s = s.replace('FULLRENDER720P', 'FULLRENDER1080P_MAIN', 1)
# Add an explicit runtime string so packaged APK verification can prove this overlay exists.
anchor = 'private static final String TAG = "M9LivePreview1A";'
if anchor not in s:
    raise SystemExit('M9LIVEPREVIEW1B preview TAG anchor missing')
s = s.replace(anchor, anchor + '\n    public static final String MODE_1B = "M9LIVEPREVIEW1B_FULLRENDER1080P_MAIN";', 1)
preview.write_text(s)

s = renderer.read_text()
old = 'FULL_PRODUCTION_RENDER_REDUCED_RAW_960x720'
new = 'FULL_PRODUCTION_RENDER_REDUCED_RAW_1440x1080_MAIN'
if old not in s:
    raise SystemExit('M9LIVEPREVIEW1B renderer 720p diagnostic marker missing')
s = s.replace(old, new, 1)
renderer.write_text(s)

# Keep the same single-flight probe/render behavior. The busy flag naturally self-throttles
# if 1080p takes longer than the existing probe interval, preventing preview backlog.
c = controller.read_text()
if 'M9LIVEPREVIEW1A_FULLRENDER720P' not in c:
    raise SystemExit('M9LIVEPREVIEW1B requires validated 1A CaptureController baseline')
# Runtime/log marker only; no capture semantics change.
c = c.replace('M9LIVEPREVIEW1A_FULLRENDER720P', 'M9LIVEPREVIEW1A_FULLRENDER720P M9LIVEPREVIEW1B_FULLRENDER1080P_MAIN', 1)
controller.write_text(c)

if gradle.exists():
    g = gradle.read_text()
    m = re.search(r'versionName\s+["\']([^"\']+)["\']', g)
    if m and 'm9livepreview1b' not in m.group(1).lower():
        old_decl = m.group(0)
        quote = '"' if '"' in old_decl else "'"
        base = m.group(1)
        base = re.sub(r'-m9livepreview1a-720pfull$', '', base, flags=re.IGNORECASE)
        g = g.replace(old_decl, 'versionName ' + quote + base + '-m9livepreview1b-1080pfull-main' + quote, 1)
        gradle.write_text(g)

print('M9LIVEPREVIEW1B_FULLRENDER1080P_MAIN applied')
print(' - preview Bayer target: 1440x1080')
print(' - full production M9 renderer retained')
print(' - production still-render methods untouched')
print(' - validation scope: main sensor first')
