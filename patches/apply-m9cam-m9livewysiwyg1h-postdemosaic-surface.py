#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m9livewysiwyg1h-postdemosaic-surface.py <PhotonCamera-root>')

root=Path(sys.argv[1]).resolve()
renderer=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
controller=root/'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
selector=root/'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
gradle=root/'app/build.gradle'
for p in (renderer,controller,selector,gradle):
    if not p.exists():
        raise SystemExit('M9LIVEWYSIWYG1H missing assembled file: '+str(p))

def replace_once(text, old, new, label):
    n=text.count(old)
    if n!=1:
        raise SystemExit(f'M9LIVEWYSIWYG1H {label}: expected 1 anchor, found {n}')
    return text.replace(old,new,1)

def method_span(text, signature):
    start=text.find(signature)
    if start<0: raise SystemExit('method missing '+signature)
    brace=text.find('{',start); depth=0; state='code'; quote=''; esc=False; i=brace
    while i<len(text):
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
            elif ch in ('"',"'"): state='string'; quote=ch
            elif ch=='{': depth+=1
            elif ch=='}':
                depth-=1
                if depth==0: return start,i+1
        i+=1
    raise SystemExit('unterminated '+signature)

r=renderer.read_text()
c=controller.read_text()
s=selector.read_text()

for token in (
    'M9LIVEWYSIWYG1C_FULLSOURCE_FINALBOUNDARY',
    'FULL_PRODUCTION_RENDER_FULL_SOURCE_FINAL_BITMAP',
    'preRenderSourceReduction", false'):
    if token not in r:
        raise SystemExit('M9LIVEWYSIWYG1H requires 1C renderer token: '+token)
for token in (
    'M9LIVEWYSIWYG1F_LIVEORIENTATION',
    'M9LIVEWYSIWYG1G_NORMALPRIORITY'):
    if token not in c:
        raise SystemExit('M9LIVEWYSIWYG1H requires controller token: '+token)
if 'setExactExposureM9Wysiwyg1B(' not in s:
    raise SystemExit('M9LIVEWYSIWYG1H requires 1B exact exposure lock')

# Mark the live renderer architecture.
r=replace_once(
    r,
    '    private static final ThreadLocal<JSONObject> M9_LIVE_PREVIEW_1C_CAPTURE_EVIDENCE = new ThreadLocal<>();',
    '    private static final ThreadLocal<JSONObject> M9_LIVE_PREVIEW_1C_CAPTURE_EVIDENCE = new ThreadLocal<>();\n'
    '    // M9LIVEWYSIWYG1H_POSTDEMOSAIC_SURFACE: full RAW source preparation is retained;\n'
    '    // only the final M9 colour/tone pixel surface uses the existing TC20 post-demosaic reference.',
    '1H marker')

# Skip still-file forensic audit writers during live viewfinder rendering. They do not feed pixels.
old='''            M9DevicePortAudit1A.captureAndWrite(
                    dngPath,
                    frame.width,
                    frame.height,
                    frame.buffer != null ? frame.buffer.capacity() : -1,
                    params,
                    characteristics,
                    captureResult,
                    captureRequest);
            final long setupDevicePortAuditElapsedMs = (System.nanoTime() - setupTraceStageStartedNs) / 1_000_000L;
'''
new='''            final long setupDevicePortAuditElapsedMs;
            if (m9LiveWysiwyg1ALiveRoute) {
                setupDevicePortAuditElapsedMs = 0L;
            } else {
                M9DevicePortAudit1A.captureAndWrite(
                        dngPath,
                        frame.width,
                        frame.height,
                        frame.buffer != null ? frame.buffer.capacity() : -1,
                        params,
                        characteristics,
                        captureResult,
                        captureRequest);
                setupDevicePortAuditElapsedMs =
                        (System.nanoTime() - setupTraceStageStartedNs) / 1_000_000L;
            }
'''
r=replace_once(r,old,new,'live device audit bypass')

