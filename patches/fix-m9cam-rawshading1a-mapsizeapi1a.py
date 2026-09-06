#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: fix-m9cam-rawshading1a-mapsizeapi1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RawShadingAudit1A.java'
p = root / rel
if not p.exists():
    raise SystemExit('RAWSHADING1A MAPSIZEAPI1A missing audit helper')
text = p.read_text()

old = '''            Size advertisedMapSize = characteristics != null
                    ? characteristics.get(CameraCharacteristics.LENS_INFO_SHADING_MAP_SIZE) : null;
            out.put("activeArray", rectJson(active));
            out.put("preCorrectionActiveArray", rectJson(preCorrection));
            if (advertisedMapSize != null) {
                JSONObject s = new JSONObject();
                s.put("width", advertisedMapSize.getWidth());
                s.put("height", advertisedMapSize.getHeight());
                out.put("advertisedShadingMapSize", s);
            } else {
                out.put("advertisedShadingMapSize", JSONObject.NULL);
            }
'''
new = '''            out.put("activeArray", rectJson(active));
            out.put("preCorrectionActiveArray", rectJson(preCorrection));
            // Android CameraCharacteristics does not expose a LENS_INFO_SHADING_MAP_SIZE key.
            // The authoritative dimensions for the map delivered for this capture come from
            // LensShadingMap.getColumnCount()/getRowCount() below. Keep this explicit so the
            // audit cannot silently substitute a guessed/static sensor map geometry.
            out.put("advertisedShadingMapSize", JSONObject.NULL);
            out.put("advertisedShadingMapSizeSource",
                    "not_exposed_by_CameraCharacteristics_use_live_CaptureResult_LensShadingMap_dimensions");
'''
if old not in text:
    raise SystemExit('RAWSHADING1A MAPSIZEAPI1A expected unsupported key block missing')
text = text.replace(old, new, 1)
text = text.replace('import android.util.Size;\n', '', 1)

if 'CameraCharacteristics.LENS_INFO_SHADING_MAP_SIZE' in text:
    raise SystemExit('RAWSHADING1A MAPSIZEAPI1A unsupported key still present')
if 'LensShadingMap.getColumnCount()/getRowCount()' not in text:
    raise SystemExit('RAWSHADING1A MAPSIZEAPI1A live-size source marker missing')

p.write_text(text)
print('M9RAWSHADING1A MAPSIZEAPI1A applied')
print(' - removed unsupported CameraCharacteristics.LENS_INFO_SHADING_MAP_SIZE reference')
print(' - live CaptureResult LensShadingMap row/column dimensions remain authoritative')
print(' - diagnostic-only change; RAW/JPEG/TC20/DNG pixel behavior untouched')
