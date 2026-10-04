#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m9livepreview1a-fullrender720p.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
controller = root / 'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
layout = root / 'app/src/main/res/layout/layout_main_viewfinder.xml'
gradle = root / 'app/build.gradle'
preview_java = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
for p in (renderer, controller, layout):
    if not p.exists():
        raise SystemExit('M9LIVEPREVIEW1A missing required file: ' + str(p))


def method_span(text: str, signature: str):
    start = text.find(signature)
    if start < 0:
        raise SystemExit('M9LIVEPREVIEW1A method missing: ' + signature)
    brace = text.find('{', start)
    if brace < 0:
        raise SystemExit('M9LIVEPREVIEW1A opening brace missing: ' + signature)
    depth = 0
    state = 'code'
    quote = ''
    escape = False
    i = brace
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ''
        if state == 'line':
            if ch == '\n': state = 'code'
        elif state == 'block':
            if ch == '*' and nxt == '/': state = 'code'; i += 1
        elif state == 'string':
            if escape: escape = False
            elif ch == '\\': escape = True
            elif ch == quote: state = 'code'
        else:
            if ch == '/' and nxt == '/': state = 'line'; i += 1
            elif ch == '/' and nxt == '*': state = 'block'; i += 1
            elif ch in ('"', "'"): state = 'string'; quote = ch; escape = False
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: return start, i + 1
        i += 1
    raise SystemExit('M9LIVEPREVIEW1A unterminated method: ' + signature)

# Add a preview-only entry around the exact primary renderer. The normal shutter path
# never sets the thread-local and remains unchanged.
s = renderer.read_text()
for marker in ('M9SENSORTARGET1A', 'm9cam.tonebound.v1a.050ev', 'SAT2_M04_M05'):
    if marker not in s:
        raise SystemExit('M9LIVEPREVIEW1A requires baseline marker: ' + marker)
if 'M9LIVEPREVIEW1A_FULLRENDER720P' in s:
    raise SystemExit('M9LIVEPREVIEW1A already applied to renderer')

field_anchor = '    private static volatile JSONObject lastDiagnostics = new JSONObject();\n'
if s.count(field_anchor) != 1:
    raise SystemExit('M9LIVEPREVIEW1A lastDiagnostics anchor count=' + str(s.count(field_anchor)))
s = s.replace(field_anchor, field_anchor + '''\n    // M9LIVEPREVIEW1A_FULLRENDER720P: active only on the viewfinder worker.\n    private static final ThreadLocal<Boolean> M9_LIVE_PREVIEW_1A_ACTIVE = new ThreadLocal<>();\n    private static final ThreadLocal<Bitmap> M9_LIVE_PREVIEW_1A_BITMAP = new ThreadLocal<>();\n''', 1)

wrapper_anchor = '    private static Result renderAndSaveInternal('
insert_at = s.find(wrapper_anchor)
if insert_at < 0:
    raise SystemExit('M9LIVEPREVIEW1A renderAndSaveInternal anchor missing')
wrapper = r'''    /** M9LIVEPREVIEW1A_FULLRENDER720P: exact primary pipeline, no file side effects. */
    public static Bitmap renderLivePreview1A(ByteBuffer packedRaw,
                                             int width,
                                             int height,
                                             CameraCharacteristics characteristics,
                                             CaptureResult captureResult,
                                             CaptureRequest captureRequest,
                                             int cameraRotation) throws Exception {
        if (packedRaw == null) throw new IllegalArgumentException("M9LIVEPREVIEW1A missing packed RAW");
        if (characteristics == null || captureResult == null || captureRequest == null) {
            throw new IllegalArgumentException("M9LIVEPREVIEW1A missing Camera2 metadata");
        }
        ImageFrame frame = new ImageFrame(packedRaw);
        frame.width = width;
        frame.height = height;
        M9_LIVE_PREVIEW_1A_ACTIVE.set(Boolean.TRUE);
        M9_LIVE_PREVIEW_1A_BITMAP.remove();
        try {
            Path synthetic = Paths.get(FileManager.sDCIM_CAMERA.getAbsolutePath(),
                    "M9LIVEPREVIEW1A_PREVIEW_ONLY.dng");
            Result r = renderAndSaveInternal(synthetic, frame, characteristics,
                    captureResult, captureRequest, cameraRotation, true);
            Bitmap out = M9_LIVE_PREVIEW_1A_BITMAP.get();
            if (!r.success || out == null) {
                throw new IllegalStateException("M9LIVEPREVIEW1A production preview render failed: " + r.error);
            }
            return out;
        } finally {
            M9_LIVE_PREVIEW_1A_BITMAP.remove();
            M9_LIVE_PREVIEW_1A_ACTIVE.remove();
            frame.close();
        }
    }

'''
s = s[:insert_at] + wrapper + s[insert_at:]

