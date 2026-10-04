#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("PhotonCamera")
path = root / "app/src/main/java/com/particlesdevs/photoncamera/processing/DngCreator.java"
text = path.read_text()

old = '''        setGainMap(parameters.gainMap,\n                   parameters.sensorPix.top,\n                   parameters.sensorPix.left,\n                   parameters.sensorPix.bottom,\n                   parameters.sensorPix.right,\n                   parameters.mapSize.x,\n                   parameters.mapSize.y);'''
new = '''        // M9 DNGGAINMAPFIX1A: native setGainMap uses x/y ordering.\n        // Rect is Android top/left/bottom/right, so pass left/top/right/bottom.\n        setGainMap(parameters.gainMap,\n                   parameters.sensorPix.left,\n                   parameters.sensorPix.top,\n                   parameters.sensorPix.right,\n                   parameters.sensorPix.bottom,\n                   parameters.mapSize.x,\n                   parameters.mapSize.y);'''

if new in text:
    print("DNGGAINMAPFIX1A already applied")
    raise SystemExit(0)

count = text.count(old)
if count != 1:
    raise SystemExit(f"DNGGAINMAPFIX1A anchor count {count}, expected 1")

path.write_text(text.replace(old, new, 1))
print("Applied M9 DNGGAINMAPFIX1A")
print(" - DNG GainMap rect coordinates corrected from top/left/bottom/right to x/y left/top/right/bottom")
print(" - RAW bytes, exposure, JPEG renderer, TC20, LIVE1 and async DNG ownership unchanged")
