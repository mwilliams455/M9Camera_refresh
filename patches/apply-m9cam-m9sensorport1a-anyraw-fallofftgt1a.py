#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m9sensorport1a-anyraw-fallofftgt1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
repo = Path(__file__).resolve().parents[1]
if not (root / 'app').is_dir():
    raise SystemExit('M9SENSORPORT1A: not a PhotonCamera root')

renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
preview = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
image_frame = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/ImageFrame.java'
saver = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/SaverImplementation.java'
gradle = root / 'app/build.gradle'
for p in (renderer, preview, image_frame, saver):
    if not p.exists():
        raise SystemExit('M9SENSORPORT1A missing assembled file: ' + str(p))

payload_rel = Path('app/src/main/java/com/particlesdevs/photoncamera/m9/render')
payload_root = repo / 'payload' / payload_rel
target_root = root / payload_rel
for name in ('M9SensorDescriptor1A.java', 'M9TargetFalloff1A.java'):
    src = payload_root / name
    if not src.exists():
        raise SystemExit('M9SENSORPORT1A missing payload: ' + str(src))
    target_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, target_root / name)

def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'M9SENSORPORT1A {label}: expected 1 anchor, found {count}')
    return text.replace(old, new, 1)

# Preserve original Camera2 Image/plane geometry on still capture ImageFrame.
s = image_frame.read_text()
if 'm9SourceImageFormat' not in s:
    s = replace_once(
        s,
        '    public IsoExpoSelector.ExpoPair pair;\n',
        '''    public IsoExpoSelector.ExpoPair pair;

    // M9SENSORPORT1A: original Camera2 RAW acquisition/copy facts.
    // Descriptive only; no pixel path consumes these values in 1A.
    public int m9SourceImageFormat = -1;
    public int m9SourceImageWidth = -1;
    public int m9SourceImageHeight = -1;
    public int m9SourceRowStrideBytes = -1;
    public int m9SourcePixelStrideBytes = -1;
    public int m9SourceCopyOffsetBytes = -1;
    public int m9SourceCopyCapacityBytes = -1;
    public int m9SourcePlaneCapacityBytes = -1;
    public boolean m9SourceAspect169Requested = false;
    public boolean m9SourceBinningRequested = false;
''',
        'ImageFrame provenance fields')
    image_frame.write_text(s)

s = saver.read_text()
if 'frame.m9SourceImageFormat = image.getFormat();' not in s:
    s = replace_once(
        s,
        '        ImageFrame frame = new ImageFrame(image.getPlanes()[0].getBuffer(), image.getFormat(), width, image.getPlanes()[0].getRowStride(), offset, capacity);\n        frame.timestamp = image.getTimestamp();\n',
        '''        ImageFrame frame = new ImageFrame(image.getPlanes()[0].getBuffer(), image.getFormat(), width, image.getPlanes()[0].getRowStride(), offset, capacity);
        // M9SENSORPORT1A: retain original RAW plane geometry for the generic source descriptor.
        frame.m9SourceImageFormat = image.getFormat();
        frame.m9SourceImageWidth = image.getWidth();
        frame.m9SourceImageHeight = image.getHeight();
        frame.m9SourceRowStrideBytes = image.getPlanes()[0].getRowStride();
        frame.m9SourcePixelStrideBytes = image.getPlanes()[0].getPixelStride();
        frame.m9SourceCopyOffsetBytes = offset;
        frame.m9SourceCopyCapacityBytes = capacity;
        frame.m9SourcePlaneCapacityBytes = image.getPlanes()[0].getBuffer().capacity();
        frame.m9SourceAspect169Requested = PhotonCamera.getSettings().aspect169;
        frame.m9SourceBinningRequested = PhotonCamera.getSettings().binning;
        frame.timestamp = image.getTimestamp();
''',
        'SaverImplementation provenance capture')
    saver.write_text(s)

# Preview path: describe the ORIGINAL full-resolution RAW before reduction.
p = preview.read_text()
if 'M9SensorDescriptor1A' not in p:
    p = replace_once(
        p,
        'import com.particlesdevs.photoncamera.m9.render.M9R35Renderer;\n',
        'import com.particlesdevs.photoncamera.m9.render.M9R35Renderer;\n'
        'import com.particlesdevs.photoncamera.m9.render.M9SensorDescriptor1A;\n',
        'preview descriptor import')
    p = replace_once(
        p,
        'import com.particlesdevs.photoncamera.util.Log;\n',
        'import com.particlesdevs.photoncamera.util.Log;\n\nimport org.json.JSONObject;\n',
        'preview JSONObject import')

    dim_anchor = '''        final int dstW = srcW >= srcH ? LANDSCAPE_WIDTH : LANDSCAPE_HEIGHT;
        final int dstH = srcW >= srcH ? LANDSCAPE_HEIGHT : LANDSCAPE_WIDTH;
'''
    dim_insert = dim_anchor + '''        final JSONObject sourceDescriptor1A = M9SensorDescriptor1A.fromPreviewImage(
                raw, characteristics, captureResult, captureRequest, dstW, dstH).toJson();
'''
    p = replace_once(p, dim_anchor, dim_insert, 'preview original-RAW descriptor')

    call_old = '''        Bitmap out = M9R35Renderer.renderLivePreview1A(
                packed, dstW, dstH, characteristics, captureResult, captureRequest, cameraRotation);
'''
    call_new = '''        Bitmap out = M9R35Renderer.renderLivePreview1A(
                packed, dstW, dstH, characteristics, captureResult, captureRequest,
                sourceDescriptor1A, cameraRotation);
'''
    p = replace_once(p, call_old, call_new, 'preview renderer call')
    preview.write_text(p)

