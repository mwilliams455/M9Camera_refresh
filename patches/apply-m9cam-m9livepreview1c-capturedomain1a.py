#!/usr/bin/env python3
from pathlib import Path
import re, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m9livepreview1c-capturedomain1a.py <PhotonCamera-root>')

root=Path(sys.argv[1]).resolve()
renderer=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
preview=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
controller=root/'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
gradle=root/'app/build.gradle'
for p in (renderer,preview,controller):
    if not p.exists(): raise SystemExit('M9LIVEPREVIEW1C missing '+str(p))

def replace_once(s, old, new, label):
    n=s.count(old)
    if n != 1:
        raise SystemExit(f'M9LIVEPREVIEW1C {label}: expected 1 anchor, found {n}')
    return s.replace(old,new,1)

# ---------------------------------------------------------------------------
# CaptureController: predict the exact step-0 still exposure without entering
# the real capture sequence, request that exposure for the one-shot RAW probe,
# and retain the target alongside the probe for residual correction.
# ---------------------------------------------------------------------------
c=controller.read_text()
if 'M9LIVEPREVIEW1C_CAPTUREDOMAIN1A' in c:
    raise SystemExit('M9LIVEPREVIEW1C already applied')

field_anchor='''    private volatile CaptureResult m9LivePreviewProbeResult;
    private volatile CaptureRequest m9LivePreviewProbeRequest;
'''
field_new=field_anchor+'''    // M9LIVEPREVIEW1C_CAPTUREDOMAIN1A: display prediction target only.
    // These values NEVER feed the still capture request; they describe the still
    // exposure that GenerateExpoPair(-1) predicts from the current user/camera state.
    private volatile int m9LivePreviewTargetIso1C = -1;
    private volatile long m9LivePreviewTargetExposureNs1C = -1L;
'''
c=replace_once(c,field_anchor,field_new,'preview target fields')

old_call='''                        rendered = M9LivePreview1A.render(previewRaw, previewChars,
                                previewResult, previewRequest, previewRotation);
'''
new_call='''                        rendered = M9LivePreview1A.render(previewRaw, previewChars,
                                previewResult, previewRequest,
                                m9LivePreviewTargetIso1C, m9LivePreviewTargetExposureNs1C,
                                previewRotation);
'''
c=replace_once(c,old_call,new_call,'preview render call')

old_stop='''        m9LivePreviewProbeResult = null;
        m9LivePreviewProbeRequest = null;
'''
new_stop=old_stop+'''        m9LivePreviewTargetIso1C = -1;
        m9LivePreviewTargetExposureNs1C = -1L;
'''
# It occurs once in stop and once in request reset in current code. Replace only first
# via explicit stop method scope.
stop_start=c.find('    private void stopM9LivePreview1A() {')
stop_end=c.find('    private void requestM9LivePreviewProbe1A() {', stop_start)
if stop_start < 0 or stop_end < 0:
    raise SystemExit('M9LIVEPREVIEW1C stop/request methods missing')
stop_block=c[stop_start:stop_end]
stop_block=replace_once(stop_block,old_stop,new_stop,'stop target reset')
c=c[:stop_start]+stop_block+c[stop_end:]

req_start=c.find('    private void requestM9LivePreviewProbe1A() {')
if req_start < 0: raise SystemExit('M9LIVEPREVIEW1C request method missing')
# lightweight brace matcher
brace=c.find('{',req_start); depth=0; i=brace
while i < len(c):
    if c[i]=='{': depth+=1
    elif c[i]=='}':
        depth-=1
        if depth==0:
            req_end=i+1; break
    i+=1