rs, re_ = method_span(s, 'private static Result renderAndSaveInternal(')
method = s[rs:re_]
bitmap_anchor = '            bitmap = out.bitmap;\n'
if method.count(bitmap_anchor) != 1:
    raise SystemExit('M9LIVEPREVIEW1A bitmap handoff anchor count=' + str(method.count(bitmap_anchor)))
early = bitmap_anchor + r'''            if (Boolean.TRUE.equals(M9_LIVE_PREVIEW_1A_ACTIVE.get())) {
                M9_LIVE_PREVIEW_1A_BITMAP.set(bitmap);
                bitmap = null;
                JSONObject previewDiag = out.diagnostics;
                try {
                    previewDiag.put("m9LivePreview1A", true);
                    previewDiag.put("m9LivePreviewMode", "FULL_PRODUCTION_RENDER_REDUCED_RAW_960x720");
                    previewDiag.put("m9LivePreviewNoFileSideEffects", true);
                } catch (Throwable ignored) {}
                return new Result(true, null, null, null, previewDiag, null);
            }
'''
method = method.replace(bitmap_anchor, early, 1)
s = s[:rs] + method + s[re_:]
renderer.write_text(s)

# RAW_SENSOR is reduced in the Bayer domain while preserving CFA parity, then the
# exact production renderer above is used. No alternate preview LUT exists.
preview_java.parent.mkdir(parents=True, exist_ok=True)
preview_java.write_text(r'''package com.particlesdevs.photoncamera.m9.preview;

import android.graphics.Bitmap;
import android.graphics.ImageFormat;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.CaptureResult;
import android.media.Image;

import com.particlesdevs.photoncamera.m9.render.M9R35Renderer;
import com.particlesdevs.photoncamera.util.Log;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;

public final class M9LivePreview1A {
    public static final boolean ENABLED = true;
    public static final int LANDSCAPE_WIDTH = 960;
    public static final int LANDSCAPE_HEIGHT = 720;
    private static final String TAG = "M9LivePreview1A";

    private M9LivePreview1A() {}

    public static Bitmap render(Image raw,
                                CameraCharacteristics characteristics,
                                CaptureResult captureResult,
                                CaptureRequest captureRequest,
                                int cameraRotation) throws Exception {
        if (raw == null || raw.getFormat() != ImageFormat.RAW_SENSOR) {
            throw new IllegalArgumentException("M9LIVEPREVIEW1A requires RAW_SENSOR image");
        }
        final int srcW = raw.getWidth();
        final int srcH = raw.getHeight();
        final int dstW = srcW >= srcH ? LANDSCAPE_WIDTH : LANDSCAPE_HEIGHT;
        final int dstH = srcW >= srcH ? LANDSCAPE_HEIGHT : LANDSCAPE_WIDTH;
        long started = System.nanoTime();
        ByteBuffer packed = reduceBayerParityPreserving(raw, dstW, dstH);
        long reduced = System.nanoTime();
        Bitmap out = M9R35Renderer.renderLivePreview1A(
                packed, dstW, dstH, characteristics, captureResult, captureRequest, cameraRotation);
        long finished = System.nanoTime();
        Log.d(TAG, "FULLRENDER720P raw=" + srcW + "x" + srcH
                + " reduced=" + dstW + "x" + dstH
                + " reduceMs=" + ((reduced - started) / 1_000_000.0)
                + " renderMs=" + ((finished - reduced) / 1_000_000.0));
        return out;
    }

    private static ByteBuffer reduceBayerParityPreserving(Image raw, int dstW, int dstH) {
        if ((dstW & 1) != 0 || (dstH & 1) != 0) {
            throw new IllegalArgumentException("M9LIVEPREVIEW1A target Bayer dimensions must be even");
        }
        Image.Plane[] planes = raw.getPlanes();
        if (planes == null || planes.length < 1) {
            throw new IllegalArgumentException("M9LIVEPREVIEW1A RAW has no plane");
        }
        Image.Plane p = planes[0];
        ByteBuffer src = p.getBuffer().duplicate().order(ByteOrder.LITTLE_ENDIAN);
        final int srcW = raw.getWidth();
        final int srcH = raw.getHeight();
        final int rowStride = p.getRowStride();
        final int pixelStride = p.getPixelStride();
        if (pixelStride < 2 || rowStride <= 0) {
            throw new IllegalArgumentException("M9LIVEPREVIEW1A unsupported RAW stride row="
                    + rowStride + " pixel=" + pixelStride);
        }
        ByteBuffer out = ByteBuffer.allocateDirect(dstW * dstH * 2).order(ByteOrder.LITTLE_ENDIAN);
        final double sxScale = srcW / (double) dstW;
        final double syScale = srcH / (double) dstH;
        for (int y = 0; y < dstH; y++) {
            int cy = sameParityNear((int)Math.floor((y + 0.5) * syScale), y & 1, srcH);
            int y0 = sameParityNear(cy - 2, y & 1, srcH);
            int y1 = sameParityNear(cy + 2, y & 1, srcH);
            for (int x = 0; x < dstW; x++) {
                int cx = sameParityNear((int)Math.floor((x + 0.5) * sxScale), x & 1, srcW);
                int x0 = sameParityNear(cx - 2, x & 1, srcW);
                int x1 = sameParityNear(cx + 2, x & 1, srcW);
                int a = u16(src, rowStride, pixelStride, x0, y0);
                int b = u16(src, rowStride, pixelStride, x1, y0);
                int c = u16(src, rowStride, pixelStride, x0, y1);
                int d = u16(src, rowStride, pixelStride, x1, y1);
                out.putShort((short)(((a + b + c + d + 2) >> 2) & 0xffff));
            }
        }
        out.flip();
        return out;
    }

    private static int u16(ByteBuffer src, int rowStride, int pixelStride, int x, int y) {
        int off = y * rowStride + x * pixelStride;
        if (off < 0 || off + 1 >= src.capacity()) {
            throw new IllegalArgumentException("M9LIVEPREVIEW1A RAW address out of bounds");
        }
        return src.getShort(off) & 0xffff;
    }

    private static int sameParityNear(int candidate, int parity, int limit) {
        if (limit < 2) return 0;
        int v = Math.max(0, Math.min(limit - 1, candidate));
        if ((v & 1) != parity) {
            if (v + 1 < limit) v++;
            else if (v - 1 >= 0) v--;
        }
        if ((v & 1) != parity) {
            throw new IllegalArgumentException("M9LIVEPREVIEW1A cannot preserve CFA parity");
        }
        return v;
    }
}
''')

