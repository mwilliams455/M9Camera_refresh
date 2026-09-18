#!/usr/bin/env python3
from pathlib import Path
import re, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m9livepreview1f-fullmeter-reducedrender1a.py <PhotonCamera-root>')

root=Path(sys.argv[1]).resolve()
renderer=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
preview=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
gradle=root/'app/build.gradle'
for p in (renderer,preview):
    if not p.exists(): raise SystemExit('M9LIVEPREVIEW1F missing '+str(p))

def method_span(text, signature):
    start=text.find(signature)
    if start < 0: raise SystemExit('M9LIVEPREVIEW1F method missing: '+signature)
    brace=text.find('{',start)
    depth=0; state='code'; quote=''; esc=False; i=brace
    while i < len(text):
        ch=text[i]; nxt=text[i+1] if i+1<len(text) else ''
        if state=='line':
            if ch=='\n': state='code'
        elif state=='block':
            if ch=='*' and nxt=='/': state='code'; i+=1
        elif state=='string':
            if esc: esc=False
            elif ch=='\\': esc=True
            elif ch==quote: state='code'
        else:
            if ch=='/' and nxt=='/': state='line'; i+=1
            elif ch=='/' and nxt=='*': state='block'; i+=1
            elif ch in ('"',"'"): state='string'; quote=ch; esc=False
            elif ch=='{': depth+=1
            elif ch=='}':
                depth-=1
                if depth==0: return start,i+1
        i+=1
    raise SystemExit('M9LIVEPREVIEW1F unterminated method: '+signature)

def replace_once(s, old, new, label):
    n=s.count(old)
    if n != 1: raise SystemExit(f'M9LIVEPREVIEW1F {label}: expected 1 anchor, found {n}')
    return s.replace(old,new,1)

r=renderer.read_text()
for m in [
    'M9LIVEPREVIEW1D_VIRTUALCAPTUREDOMAIN1A',
    'M9LIVEPARITY1B_VIEWFINDER_REFERENCE',
    'm9cam.tonebound.v1a.050ev',
    'private static RenderCore renderNativeSourceProduction1P(',
    'private static RenderCore renderNativeProspectiveCore(',
]:
    if m not in r: raise SystemExit('M9LIVEPREVIEW1F baseline marker missing: '+m)
if 'M9LIVEPREVIEW1F_FULLMETER_REDUCEDRENDER1A' in r:
    raise SystemExit('M9LIVEPREVIEW1F already applied')

# State is preview-thread-local only. Still rendering never sets either flag.
field_anchor='''    private static final ThreadLocal<JSONObject> M9_LIVE_PREVIEW_1D_VIRTUAL_DOMAIN =
            new ThreadLocal<>();
'''
field_new=field_anchor+'''    // M9LIVEPREVIEW1F_FULLMETER_REDUCEDRENDER1A:
    // full-resolution source/tone decision; reduced-resolution color output.
    private static final ThreadLocal<Boolean> M9_LIVE_PREVIEW_1F_METER_ONLY =
            new ThreadLocal<>();
    private static final ThreadLocal<M9LiveDecision1F> M9_LIVE_PREVIEW_1F_DECISION =
            new ThreadLocal<>();
    private static final ThreadLocal<M9LiveDecision1F> M9_LIVE_PREVIEW_1F_OVERRIDE =
            new ThreadLocal<>();
'''
r=replace_once(r,field_anchor,field_new,'thread-local state')

# Add decision object before Meter class.
meter_class='    private static final class Meter {\n'
decision_class=r'''    private static final class M9LiveDecision1F {
        final double gain, baseGain, legacyGain, p98, guardGain, median;
        final int validCount;
        final long measuredNs;

        M9LiveDecision1F(Meter meter, long measuredNs) {
            this.gain = meter.gain;
            this.baseGain = meter.baseGain;
            this.legacyGain = meter.legacyGain;
            this.p98 = meter.p98;
            this.guardGain = meter.guardGain;
            this.median = meter.median;
            this.validCount = meter.validCount;
            this.measuredNs = measuredNs;
        }

        Meter toMeter() {
            Meter m = new Meter();
            m.gain = gain;
            m.baseGain = baseGain;
            m.legacyGain = legacyGain;
            m.p98 = p98;
            m.guardGain = guardGain;
            m.median = median;
            m.validCount = validCount;
            return m;
        }

        JSONObject toJson() throws Exception {
            JSONObject j = new JSONObject();
            j.put("schema", "m9cam.livepreview.fullmeter.v1a");
            j.put("revision", "M9LIVEPREVIEW1F_FULLMETER_REDUCEDRENDER1A");
            j.put("decisionSource", "full_resolution_RAW_source_path_plus_1600_long_side_TC20");
            j.put("fullResolutionColorRenderPerformed", false);
            j.put("tc20Gain", gain);
            j.put("baseMedianGain", baseGain);
            j.put("legacyGain", legacyGain);
            j.put("p98", Double.isFinite(p98) ? p98 : JSONObject.NULL);
            j.put("guardGain", guardGain);
            j.put("weightedMedian", Double.isFinite(median) ? median : JSONObject.NULL);
            j.put("validLumaCount", validCount);
            j.put("measuredElapsedMs", measuredNs / 1_000_000.0);
            return j;
        }
    }

'''
r=replace_once(r,meter_class,decision_class+meter_class,'decision class')

