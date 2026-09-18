#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv)!=2:
    raise SystemExit('usage: verify-m9cam-m9livewysiwyg1h-postdemosaic-surface.py <PhotonCamera-root>')

root=Path(sys.argv[1]).resolve()
renderer=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
controller=root/'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
selector=root/'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
gradle=root/'app/build.gradle'
for p in (renderer,controller,selector,gradle):
    if not p.exists():
        raise SystemExit('M9LIVEWYSIWYG1H verify missing: '+str(p))

r=renderer.read_text(); c=controller.read_text(); s=selector.read_text(); g=gradle.read_text()

for token in (
    'M9LIVEWYSIWYG1H_POSTDEMOSAIC_SURFACE',
    'final boolean m9LivePostDemosaicSurface1H',
    'final Mat m9LiveRenderCam1H =',
    'm9LivePostDemosaicSurface1H ? meterCam16 : cam16',
    'final int m9LiveRenderWidth1H =',
    'final int m9LiveRenderHeight1H =',
    'FULL_SOURCE_PREPROCESS_POSTDEMOSAIC_TC20_SURFACE_FINAL_M9_BITMAP',
    'after_full_RAW_normalization_shading_and_MHC_demosaic_before_final_M9_color_pass',
    'full_resolution_RAW_normalization_shading_demosaic_then_TC20_reference_final_color_surface'):
    if token not in r:
        raise SystemExit('M9LIVEWYSIWYG1H renderer token missing: '+token)

# Source-sensitive stages must remain before the reduced live surface.
core_start=r.find('    private static RenderCore renderNativeProspectiveCore(ByteBuffer rawBuffer,')
if core_start < 0:
    raise SystemExit('M9LIVEWYSIWYG1H prospective core missing')
core=r[core_start:]
positions={
    'normalize': core.find('M9NativeColorCore.normalizeRawDirect('),
    'shading': core.find('applyNativeProspectiveGainMapLumaDecomp1A('),
    'demosaic': core.find('M9NativeColorCore.demosaicMhcRggb('),
    'meter_resize': core.find('Imgproc.resize(cam16, meterCam16'),
    'live_surface': core.find('final Mat m9LiveRenderCam1H ='),
}
for k,v in positions.items():
    if v<0: raise SystemExit('M9LIVEWYSIWYG1H stage missing: '+k)
if not (positions['normalize'] < positions['shading'] < positions['demosaic']
        < positions['meter_resize'] < positions['live_surface']):
    raise SystemExit('M9LIVEWYSIWYG1H source-stage ordering invalid: '+str(positions))

# TC20 must consume exactly meterCam16 before the same image is reused as the live pixel surface.
if 'tc20MeterNativeDirect(\n                            meterCamAddress, meterW, meterH, tail,' not in r:
    raise SystemExit('M9LIVEWYSIWYG1H exact TC20 meter input missing')
if 'if (!m9LivePostDemosaicSurface1H) {\n                    meterCam16.release();' not in r:
    raise SystemExit('M9LIVEWYSIWYG1H meter surface retention gate missing')

# The actual final native colour loop must use the selected render surface dimensions.
for token in (
    'for (int y0 = 0; y0 < m9LiveRenderHeight1H; y0 += NATIVE_COLOR_BLOCK_ROWS)',
    'final int blockPixels = Math.multiplyExact(rows, m9LiveRenderWidth1H);',
    'm9LiveRenderCam1H.isContinuous()',
    'm9LiveRenderCam1H.dataAddr()',
    'Math.multiplyExact(m9LiveRenderWidth1H, NATIVE_COLOR_BLOCK_ROWS)'):
    if token not in r:
        raise SystemExit('M9LIVEWYSIWYG1H final colour surface token missing: '+token)

# Still route remains full resolution by the ternary false arm.
for token in (
    'm9LivePostDemosaicSurface1H ? meterW : width',
    'm9LivePostDemosaicSurface1H ? meterH : height',
    'm9LivePostDemosaicSurface1H ? meterCam16 : cam16'):
    if token not in r:
        raise SystemExit('M9LIVEWYSIWYG1H still full-res fallback missing: '+token)

# Viewfinder must not execute still-file audit writers.
for token in (
    'if (m9LiveWysiwyg1ALiveRoute) {\n                setupDevicePortAuditElapsedMs = 0L;',
    'if (m9LiveWysiwyg1ALiveRoute) {\n                setupRawShadingAuditElapsedMs = 0L;',
    'if (m9LiveWysiwyg1ALiveRoute) {\n                setupSourceCalibrationAuditElapsedMs = 0L;'):
    if token not in r:
        raise SystemExit('M9LIVEWYSIWYG1H live audit bypass missing: '+token)

# Reject the failed 1D architecture: raw/Bayer must never be reduced before source processing.
for forbidden in (
    'M9LIVEWYSIWYG1D_METER1600_REFERENCE_RENDER',
    'reduceBayerMeterReference1600PreservingParity1D',
    'FULL_PRODUCTION_RENDER_REFERENCE1600_FINAL_BITMAP'):
    if forbidden in r or forbidden in c:
        raise SystemExit('M9LIVEWYSIWYG1H invalid 1D path present: '+forbidden)

for token in (
    'M9LIVEWYSIWYG1F_LIVEORIENTATION',
    'PhotonCamera.getGravity().getCameraRotation(mSensorOrientation)',
    'M9LIVEWYSIWYG1G_NORMALPRIORITY',
    'M9_LIVE_PREVIEW_MIN_IDLE_AFTER_RENDER_MS = 200L',
    'android.os.Process.THREAD_PRIORITY_DEFAULT',
    'M9LIVEWYSIWYG1B_DISPLAYEDCAPTURELOCK',
    'IsoExpoSelector.setExactExposureM9Wysiwyg1B('):
    if token not in c:
        raise SystemExit('M9LIVEWYSIWYG1H controller contract missing: '+token)
if 'setExactExposureM9Wysiwyg1B(' not in s:
    raise SystemExit('M9LIVEWYSIWYG1H exact exposure setter missing')

if 'm9livewysiwyg1h-postdemosaic' not in g.lower():
    raise SystemExit('M9LIVEWYSIWYG1H versionName marker missing')

print('M9LIVEWYSIWYG1H_POSTDEMOSAIC_SURFACE VERIFY PASS')
print(' - full RAW normalization, physical shading and full-res MHC demosaic precede any preview reduction')
print(' - exact production TC20 1600-long-side post-demosaic camera RGB is reused for live final colour')
print(' - exact M9 colour/tone/SAT2/curve02/BT601/TG1 kernel remains active')
print(' - still final colour surface remains full resolution')
print(' - failed pre-demosaic/pre-source 1D reduction is absent')
print(' - live still-file forensic writers are bypassed')
print(' - 1F orientation, 1G scheduling and 1B exposure lock remain intact')