old='''            JSONObject rawShadingAudit1A = M9RawShadingAudit1A.captureAndWrite(
                    dngPath, frame.width, frame.height, params, characteristics,
                    diagnosticCaptureResult1A, captureRequest);
            final long setupRawShadingAuditElapsedMs = (System.nanoTime() - setupTraceStageStartedNs) / 1_000_000L;
            // BASISHSM1P-NATIVESOURCE1A: native Camera2/DNG source characterization is now the production source transform.
            setupTraceStageStartedNs = System.nanoTime();
            JSONObject sourceCalibrationAudit1A = M9SourceCalibrationAudit1A.captureAndWrite(
                    dngPath, params, characteristics, diagnosticCaptureResult1A);
            final long setupSourceCalibrationAuditElapsedMs = (System.nanoTime() - setupTraceStageStartedNs) / 1_000_000L;
'''
new='''            JSONObject rawShadingAudit1A = null;
            final long setupRawShadingAuditElapsedMs;
            if (m9LiveWysiwyg1ALiveRoute) {
                setupRawShadingAuditElapsedMs = 0L;
            } else {
                rawShadingAudit1A = M9RawShadingAudit1A.captureAndWrite(
                        dngPath, frame.width, frame.height, params, characteristics,
                        diagnosticCaptureResult1A, captureRequest);
                setupRawShadingAuditElapsedMs =
                        (System.nanoTime() - setupTraceStageStartedNs) / 1_000_000L;
            }
            // BASISHSM1P-NATIVESOURCE1A: native Camera2/DNG source characterization is now the production source transform.
            setupTraceStageStartedNs = System.nanoTime();
            JSONObject sourceCalibrationAudit1A = null;
            final long setupSourceCalibrationAuditElapsedMs;
            if (m9LiveWysiwyg1ALiveRoute) {
                setupSourceCalibrationAuditElapsedMs = 0L;
            } else {
                sourceCalibrationAudit1A = M9SourceCalibrationAudit1A.captureAndWrite(
                        dngPath, params, characteristics, diagnosticCaptureResult1A);
                setupSourceCalibrationAuditElapsedMs =
                        (System.nanoTime() - setupTraceStageStartedNs) / 1_000_000L;
            }
'''
r=replace_once(r,old,new,'live metadata audit bypass')

old='''            JSONObject stillSensorDescriptor1A = M9SensorDescriptor1A.fromImageFrame(
                    frame, params, characteristics, diagnosticCaptureResult1A, captureRequest).toJson();
'''
new='''            JSONObject stillSensorDescriptor1A = m9LiveWysiwyg1ALiveRoute
                    ? M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR.get()
                    : M9SensorDescriptor1A.fromImageFrame(
                            frame, params, characteristics, diagnosticCaptureResult1A, captureRequest).toJson();
'''
r=replace_once(r,old,new,'live descriptor reuse')

# Gate the new surface strictly to the live preview thread-local.
sig='    private static RenderCore renderNativeProspectiveCore(ByteBuffer rawBuffer,'
ms,me=method_span(r,sig)
m=r[ms:me]
anchor='''                                         boolean skinLumaStageAuditEnabled1A) throws Exception {
'''
m=replace_once(
    m,anchor,
    anchor+'''        final boolean m9LivePostDemosaicSurface1H =
                Boolean.TRUE.equals(M9_LIVE_PREVIEW_1A_ACTIVE.get());
''',
    'core live gate')

# Lift meter dimensions to method scope so the exact TC20 image can also feed the live pixel pass.
m=replace_once(
    m,
    '''            boolean meterCvDirectEligible = false;
            Meter meter = new Meter();
            if (meterParitySelfMeter) {
                long meterStartedNs = System.nanoTime();
                int meterW = width;
                int meterH = height;
''',
    '''            boolean meterCvDirectEligible = false;
            Meter meter = new Meter();
            int meterW = width;
            int meterH = height;
            if (meterParitySelfMeter) {
                long meterStartedNs = System.nanoTime();
''',
    'meter scope')

# Retain the meter image only for live preview; still releases at the original point.
m=replace_once(
    m,
    '''                nativeTc20ElapsedMs = (System.nanoTime() - nativeTc20StartedNs) / 1_000_000L;
                meterCam16.release();
                meterCam = null;
''',
    '''                nativeTc20ElapsedMs = (System.nanoTime() - nativeTc20StartedNs) / 1_000_000L;
                if (!m9LivePostDemosaicSurface1H) {
                    meterCam16.release();
                }
                meterCam = null;
''',
    'meter surface retention')

# Replace only the final colour-render block's spatial surface. Full RAW normalization,
# physical LensShadingMap, RAW-tail, MHC demosaic and TC20 remain full-source/exact.
block_start=m.find('            long fullRenderStartedNs = System.nanoTime();')
block_end_marker='            fullColorRenderElapsedMs = (System.nanoTime() - fullRenderStartedNs) / 1_000_000L;'
block_end=m.find(block_end_marker,block_start)
if block_start<0 or block_end<0:
    raise SystemExit('M9LIVEWYSIWYG1H full render block missing')
block_end += len(block_end_marker)
block=m[block_start:block_end]

prefix='''            final Mat m9LiveRenderCam1H =
                    m9LivePostDemosaicSurface1H ? meterCam16 : cam16;
            final int m9LiveRenderWidth1H =
                    m9LivePostDemosaicSurface1H ? meterW : width;
            final int m9LiveRenderHeight1H =
                    m9LivePostDemosaicSurface1H ? meterH : height;
            final int m9LiveRenderPixels1H =
                    Math.multiplyExact(m9LiveRenderWidth1H, m9LiveRenderHeight1H);
            long fullRenderStartedNs = System.nanoTime();'''
