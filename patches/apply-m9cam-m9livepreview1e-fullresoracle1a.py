#!/usr/bin/env python3
from pathlib import Path
import re, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m9livepreview1e-fullresoracle1a.py <PhotonCamera-root>')

root=Path(sys.argv[1]).resolve()
preview=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
renderer=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle=root/'app/build.gradle'
for p in (preview,renderer):
    if not p.exists(): raise SystemExit('M9LIVEPREVIEW1E missing '+str(p))

def replace_once(s, old, new, label):
    n=s.count(old)
    if n != 1:
        raise SystemExit(f'M9LIVEPREVIEW1E {label}: expected 1 anchor, found {n}')
    return s.replace(old,new,1)

p=preview.read_text()
for marker in (
        'M9LIVEPREVIEW1D exact paired probe exposure metadata missing',
        'scaleVirtualCaptureDomain1D',
        'exposureDomainScale',
        'renderLivePreview1A('):
    if marker not in p:
        raise SystemExit('M9LIVEPREVIEW1E 1D baseline marker missing: '+marker)
if 'M9LIVEPREVIEW1E_FULLRESORACLE1A' in p:
    raise SystemExit('M9LIVEPREVIEW1E already applied')

# The oracle deliberately renders the ORIGINAL RAW lattice. Display reduction happens only
# after the unchanged M9 renderer has completed all source normalization, TC20 and tone.
dims_old='''        final int dstW = srcW >= srcH ? LANDSCAPE_WIDTH : LANDSCAPE_HEIGHT;
        final int dstH = srcW >= srcH ? LANDSCAPE_HEIGHT : LANDSCAPE_WIDTH;
'''
dims_new='''        // M9LIVEPREVIEW1E_FULLRESORACLE1A:
        // run the exact M9 renderer at original RAW resolution; downscale only its final Bitmap.
        final int dstW = srcW;
        final int dstH = srcH;
'''
p=replace_once(p,dims_old,dims_new,'full-resolution oracle dimensions')

reduce_call='''        ByteBuffer packed = reduceBayerParityPreserving(raw, dstW, dstH, characteristics, exposureDomainScale);
'''
reduce_new='''        ByteBuffer packed = copyFullResolutionBayerVirtualDomain1E(
                raw, characteristics, exposureDomainScale);
'''
p=replace_once(p,reduce_call,reduce_new,'full-resolution RAW copy')

render_call='''        Bitmap out = M9R35Renderer.renderLivePreview1A(
                packed, dstW, dstH, characteristics, captureResult, captureRequest,
                sourceDescriptor1A, targetIso, targetExposureNs,
                probeIso, probeExposureNs, exposureDomainScale, cameraRotation);
        long finished = System.nanoTime();
'''
render_new='''        Bitmap fullRes = M9R35Renderer.renderLivePreview1A(
                packed, dstW, dstH, characteristics, captureResult, captureRequest,
                sourceDescriptor1A, targetIso, targetExposureNs,
                probeIso, probeExposureNs, exposureDomainScale, cameraRotation);
        if (fullRes == null) {
            throw new IllegalStateException("M9LIVEPREVIEW1E full-resolution M9 render returned null");
        }
        final int displayW = fullRes.getWidth() >= fullRes.getHeight()
                ? LANDSCAPE_WIDTH : LANDSCAPE_HEIGHT;
        final int displayH = fullRes.getWidth() >= fullRes.getHeight()
                ? LANDSCAPE_HEIGHT : LANDSCAPE_WIDTH;
        Bitmap out;
        if (fullRes.getWidth() == displayW && fullRes.getHeight() == displayH) {
            out = fullRes;
        } else {
            out = Bitmap.createScaledBitmap(fullRes, displayW, displayH, true);
            fullRes.recycle();
        }
        long finished = System.nanoTime();
'''
p=replace_once(p,render_call,render_new,'post-render display downscale')

log_anchor='''                + " virtualDeltaEv=" + (Math.log(exposureDomainScale) / Math.log(2.0))
                + " reduceMs=" + ((reduced - started) / 1_000_000.0)
'''
log_new='''                + " virtualDeltaEv=" + (Math.log(exposureDomainScale) / Math.log(2.0))
                + " oracle=FULL_RES_M9_THEN_DISPLAY_DOWNSCALE"
                + " source=" + srcW + "x" + srcH
                + " display=" + out.getWidth() + "x" + out.getHeight()
                + " reduceMs=" + ((reduced - started) / 1_000_000.0)
'''
p=replace_once(p,log_anchor,log_new,'oracle log')

