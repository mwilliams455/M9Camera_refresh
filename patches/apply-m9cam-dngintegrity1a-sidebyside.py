#!/usr/bin/env python3
from pathlib import Path
import re
import subprocess
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply-m9cam-dngintegrity1a-sidebyside.py <PhotonCamera-root>")

root = Path(sys.argv[1]).resolve()
if not (root / "app").is_dir():
    raise SystemExit(f"not a PhotonCamera root: {root}")

build_gradle = root / "app/build.gradle"
strings_xml = root / "app/src/main/res/values/strings.xml"

if not build_gradle.exists() or not strings_xml.exists():
    raise SystemExit("DNGINTEGRITY1A side-by-side patch failed: required app files missing")

# Give this diagnostic APK a distinct Android package identity so it can be installed
# alongside the current M9Cam build. Namespace/class packages deliberately stay unchanged.
g = build_gradle.read_text()
app_id_re = re.compile(r"(?m)^(\s*)applicationId\s+['\"][^'\"]+['\"]\s*$")
m = app_id_re.search(g)
if not m:
    raise SystemExit("DNGINTEGRITY1A side-by-side patch failed: applicationId anchor missing")
g = g[:m.start()] + f"{m.group(1)}applicationId 'com.particlesdevs.photoncamera.m9dngintegrity1a'" + g[m.end():]

# Make the generated filename unmistakable in Actions/downloads. This is cosmetic;
# the distinct applicationId above is what permits simultaneous installation.
out_re = re.compile(r'(?m)^(\s*)outputFileName\s*=\s*"[^"]+"\s*$')
m = out_re.search(g)
if not m:
    raise SystemExit("DNGINTEGRITY1A side-by-side patch failed: outputFileName anchor missing")
g = g[:m.start()] + f'{m.group(1)}outputFileName = "M9Cam-DNGINTEGRITY1A-${{versionName}}${{versionBuild}}-${{variant.name}}.apk"' + g[m.end():]
build_gradle.write_text(g)

s = strings_xml.read_text()
app_name_re = re.compile(r'<string\s+name="app_name"[^>]*>.*?</string>')
if not app_name_re.search(s):
    raise SystemExit("DNGINTEGRITY1A side-by-side patch failed: app_name string missing")
s = app_name_re.sub('<string name="app_name" translatable="false">M9Cam DNG Integrity</string>', s, count=1)
strings_xml.write_text(s)

# DNGGAINMAPFIX1A is deliberately chained only into this side-by-side diagnostic APK.
# It corrects DNG metadata geometry only; RAW bytes and the photographic pipeline stay frozen.
gainmap_patch = Path(__file__).with_name("apply-m9cam-dnggainmapfix1a.py")
subprocess.run([sys.executable, str(gainmap_patch), str(root)], check=True)

print("M9Cam DNGINTEGRITY1A side-by-side identity applied")
print(" - applicationId: com.particlesdevs.photoncamera.m9dngintegrity1a")
print(" - launcher label: M9Cam DNG Integrity")
print(" - APK filename prefix: M9Cam-DNGINTEGRITY1A-")
print(" - DNGGAINMAPFIX1A chained: corrected DNG GainMap rectangle ordering")
print(" - namespace/classes unchanged; current M9Cam install remains independent")
