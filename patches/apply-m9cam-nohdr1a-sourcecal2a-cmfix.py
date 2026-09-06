#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-nohdr1a-sourcecal2a-cmfix.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root/'app').is_dir():
    raise SystemExit('NOHDR1A/SOURCECAL2A-CMFIX: not a PhotonCamera root')

def read(rel):
    p=root/rel
    if not p.exists(): raise SystemExit('missing expected file: '+rel)
    return p.read_text()
def write(rel,text):
    p=root/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text)
def once(text,old,new,label):
    if text.count(old)!=1: raise SystemExit(f'{label} anchor count={text.count(old)}')
    return text.replace(old,new,1)

frames_rel='app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
iso_rel='app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
renderer_rel='app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
source_rel='app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9SourceCalibrationAudit1A.java'

frames=read(frames_rel)
if 'M9_NOHDR1A_SINGLE_FRAME_BOUNDARY' in frames: raise SystemExit('NOHDR1A already applied')
if 'import com.particlesdevs.photoncamera.m9.M9Config;' not in frames:
    frames=once(frames,'import com.particlesdevs.photoncamera.app.PhotonCamera;\n','import com.particlesdevs.photoncamera.app.PhotonCamera;\nimport com.particlesdevs.photoncamera.m9.M9Config;\n','FrameNumberSelector import')
anchor='    public static int getFrames() {\n'
frames=once(frames,anchor,anchor+'''        // M9_NOHDR1A_SINGLE_FRAME_BOUNDARY
        CameraMode mode = PhotonCamera.getSettings().selectedMode;
        if (M9Config.usesM9Pipeline()
                && mode != CameraMode.UNLIMITED
                && mode != CameraMode.RAWVIDEO) {
            frameCount = 1;
            throwCount = 0;
            IsoExpoSelector.HDR = false;
            return 1;
        }
''','FrameNumberSelector getFrames')
write(frames_rel,frames)

iso=read(iso_rel)
if 'M9_NOHDR1A_EXPOSURE_ALLOCATOR' in iso: raise SystemExit('NOHDR1A allocator already applied')
if 'import com.particlesdevs.photoncamera.m9.M9Config;' not in iso:
    iso=once(iso,'import com.particlesdevs.photoncamera.app.PhotonCamera;\n','import com.particlesdevs.photoncamera.app.PhotonCamera;\nimport com.particlesdevs.photoncamera.m9.M9Config;\n','IsoExpoSelector import')
anchor='    public static ExpoPair GenerateExpoPair(int step, CaptureController captureController) {\n'
iso=once(iso,anchor,anchor+'''        // M9_NOHDR1A_EXPOSURE_ALLOCATOR
        // Bracketing preference may remain nonzero in UI, but cannot perturb M9 exposure.
        if (M9Config.usesM9Pipeline()) HDR = false;
''','IsoExpoSelector GenerateExpoPair')
write(iso_rel,iso)

renderer=read(renderer_rel)
start=renderer.find('    public static synchronized void preparePrimaryDiagnostics(')
end=renderer.find('\n    public static synchronized void recordBackgroundHandoffFailure',start)
if start<0 or end<0: raise SystemExit('preparePrimaryDiagnostics boundary missing')
m=renderer[start:end]
if 'M9_NOHDR1A_DIAGNOSTICS' in m: raise SystemExit('NOHDR diagnostics already applied')
anchor='            d.put("bufferedFrameCountAtTransfer", bufferedFrameCount);\n'
insert=anchor+'''            // M9_NOHDR1A_DIAGNOSTICS
            d.put("captureMode", "single_frame_raw");
            d.put("requestedFrameCount", 1);
            d.put("contributingRawFrameCount", 1);
            d.put("sourceFrameCount", 1);
            d.put("hdrExposureAllocatorEnabled", false);
            d.put("bracketingRequested", com.particlesdevs.photoncamera.settings.PreferenceKeys.getBracketingMode());
            d.put("bracketingEffective", false);
            d.put("isoExpoSelectorHdrEffective", false);
            d.put("multiFrameFusion", false);
            d.put("temporalMerge", false);
            d.put("hdrToneMapper", false);
            d.put("ultraHdrOutput", false);
            d.put("androidHdrGainmapUsed", false);
            d.put("outputEncoding", "SDR_JPEG");
'''
if m.count(anchor)!=1: raise SystemExit('NOHDR diagnostic anchor missing/non-unique')
m=m.replace(anchor,insert,1)
write(renderer_rel,renderer[:start]+m+renderer[end:])

source=read(source_rel)
old='''                Converter.normalizeFM(ncm1);
                Converter.normalizeFM(ncm2);
                Converter.normalizeFM(nfm1);
                Converter.normalizeFM(nfm2);
'''
new='''                // SOURCECAL2A_CMFIX: preserve DNG XYZ->camera ColorMatrix rows.
                // Only ForwardMatrix receives the D50 normalization convention.
                Converter.normalizeFM(nfm1);
                Converter.normalizeFM(nfm2);
'''
source=once(source,old,new,'SOURCECAL2A ColorMatrix normalization')
phase='            out.put("phase", "A_native_metadata_and_transform_audit");\n'
source=once(source,phase,phase+'''            out.put("sourceCalibrationRevision", "SOURCECAL2A_CMFIX");
            out.put("nativeColorMatrixNormalization", "none_preserve_DNG_XYZ_to_reference_camera");
            out.put("nativeForwardMatrixNormalization", "D50_forward_matrix_only");
            out.put("matrixStorageConvention", "row_major_getElement_row_column");
''','SOURCECAL2A diagnostic identity')
source=source.replace('"Photon_Converter_DNG_dual_illuminant_math_using_only_CameraCharacteristics_and_live_neutral"','"SOURCECAL2A_CMFIX_DNG_dual_illuminant_math_CM_unchanged_FM_D50_normalized_live_neutral"')
write(source_rel,source)

print('M9 NOHDR1A + SOURCECAL2A-CMFIX applied')
print(' - M9 still modes request exactly one RAW; IsoExpoSelector.HDR forced false')
print(' - diagnostics explicitly record SDR/no-fusion/no-Ultra-HDR contract')
print(' - ColorMatrix preserved row-major; ForwardMatrix-only D50 normalization')
