#!/usr/bin/env python3
from pathlib import Path
import re, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m9livepreview1d-virtualcapturedomain1a.py <PhotonCamera-root>')

root=Path(sys.argv[1]).resolve()
renderer=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
preview=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
controller=root/'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
gradle=root/'app/build.gradle'
for p in (renderer,preview,controller):
    if not p.exists(): raise SystemExit('M9LIVEPREVIEW1D missing '+str(p))

def replace_once(s, old, new, label):
    n=s.count(old)
    if n != 1:
        raise SystemExit(f'M9LIVEPREVIEW1D {label}: expected 1 anchor, found {n}')
    return s.replace(old,new,1)

c=controller.read_text()
for marker in (
        'M9LIVEPREVIEW1A_FULLRENDER720P',
        'M9LIVEPREVIEW1B_FULLRENDER1080P_MAIN',
        'M9LivePreview1A.markDisplayed1B();'):
    if marker not in c:
        raise SystemExit('M9LIVEPREVIEW1D controller baseline marker missing: '+marker)
if 'M9LIVEPREVIEW1D_VIRTUALCAPTUREDOMAIN1A' in c:
    raise SystemExit('M9LIVEPREVIEW1D already applied')

# Exact RAW<->CaptureResult pairing state plus display-only predicted-still exposure target.
field_anchor='''    private volatile CaptureResult m9LivePreviewProbeResult;
    private volatile CaptureRequest m9LivePreviewProbeRequest;
'''
field_new=field_anchor+'''    // M9LIVEPREVIEW1D_VIRTUALCAPTUREDOMAIN1A
    // Sensor exposure stays on the normal preview state. We only transform the in-memory
    // preview RAW after pairing it to its exact TotalCaptureResult.
    private final Object m9LivePreviewPairLock1D = new Object();
    private Image m9LivePreviewPendingImage1D = null;
    private TotalCaptureResult m9LivePreviewPendingResult1D = null;
    private CaptureRequest m9LivePreviewPendingRequest1D = null;
    private int m9LivePreviewTargetIso1D = -1;
    private long m9LivePreviewTargetExposureNs1D = -1L;
'''
c=replace_once(c,field_anchor,field_new,'pair fields')

# Replace capture callback with timestamp-paired result handling.
cb_start=c.find('    private final CameraCaptureSession.CaptureCallback m9LivePreviewCaptureCallback1A =')
if cb_start < 0:
    raise SystemExit('M9LIVEPREVIEW1D callback start missing')
cb_end=c.find('    };', cb_start)
if cb_end < 0:
    raise SystemExit('M9LIVEPREVIEW1D callback end missing')
cb_end += len('    };')
new_cb=r'''    private final CameraCaptureSession.CaptureCallback m9LivePreviewCaptureCallback1A =
            new CameraCaptureSession.CaptureCallback() {
        @Override
        public void onCaptureCompleted(@NonNull CameraCaptureSession session,
                                       @NonNull CaptureRequest request,
                                       @NonNull TotalCaptureResult result) {
            m9LivePreviewProbeRequest = request;
            m9LivePreviewProbeResult = result;
            synchronized (m9LivePreviewPairLock1D) {
                m9LivePreviewPendingResult1D = result;
                m9LivePreviewPendingRequest1D = request;
            }
            tryDispatchM9LivePreviewPair1D();
        }

        @Override
        public void onCaptureFailed(@NonNull CameraCaptureSession session,
                                    @NonNull CaptureRequest request,
                                    @NonNull android.hardware.camera2.CaptureFailure failure) {
            clearM9LivePreviewPair1D(true);
            Log.w(TAG, "M9LIVEPREVIEW1D probe capture failed reason=" + failure.getReason());
        }
    };'''
c=c[:cb_start]+new_cb+c[cb_end:]

# Replace RAW-listener preview block: acquire and hold image until exact result arrives.
listener_start=c.find('            if (M9LivePreview1A.ENABLED && !isZslMode()', c.find('mOnRawImageAvailableListener'))
if listener_start < 0:
    raise SystemExit('M9LIVEPREVIEW1D RAW preview listener block missing')