# Meter block: if preview has a full-resolution decision, skip reduced-frame TC20 and reuse it.
ps,pe=method_span(r,'    private static RenderCore renderNativeProspectiveCore(')
core=r[ps:pe]
meter_anchor='''            final boolean meterParitySelfMeter = selfMeter;
            boolean meterCvDirectEligible = false;
            Meter meter = new Meter();
            if (meterParitySelfMeter) {
'''
meter_new='''            final boolean meterParitySelfMeter = selfMeter;
            boolean meterCvDirectEligible = false;
            Meter meter = new Meter();
            final M9LiveDecision1F liveDecision1F =
                    M9_LIVE_PREVIEW_1F_OVERRIDE.get();
            if (meterParitySelfMeter && liveDecision1F != null) {
                // 1F: preserve the tone decision measured from the full RAW while keeping
                // the expensive color render on the reduced live raster.
                meter = liveDecision1F.toMeter();
                meterCam16.release();
                meterResizeElapsedMs = 0L;
                meterTransferElapsedMs = 0L;
                meterWeightElapsedMs = 0L;
                nativeTc20ElapsedMs = 0L;
                meterTc20ElapsedMs = 0L;
            } else if (meterParitySelfMeter) {
'''
if core.count(meter_anchor)!=1:
    raise SystemExit('M9LIVEPREVIEW1F meter anchor count='+str(core.count(meter_anchor)))
core=core.replace(meter_anchor,meter_new,1)

# Capture full-resolution decision after TONEBOUND inputs exist but before any color render.
tone_anchor='''            final JSONObject toneForensics1AJson = toneForensics1A(
                    meter, tail, edgePlacementGainEv, effectiveRenderGain, meterParitySelfMeter);
'''
if core.count(tone_anchor)!=1:
    raise SystemExit('M9LIVEPREVIEW1F tone-forensics anchor count='+str(core.count(tone_anchor)))
tone_new=tone_anchor+'''            if (Boolean.TRUE.equals(M9_LIVE_PREVIEW_1F_METER_ONLY.get())) {
                M9_LIVE_PREVIEW_1F_DECISION.set(
                        new M9LiveDecision1F(meter, System.nanoTime()));
                JSONObject meterOnly = new JSONObject();
                meterOnly.put("schema", "m9cam.livepreview.fullmeter.v1a");
                meterOnly.put("revision", "M9LIVEPREVIEW1F_FULLMETER_REDUCEDRENDER1A");
                meterOnly.put("meterOnly", true);
                meterOnly.put("fullResolutionColorRenderPerformed", false);
                meterOnly.put("inputWidth", width);
                meterOnly.put("inputHeight", height);
                meterOnly.put("tc20MeterLongSide", METER_LONG_SIDE);
                meterOnly.put("gain", meter.gain);
                meterOnly.put("baseMedianGain", meter.baseGain);
                meterOnly.put("tc20GuardGain", meter.guardGain);
                meterOnly.put("toneBound1A", toneBound1AJson);
                meterOnly.put("toneForensics1A", toneForensics1AJson);
                return new RenderCore(null, meterOnly);
            }
'''
core=core.replace(tone_anchor,tone_new,1)

# Diagnostics on reduced color render say that TC20 was inherited from full source decision.
diag_anchor='''            d.put("tc20TailValue", tail.tailValue);
'''
if core.count(diag_anchor)!=1:
    raise SystemExit('M9LIVEPREVIEW1F diagnostic anchor count='+str(core.count(diag_anchor)))
diag_new=diag_anchor+'''            d.put("livePreviewFullMeter1FOverrideApplied", liveDecision1F != null);
            if (liveDecision1F != null) {
                d.put("livePreviewFullMeter1F", liveDecision1F.toJson());
            }
'''
core=core.replace(diag_anchor,diag_new,1)
r=r[:ps]+core+r[pe:]