block=block.replace('            long fullRenderStartedNs = System.nanoTime();',prefix,1)
block=re.sub(r'\bcam16\b','m9LiveRenderCam1H',block)
block=re.sub(r'\bwidth\b','m9LiveRenderWidth1H',block)
block=re.sub(r'\bheight\b','m9LiveRenderHeight1H',block)
# The cleanup must release the full-resolution demosaic Mat in both paths, plus retained meter Mat for live.
block=block.replace(
    '            m9LiveRenderCam1H.release();',
    '''            if (m9LivePostDemosaicSurface1H && !meterCam16.empty()) {
                meterCam16.release();
            }
            if (!cam16.empty()) {
                cam16.release();
            }''',
    1)
m=m[:block_start]+block+m[block_end:]

# Add explicit diagnostics so a device capture proves where reduction occurs.
diag_anchor='''            d.put("meterReferenceLongSide", METER_LONG_SIDE);
'''
m=replace_once(
    m,diag_anchor,
    diag_anchor+'''            d.put("m9LivePreview1HPostDemosaicSurface", m9LivePostDemosaicSurface1H);
            d.put("m9LivePreview1HSourceRawWidth", width);
            d.put("m9LivePreview1HSourceRawHeight", height);
            d.put("m9LivePreview1HRenderSurfaceWidth", m9LivePostDemosaicSurface1H ? meterW : width);
            d.put("m9LivePreview1HRenderSurfaceHeight", m9LivePostDemosaicSurface1H ? meterH : height);
            d.put("m9LivePreview1HReductionBoundary",
                    m9LivePostDemosaicSurface1H
                            ? "after_full_RAW_normalization_LensShadingMap_MHC_demosaic_at_TC20_reference"
                            : "none_still_full_resolution");
''',
    '1H diagnostics')

r=r[:ms]+m+r[me:]

# Update live-route contract language. It remains full-source through demosaic; the final
# pixel surface is reduced only after all source-sensitive stages.
r=replace_once(
    r,
    '"FULL_PRODUCTION_RENDER_FULL_SOURCE_FINAL_BITMAP"',
    '"FULL_SOURCE_PREPROCESS_POSTDEMOSAIC_TC20_SURFACE_FINAL_M9_BITMAP"',
    'live preview mode')
r=replace_once(
    r,
    'previewDiag.put("postRenderDisplayDownscaleOnly", true);',
    '''previewDiag.put("postRenderDisplayDownscaleOnly", true);
                    previewDiag.put("postDemosaicPreviewSurface1H", true);
                    previewDiag.put("previewSurfaceBoundary",
                            "after_full_RAW_normalization_shading_and_MHC_demosaic_before_final_M9_color_pass");''',
    'preview boundary diag')
r=replace_once(
    r,
    '"full_resolution_RAW_is_renderer_input_no_pre_render_reduction"',
    '"full_resolution_RAW_normalization_shading_demosaic_then_TC20_reference_final_color_surface"',
    'source authority diag')

renderer.write_text(r)

g=gradle.read_text()
lines=g.splitlines(); changed=False
for i,line in enumerate(lines):
    stripped=line.strip()
    if stripped.startswith('versionName '):
        if 'm9livewysiwyg1h' not in stripped.lower():
            prefix=line[:len(line)-len(line.lstrip())]
            value=stripped[len('versionName '):].strip()
            quote='"' if value.startswith('"') else "'"
            if not (value.startswith(quote) and value.endswith(quote)):
                raise SystemExit('M9LIVEWYSIWYG1H unsupported versionName syntax: '+line)
            base=value[1:-1]
            lines[i]=prefix+'versionName '+quote+base+'-m9livewysiwyg1h-postdemosaic'+quote
            changed=True
        break
else:
    raise SystemExit('M9LIVEWYSIWYG1H versionName missing')
if changed:
    gradle.write_text('\n'.join(lines)+('\n' if g.endswith('\n') else ''))

print('M9LIVEWYSIWYG1H_POSTDEMOSAIC_SURFACE applied')
print(' - full RAW black/white normalization retained')
print(' - full-resolution physical LensShadingMap retained')
print(' - full-resolution MHC demosaic retained')
print(' - TC20 still meters its exact existing 1600-long-side post-demosaic camera RGB')
print(' - live final M9 colour/tone/SAT2/curve/BT601/TG1 renders that same TC20 reference surface')
print(' - still final colour pass remains full resolution')
print(' - live-only file/forensic audit writers bypassed; they never feed pixels')
print(' - 1F orientation, 1G scheduler, and 1B exposure lock remain outside renderer unchanged')
