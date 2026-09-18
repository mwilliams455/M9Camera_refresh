#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m9livewysiwyg1d-meter1600.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
preview = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
controller = root / 'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
selector = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
gradle = root / 'app/build.gradle'
for p in (preview, renderer, controller, selector, gradle):
    if not p.exists():
        raise SystemExit('M9LIVEWYSIWYG1D missing assembled file: ' + str(p))

def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'M9LIVEWYSIWYG1D {label}: expected 1 anchor, found {n}')
    return text.replace(old, new, 1)

def method_span(text, signature):
    start = text.find(signature)
    if start < 0:
        raise SystemExit('M9LIVEWYSIWYG1D method missing: ' + signature)
    brace = text.find('{', start)
    if brace < 0:
        raise SystemExit('M9LIVEWYSIWYG1D opening brace missing: ' + signature)
    depth = 0
    state = 'code'
    quote = ''
    esc = False
    i = brace
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ''
        if state == 'line':
            if ch == '\n': state = 'code'
        elif state == 'block':
            if ch == '*' and nxt == '/': state = 'code'; i += 1
        elif state == 'string':
            if esc: esc = False
            elif ch == '\\': esc = True
            elif ch == quote: state = 'code'
        else:
            if ch == '/' and nxt == '/': state = 'line'; i += 1
            elif ch == '/' and nxt == '*': state = 'block'; i += 1
            elif ch in ('"', "'"): state = 'string'; quote = ch
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: return start, i + 1
        i += 1
    raise SystemExit('M9LIVEWYSIWYG1D unterminated method: ' + signature)

# 1C correctness architecture + 1B exact displayed-exposure lock are required.
p = preview.read_text()
r = renderer.read_text()
c = controller.read_text()
s = selector.read_text()
for marker in (
        'M9LIVEWYSIWYG1C_FULLSOURCE_FINALBOUNDARY',
        'packFullRawPreservingSamples1C(raw)',
        'FULL_PRODUCTION_RENDER_FULL_SOURCE_FINAL_BITMAP'):
    if marker not in p and marker not in r:
        raise SystemExit('M9LIVEWYSIWYG1D requires 1C baseline marker: ' + marker)
for marker in (
        'M9LIVEWYSIWYG1B_DISPLAYEDCAPTURELOCK',
        'm9LiveWysiwygDisplayedIso1B',
        'm9LiveWysiwygDisplayedExposureNs1B'):
    if marker not in c:
        raise SystemExit('M9LIVEWYSIWYG1D requires 1B controller marker: ' + marker)
if 'setExactExposureM9Wysiwyg1B(' not in s:
    raise SystemExit('M9LIVEWYSIWYG1D requires exact 1B exposure setter')

# ---------------------------------------------------------------------------
# Preview source: reduce only to TC20's own 1600-long-side reference before the shared
# production renderer. Everything photographic still runs; only spatial workload changes.
# ---------------------------------------------------------------------------
p = replace_once(
    p,
    'public static final int LANDSCAPE_WIDTH = 1440;',
    'public static final int LANDSCAPE_WIDTH = 1600;',
    'preview width')
p = replace_once(
    p,
    'public static final int LANDSCAPE_HEIGHT = 1080;',
    'public static final int LANDSCAPE_HEIGHT = 1200;',
    'preview height')
p = replace_once(
    p,
    '    public static final String MODE_1C = "M9LIVEWYSIWYG1C_FULLSOURCE_FINALBOUNDARY";',
    '    public static final String MODE_1C = "M9LIVEWYSIWYG1C_FULLSOURCE_FINALBOUNDARY";\n'
    '    public static final String MODE_1D = "M9LIVEWYSIWYG1D_METER1600_REFERENCE_RENDER";',
    '1D mode marker')