# renderAndSaveInternal must return cleanly for the meter-only pass before bitmap/file handling.
rs,re_=method_span(r,'    private static Result renderAndSaveInternal(')
method=r[rs:re_]
bitmap_anchor='''            bitmap = out.bitmap;
'''
if method.count(bitmap_anchor)!=1:
    raise SystemExit('M9LIVEPREVIEW1F render wrapper bitmap anchor count='+str(method.count(bitmap_anchor)))
meter_return='''            if (Boolean.TRUE.equals(M9_LIVE_PREVIEW_1F_METER_ONLY.get())) {
                if (M9_LIVE_PREVIEW_1F_DECISION.get() == null) {
                    throw new IllegalStateException("M9LIVEPREVIEW1F full meter produced no decision");
                }
                return new Result(true, null, null, null, out.diagnostics, null);
            }
            bitmap = out.bitmap;
'''
method=method.replace(bitmap_anchor,meter_return,1)
r=r[:rs]+method+r[re_:]

# Public wrapper: run production source path meter-only on full RAW, then ordinary reduced
# preview render with the full-source Meter injected. No full-res color bitmap is ever made.
wrapper_anchor='''    /** M9LIVEPREVIEW1A_FULLRENDER720P: exact primary pipeline, no file side effects. */
'''
wi=r.find(wrapper_anchor)
if wi<0: raise SystemExit('M9LIVEPREVIEW1F public wrapper insertion anchor missing')
wrapper=r'''    /**
     * M9LIVEPREVIEW1F: full-resolution source/tone decision, reduced-resolution color render.
     * Still path is unchanged because both thread-locals exist only on this preview worker.
     */
    public static Bitmap renderLivePreviewSplit1F(ByteBuffer fullPackedRaw,
                                                  int fullWidth,
                                                  int fullHeight,
                                                  ByteBuffer reducedPackedRaw,
                                                  int reducedWidth,
                                                  int reducedHeight,
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
        if (fullPackedRaw == null || reducedPackedRaw == null) {
            throw new IllegalArgumentException("M9LIVEPREVIEW1F missing RAW buffers");
        }
        M9_LIVE_PREVIEW_1F_DECISION.remove();
        M9_LIVE_PREVIEW_1F_OVERRIDE.remove();

        ImageFrame fullFrame = new ImageFrame(fullPackedRaw);
        fullFrame.width = fullWidth;
        fullFrame.height = fullHeight;
        long meterStarted = System.nanoTime();
        try {
            M9_LIVE_PREVIEW_1F_METER_ONLY.set(Boolean.TRUE);
            Path synthetic = Paths.get(FileManager.sDCIM_CAMERA.getAbsolutePath(),
                    "M9LIVEPREVIEW1F_METER_ONLY.dng");
            Result meterResult = renderAndSaveInternal(synthetic, fullFrame,
                    characteristics, captureResult, captureRequest, cameraRotation, true);
            if (!meterResult.success) {
                throw new IllegalStateException(
                        "M9LIVEPREVIEW1F full-source meter failed: " + meterResult.error);
            }
        } finally {
            M9_LIVE_PREVIEW_1F_METER_ONLY.remove();
            fullFrame.close();
        }

        M9LiveDecision1F decision = M9_LIVE_PREVIEW_1F_DECISION.get();
        if (decision == null) {
            throw new IllegalStateException("M9LIVEPREVIEW1F full-source decision missing");
        }
        long measuredNs = System.nanoTime() - meterStarted;
        decision = new M9LiveDecision1F(decision.toMeter(), measuredNs);

        try {
            M9_LIVE_PREVIEW_1F_OVERRIDE.set(decision);
            return renderLivePreview1A(
                    reducedPackedRaw, reducedWidth, reducedHeight,
                    characteristics, captureResult, captureRequest,
                    sourceDescriptor1A,
                    targetIso, targetExposureNs, probeIso, probeExposureNs,
                    exposureDomainScale, cameraRotation);
        } finally {
            M9_LIVE_PREVIEW_1F_OVERRIDE.remove();
            M9_LIVE_PREVIEW_1F_DECISION.remove();
        }
    }

'''
r=r[:wi]+wrapper+r[wi:]
renderer.write_text(r)