# Transparent display overlay above GLPreview and below focus/horizon controls.
x = layout.read_text()
if 'android:id="@+id/m9_live_preview"' in x:
    raise SystemExit('M9LIVEPREVIEW1A layout already patched')
view_start = x.find('<com.particlesdevs.photoncamera.ui.camera.views.viewfinder.GLPreview')
if view_start < 0:
    raise SystemExit('M9LIVEPREVIEW1A GLPreview layout anchor missing')
view_end = x.find('/>', view_start)
if view_end < 0:
    raise SystemExit('M9LIVEPREVIEW1A GLPreview closing anchor missing')
view_end += 2
overlay = r'''

            <!-- M9LIVEPREVIEW1A_FULLRENDER720P -->
            <ImageView
                    android:id="@+id/m9_live_preview"
                    android:layout_width="0dp"
                    android:layout_height="0dp"
                    android:background="@android:color/transparent"
                    android:clickable="false"
                    android:focusable="false"
                    android:scaleType="centerCrop"
                    android:visibility="invisible"
                    app:layout_constraintBottom_toBottomOf="@id/texture"
                    app:layout_constraintEnd_toEndOf="@id/texture"
                    app:layout_constraintStart_toStartOf="@id/texture"
                    app:layout_constraintTop_toTopOf="@id/texture" />'''