rs, re_ = method_span(p, '    public static Bitmap render(Image raw,')
new_render = r'''    /**
     * M9LIVEWYSIWYG1D_METER1600_REFERENCE_RENDER
     *
     * Correctness architecture from 1C is preserved: exact current exposure, the same production
     * M9 renderer, the same live scene evidence and the same final edge-placement boundary.
     *
     * Performance change only: the Bayer image is reduced to TC20's own 1600-pixel-long-side
     * reference before demosaic/full-colour rendering. This avoids a 4096x3072 production render
     * for every viewfinder refresh while keeping every M9 photographic stage active.
     */
    public static Bitmap render(Image raw,
                                CameraCharacteristics characteristics,
                                CaptureResult captureResult,
                                CaptureRequest captureRequest,
                                int cameraRotation) throws Exception {
        if (raw == null || raw.getFormat() != ImageFormat.RAW_SENSOR) {
            throw new IllegalArgumentException("M9LIVEWYSIWYG1D requires RAW_SENSOR image");
        }
        final int srcW = raw.getWidth();
        final int srcH = raw.getHeight();
        final int targetW = srcW >= srcH ? LANDSCAPE_WIDTH : LANDSCAPE_HEIGHT;
        final int targetH = srcW >= srcH ? LANDSCAPE_HEIGHT : LANDSCAPE_WIDTH;
        final boolean reduce = srcW > targetW || srcH > targetH;
        final int renderW = reduce ? targetW : srcW;
        final int renderH = reduce ? targetH : srcH;

        long started = System.nanoTime();
        final JSONObject sourceDescriptor1A = M9SensorDescriptor1A.fromPreviewImage(
                raw, characteristics, captureResult, captureRequest, renderW, renderH).toJson();
        ByteBuffer packed = reduce
                ? reduceBayerMeterReference1600PreservingParity1D(raw, renderW, renderH)
                : packFullRawPreservingSamples1C(raw);
        long packedAt = System.nanoTime();
        Bitmap out = M9R35Renderer.renderLivePreview1A(
                packed, renderW, renderH, characteristics, captureResult, captureRequest,
                sourceDescriptor1A, cameraRotation);
        long finished = System.nanoTime();
        Log.d(TAG, "M9LIVEWYSIWYG1D METER1600 raw=" + srcW + "x" + srcH
                + " renderInput=" + renderW + "x" + renderH
                + " tc20ReferenceLongSide=1600"
                + " preRenderReferenceReduction=" + reduce
                + " reduceOrPackMs=" + ((packedAt - started) / 1_000_000.0)
                + " renderMs=" + ((finished - packedAt) / 1_000_000.0));
        return out;
    }'''
p = p[:rs] + new_render + p[re_:]

# Add the bounded reference reducer before the existing exact full-source packer.
insert = p.find('    /** 1:1 RAW plane copy.')
if insert < 0:
    raise SystemExit('M9LIVEWYSIWYG1D full-source packer anchor missing')
reducer = r'''    /**
     * CFA-parity-preserving four-sample area proxy at TC20's native 1600-long-side reference.
     * This changes spatial sampling only; it does not alter ISO/shutter, WB, tone, colour,
     * saturation bank, curve, shading/falloff policy or final edge-placement processing.
     */
    private static ByteBuffer reduceBayerMeterReference1600PreservingParity1D(
            Image raw, int dstW, int dstH) {
        if ((dstW & 1) != 0 || (dstH & 1) != 0) {
            throw new IllegalArgumentException("M9LIVEWYSIWYG1D target Bayer dimensions must be even");
        }
        Image.Plane[] planes = raw.getPlanes();
        if (planes == null || planes.length < 1) {
            throw new IllegalArgumentException("M9LIVEWYSIWYG1D RAW has no plane");
        }
        Image.Plane plane = planes[0];
        ByteBuffer src = plane.getBuffer().duplicate().order(ByteOrder.LITTLE_ENDIAN);
        final int srcW = raw.getWidth();
        final int srcH = raw.getHeight();
        final int rowStride = plane.getRowStride();
        final int pixelStride = plane.getPixelStride();
        if (pixelStride < 2 || rowStride <= 0) {
            throw new IllegalArgumentException("M9LIVEWYSIWYG1D unsupported RAW stride row="
                    + rowStride + " pixel=" + pixelStride);
        }

        ByteBuffer out = ByteBuffer.allocateDirect(Math.multiplyExact(Math.multiplyExact(dstW, dstH), 2))
                .order(ByteOrder.LITTLE_ENDIAN);
        final double sxScale = srcW / (double)dstW;
        final double syScale = srcH / (double)dstH;

        for (int y = 0; y < dstH; y++) {
            final int parityY = y & 1;
            int cy = sameParityNear1D((int)Math.floor((y + 0.5) * syScale), parityY, srcH);
            int y0 = sameParityNear1D(cy - 2, parityY, srcH);
            int y1 = sameParityNear1D(cy + 2, parityY, srcH);
            final int row0 = y0 * rowStride;
            final int row1 = y1 * rowStride;
            for (int x = 0; x < dstW; x++) {
                final int parityX = x & 1;
                int cx = sameParityNear1D((int)Math.floor((x + 0.5) * sxScale), parityX, srcW);
                int x0 = sameParityNear1D(cx - 2, parityX, srcW);
                int x1 = sameParityNear1D(cx + 2, parityX, srcW);
                int a = u16At1D(src, row0 + x0 * pixelStride);
                int b = u16At1D(src, row0 + x1 * pixelStride);
                int cc = u16At1D(src, row1 + x0 * pixelStride);
                int d = u16At1D(src, row1 + x1 * pixelStride);
                out.putShort((short)(((a + b + cc + d + 2) >> 2) & 0xffff));
            }
        }
        out.flip();
        return out;
    }

    private static int u16At1D(ByteBuffer src, int off) {
        if (off < 0 || off + 1 >= src.capacity()) {
            throw new IllegalArgumentException("M9LIVEWYSIWYG1D RAW sample out of bounds");
        }
        return src.getShort(off) & 0xffff;
    }

    private static int sameParityNear1D(int candidate, int parity, int limit) {
        if (limit < 2) return 0;
        int v = Math.max(0, Math.min(limit - 1, candidate));
        if ((v & 1) != parity) {
            if (v + 1 < limit) v++;
            else if (v - 1 >= 0) v--;
        }
        if ((v & 1) != parity) {
            throw new IllegalArgumentException("M9LIVEWYSIWYG1D cannot preserve CFA parity");
        }
        return v;
    }

'''
p = p[:insert] + reducer + p[insert:]
preview.write_text(p)