# Renderer: keep the full-source preview descriptor beside the synthetic reduced frame.
r = renderer.read_text()
if 'M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR' not in r:
    r = replace_once(
        r,
        '    private static final ThreadLocal<Bitmap> M9_LIVE_PREVIEW_1A_BITMAP = new ThreadLocal<>();\n',
        '    private static final ThreadLocal<Bitmap> M9_LIVE_PREVIEW_1A_BITMAP = new ThreadLocal<>();\n'
        '    private static final ThreadLocal<JSONObject> M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR = new ThreadLocal<>();\n',
        'preview descriptor ThreadLocal')

    sig_old = '''    public static Bitmap renderLivePreview1A(ByteBuffer packedRaw,
                                             int width,
                                             int height,
                                             CameraCharacteristics characteristics,
                                             CaptureResult captureResult,
                                             CaptureRequest captureRequest,
                                             int cameraRotation) throws Exception {
'''
    sig_new = '''    public static Bitmap renderLivePreview1A(ByteBuffer packedRaw,
                                             int width,
                                             int height,
                                             CameraCharacteristics characteristics,
                                             CaptureResult captureResult,
                                             CaptureRequest captureRequest,
                                             JSONObject sourceDescriptor1A,
                                             int cameraRotation) throws Exception {
'''
    r = replace_once(r, sig_old, sig_new, 'preview renderer signature')

    set_anchor = '''        M9_LIVE_PREVIEW_1A_ACTIVE.set(Boolean.TRUE);
        M9_LIVE_PREVIEW_1A_BITMAP.remove();
'''
    set_new = '''        M9_LIVE_PREVIEW_1A_ACTIVE.set(Boolean.TRUE);
        M9_LIVE_PREVIEW_1A_BITMAP.remove();
        M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR.set(sourceDescriptor1A);
'''
    r = replace_once(r, set_anchor, set_new, 'preview descriptor set')

    diag_anchor = '''                    previewDiag.put("m9LivePreviewNoFileSideEffects", true);
'''
    diag_new = '''                    previewDiag.put("m9LivePreviewNoFileSideEffects", true);
                    previewDiag.put("sensorDescriptor1A", M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR.get());
                    previewDiag.put("targetFalloff1A", M9TargetFalloff1A.describe());
                    previewDiag.put("sourceGeometryAuthority",
                            "original_full_resolution_RAW_descriptor_retained_before_preview_reduction");
'''
    r = replace_once(r, diag_anchor, diag_new, 'preview descriptor diagnostics')

    cleanup_anchor = '''            M9_LIVE_PREVIEW_1A_BITMAP.remove();
            M9_LIVE_PREVIEW_1A_ACTIVE.remove();
'''
    cleanup_new = '''            M9_LIVE_PREVIEW_1A_BITMAP.remove();
            M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR.remove();
            M9_LIVE_PREVIEW_1A_ACTIVE.remove();
'''
    r = replace_once(r, cleanup_anchor, cleanup_new, 'preview descriptor cleanup')

# Attach source descriptor to the normal still path without touching native render math.
if 'stillSensorDescriptor1A' not in r:
    call_token = '            RenderCore out = renderNativeSourceProduction1P(\n'
    start = r.find(call_token)
    if start < 0:
        raise SystemExit('M9SENSORPORT1A still render call anchor missing')
    semi = r.find(';', start)
    if semi < 0:
        raise SystemExit('M9SENSORPORT1A still render call terminator missing')
    insertion = '''
            JSONObject stillSensorDescriptor1A = M9SensorDescriptor1A.fromImageFrame(
                    frame, params, characteristics, diagnosticCaptureResult1A, captureRequest).toJson();
            out.diagnostics.put("sensorDescriptor1A", stillSensorDescriptor1A);
            out.diagnostics.put("targetFalloff1A", M9TargetFalloff1A.describe());
            out.diagnostics.put("targetFalloffPixelMutationEnabled", false);
            out.diagnostics.put("sourceShadingAndTargetFalloffSeparatedArchitecturally", true);
'''
    r = r[:semi + 1] + insertion + r[semi + 1:]

renderer.write_text(r)

if gradle.exists():
    g = gradle.read_text()
    m = re.search(r'versionName\s+["\']([^"\']+)["\']', g)
    if m and 'm9sensorport1a' not in m.group(1).lower():
        old = m.group(0)
        quote = '"' if '"' in old else "'"
        g = g.replace(old, 'versionName ' + quote + m.group(1)
                      + '-m9sensorport1a-anyraw-fallofftgt1a' + quote, 1)
        gradle.write_text(g)

print('M9SENSORPORT1A_ANYRAW_FALLOFFTGT1A applied')
print(' - original RAW acquisition geometry retained for still and preview descriptors')
print(' - preview keeps original full-resolution source descriptor before 1440x1080 reduction')
print(' - camera/manufacturer/focal labels are provenance only, never M9 look selectors')
print(' - normalized M9 target-falloff coordinate/model contract installed')
print(' - target falloff coefficients intentionally uncalibrated; pixel gain remains identity')
print(' - native M9 photographic core untouched')
