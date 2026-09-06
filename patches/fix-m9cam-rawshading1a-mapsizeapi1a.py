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

# org.json on this Android baseline declares JSONArray.put(...) as throwing JSONException.
# These helpers are only called inside captureAndWrite's existing broad try/catch, so propagate
# the checked exception rather than swallowing diagnostics or altering any photographic path.
sample_old = '    private static JSONArray sample(float[] factors, int cols, int rows, double nx, double ny) {\n'
sample_new = '    private static JSONArray sample(float[] factors, int cols, int rows, double nx, double ny) throws Exception {\n'
if sample_old not in text:
    raise SystemExit('RAWSHADING1A MAPSIZEAPI1A sample helper anchor missing')
text = text.replace(sample_old, sample_new, 1)

float_old = '    private static JSONArray floatArray(float[] values) {\n'
float_new = '    private static JSONArray floatArray(float[] values) throws Exception {\n'
if float_old not in text:
    raise SystemExit('RAWSHADING1A MAPSIZEAPI1A floatArray helper anchor missing')
text = text.replace(float_old, float_new, 1)

if 'CameraCharacteristics.LENS_INFO_SHADING_MAP_SIZE' in text:
    raise SystemExit('RAWSHADING1A MAPSIZEAPI1A unsupported key still present')
if 'LensShadingMap.getColumnCount()/getRowCount()' not in text:
    raise SystemExit('RAWSHADING1A MAPSIZEAPI1A live-size source marker missing')
if 'private static JSONArray sample(float[] factors, int cols, int rows, double nx, double ny) throws Exception' not in text:
    raise SystemExit('RAWSHADING1A JSON exception fix missing for sample')
if 'private static JSONArray floatArray(float[] values) throws Exception' not in text:
    raise SystemExit('RAWSHADING1A JSON exception fix missing for floatArray')

p.write_text(text)
print('M9RAWSHADING1A MAPSIZEAPI1A/JSONEXCEPTION1A applied')
print(' - removed unsupported CameraCharacteristics.LENS_INFO_SHADING_MAP_SIZE reference')
print(' - live CaptureResult LensShadingMap row/column dimensions remain authoritative')
print(' - propagated checked JSONException from diagnostic JSONArray helpers')
print(' - diagnostic-only change; RAW/JPEG/TC20/DNG pixel behavior untouched')