x = x[:view_end] + overlay + x[view_end:]
layout.write_text(x)

# CaptureController: periodic one-shot RAW probes. RAW is never added to the normal
# repeating request, protecting shutter semantics and avoiding an unbounded RAW stream.
c = controller.read_text()
if 'M9LIVEPREVIEW1A_FULLRENDER720P' in c:
    raise SystemExit('M9LIVEPREVIEW1A already applied to CaptureController')
imp_anchor = 'import android.widget.Toast;\n'
if c.count(imp_anchor) != 1:
    raise SystemExit('M9LIVEPREVIEW1A Toast import anchor count=' + str(c.count(imp_anchor)))
c = c.replace(imp_anchor, imp_anchor + 'import android.widget.ImageView;\n', 1)
exec_anchor = 'import java.util.concurrent.ExecutorService;\n'
if c.count(exec_anchor) != 1:
    raise SystemExit('M9LIVEPREVIEW1A ExecutorService import anchor count=' + str(c.count(exec_anchor)))
c = c.replace(exec_anchor, exec_anchor + 'import java.util.concurrent.Executors;\n', 1)
class_import_anchor = 'import com.particlesdevs.photoncamera.processing.ImageSaver;\n'
if c.count(class_import_anchor) != 1:
    raise SystemExit('M9LIVEPREVIEW1A ImageSaver import anchor count=' + str(c.count(class_import_anchor)))
c = c.replace(class_import_anchor, class_import_anchor + 'import com.particlesdevs.photoncamera.m9.preview.M9LivePreview1A;\n', 1)

field_anchor = '    private final ExecutorService processExecutor;\n'
if c.count(field_anchor) != 1:
    raise SystemExit('M9LIVEPREVIEW1A processExecutor field anchor count=' + str(c.count(field_anchor)))
fields = field_anchor + r'''    // M9LIVEPREVIEW1A_FULLRENDER720P: one frame/probe and one render at a time.
    private static final long M9_LIVE_PREVIEW_INTERVAL_MS = 140L;
    private final ExecutorService m9LivePreviewExecutor = Executors.newSingleThreadExecutor();
    private final AtomicBoolean m9LivePreviewProbeInFlight = new AtomicBoolean(false);
    private final AtomicBoolean m9LivePreviewRenderBusy = new AtomicBoolean(false);
    private volatile CaptureResult m9LivePreviewProbeResult;
    private volatile CaptureRequest m9LivePreviewProbeRequest;
    private ImageView m9LivePreviewImageView;
    private android.graphics.Bitmap m9LivePreviewDisplayedBitmap;

    private final Runnable m9LivePreviewTick = new Runnable() {
        @Override public void run() {
            requestM9LivePreviewProbe1A();
            Handler h = mBackgroundHandler;
            if (h != null) h.postDelayed(this, M9_LIVE_PREVIEW_INTERVAL_MS);
        }
    };

    private final CameraCaptureSession.CaptureCallback m9LivePreviewCaptureCallback1A =
            new CameraCaptureSession.CaptureCallback() {
        @Override
        public void onCaptureCompleted(@NonNull CameraCaptureSession session,
                                       @NonNull CaptureRequest request,
                                       @NonNull TotalCaptureResult result) {
            m9LivePreviewProbeRequest = request;
            m9LivePreviewProbeResult = result;
        }

        @Override
        public void onCaptureFailed(@NonNull CameraCaptureSession session,
                                    @NonNull CaptureRequest request,
                                    @NonNull android.hardware.camera2.CaptureFailure failure) {
            m9LivePreviewProbeInFlight.set(false);
            Log.w(TAG, "M9LIVEPREVIEW1A probe capture failed reason=" + failure.getReason());
        }
    };
'''
c = c.replace(field_anchor, fields, 1)