listener_end=c.find('                return;\n            }', listener_start)
if listener_end < 0:
    raise SystemExit('M9LIVEPREVIEW1D RAW preview listener end missing')
listener_end += len('                return;\n            }')
new_listener=r'''            if (M9LivePreview1A.ENABLED && !isZslMode()
                    && m9LivePreviewProbeInFlight.get()) {
                final Image previewRaw = reader.acquireLatestImage();
                if (previewRaw == null) return;
                synchronized (m9LivePreviewPairLock1D) {
                    Image old = m9LivePreviewPendingImage1D;
                    m9LivePreviewPendingImage1D = previewRaw;
                    if (old != null && old != previewRaw) {
                        try { old.close(); } catch (Throwable ignored) {}
                    }
                }
                tryDispatchM9LivePreviewPair1D();
                return;
            }'''
c=c[:listener_start]+new_listener+c[listener_end:]

# Replace stop helper to close any held RAW.
stop_start=c.find('    private void stopM9LivePreview1A() {')
req_start=c.find('    private void requestM9LivePreviewProbe1A() {', stop_start)
if stop_start < 0 or req_start < 0:
    raise SystemExit('M9LIVEPREVIEW1D stop/request methods missing')
stop_block=c[stop_start:req_start]
stop_anchor='''        m9LivePreviewProbeResult = null;
        m9LivePreviewProbeRequest = null;
'''
stop_new=stop_anchor+'''        clearM9LivePreviewPair1D(true);
'''
stop_block=replace_once(stop_block,stop_anchor,stop_new,'stop pair clear')
c=c[:stop_start]+stop_block+c[req_start:]

# Replace probe request method: predict target, but DO NOT alter sensor ISO/shutter.
req_start=c.find('    private void requestM9LivePreviewProbe1A() {')
brace=c.find('{',req_start); depth=0; i=brace
while i < len(c):
    if c[i]=='{': depth+=1
    elif c[i]=='}':
        depth-=1
        if depth==0:
            req_end=i+1; break
    i+=1
else: raise SystemExit('M9LIVEPREVIEW1D unterminated request method')

new_req=r'''    private void requestM9LivePreviewProbe1A() {
        if (!M9LivePreview1A.ENABLED || isZslMode() || burst || isProcessing
                || mState != STATE_PREVIEW || mCameraDevice == null || mCaptureSession == null
                || mPreviewRequestBuilder == null || mImageReaderRaw == null
                || m9LivePreviewRenderBusy.get()) return;
        if (!m9LivePreviewProbeInFlight.compareAndSet(false, true)) return;

        int targetIso = mPreviewIso;
        long targetExposureNs = mPreviewExposureTime;
        try {
            // step=-1 runs the same current still-exposure arithmetic without admitting a
            // real capture pair into IsoExpoSelector history.
            IsoExpoSelector.ExpoPair predicted = IsoExpoSelector.GenerateExpoPair(-1, this);
            if (predicted != null && predicted.iso > 0 && predicted.exposure > 0L) {
                targetIso = predicted.iso;
                targetExposureNs = predicted.exposure;
            }
        } catch (Throwable t) {
            Log.w(TAG, "M9LIVEPREVIEW1D still-target prediction fallback: " + t);
        }

        synchronized (m9LivePreviewPairLock1D) {
            if (m9LivePreviewPendingImage1D != null) {
                try { m9LivePreviewPendingImage1D.close(); } catch (Throwable ignored) {}
            }
            m9LivePreviewPendingImage1D = null;
            m9LivePreviewPendingResult1D = null;
            m9LivePreviewPendingRequest1D = null;
            m9LivePreviewTargetIso1D = targetIso;
            m9LivePreviewTargetExposureNs1D = targetExposureNs;
        }

        Surface rawSurface = mImageReaderRaw.getSurface();
        boolean targetAdded = false;
        try {
            m9LivePreviewProbeResult = null;
            m9LivePreviewProbeRequest = null;

            // CRITICAL: this request is the ordinary repeating-preview request plus RAW output.
            // No AE-mode, ISO, shutter, frame-duration, WB, tone or still-capture value changes.
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
            clearM9LivePreviewPair1D(true);
            Log.w(TAG, "M9LIVEPREVIEW1D virtual-domain RAW probe request failed: " + t);
        }
    }'''
