#!/usr/bin/env python3
from pathlib import Path
import math
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: verify-m9cam-metadatafix1a.py <PhotonCamera-root>")

root = Path(sys.argv[1]).resolve()
if not (root / "app").is_dir():
    raise SystemExit(f"not a PhotonCamera root: {root}")


def text(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f"METADATAFIX1A verify missing: {rel}")
    return p.read_text()


renderer = text("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java")
image_saver = text("app/src/main/java/com/particlesdevs/photoncamera/processing/ImageSaver.java")
finalizer = text("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9JpegFinalizeQueue.java")
queue = text("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java")
gradle = text("app/build.gradle")
parse_exif = text("app/src/main/java/com/particlesdevs/photoncamera/api/ParseExif.java")

checks = {
    "M9 physical ISO marker": "METADATAFIX1A_PHYSICAL_ISO" in renderer,
    "M9 physical ISO source": "captureResult.get(CaptureResult.SENSOR_SENSITIVITY)" in renderer,
    "M9 ISO overrides PhotographicSensitivity": "exif.PHOTOGRAPHIC_SENSITIVITY" in renderer,
    "generic ParseExif still contains Photon MPY behavior": "IsoExpoSelector.getMPY()" in parse_exif,
    "M9 JPEG compression marker": "METADATAFIX1A_PRIMARY_JPEG_COMPRESSION_TAG_OMITTED" in image_saver,
    "M9 JPEG helper keeps quality argument": "img.compress(Bitmap.CompressFormat.JPEG, jpgQuality, outputStream);" in image_saver,
    "M9 finalizer marker": "METADATAFIX1A_EXIF_FINALIZE" in finalizer,
    "M9 orientation normalized": "ExifInterface.ORIENTATION_NORMAL" in finalizer,
    "DateTimeOriginal written": "ExifInterface.TAG_DATETIME_ORIGINAL" in finalizer,
    "DateTimeDigitized written": "ExifInterface.TAG_DATETIME_DIGITIZED" in finalizer,
    "Software written": "ExifInterface.TAG_SOFTWARE" in finalizer,
    "Compression removed": "inter.setAttribute(ExifInterface.TAG_COMPRESSION, null);" in finalizer,
    "APEX ApertureValue computed": "2.0 * Math.log(f) / Math.log(2.0)" in finalizer,
    "metadata diagnostics schema": "m9cam.metadata.v1a" in finalizer,
    "DNG still uses untouched saveSingleRaw path": "ImageSaver.Util.saveSingleRaw(" in queue,
    "metadata-only version suffix": "metadatafix1a" in gradle,
}

failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(("OK   " if ok else "FAIL ") + name)
if failed:
    raise SystemExit("METADATAFIX1A source verification failed: " + ", ".join(failed))

# Local semantic check for the corrected Av definition. FNumber remains 1.63 while
# ApertureValue should be log2(N^2), not another literal 1.63.
f = 1.63
av = 2.0 * math.log(f, 2.0)
if not (1.40 < av < 1.42):
    raise SystemExit(f"METADATAFIX1A APEX sanity failed: f/{f} -> Av {av}")
print(f"OK   APEX sanity f/{f:.2f} -> Av {av:.6f}")

# Guard the frozen photographic invariants that this metadata patch must not touch.
for required in [
    "public static final int JPEG_QUALITY = 95;",
    "private static final double METER_TARGET = 0.107 * (8192.0 / 10000.0);",
    "private static final double HSM_H = 0.25;",
    "private static final double TG_NEG_CB_COMPRESSION = 0.25;",
    "private static final double TG_NEG_CR_COMPRESSION = 0.16;",
    "public static final int SATURATION_BANK = 3;",
]:
    if required not in renderer:
        raise SystemExit("METADATAFIX1A photographic freeze guard missing: " + required)
print("OK   frozen JPEG/TC20/H25/TG1/SAT3 constants retained")

# Ensure the M9 helper no longer writes quality as Compression. Scope only the M9 helper.
start = image_saver.find("public static boolean saveBitmapAsJPGPayloadM9")
end = image_saver.find("public static", start + 10)
segment = image_saver[start:end if end > start else len(image_saver)]
if "exifData.COMPRESSION = String.valueOf(jpgQuality);" in segment:
    raise SystemExit("METADATAFIX1A M9 helper still writes JPEG quality into EXIF Compression")
if "exifData.COMPRESSION = null;" not in segment:
    raise SystemExit("METADATAFIX1A M9 helper does not omit primary JPEG Compression")
print("OK   M9 JPEG quality remains encoder-only, not EXIF Compression")

print("M9Cam METADATAFIX1A verification passed")