ctor_anchor = '        this.mTextureView = activity.findViewById(R.id.texture);\n'
if c.count(ctor_anchor) != 1:
    raise SystemExit('M9LIVEPREVIEW1A constructor texture anchor count=' + str(c.count(ctor_anchor)))
c = c.replace(ctor_anchor, ctor_anchor + '        this.m9LivePreviewImageView = activity.findViewById(R.id.m9_live_preview);\n', 1)

listener_sig = '        public void onImageAvailable(ImageReader reader) {'
ls = c.find(listener_sig, c.find('mOnRawImageAvailableListener'))
if ls < 0:
    raise SystemExit('M9LIVEPREVIEW1A RAW listener anchor missing')
li = ls + len(listener_sig)
listener_block = r'''
            if (M9LivePreview1A.ENABLED && !isZslMode()
                    && m9LivePreviewProbeInFlight.compareAndSet(true, false)) {
                final Image previewRaw = reader.acquireLatestImage();
                if (previewRaw == null) return;
                if (!m9LivePreviewRenderBusy.compareAndSet(false, true)) {
                    previewRaw.close();
                    return;
                }
                final CameraCharacteristics previewChars = mCameraCharacteristics;
                final CaptureResult previewResult = m9LivePreviewProbeResult != null
                        ? m9LivePreviewProbeResult : mPreviewCaptureResult;
                final CaptureRequest previewRequest = m9LivePreviewProbeRequest != null
                        ? m9LivePreviewProbeRequest : mPreviewCaptureRequest;
                final int previewRotation = cameraRotation;
                m9LivePreviewExecutor.execute(() -> {
                    android.graphics.Bitmap rendered = null;
                    try {
                        rendered = M9LivePreview1A.render(previewRaw, previewChars,
                                previewResult, previewRequest, previewRotation);
                        final android.graphics.Bitmap ready = rendered;
                        rendered = null;
                        activity.runOnUiThread(() -> {
                            if (m9LivePreviewImageView == null) {
                                if (ready != null && !ready.isRecycled()) ready.recycle();
                                return;
                            }
                            android.graphics.Bitmap old = m9LivePreviewDisplayedBitmap;
                            m9LivePreviewDisplayedBitmap = ready;
                            m9LivePreviewImageView.setImageBitmap(ready);
                            m9LivePreviewImageView.setVisibility(android.view.View.VISIBLE);
                            if (old != null && old != ready && !old.isRecycled()) old.recycle();
                        });
                    } catch (Throwable t) {
                        Log.e(TAG, "M9LIVEPREVIEW1A full-render frame failed", t);
                    } finally {
                        try { previewRaw.close(); } catch (Throwable ignored) {}
                        if (rendered != null && !rendered.isRecycled()) rendered.recycle();
                        m9LivePreviewRenderBusy.set(false);
                    }
                });
                return;
            }
'''
c = c[:li] + listener_block + c[li:]

show_anchor = '    private void showToast(String msg) {'
si = c.find(show_anchor)
if si < 0:
    raise SystemExit('M9LIVEPREVIEW1A showToast anchor missing')