c=c[:req_start]+new_req+c[req_end:]

# Insert exact-pair dispatch helpers before showToast.
helper_anchor='    private void showToast(String msg) {'
hi=c.find(helper_anchor)
if hi < 0:
    raise SystemExit('M9LIVEPREVIEW1D helper insertion anchor missing')
helpers=r'''    private void clearM9LivePreviewPair1D(boolean clearInFlight) {
        Image image = null;
        synchronized (m9LivePreviewPairLock1D) {
            image = m9LivePreviewPendingImage1D;
            m9LivePreviewPendingImage1D = null;
            m9LivePreviewPendingResult1D = null;
            m9LivePreviewPendingRequest1D = null;
            m9LivePreviewTargetIso1D = -1;
            m9LivePreviewTargetExposureNs1D = -1L;
        }
        if (image != null) {
            try { image.close(); } catch (Throwable ignored) {}
        }
        if (clearInFlight) m9LivePreviewProbeInFlight.set(false);
    }

    private void tryDispatchM9LivePreviewPair1D() {
        final Image image;
        final TotalCaptureResult result;
        final CaptureRequest request;
        final int targetIso;
        final long targetExposureNs;

        synchronized (m9LivePreviewPairLock1D) {
            if (m9LivePreviewPendingImage1D == null
                    || m9LivePreviewPendingResult1D == null
                    || m9LivePreviewPendingRequest1D == null) {
                return;
            }
            image = m9LivePreviewPendingImage1D;
            result = m9LivePreviewPendingResult1D;
            request = m9LivePreviewPendingRequest1D;
            targetIso = m9LivePreviewTargetIso1D;
            targetExposureNs = m9LivePreviewTargetExposureNs1D;

            Long resultTsObj = result.get(CaptureResult.SENSOR_TIMESTAMP);
            long imageTs = image.getTimestamp();
            long resultTs = resultTsObj != null ? resultTsObj : Long.MIN_VALUE;
            long delta = resultTsObj != null ? Math.abs(imageTs - resultTs) : Long.MAX_VALUE;

            // RAW Image timestamp and SENSOR_TIMESTAMP should be identical. Permit a tiny
            // vendor scheduling tolerance but never pair adjacent frames (~tens of ms apart).
            if (resultTsObj == null || delta > 2_000_000L) {
                Log.w(TAG, "M9LIVEPREVIEW1D timestamp mismatch image=" + imageTs
                        + " result=" + resultTs + " deltaNs=" + delta);
                try { image.close(); } catch (Throwable ignored) {}
                m9LivePreviewPendingImage1D = null;
                m9LivePreviewPendingResult1D = null;
                m9LivePreviewPendingRequest1D = null;
                m9LivePreviewProbeInFlight.set(false);
                return;
            }

            m9LivePreviewPendingImage1D = null;
            m9LivePreviewPendingResult1D = null;
            m9LivePreviewPendingRequest1D = null;
            m9LivePreviewProbeInFlight.set(false);
        }

        if (!m9LivePreviewRenderBusy.compareAndSet(false, true)) {
            try { image.close(); } catch (Throwable ignored) {}
            return;
        }

        final CameraCharacteristics previewChars = mCameraCharacteristics;
        final int previewRotation = cameraRotation;
        m9LivePreviewExecutor.execute(() -> {
            android.graphics.Bitmap rendered = null;
            try {
                rendered = M9LivePreview1A.render(image, previewChars,
                        result, request, targetIso, targetExposureNs, previewRotation);
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
                    M9LivePreview1A.markDisplayed1B();
                    m9LivePreviewImageView.setVisibility(android.view.View.VISIBLE);
                    if (old != null && old != ready && !old.isRecycled()) old.recycle();
                });
            } catch (Throwable t) {
                Log.e(TAG, "M9LIVEPREVIEW1D virtual-domain frame failed", t);
            } finally {
                try { image.close(); } catch (Throwable ignored) {}
                if (rendered != null && !rendered.isRecycled()) rendered.recycle();
                m9LivePreviewRenderBusy.set(false);
            }
        });
    }

'''
c=c[:hi]+helpers+c[hi:]
controller.write_text(c)