# ---------------------------------------------------------------------------
# Renderer diagnostics/display transport: 1600x1200 is already the display/render reference,
# so do not create a second 1440 bitmap. Final edge-placement boundary remains unchanged.
# ---------------------------------------------------------------------------
r = renderer.read_text()
r = replace_once(r, 'final int maxLandscapeW1C = 1440;',
                 'final int maxLandscapeW1C = 1600;', 'post-render max width')
r = replace_once(r, 'final int maxLandscapeH1C = 1080;',
                 'final int maxLandscapeH1C = 1200;', 'post-render max height')
r = replace_once(r,
                 '"FULL_PRODUCTION_RENDER_FULL_SOURCE_FINAL_BITMAP"',
                 '"FULL_PRODUCTION_RENDER_REFERENCE1600_FINAL_BITMAP"',
                 'preview mode')
r = replace_once(r,
                 'previewDiag.put("preRenderSourceReduction", false);',
                 'previewDiag.put("preRenderSourceReduction", true);\n'
                 '                    previewDiag.put("preRenderReductionRole",\n'
                 '                            "TC20_1600_long_side_reference_spatial_workload_only");\n'
                 '                    previewDiag.put("tc20ReferenceLongSide", 1600);',
                 'reduction diagnostic')
r = replace_once(r,
                 'previewDiag.put("fullSourceRawWidth", frame.width);\n'
                 '                    previewDiag.put("fullSourceRawHeight", frame.height);',
                 'previewDiag.put("fullSourceRawWidth",\n'
                 '                            M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR.get() != null\n'
                 '                                    ? M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR.get().optInt("rawWidth", -1) : -1);\n'
                 '                    previewDiag.put("fullSourceRawHeight",\n'
                 '                            M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR.get() != null\n'
                 '                                    ? M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR.get().optInt("rawHeight", -1) : -1);',
                 'full-source descriptor dimensions')
r = replace_once(r,
                 'previewDiag.put("postRenderDisplayDownscaleOnly", true);',
                 'previewDiag.put("postRenderDisplayDownscaleOnly", false);\n'
                 '                    previewDiag.put("allM9PhotographicStagesAppliedAtReferenceResolution", true);',
                 'scale diagnostic')
r = replace_once(r,
                 '"full_resolution_RAW_is_renderer_input_no_pre_render_reduction"',
                 '"original_full_RAW_descriptor_retained_reference1600_is_renderer_input"',
                 'source geometry diagnostic')
renderer.write_text(r)

# Distinct build identity. Controller/exposure lock are deliberately untouched.
g = gradle.read_text()
m = re.search(r'versionName\s+["\']([^"\']+)["\']', g)
if not m:
    raise SystemExit('M9LIVEWYSIWYG1D versionName missing')
if 'm9livewysiwyg1d' not in m.group(1).lower():
    old = m.group(0)
    quote = '"' if '"' in old else "'"
    g = g.replace(old, 'versionName ' + quote + m.group(1)
                  + '-m9livewysiwyg1d-meter1600' + quote, 1)
    gradle.write_text(g)

print('M9LIVEWYSIWYG1D_METER1600_REFERENCE_RENDER applied')
print(' - live Bayer render workload reduced to 1600x1200 / 1200x1600')
print(' - 4096x3072 main-camera pixel workload reduced by ~6.55x')
print(' - TC20 reference long side remains 1600')
print(' - full M9 production stages remain active, including final edge-placement')
print(' - original full RAW descriptor retained for source geometry/shading/falloff mapping')
print(' - no second 1440 post-render bitmap allocation for normal 4:3 preview')
print(' - LIVEWYSIWYG1B exact displayed ISO/shutter capture lock untouched')