helpers = r'''    private void scheduleM9LivePreview1A() {
        if (!M9LivePreview1A.ENABLED || mBackgroundHandler == null) return;
        mBackgroundHandler.removeCallbacks(m9LivePreviewTick);
        mBackgroundHandler.postDelayed(m9LivePreviewTick, 180L);
    }

    private void stopM9LivePreview1A() {
        Handler h = mBackgroundHandler;
        if (h != null) h.removeCallbacks(m9LivePreviewTick);
        m9LivePreviewProbeInFlight.set(false);
        m9LivePreviewProbeResult = null;
        m9LivePreviewProbeRequest = null;
        activity.runOnUiThread(() -> {
            if (m9LivePreviewImageView != null) {
                m9LivePreviewImageView.setVisibility(android.view.View.INVISIBLE);
                m9LivePreviewImageView.setImageDrawable(null);
            }
            android.graphics.Bitmap old = m9LivePreviewDisplayedBitmap;
            m9LivePreviewDisplayedBitmap = null;
            if (old != null && !old.isRecycled()) old.recycle();
        });
    }

    private void requestM9LivePreviewProbe1A() {
        if (!M9LivePreview1A.ENABLED || isZslMode() || burst || isProcessing
                || mState != STATE_PREVIEW || mCameraDevice == null || mCaptureSession == null
                || mPreviewRequestBuilder == null || mImageReaderRaw == null
                || m9LivePreviewRenderBusy.get()) return;
        if (!m9LivePreviewProbeInFlight.compareAndSet(false, true)) return;
        Surface rawSurface = mImageReaderRaw.getSurface();
        boolean targetAdded = false;
        try {
            m9LivePreviewProbeResult = null;
            m9LivePreviewProbeRequest = null;
            mPreviewRequestBuilder.addTarget(rawSurface);
            targetAdded = true;
            CaptureRequest probe = mPreviewRequestBuilder.build();
            mPreviewRequestBuilder.removeTarget(rawSurface);
            targetAdded = false;
            m9LivePreviewProbeRequest = probe;
            mCaptureSession.capture(probe, m9LivePreviewCaptureCallback1A, mBackgroundHandler);
        } catch (Throwable t) {
            if (targetAdded) {
                try { mPreviewRequestBuilder.removeTarget(rawSurface); } catch (Throwable ignored) {}
            }
            m9LivePreviewProbeInFlight.set(false);
            Log.w(TAG, "M9LIVEPREVIEW1A probe request failed: " + t);
        }
    }

'''
c = c[:si] + helpers + c[si:]

start_anchor = '''                            mCaptureSession.setRepeatingRequest(mPreviewInputRequest,\n                                    mCaptureCallback, mBackgroundHandler);\n                            unlockFocus();\n'''
if c.count(start_anchor) != 1:
    raise SystemExit('M9LIVEPREVIEW1A configured-preview start anchor count=' + str(c.count(start_anchor)))
c = c.replace(start_anchor, start_anchor + '                            scheduleM9LivePreview1A();\n', 1)

close_anchor = '    public void closeCamera() {\n'
if c.count(close_anchor) != 1:
    raise SystemExit('M9LIVEPREVIEW1A closeCamera anchor count=' + str(c.count(close_anchor)))
c = c.replace(close_anchor, close_anchor + '        stopM9LivePreview1A();\n', 1)
restart_anchor = '    public void restartCamera() {\n'
if c.count(restart_anchor) != 1:
    raise SystemExit('M9LIVEPREVIEW1A restartCamera anchor count=' + str(c.count(restart_anchor)))
c = c.replace(restart_anchor, restart_anchor + '        stopM9LivePreview1A();\n', 1)
controller.write_text(c)

if gradle.exists():
    g = gradle.read_text()
    m = re.search(r'versionName\s+["\']([^"\']+)["\']', g)
    if m and 'm9livepreview1a' not in m.group(1).lower():
        old = m.group(0)
        quote = '"' if '"' in old else "'"
        g = g.replace(old, 'versionName ' + quote + m.group(1) + '-m9livepreview1a-720pfull' + quote, 1)
        gradle.write_text(g)

print('M9LIVEPREVIEW1A_FULLRENDER720P applied')
print(' - one-shot RAW_SENSOR probe, not repeating RAW')
print(' - CFA-preserving 960x720 Bayer reduction')
print(' - exact current primary M9 render path')
print(' - no preview JPEG/DNG publication')
print(' - normal shutter path unchanged when thread-local preview gate is inactive')