# Preview facade: produce both a full-resolution virtual-domain RAW copy and the 1440x1080
# display RAW. Full copy is used only through the meter-only path; reduced copy is rendered.
p=preview.read_text()
call_old='''        ByteBuffer packed = reduceBayerParityPreserving(raw, dstW, dstH, characteristics, exposureDomainScale);
        long reduced = System.nanoTime();
        Bitmap out = M9R35Renderer.renderLivePreview1A(
                packed, dstW, dstH, characteristics, captureResult, captureRequest,
                sourceDescriptor1A, targetIso, targetExposureNs,
                probeIso, probeExposureNs, exposureDomainScale, cameraRotation);
'''
call_new='''        ByteBuffer fullPacked = copyFullResolutionVirtualDomain1F(
                raw, characteristics, exposureDomainScale);
        long fullCopied = System.nanoTime();
        ByteBuffer packed = reduceBayerParityPreserving(
                raw, dstW, dstH, characteristics, exposureDomainScale);
        long reduced = System.nanoTime();
        Bitmap out = M9R35Renderer.renderLivePreviewSplit1F(
                fullPacked, srcW, srcH,
                packed, dstW, dstH,
                characteristics, captureResult, captureRequest,
                sourceDescriptor1A, targetIso, targetExposureNs,
                probeIso, probeExposureNs, exposureDomainScale, cameraRotation);
'''
p=replace_once(p,call_old,call_new,'split render call')

log_anchor='''                + " virtualDeltaEv=" + (Math.log(exposureDomainScale) / Math.log(2.0))
                + " reduceMs=" + ((reduced - started) / 1_000_000.0)
'''
log_new='''                + " virtualDeltaEv=" + (Math.log(exposureDomainScale) / Math.log(2.0))
                + " mode=FULL_SOURCE_METER_REDUCED_COLOR_RENDER"
                + " fullCopyMs=" + ((fullCopied - started) / 1_000_000.0)
                + " reduceMs=" + ((reduced - fullCopied) / 1_000_000.0)
'''
p=replace_once(p,log_anchor,log_new,'split timing log')

helper_anchor='''    private static ByteBuffer reduceBayerParityPreserving(
'''
full_helper=r'''    private static ByteBuffer copyFullResolutionVirtualDomain1F(
            Image raw,
            CameraCharacteristics characteristics,
            double exposureDomainScale) {
        Image.Plane[] planes = raw.getPlanes();
        if (planes == null || planes.length == 0) {
            throw new IllegalArgumentException("M9LIVEPREVIEW1F RAW plane missing");
        }
        Image.Plane plane = planes[0];
        ByteBuffer src = plane.getBuffer().duplicate().order(ByteOrder.LITTLE_ENDIAN);
        int width = raw.getWidth();
        int height = raw.getHeight();
        int rowStride = plane.getRowStride();
        int pixelStride = plane.getPixelStride();
        BlackLevelPattern blackPattern = characteristics != null
                ? characteristics.get(CameraCharacteristics.SENSOR_BLACK_LEVEL_PATTERN) : null;
        Integer whiteObj = characteristics != null
                ? characteristics.get(CameraCharacteristics.SENSOR_INFO_WHITE_LEVEL) : null;
        int whiteLevel = whiteObj != null ? whiteObj : 65535;
        ByteBuffer out = ByteBuffer.allocateDirect(width * height * 2)
                .order(ByteOrder.LITTLE_ENDIAN);
        for (int y=0; y<height; y++) {
            for (int x=0; x<width; x++) {
                int code = u16(src,rowStride,pixelStride,x,y);
                int black=0;
                if (blackPattern != null) {
                    try { black=blackPattern.getOffsetForIndex(x & 1, y & 1); }
                    catch (Throwable ignored) {}
                }
                int mapped=scaleVirtualCaptureDomain1D(
                        code,black,whiteLevel,exposureDomainScale);
                out.putShort((short)(mapped & 0xffff));
            }
        }
        out.flip();
        return out;
    }

'''
p=replace_once(p,helper_anchor,full_helper+helper_anchor,'full copy helper')
preview.write_text(p)

if gradle.exists():
    g=gradle.read_text()
    m=re.search(r'versionName\s+["\']([^"\']+)["\']',g)
    if m and 'm9livepreview1f' not in m.group(1).lower():
        old=m.group(0); q='"' if '"' in old else "'"
        g=g.replace(old,'versionName '+q+m.group(1)+'-m9livepreview1f-fullmeter-reducedrender1a'+q,1)
        gradle.write_text(g)

print('M9LIVEPREVIEW1F_FULLMETER_REDUCEDRENDER1A applied')
print(' - full RAW runs source normalization + demosaic + 1600-side TC20 only')
print(' - full-resolution M9 color render is skipped')
print(' - reduced 1440x1080 color render inherits full-source TC20 decision')
print(' - still JPEG/capture exposure/SAT2/curve02/TONEBOUND policy unchanged')