# Preview RAW -> intended still exposure domain, purely in-memory after exact pairing.
p=preview.read_text()
if 'import android.hardware.camera2.params.BlackLevelPattern;' not in p:
    p=replace_once(p,'import android.hardware.camera2.CaptureResult;\n',
        'import android.hardware.camera2.CaptureResult;\nimport android.hardware.camera2.params.BlackLevelPattern;\n',
        'BlackLevelPattern import')

sig_old='''    public static Bitmap render(Image raw,
                                CameraCharacteristics characteristics,
                                CaptureResult captureResult,
                                CaptureRequest captureRequest,
                                int cameraRotation) throws Exception {
'''
sig_new='''    public static Bitmap render(Image raw,
                                CameraCharacteristics characteristics,
                                CaptureResult captureResult,
                                CaptureRequest captureRequest,
                                int targetIso,
                                long targetExposureNs,
                                int cameraRotation) throws Exception {
'''
p=replace_once(p,sig_old,sig_new,'render signature')

dims='''        final int dstW = srcW >= srcH ? LANDSCAPE_WIDTH : LANDSCAPE_HEIGHT;
        final int dstH = srcW >= srcH ? LANDSCAPE_HEIGHT : LANDSCAPE_WIDTH;
'''
dims_new=dims+'''        Integer probeIsoObj = captureResult.get(CaptureResult.SENSOR_SENSITIVITY);
        Long probeExposureObj = captureResult.get(CaptureResult.SENSOR_EXPOSURE_TIME);
        if (probeIsoObj == null || probeIsoObj <= 0
                || probeExposureObj == null || probeExposureObj <= 0L) {
            throw new IllegalStateException(
                    "M9LIVEPREVIEW1D exact paired probe exposure metadata missing");
        }
        final int probeIso = probeIsoObj;
        final long probeExposureNs = probeExposureObj;
        if (targetIso <= 0) targetIso = probeIso;
        if (targetExposureNs <= 0L) targetExposureNs = probeExposureNs;

        double targetEnergy = targetIso * (double) targetExposureNs;
        double probeEnergy = probeIso * (double) probeExposureNs;
        double exposureDomainScale = targetEnergy / probeEnergy;
        if (!Double.isFinite(exposureDomainScale) || exposureDomainScale <= 0.0) {
            exposureDomainScale = 1.0;
        }
        exposureDomainScale = Math.max(1.0 / 64.0, Math.min(64.0, exposureDomainScale));
'''
p=replace_once(p,dims,dims_new,'domain scale')

p=replace_once(p,
    '        ByteBuffer packed = reduceBayerParityPreserving(raw, dstW, dstH);\n',
    '        ByteBuffer packed = reduceBayerParityPreserving(raw, dstW, dstH, characteristics, exposureDomainScale);\n',
    'scaled reducer call')

call_old='''        Bitmap out = M9R35Renderer.renderLivePreview1A(
                packed, dstW, dstH, characteristics, captureResult, captureRequest,
                sourceDescriptor1A, cameraRotation);
'''
call_new='''        Bitmap out = M9R35Renderer.renderLivePreview1A(
                packed, dstW, dstH, characteristics, captureResult, captureRequest,
                sourceDescriptor1A, targetIso, targetExposureNs,
                probeIso, probeExposureNs, exposureDomainScale, cameraRotation);
'''
p=replace_once(p,call_old,call_new,'renderer wrapper call')

log_old='''                + " reduceMs=" + ((reduced - started) / 1_000_000.0)
                + " renderMs=" + ((finished - reduced) / 1_000_000.0));
'''
log_new='''                + " target=" + targetIso + "x" + targetExposureNs
                + " probe=" + probeIso + "x" + probeExposureNs
                + " virtualScale=" + exposureDomainScale
                + " virtualDeltaEv=" + (Math.log(exposureDomainScale) / Math.log(2.0))
                + " reduceMs=" + ((reduced - started) / 1_000_000.0)
                + " renderMs=" + ((finished - reduced) / 1_000_000.0));
'''
p=replace_once(p,log_old,log_new,'virtual-domain log')