else: raise SystemExit('M9LIVEPREVIEW1C unterminated request method')
old_req=c[req_start:req_end]
new_req=r'''    private void requestM9LivePreviewProbe1A() {
        if (!M9LivePreview1A.ENABLED || isZslMode() || burst || isProcessing
                || mState != STATE_PREVIEW || mCameraDevice == null || mCaptureSession == null
                || mPreviewRequestBuilder == null || mImageReaderRaw == null
                || m9LivePreviewRenderBusy.get()) return;
        if (!m9LivePreviewProbeInFlight.compareAndSet(false, true)) return;

        Surface rawSurface = mImageReaderRaw.getSurface();
        boolean targetAdded = false;

        // Predict what step-0 would capture from the CURRENT app state. step=-1 deliberately
        // bypasses IsoExpoSelector pair-history admission while retaining the same exposure
        // arithmetic, user EV/manual settings, live M9 feedback and shutter/ISO policy.
        int targetIso = mPreviewIso;
        long targetExposureNs = mPreviewExposureTime;
        try {
            IsoExpoSelector.ExpoPair predicted = IsoExpoSelector.GenerateExpoPair(-1, this);
            if (predicted != null && predicted.iso > 0 && predicted.exposure > 0L) {
                targetIso = predicted.iso;
                targetExposureNs = predicted.exposure;
            }
        } catch (Throwable t) {
            Log.w(TAG, "M9LIVEPREVIEW1C target prediction fallback to repeating preview: " + t);
        }
        m9LivePreviewTargetIso1C = targetIso;
        m9LivePreviewTargetExposureNs1C = targetExposureNs;

        // Build ONE immutable RAW probe request at the predicted still exposure, then restore
        // the repeating-preview builder immediately. This cannot change the eventual still.
        Integer oldAe = null;
        Integer oldIso = null;
        Long oldExposure = null;
        Long oldFrameDuration = null;
        try {
            oldAe = mPreviewRequestBuilder.get(CaptureRequest.CONTROL_AE_MODE);
            oldIso = mPreviewRequestBuilder.get(CaptureRequest.SENSOR_SENSITIVITY);
            oldExposure = mPreviewRequestBuilder.get(CaptureRequest.SENSOR_EXPOSURE_TIME);
            oldFrameDuration = mPreviewRequestBuilder.get(CaptureRequest.SENSOR_FRAME_DURATION);

            m9LivePreviewProbeResult = null;
            m9LivePreviewProbeRequest = null;
            mPreviewRequestBuilder.set(CaptureRequest.CONTROL_AE_MODE,
                    CaptureRequest.CONTROL_AE_MODE_OFF);
            if (targetIso > 0) {
                mPreviewRequestBuilder.set(CaptureRequest.SENSOR_SENSITIVITY, targetIso);
            }
            if (targetExposureNs > 0L) {
                mPreviewRequestBuilder.set(CaptureRequest.SENSOR_EXPOSURE_TIME, targetExposureNs);
                if (oldFrameDuration != null) {
                    mPreviewRequestBuilder.set(CaptureRequest.SENSOR_FRAME_DURATION,
                            Math.max(oldFrameDuration, targetExposureNs));
                }
            }

            mPreviewRequestBuilder.addTarget(rawSurface);
            targetAdded = true;
            CaptureRequest probe = mPreviewRequestBuilder.build();
            mPreviewRequestBuilder.removeTarget(rawSurface);
            targetAdded = false;
            m9LivePreviewProbeRequest = probe;

            // Restore the long-lived repeating builder BEFORE submitting the immutable probe.
            mPreviewRequestBuilder.set(CaptureRequest.CONTROL_AE_MODE, oldAe);
            mPreviewRequestBuilder.set(CaptureRequest.SENSOR_SENSITIVITY, oldIso);
            mPreviewRequestBuilder.set(CaptureRequest.SENSOR_EXPOSURE_TIME, oldExposure);
            mPreviewRequestBuilder.set(CaptureRequest.SENSOR_FRAME_DURATION, oldFrameDuration);

            mCaptureSession.capture(probe, m9LivePreviewCaptureCallback1A, mBackgroundHandler);
        } catch (Throwable t) {
            if (targetAdded) {
                try { mPreviewRequestBuilder.removeTarget(rawSurface); } catch (Throwable ignored) {}
            }
            try { mPreviewRequestBuilder.set(CaptureRequest.CONTROL_AE_MODE, oldAe); }
            catch (Throwable ignored) {}
            try { mPreviewRequestBuilder.set(CaptureRequest.SENSOR_SENSITIVITY, oldIso); }
            catch (Throwable ignored) {}
            try { mPreviewRequestBuilder.set(CaptureRequest.SENSOR_EXPOSURE_TIME, oldExposure); }
            catch (Throwable ignored) {}
            try { mPreviewRequestBuilder.set(CaptureRequest.SENSOR_FRAME_DURATION, oldFrameDuration); }
            catch (Throwable ignored) {}
            m9LivePreviewProbeInFlight.set(false);
            Log.w(TAG, "M9LIVEPREVIEW1C capturedomain RAW probe request failed: " + t);
        }
    }'''
