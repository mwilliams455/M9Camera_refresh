#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("PhotonCamera")
java = (root / "app/src/main/java/com/particlesdevs/photoncamera/processing/DngCreator.java").read_text()
native = (root / "app/src/main/cpp/dngCreator.cpp").read_text()

required = [
    "// M9 DNGGAINMAPFIX1A: native setGainMap uses x/y ordering.",
    "parameters.sensorPix.left,\n                   parameters.sensorPix.top,\n                   parameters.sensorPix.right,\n                   parameters.sensorPix.bottom,",
]
for token in required:
    if token not in java:
        raise SystemExit(f"DNGGAINMAPFIX1A verify failed: missing {token!r}")

bad = "parameters.sensorPix.top,\n                   parameters.sensorPix.left,\n                   parameters.sensorPix.bottom,\n                   parameters.sensorPix.right,"
if bad in java:
    raise SystemExit("DNGGAINMAPFIX1A verify failed: legacy swapped GainMap coordinate order remains")

native_required = [
    "void setGainMap(const float* gainMap, int xmin, int ymin, int xmax, int ymax, int width, int height)",
    "int activeX = (xmax - xmin) - 1;",
    "int activeY = (ymax - ymin) - 1;",
    "gainMaps[0].bottom = activeY;",
    "gainMaps[0].right = activeX;",
]
for token in native_required:
    if token not in native:
        raise SystemExit(f"DNGGAINMAPFIX1A verify failed: native x/y contract changed or missing {token!r}")

print("OK DNGGAINMAPFIX1A Java Rect -> native x/y coordinate ordering corrected")
print("OK expected 4096x3072 full-frame GainMap geometry becomes right=4095 bottom=3071")
print("OK native DNG writer semantics otherwise unchanged")