p=replace_once(p,
'''    private static ByteBuffer reduceBayerParityPreserving(Image raw, int dstW, int dstH) {
''',
'''    private static ByteBuffer reduceBayerParityPreserving(
            Image raw, int dstW, int dstH,
            CameraCharacteristics characteristics, double exposureDomainScale) {
''','reducer signature')

p=replace_once(p,
'''        ByteBuffer out = ByteBuffer.allocateDirect(dstW * dstH * 2).order(ByteOrder.LITTLE_ENDIAN);
        final double sxScale = srcW / (double) dstW;
''',
'''        ByteBuffer out = ByteBuffer.allocateDirect(dstW * dstH * 2).order(ByteOrder.LITTLE_ENDIAN);
        BlackLevelPattern blackPattern = characteristics != null
                ? characteristics.get(CameraCharacteristics.SENSOR_BLACK_LEVEL_PATTERN) : null;
        Integer whiteObj = characteristics != null
                ? characteristics.get(CameraCharacteristics.SENSOR_INFO_WHITE_LEVEL) : null;
        final int whiteLevel = whiteObj != null ? whiteObj : 65535;
        final double sxScale = srcW / (double) dstW;
''','reducer metadata')

p=replace_once(p,
'''                int d = u16(src, rowStride, pixelStride, x1, y1);
                out.putShort((short)(((a + b + c + d + 2) >> 2) & 0xffff));
''',
'''                int d = u16(src, rowStride, pixelStride, x1, y1);
                int avg = (a + b + c + d + 2) >> 2;
                int black = 0;
                if (blackPattern != null) {
                    try { black = blackPattern.getOffsetForIndex(x & 1, y & 1); }
                    catch (Throwable ignored) {}
                }
                int mapped = scaleVirtualCaptureDomain1D(
                        avg, black, whiteLevel, exposureDomainScale);
                out.putShort((short)(mapped & 0xffff));
''','black-relative map')

helper_anchor='''    private static int u16(ByteBuffer src, int rowStride, int pixelStride, int x, int y) {
'''
helper=r'''    private static int scaleVirtualCaptureDomain1D(
            int code, int black, int white, double scale) {
        int lo = Math.max(0, black);
        int hi = Math.max(lo + 1, Math.min(65535, white));
        double linear = Math.max(0.0, code - lo);
        double mapped = lo + linear * scale;
        if (!Double.isFinite(mapped)) mapped = code;
        int out = (int)Math.round(mapped);
        if (out < lo) out = lo;
        if (out > hi) out = hi;
        return out;
    }

'''
p=replace_once(p,helper_anchor,helper+helper_anchor,'virtual map helper')
preview.write_text(p)

# Renderer wrapper gets preview-only diagnostic context; frozen render core remains untouched.
r=renderer.read_text()
field='''    private static final ThreadLocal<JSONObject> M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR = new ThreadLocal<>();
'''
field_new=field+'''    // M9LIVEPREVIEW1D: diagnostic context only; never read by still rendering.
    private static final ThreadLocal<JSONObject> M9_LIVE_PREVIEW_1D_VIRTUAL_DOMAIN =
            new ThreadLocal<>();
'''
r=replace_once(r,field,field_new,'renderer ThreadLocal')

sig_old='''    public static Bitmap renderLivePreview1A(ByteBuffer packedRaw,
                                             int width,
                                             int height,
                                             CameraCharacteristics characteristics,
                                             CaptureResult captureResult,
                                             CaptureRequest captureRequest,
                                             JSONObject sourceDescriptor1A,
                                             int cameraRotation) throws Exception {
'''
sig_new='''    public static Bitmap renderLivePreview1A(ByteBuffer packedRaw,
                                             int width,
                                             int height,
                                             CameraCharacteristics characteristics,
                                             CaptureResult captureResult,
                                             CaptureRequest captureRequest,
                                             JSONObject sourceDescriptor1A,
                                             int targetIso,
                                             long targetExposureNs,
                                             int probeIso,
                                             long probeExposureNs,
                                             double exposureDomainScale,
                                             int cameraRotation) throws Exception {
'''
r=replace_once(r,sig_old,sig_new,'renderer wrapper signature')

