#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply-m9cam-metadatafix1a.py <PhotonCamera-root>")

root = Path(sys.argv[1]).resolve()
if not (root / "app").is_dir():
    raise SystemExit(f"not a PhotonCamera root: {root}")


def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f"METADATAFIX1A missing expected file: {rel}")
    return p.read_text()


def write(rel, text):
    p = root / rel
    p.write_text(text)


# -----------------------------------------------------------------------------
# 1) JPEG ISO must describe the physical Camera2 capture, not Photon's internal
#    IsoExpoSelector multiplier.  This is M9-path-only and happens after the
#    generic ParseExif.parse() call so upstream/non-M9 metadata behavior is untouched.
# -----------------------------------------------------------------------------
renderer_rel = "app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java"
renderer = read(renderer_rel)
renderer_marker = "METADATAFIX1A_PHYSICAL_ISO"
if renderer_marker not in renderer:
    anchor = "            ParseExif.ExifData exif = ParseExif.parse(captureResult, captureRequest);\n"
    if anchor not in renderer:
        raise SystemExit("METADATAFIX1A renderer anchor missing: ParseExif.parse")
    addition = r'''            // METADATAFIX1A_PHYSICAL_ISO
            // Photon's generic ParseExif.parse() multiplies SENSOR_SENSITIVITY by
            // IsoExpoSelector.getMPY().  That is useful to Photon internally but is not
            // the physical ISO that produced this M9 JPEG.  Override only the M9 copy.
            Integer m9PhysicalIso = captureResult.get(CaptureResult.SENSOR_SENSITIVITY);
            if (m9PhysicalIso != null && m9PhysicalIso > 0) {
                exif.PHOTOGRAPHIC_SENSITIVITY = String.valueOf(Math.min(65535, m9PhysicalIso));
            }
'''
    renderer = renderer.replace(anchor, anchor + addition, 1)
    write(renderer_rel, renderer)


# -----------------------------------------------------------------------------
# 2) Do not encode JPEG quality as EXIF Compression.  EXIF Compression is an enum
#    and is not a JPEG quality field; for the primary JPEG it is best omitted.
#    This changes metadata only. Bitmap.compress(..., jpgQuality, ...) is untouched.
# -----------------------------------------------------------------------------
image_saver_rel = "app/src/main/java/com/particlesdevs/photoncamera/processing/ImageSaver.java"
image_saver = read(image_saver_rel)
compression_marker = "METADATAFIX1A_PRIMARY_JPEG_COMPRESSION_TAG_OMITTED"
if compression_marker not in image_saver:
    method_pos = image_saver.find("public static boolean saveBitmapAsJPGPayloadM9")
    if method_pos < 0:
        raise SystemExit("METADATAFIX1A M9 JPEG payload helper missing")
    assignment_pos = image_saver.find("exifData.COMPRESSION = String.valueOf(jpgQuality);", method_pos)
    if assignment_pos < 0:
        raise SystemExit("METADATAFIX1A M9 JPEG compression assignment missing")
    # Make sure we did not accidentally walk into a later unrelated method.
    next_method = image_saver.find("public static", method_pos + 10)
    if next_method >= 0 and assignment_pos > next_method:
        raise SystemExit("METADATAFIX1A could not localize M9 JPEG compression assignment")
    old = "exifData.COMPRESSION = String.valueOf(jpgQuality);"
    new = "// METADATAFIX1A_PRIMARY_JPEG_COMPRESSION_TAG_OMITTED\n            exifData.COMPRESSION = null;"
    image_saver = image_saver[:assignment_pos] + image_saver[assignment_pos:].replace(old, new, 1)
    write(image_saver_rel, image_saver)