c=c[:req_start]+new_req+c[req_end:]
controller.write_text(c)

# ---------------------------------------------------------------------------
# M9LivePreview1A: remap the ACTUAL probe RAW linearly (black-relative) into the
# predicted still exposure domain. The final renderer stays untouched.
# ---------------------------------------------------------------------------
p=preview.read_text()
import_anchor='import android.hardware.camera2.CaptureResult;\n'
if 'import android.hardware.camera2.params.BlackLevelPattern;' not in p:
    p=replace_once(p,import_anchor,
        import_anchor+'import android.hardware.camera2.params.BlackLevelPattern;\n',
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
p=replace_once(p,sig_old,sig_new,'preview render signature')

dims='''        final int dstW = srcW >= srcH ? LANDSCAPE_WIDTH : LANDSCAPE_HEIGHT;
        final int dstH = srcW >= srcH ? LANDSCAPE_HEIGHT : LANDSCAPE_WIDTH;
'''
dims_new=dims+'''        Integer probeIsoObj = captureResult != null
                ? captureResult.get(CaptureResult.SENSOR_SENSITIVITY) : null;
        Long probeExposureObj = captureResult != null
                ? captureResult.get(CaptureResult.SENSOR_EXPOSURE_TIME) : null;
        int probeIso = probeIsoObj != null ? probeIsoObj : -1;
        long probeExposureNs = probeExposureObj != null ? probeExposureObj : -1L;

        // If the result callback has not landed yet, the immutable probe request is the
        // best exposure-domain evidence. The request itself is already built at target.
        if (probeIso <= 0 && captureRequest != null) {
            Integer v = captureRequest.get(CaptureRequest.SENSOR_SENSITIVITY);
            if (v != null) probeIso = v;
        }
        if (probeExposureNs <= 0L && captureRequest != null) {
            Long v = captureRequest.get(CaptureRequest.SENSOR_EXPOSURE_TIME);
            if (v != null) probeExposureNs = v;
        }
        if (targetIso <= 0) targetIso = probeIso;
        if (targetExposureNs <= 0L) targetExposureNs = probeExposureNs;

        double exposureDomainScale = 1.0;
        if (targetIso > 0 && targetExposureNs > 0L
                && probeIso > 0 && probeExposureNs > 0L) {
            double targetEnergy = targetIso * (double) targetExposureNs;
            double probeEnergy = probeIso * (double) probeExposureNs;
            if (Double.isFinite(targetEnergy) && Double.isFinite(probeEnergy)
                    && targetEnergy > 0.0 && probeEnergy > 0.0) {
                exposureDomainScale = targetEnergy / probeEnergy;
                // A preview probe this far from target is not trustworthy enough for
                // arbitrary extrapolation. This wide guard is operational, not photographic.
                exposureDomainScale = Math.max(1.0 / 64.0,
                        Math.min(64.0, exposureDomainScale));
            }
        }
'''
p=replace_once(p,dims,dims_new,'exposure-domain derivation')

reduce_old='''        ByteBuffer packed = reduceBayerParityPreserving(raw, dstW, dstH);
'''
reduce_new='''        ByteBuffer packed = reduceBayerParityPreserving(
                raw, dstW, dstH, characteristics, exposureDomainScale);
'''
p=replace_once(p,reduce_old,reduce_new,'scaled Bayer reduction')

call_old='''        Bitmap out = M9R35Renderer.renderLivePreview1A(
                packed, dstW, dstH, characteristics, captureResult, captureRequest,
                sourceDescriptor1A, cameraRotation);
'''
call_new='''        Bitmap out = M9R35Renderer.renderLivePreview1A(
                packed, dstW, dstH, characteristics, captureResult, captureRequest,
                sourceDescriptor1A,
                targetIso, targetExposureNs, probeIso, probeExposureNs,
                exposureDomainScale, cameraRotation);
'''
p=replace_once(p,call_old,call_new,'renderer capturedomain call')

log_old='''                + " reduceMs=" + ((reduced - started) / 1_000_000.0)
                + " renderMs=" + ((finished - reduced) / 1_000_000.0));
'''
log_new='''                + " target=" + targetIso + "x" + targetExposureNs
                + " probe=" + probeIso + "x" + probeExposureNs
                + " domainScale=" + exposureDomainScale
                + " domainDeltaEv=" + (Math.log(exposureDomainScale) / Math.log(2.0))
                + " reduceMs=" + ((reduced - started) / 1_000_000.0)
                + " renderMs=" + ((finished - reduced) / 1_000_000.0));
'''
p=replace_once(p,log_old,log_new,'preview capturedomain log')

reduce_sig='''    private static ByteBuffer reduceBayerParityPreserving(Image raw, int dstW, int dstH) {
'''
reduce_sig_new='''    private static ByteBuffer reduceBayerParityPreserving(
            Image raw, int dstW, int dstH,
            CameraCharacteristics characteristics, double exposureDomainScale) {
'''
p=replace_once(p,reduce_sig,reduce_sig_new,'reducer signature')

alloc_anchor='''        ByteBuffer out = ByteBuffer.allocateDirect(dstW * dstH * 2).order(ByteOrder.LITTLE_ENDIAN);
        final double sxScale = srcW / (double) dstW;
'''
alloc_new='''        ByteBuffer out = ByteBuffer.allocateDirect(dstW * dstH * 2).order(ByteOrder.LITTLE_ENDIAN);
        BlackLevelPattern blackPattern = characteristics != null
                ? characteristics.get(CameraCharacteristics.SENSOR_BLACK_LEVEL_PATTERN) : null;
        Integer whiteObj = characteristics != null
                ? characteristics.get(CameraCharacteristics.SENSOR_INFO_WHITE_LEVEL) : null;
        final int whiteLevel = whiteObj != null ? whiteObj : 65535;
        final double sxScale = srcW / (double) dstW;
'''
p=replace_once(p,alloc_anchor,alloc_new,'reducer black/white metadata')

avg_old='''                int d = u16(src, rowStride, pixelStride, x1, y1);
                out.putShort((short)(((a + b + c + d + 2) >> 2) & 0xffff));
'''
avg_new='''                int d = u16(src, rowStride, pixelStride, x1, y1);
                int avg = (a + b + c + d + 2) >> 2;
                int black = 0;
                if (blackPattern != null) {
                    try {
                        black = blackPattern.getOffsetForIndex(x & 1, y & 1);
                    } catch (Throwable ignored) {}
                }
                int scaled = scaleExposureDomainCode(
                        avg, black, whiteLevel, exposureDomainScale);
                out.putShort((short)(scaled & 0xffff));
'''
p=replace_once(p,avg_old,avg_new,'black-relative scaling')

helper_anchor='''    private static int u16(ByteBuffer src, int rowStride, int pixelStride, int x, int y) {
'''
helper=r'''    private static int scaleExposureDomainCode(
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
p=replace_once(p,helper_anchor,helper+helper_anchor,'exposure-domain code helper')
preview.write_text(p)

# ---------------------------------------------------------------------------
# Renderer wrapper diagnostics only: record the mapping used by the live frame.
# No production render method or native asset is changed.
# ---------------------------------------------------------------------------
r=renderer.read_text()
field='''    private static final ThreadLocal<JSONObject> M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR = new ThreadLocal<>();
'''
field_new=field+'''    // M9LIVEPREVIEW1C: viewfinder-only physical-probe -> intended-still domain record.
    private static final ThreadLocal<JSONObject> M9_LIVE_PREVIEW_1C_EXPOSURE_DOMAIN =
            new ThreadLocal<>();
'''
r=replace_once(r,field,field_new,'renderer exposure-domain ThreadLocal')

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
set_new=set_anchor+'''        JSONObject exposureDomain1C = new JSONObject();
        exposureDomain1C.put("schema", "m9cam.livepreview.capturedomain.v1a");
        exposureDomain1C.put("revision", "M9LIVEPREVIEW1C_CAPTUREDOMAIN1A");
        exposureDomain1C.put("scope", "viewfinder_prediction_only");
        exposureDomain1C.put("finalJpegIsAuthority", true);
        exposureDomain1C.put("stillCaptureMutation", false);
        exposureDomain1C.put("stillToneMutation", false);
        exposureDomain1C.put("targetSource", "IsoExpoSelector_GenerateExpoPair_step_minus1");
        exposureDomain1C.put("targetIso", targetIso);
        exposureDomain1C.put("targetExposureTimeNs", targetExposureNs);
        exposureDomain1C.put("probeResultIso", probeIso);
        exposureDomain1C.put("probeResultExposureTimeNs", probeExposureNs);
        exposureDomain1C.put("probeToTargetLinearScale", exposureDomainScale);
        exposureDomain1C.put("probeToTargetEv",
                Math.log(Math.max(exposureDomainScale, 1.0e-12)) / Math.log(2.0));
        exposureDomain1C.put("rawScalingDomain",
                "black_relative_linear_Bayer_before_unchanged_M9_renderer");
        M9_LIVE_PREVIEW_1C_EXPOSURE_DOMAIN.set(exposureDomain1C);
'''
r=replace_once(r,set_anchor,set_new,'renderer exposure-domain set')

diag_anchor='''                    previewDiag.put("sourceGeometryAuthority",
                            "original_full_resolution_RAW_descriptor_retained_before_preview_reduction");
'''
diag_new=diag_anchor+'''                    previewDiag.put("previewExposureDomain1C",
                            M9_LIVE_PREVIEW_1C_EXPOSURE_DOMAIN.get());
'''
r=replace_once(r,diag_anchor,diag_new,'renderer preview diagnostic attach')

cleanup='''            M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR.remove();
            M9_LIVE_PREVIEW_1A_ACTIVE.remove();
'''
cleanup_new='''            M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR.remove();
            M9_LIVE_PREVIEW_1C_EXPOSURE_DOMAIN.remove();
            M9_LIVE_PREVIEW_1A_ACTIVE.remove();
'''
r=replace_once(r,cleanup,cleanup_new,'renderer exposure-domain cleanup')

# Let the 1B parity snapshot copy this preview-only record if a displayed frame exists.
key_anchor='''                    "targetFalloff1A"
'''
if key_anchor not in r:
    raise SystemExit('M9LIVEPREVIEW1C parity key-list anchor missing')
r=r.replace(key_anchor,'''                    "targetFalloff1A",
                    "previewExposureDomain1C"
''',1)

renderer.write_text(r)

if gradle.exists():
    g=gradle.read_text()
    m=re.search(r'versionName\s+["\']([^"\']+)["\']',g)
    if m and 'm9livepreview1c' not in m.group(1).lower():
        old=m.group(0); q='"' if '"' in old else "'"
        g=g.replace(old,'versionName '+q+m.group(1)+'-m9livepreview1c-capturedomain1a'+q,1)
        gradle.write_text(g)

print('M9LIVEPREVIEW1C_CAPTUREDOMAIN1A applied')
print(' - predicts current step-0 still exposure with IsoExpoSelector.GenerateExpoPair(-1)')
print(' - one-shot RAW probe is requested at predicted still ISO/shutter')
print(' - actual probe result is residual-scaled black-relative into exact target energy')
print(' - scale exists only in reduced viewfinder RAW; final still request/render untouched')
print(' - SAT2, TC20, TONEBOUND, curve02, M9 color and full-resolution renderer unchanged')