set_anchor='''        M9_LIVE_PREVIEW_1A_BITMAP.remove();
        M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR.set(sourceDescriptor1A);
'''
set_new=set_anchor+'''        JSONObject virtualDomain1D = new JSONObject();
        virtualDomain1D.put("schema", "m9cam.livepreview.virtualcapturedomain.v1a");
        virtualDomain1D.put("revision", "M9LIVEPREVIEW1D_VIRTUALCAPTUREDOMAIN1A");
        virtualDomain1D.put("scope", "viewfinder_prediction_only");
        virtualDomain1D.put("sensorProbeExposureMutation", false);
        virtualDomain1D.put("stillCaptureMutation", false);
        virtualDomain1D.put("finalJpegIsAuthority", true);
        virtualDomain1D.put("rawCaptureResultPairing",
                "Image_timestamp_matches_TotalCaptureResult_SENSOR_TIMESTAMP");
        virtualDomain1D.put("targetIso", targetIso);
        virtualDomain1D.put("targetExposureTimeNs", targetExposureNs);
        virtualDomain1D.put("probeIso", probeIso);
        virtualDomain1D.put("probeExposureTimeNs", probeExposureNs);
        virtualDomain1D.put("virtualLinearScale", exposureDomainScale);
        virtualDomain1D.put("virtualDeltaEv",
                Math.log(Math.max(exposureDomainScale, 1.0e-12)) / Math.log(2.0));
        virtualDomain1D.put("mappingDomain",
                "black_relative_linear_Bayer_after_exact_frame_pairing");
        M9_LIVE_PREVIEW_1D_VIRTUAL_DOMAIN.set(virtualDomain1D);
'''
r=replace_once(r,set_anchor,set_new,'virtual context set')

diag_anchor='''                    previewDiag.put("sourceGeometryAuthority",
                            "original_full_resolution_RAW_descriptor_retained_before_preview_reduction");
'''
diag_new=diag_anchor+'''                    previewDiag.put("previewVirtualCaptureDomain1D",
                            M9_LIVE_PREVIEW_1D_VIRTUAL_DOMAIN.get());
'''
r=replace_once(r,diag_anchor,diag_new,'preview diagnostic attach')

cleanup='''            M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR.remove();
            M9_LIVE_PREVIEW_1A_ACTIVE.remove();
'''
cleanup_new='''            M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR.remove();
            M9_LIVE_PREVIEW_1D_VIRTUAL_DOMAIN.remove();
            M9_LIVE_PREVIEW_1A_ACTIVE.remove();
'''
r=replace_once(r,cleanup,cleanup_new,'virtual context cleanup')

key_anchor='''                    "sensorDescriptor1A",
                    "targetFalloff1A"
            };'''
if key_anchor in r:
    r=r.replace(key_anchor,'''                    "sensorDescriptor1A",
                    "targetFalloff1A",
                    "previewVirtualCaptureDomain1D"
            };''',1)

renderer.write_text(r)

if gradle.exists():
    g=gradle.read_text()
    m=re.search(r'versionName\s+["\']([^"\']+)["\']',g)
    if m and 'm9livepreview1d' not in m.group(1).lower():
        old=m.group(0); q='"' if '"' in old else "'"
        g=g.replace(old,'versionName '+q+m.group(1)+'-m9livepreview1d-virtualcapturedomain1a'+q,1)
        gradle.write_text(g)

print('M9LIVEPREVIEW1D_VIRTUALCAPTUREDOMAIN1A applied')
print(' - RAW probe uses unchanged normal preview sensor exposure: no 1C exposure flicker')
print(' - RAW Image is paired to exact TotalCaptureResult by sensor timestamp')
print(' - current still exposure is predicted with GenerateExpoPair(-1)')
print(' - only the in-memory reduced RAW is black-relative mapped into predicted still domain')
print(' - final JPEG/capture exposure/TC20/TONEBOUND/SAT2/curve02 remain unchanged')