# -----------------------------------------------------------------------------
# 3) M9-only finalization audit/fix:
#      - Orientation=1 because the M9 JPEG pixels are already physically rotated.
#      - DateTime/Original/Digitized come from the capture filename where possible,
#        rather than the later asynchronous render/finalize wall clock.
#      - ApertureValue is APEX Av, not the f-number duplicated into the Av tag.
#      - Compression tag is explicitly removed from the primary JPEG.
#      - Software identifies the actual M9Cam processing path.
#    Make/Model, FNumber, FocalLength, ExposureTime and WhiteBalance remain the
#    exact values supplied by ParseExif from Camera2.
# -----------------------------------------------------------------------------
finalizer_rel = "app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9JpegFinalizeQueue.java"
finalizer = read(finalizer_rel)
finalizer_marker = "METADATAFIX1A_EXIF_FINALIZE"
if finalizer_marker not in finalizer:
    import_anchor = "import java.nio.file.Path;\n"
    if import_anchor not in finalizer:
        raise SystemExit("METADATAFIX1A finalizer import anchor missing")
    finalizer = finalizer.replace(
        import_anchor,
        import_anchor + "import java.util.Locale;\nimport java.util.regex.Matcher;\nimport java.util.regex.Pattern;\n",
        1,
    )

    static_anchor = "    private static final String TAG = \"M9JpegFinalize\";\n"
    if static_anchor not in finalizer:
        raise SystemExit("METADATAFIX1A finalizer TAG anchor missing")
    static_addition = r'''    // METADATAFIX1A_EXIF_FINALIZE
    private static final String METADATA_SCHEMA = "m9cam.metadata.v1a";
    private static final String M9_SOFTWARE = "M9Cam";
    private static final Pattern CAPTURE_NAME = Pattern.compile(
            "IMG_([0-9]{4})([0-9]{2})([0-9]{2})_([0-9]{2})([0-9]{2})([0-9]{2})_");
'''
    finalizer = finalizer.replace(static_anchor, static_anchor + static_addition, 1)

    ticket_field_anchor = "        private volatile String error;\n"
    if ticket_field_anchor not in finalizer:
        raise SystemExit("METADATAFIX1A Ticket field anchor missing")
    ticket_fields = r'''        private volatile String metadataSchema;
        private volatile String exifPhotographicSensitivity;
        private volatile String exifCaptureDateTime;
        private volatile String exifApertureValue;
        private volatile String exifSoftware;
        private volatile int exifOrientation = -1;
        private volatile boolean exifCompressionTagOmitted;
'''
    finalizer = finalizer.replace(ticket_field_anchor, ticket_field_anchor + ticket_fields, 1)

    diag_anchor = "                diag.put(\"jpegPublicationAfterExif\", true);\n"
    if diag_anchor not in finalizer:
        raise SystemExit("METADATAFIX1A diagnostic anchor missing")
    diag_addition = r'''                if (metadataSchema != null) diag.put("jpegMetadataSchema", metadataSchema);
                if (exifPhotographicSensitivity != null) diag.put("jpegExifPhotographicSensitivity", exifPhotographicSensitivity);
                if (exifCaptureDateTime != null) diag.put("jpegExifCaptureDateTime", exifCaptureDateTime);
                if (exifApertureValue != null) diag.put("jpegExifApertureValue", exifApertureValue);
                if (exifSoftware != null) diag.put("jpegExifSoftware", exifSoftware);
                if (exifOrientation >= 0) diag.put("jpegExifOrientation", exifOrientation);
                diag.put("jpegExifCompressionTagOmitted", exifCompressionTagOmitted);
'''
    finalizer = finalizer.replace(diag_anchor, diag_anchor + diag_addition, 1)

    helper_anchor = "    private static void runFinalize(Ticket ticket,\n"
    if helper_anchor not in finalizer:
        raise SystemExit("METADATAFIX1A runFinalize anchor missing")
    helpers = r'''    private static String captureDateTimeFromPath(Path jpegPath, String fallback) {
        try {
            if (jpegPath != null && jpegPath.getFileName() != null) {
                Matcher matcher = CAPTURE_NAME.matcher(jpegPath.getFileName().toString());
                if (matcher.find()) {
                    return matcher.group(1) + ":" + matcher.group(2) + ":" + matcher.group(3)
                            + " " + matcher.group(4) + ":" + matcher.group(5) + ":" + matcher.group(6);
                }
            }
        } catch (Throwable ignored) {
        }
        return fallback;
    }

    private static String apexApertureValue(String fNumber) {
        if (fNumber == null || fNumber.isEmpty()) return null;
        try {
            double f = Double.parseDouble(fNumber);
            if (!(f > 0.0) || !Double.isFinite(f)) return null;
            double av = 2.0 * Math.log(f) / Math.log(2.0);
            if (!Double.isFinite(av)) return null;
            return String.format(Locale.US, "%.6f", av);
        } catch (Throwable ignored) {
            return null;
        }
    }

'''
    finalizer = finalizer.replace(helper_anchor, helpers + helper_anchor, 1)

    finalize_anchor = (
        "            if (inter == null) throw new IllegalStateException(\"ParseExif.setAllAttributes returned null\");\n\n"
        "            stageStartedNs = System.nanoTime();\n"
    )
    if finalize_anchor not in finalizer:
        raise SystemExit("METADATAFIX1A EXIF save anchor missing")
    finalize_addition = r'''            // METADATAFIX1A_EXIF_FINALIZE: metadata-only normalization.
            String captureDateTime = captureDateTimeFromPath(jpegPath, exifData.DATETIME);
            if (captureDateTime != null && !captureDateTime.isEmpty()) {
                inter.setAttribute(ExifInterface.TAG_DATETIME, captureDateTime);
                inter.setAttribute(ExifInterface.TAG_DATETIME_ORIGINAL, captureDateTime);
                inter.setAttribute(ExifInterface.TAG_DATETIME_DIGITIZED, captureDateTime);
            }
            inter.setAttribute(ExifInterface.TAG_ORIENTATION,
                    String.valueOf(ExifInterface.ORIENTATION_NORMAL));
            // Primary JPEG compression is identified by the JPEG stream itself; do not write
            // JPEG quality (95) into the TIFF/EXIF Compression enum.
            inter.setAttribute(ExifInterface.TAG_COMPRESSION, null);
            inter.setAttribute(ExifInterface.TAG_SOFTWARE, M9_SOFTWARE);

            String apertureValue = apexApertureValue(exifData.F_NUMBER);
            if (apertureValue != null) {
                inter.setAttribute(ExifInterface.TAG_APERTURE_VALUE, apertureValue);
            }

            ticket.metadataSchema = METADATA_SCHEMA;
            ticket.exifPhotographicSensitivity = exifData.PHOTOGRAPHIC_SENSITIVITY;
            ticket.exifCaptureDateTime = captureDateTime;
            ticket.exifApertureValue = apertureValue;
            ticket.exifSoftware = M9_SOFTWARE;
            ticket.exifOrientation = ExifInterface.ORIENTATION_NORMAL;
            ticket.exifCompressionTagOmitted = true;

'''
    finalizer = finalizer.replace(
        finalize_anchor,
        "            if (inter == null) throw new IllegalStateException(\"ParseExif.setAllAttributes returned null\");\n\n"
        + finalize_addition
        + "            stageStartedNs = System.nanoTime();\n",
        1,
    )
    write(finalizer_rel, finalizer)