# Add an exact full-resolution Bayer copy. This intentionally does NO spatial averaging.
helper_anchor='''    private static ByteBuffer reduceBayerParityPreserving(
'''
helper=r'''    private static ByteBuffer copyFullResolutionBayerVirtualDomain1E(
            Image raw,
            CameraCharacteristics characteristics,
            double exposureDomainScale) {
        if (raw == null || raw.getPlanes() == null || raw.getPlanes().length == 0) {
            throw new IllegalArgumentException("M9LIVEPREVIEW1E RAW plane missing");
        }
        final int width = raw.getWidth();
        final int height = raw.getHeight();
        Image.Plane plane = raw.getPlanes()[0];
        ByteBuffer src = plane.getBuffer().duplicate().order(ByteOrder.LITTLE_ENDIAN);
        final int rowStride = plane.getRowStride();
        final int pixelStride = plane.getPixelStride();

        BlackLevelPattern blackPattern = characteristics != null
                ? characteristics.get(CameraCharacteristics.SENSOR_BLACK_LEVEL_PATTERN) : null;
        Integer whiteObj = characteristics != null
                ? characteristics.get(CameraCharacteristics.SENSOR_INFO_WHITE_LEVEL) : null;
        final int whiteLevel = whiteObj != null ? whiteObj : 65535;

        ByteBuffer out = ByteBuffer.allocateDirect(width * height * 2)
                .order(ByteOrder.LITTLE_ENDIAN);
        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                int code = u16(src, rowStride, pixelStride, x, y);
                int black = 0;
                if (blackPattern != null) {
                    try { black = blackPattern.getOffsetForIndex(x & 1, y & 1); }
                    catch (Throwable ignored) {}
                }
                int mapped = scaleVirtualCaptureDomain1D(
                        code, black, whiteLevel, exposureDomainScale);
                out.putShort((short)(mapped & 0xffff));
            }
        }
        out.flip();
        return out;
    }

'''
p=replace_once(p,helper_anchor,helper+helper_anchor,'full-res copy helper')
preview.write_text(p)

# Renderer wrapper diagnostics only: label this as a full-resolution oracle.
r=renderer.read_text()
diag_anchor='''                    previewDiag.put("previewVirtualCaptureDomain1D",
                            M9_LIVE_PREVIEW_1D_VIRTUAL_DOMAIN.get());
'''
diag_new=diag_anchor+'''                    JSONObject fullResOracle1E = new JSONObject();
                    fullResOracle1E.put("schema", "m9cam.livepreview.fullresoracle.v1a");
                    fullResOracle1E.put("revision", "M9LIVEPREVIEW1E_FULLRESORACLE1A");
                    fullResOracle1E.put("sourceRaster", frame.width + "x" + frame.height);
                    fullResOracle1E.put("rendererDecisionRaster", "ORIGINAL_FULL_RESOLUTION_RAW");
                    fullResOracle1E.put("spatialReductionBeforeM9Renderer", false);
                    fullResOracle1E.put("displayReductionAfterM9Renderer", true);
                    fullResOracle1E.put("stillPhotographicMutation", false);
                    previewDiag.put("previewFullResOracle1E", fullResOracle1E);
'''
r=replace_once(r,diag_anchor,diag_new,'oracle diagnostics')

# Ensure 1B parity snapshot retains the oracle marker where available.
key_anchor='''                    "previewVirtualCaptureDomain1D"
            };'''
if key_anchor in r:
    r=r.replace(key_anchor,'''                    "previewVirtualCaptureDomain1D",
                    "previewFullResOracle1E"
            };''',1)

renderer.write_text(r)

if gradle.exists():
    g=gradle.read_text()
    m=re.search(r'versionName\s+["\']([^"\']+)["\']',g)
    if m and 'm9livepreview1e' not in m.group(1).lower():
        old=m.group(0); q='"' if '"' in old else "'"
        g=g.replace(old,'versionName '+q+m.group(1)+'-m9livepreview1e-fullresoracle1a'+q,1)
        gradle.write_text(g)

print('M9LIVEPREVIEW1E_FULLRESORACLE1A applied')
print(' - exact full-resolution RAW lattice enters unchanged M9 renderer')
print(' - no Bayer spatial reduction before source normalization/TC20/tone')
print(' - final rendered Bitmap alone is reduced to 1440x1080/1080x1440 for display')
print(' - virtual capture-domain mapping from 1D retained')
print(' - final still capture and JPEG path untouched')
