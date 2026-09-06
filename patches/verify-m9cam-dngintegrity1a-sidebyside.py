#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: verify-m9cam-dngintegrity1a-sidebyside.py <PhotonCamera-root>")

root = Path(sys.argv[1]).resolve()
checks = {
    "app/build.gradle": [
        "applicationId 'com.particlesdevs.photoncamera.m9dngintegrity1a'",
        'outputFileName = "M9Cam-DNGINTEGRITY1A-${versionName}${versionBuild}-${variant.name}.apk"',
        "namespace 'com.particlesdevs.photoncamera'",
    ],
    "app/src/main/res/values/strings.xml": [
        '<string name="app_name" translatable="false">M9Cam DNG Integrity</string>',
    ],
    "app/src/main/AndroidManifest.xml": [
        'android:authorities="${applicationId}.provider"',
    ],
}

for rel, needles in checks.items():
    p = root / rel
    if not p.exists():
        raise SystemExit(f"FAIL missing {rel}")
    text = p.read_text()
    for needle in needles:
        if needle not in text:
            raise SystemExit(f"FAIL {rel}: missing {needle!r}")
        print(f"OK   {rel}: {needle}")

# Verify the DNG metadata coordinate repair chained by the side-by-side patch.
gainmap_verify = Path(__file__).with_name("verify-m9cam-dnggainmapfix1a.py")
subprocess.run([sys.executable, str(gainmap_verify), str(root)], check=True)

print("DNGINTEGRITY1A side-by-side verifier PASS")
print("Current M9Cam and M9Cam DNG Integrity use distinct application IDs and may coexist.")
print("DNG GainMap x/y rectangle ordering is corrected in this diagnostic APK only.")