# -----------------------------------------------------------------------------
# 4) Distinguishable metadata-only APK identity. Earlier verifiers have already run
#    before this patch, so suffixing at the end cannot disturb the frozen chain.
# -----------------------------------------------------------------------------
gradle_rel = "app/build.gradle"
gradle = read(gradle_rel)
if "metadatafix1a" not in gradle:
    version_re = re.compile(r"(versionName\s+['\"])([^'\"]+)(['\"])")
    match = version_re.search(gradle)
    if not match:
        raise SystemExit("METADATAFIX1A versionName anchor missing")
    value = match.group(2)
    new_value = value + "-metadatafix1a"
    gradle = gradle[:match.start(2)] + new_value + gradle[match.end(2):]
    write(gradle_rel, gradle)

print("M9Cam METADATAFIX1A applied")
print(" - JPEG PhotographicSensitivity forced to physical CaptureResult SENSOR_SENSITIVITY")
print(" - primary JPEG Compression tag omitted; JPEG quality/pixels untouched")
print(" - Orientation normalized for already-rotated M9 JPEG pixels")
print(" - DateTimeOriginal/Digitized recovered from capture filename when available")
print(" - ApertureValue corrected to APEX Av while FNumber remains physical f-number")
print(" - DNG path/capture/render/TC20/color stages untouched")
