#!/usr/bin/env python3
from pathlib import Path
import hashlib
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-fixedgain1a-nativeab1a.py <PhotonCamera-root>')
root=Path(sys.argv[1]).resolve()
if not (root/'app').is_dir(): raise SystemExit('FIXEDGAIN1A/NATIVEAB1A: not a PhotonCamera root')
P=Path(__file__).resolve().parent
renderer_rel='app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_rel='app/build.gradle'

def read(rel):
    p=root/rel
    if not p.exists(): raise SystemExit('missing expected file: '+rel)
    return p.read_text()
def write(rel,text):
    p=root/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text)
def sha(rel): return hashlib.sha256((root/rel).read_bytes()).hexdigest()
def replace_once(text,old,new,label):
    if text.count(old)!=1: raise SystemExit(f'{label} anchor count={text.count(old)}')
    return text.replace(old,new,1)
def extract_top_method(text,marker):
    start=text.find(marker)
    if start<0: raise SystemExit('method marker missing: '+marker)
    end=text.find('\n    private static ',start+len(marker))
    if end<0: raise SystemExit('next method marker missing: '+marker)
    m=text[start:end].rstrip('\n')
    return start,start+len(m),m

# Requires the preceding NOHDR1A/SOURCECAL2A-CMFIX stage.
if 'M9_NOHDR1A_SINGLE_FRAME_BOUNDARY' not in read('app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'):
    raise SystemExit('FIXEDGAIN1A requires NOHDR1A')
if 'SOURCECAL2A_CMFIX' not in read('app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9SourceCalibrationAudit1A.java'):
    raise SystemExit('NATIVEAB1A requires SOURCECAL2A-CMFIX')

frozen_rels=[
 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
 'app/src/main/java/com/particlesdevs/photoncamera/processing/DngCreator.java',
 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java',
 'app/src/main/cpp/m9color_jni.cpp',
 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java',
 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java',
 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9JpegFinalizeQueue.java',
 'app/src/main/java/com/particlesdevs/photoncamera/processing/ImageSaver.java',
]
frozen_before={rel:sha(rel) for rel in frozen_rels}
_,_,primary_render_core_before=extract_top_method(read(renderer_rel),'    private static RenderCore renderCore(')
primary_render_core_sha=hashlib.sha256(primary_render_core_before.encode('utf-8')).hexdigest()

# -----------------------------------------------------------------------------
# 3/4) Reuse the prior additive prospective scaffolding, but transform it before
# execution so the generated method has corrected CM convention, row-major Camera2
# matrices, no private Converter calls, optional shading, and no independent TC20.
# The primary renderCore remains byte-identical.
# -----------------------------------------------------------------------------
old_apply = P / 'apply-m9cam-nativeprospective1a.py'
if not old_apply.exists():
    raise SystemExit('NATIVEAB1A missing prior prospective scaffolding: ' + str(old_apply))
text = old_apply.read_text()

# Run-409 extractor fix.
old_extractor = '''def extract_method(text, marker):\n    start = text.find(marker)\n    if start < 0:\n        raise SystemExit('NATIVEPROSPECTIVE1A method marker missing: ' + marker)\n    brace = text.find('{', start)\n    if brace < 0:\n        raise SystemExit('NATIVEPROSPECTIVE1A method opening brace missing')\n    depth = 0\n    i = brace\n    in_string = False\n    string_quote = ''\n    escape = False\n    while i < len(text):\n        ch = text[i]\n        if in_string:\n            if escape:\n                escape = False\n            elif ch == '\\\\':\n                escape = True\n            elif ch == string_quote:\n                in_string = False\n        else:\n            if ch in ('\"', "'"):\n                in_string = True\n                string_quote = ch\n            elif ch == '{':\n                depth += 1\n            elif ch == '}':\n                depth -= 1\n                if depth == 0:\n                    return start, i + 1, text[start:i + 1]\n        i += 1\n    raise SystemExit('NATIVEPROSPECTIVE1A unterminated method')\n'''
new_extractor = '''def extract_method(text, marker):\n    start = text.find(marker)\n    if start < 0:\n        raise SystemExit('NATIVEPROSPECTIVE1A method marker missing: ' + marker)\n    end = text.find('\\n    private static ', start + len(marker))\n    if end < 0:\n        raise SystemExit('NATIVEPROSPECTIVE1A next top-level method marker missing after: ' + marker)\n    method = text[start:end].rstrip('\\n')\n    return start, start + len(method), method\n'''
text = replace_once(text, old_extractor, new_extractor, 'NATIVEAB1A extractor')

# Generated prospective signature: primary edge EV is diagnostic; fixedPrimaryGain is
# the actual exposure placement. applyNativeShading separates the two A/B outputs.
old_sig = '''new_sig_tail = ''' + "'''" + '''                                         int cameraRotation,\n                                         double edgePlacementGainEv,\n                                         CameraCharacteristics nativeCharacteristics,\n                                         CaptureResult nativeCaptureResult) throws Exception {''' + "'''"
new_sig = '''new_sig_tail = ''' + "'''" + '''                                         int cameraRotation,\n                                         double edgePlacementGainEv,\n                                         CameraCharacteristics nativeCharacteristics,\n                                         CaptureResult nativeCaptureResult,\n                                         double fixedPrimaryGain,\n                                         boolean applyNativeShading) throws Exception {''' + "'''"
text = replace_once(text, old_sig, new_sig, 'NATIVEAB1A generated signature')

old_shade_call = '''        NativeProspectiveShadingStats nativeShading = applyNativeProspectiveGainMap(\n                norm16, width, height, nativeLiveGainMap);'''
new_shade_call = '''        NativeProspectiveShadingStats nativeShading = applyNativeShading\n                ? applyNativeProspectiveGainMap(norm16, width, height, nativeLiveGainMap)\n                : NativeProspectiveShadingStats.none();'''
text = replace_once(text, old_shade_call, new_shade_call, 'NATIVEAB1A optional shading call')

# Correct ColorMatrix handling in the generated native source adapter.
text = text.replace('        Converter.normalizeFM(ncm1);\n        Converter.normalizeFM(ncm2);\n', '')

# Camera2 ColorSpaceTransform must be read as getElement(row,column), matching the
# reviewed DNG metadata convention rather than Converter.convertColorspaceTransform's transpose.
old_transform = '''        float[] out = new float[9];\n        Converter.convertColorspaceTransform(transform, out);\n        return out;'''
new_transform = '''        float[] out = new float[9];\n        for (int r = 0; r < 3; r++) {\n            for (int c = 0; c < 3; c++) {\n                Rational v = transform.getElement(r, c);\n                out[r * 3 + c] = v != null ? v.floatValue() : Float.NaN;\n            }\n        }\n        return out;'''
text = replace_once(text, old_transform, new_transform, 'NATIVEAB1A row-major ColorSpaceTransform')

# Do not call Converter.lerp/invert, which are private in the pinned upstream.
old_scene = '''        float[] xyzToCamera = new float[9];\n        Converter.lerp(xyzToCamera1, xyzToCamera2, factor, xyzToCamera);\n        float[] cameraToXyzScene = new float[9];\n        if (!Converter.invert(xyzToCamera, cameraToXyzScene)) {\n            throw new IllegalStateException("native prospective cannot invert interpolated XYZ->camera matrix");\n        }\n        float[] whiteXyz = new float[3];\n        Converter.map(cameraToXyzScene, neutral, whiteXyz);\n        double sum = (double)whiteXyz[0] + whiteXyz[1] + whiteXyz[2];\n'''
new_scene = '''        float[] xyzToCamera = new float[9];\n        for (int i = 0; i < 9; i++) {\n            xyzToCamera[i] = (float)(xyzToCamera1[i] * (1.0 - factor) + xyzToCamera2[i] * factor);\n        }\n        double[] cameraToXyzScene = inverse3(nativeProspectiveDouble(xyzToCamera));\n        double[] whiteXyz = matVec3(cameraToXyzScene, nativeProspectiveDouble(neutral));\n        double sum = whiteXyz[0] + whiteXyz[1] + whiteXyz[2];\n'''
text = replace_once(text, old_scene, new_scene, 'NATIVEAB1A scene-white inversion')

# Inject a fixed-gain replacement into the copied prospective method after its source
# context has been swapped. This removes the entire meter resize/luma/TC20 selection.
needle = "prospective = prospective.replace(color_old, color_new, 1)\n"
fixed_meter_transform = needle + r"""

meter_start = prospective.find('            long meterStartedNs = System.nanoTime();')
meter_end = prospective.find('            long fullRenderStartedNs = System.nanoTime();', meter_start)
if meter_start < 0 or meter_end < 0:
    raise SystemExit('NATIVEAB1A copied TC20 block boundary missing')
fixed_meter = '''            // FIXEDGAIN1A: same-frame primary exposure decision is injected by the caller.
            // Do not resize/remeter the source-changed pixels in this scientific A/B.
            final boolean meterCvDirectEligible = false;
            meterCam16.release();
            Meter meter = new Meter();
            meter.gain = fixedPrimaryGain;
            meter.baseGain = fixedPrimaryGain;
            meter.legacyGain = fixedPrimaryGain;
            meter.guardGain = fixedPrimaryGain;
            meter.p98 = Double.NaN;
            meterResizeElapsedMs = 0L;
            meterTransferElapsedMs = 0L;
            meterWeightElapsedMs = 0L;
            nativeTc20ElapsedMs = 0L;
            meterTc20ElapsedMs = 0L;
            // Shading uses a representation-only scale to keep corrected Bayer samples inside
            // uint16 without clipping valid single-frame headroom. Restore that global scale
            // at the existing linear render-gain boundary; it is not a new exposure decision.
            final double effectiveRenderGain = fixedPrimaryGain * nativeShading.representationScale;

'''
prospective = prospective[:meter_start] + fixed_meter + prospective[meter_end:]
"""
text = replace_once(text, needle, fixed_meter_transform, 'FIXEDGAIN1A meter transform injection')

# Distinct build identity; the post-exec cleanup below will remove the old prospective name.
text = text.replace("'-nativeprospective1a'", "'-nohdr1a-sourcecal2a-cmfix-fixedgain1a-nativeab1a'")

# Execute the transformed additive scaffolding against the assembled Photon tree.
code = compile(text, str(old_apply), 'exec')
g = {'__name__': '__main__', '__file__': str(old_apply)}
exec(code, g, g)

# -----------------------------------------------------------------------------
# 4a) Replace the old single prospective output hook with controlled MAIN-only A/B.
# -----------------------------------------------------------------------------
renderer = read(renderer_rel)
hook_start_marker = '''            if (primaryRoute) {\n                Path nativeProspectivePath = Paths.get(FileManager.sDCIM_CAMERA.getAbsolutePath(),\n                        stem + "_M9_NATIVEPROSPECTIVE.jpg");'''
hook_start = renderer.find(hook_start_marker)
hook_end_marker = '''\n            // Do not overwrite capture-time lastDiagnostics here: a later shutter may already\n'''
hook_end = renderer.find(hook_end_marker, hook_start)
if hook_start < 0 or hook_end < 0:
    raise SystemExit('NATIVEAB1A old prospective hook boundary missing')

new_hook = (P / 'fragments/nativeab1a-hook.javafrag').read_text()
renderer = renderer[:hook_start] + new_hook + renderer[hook_end:]

# -----------------------------------------------------------------------------
# 4b) Headroom-safe LensShadingMap implementation. Scale the entire corrected plane
# by maxGain for uint16 representation and restore that constant later at fixed gain.
# This preserves intended >1.0 single-frame values instead of clipping them to 1.0.
# -----------------------------------------------------------------------------
class_start = renderer.find('    private static final class NativeProspectiveShadingStats {')
func_start = renderer.find('    private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(', class_start)
func_end = renderer.find('\n    }', func_start)
if class_start < 0 or func_start < 0 or func_end < 0:
    raise SystemExit('NATIVEAB1A shading helper boundary missing')
# Need the full method's closing brace; simple search above lands at first nested brace. Use brace count.
def java_method_end(src, start):
    brace = src.find('{', start)
    depth = 0
    i = brace
    while i < len(src):
        if src[i] == '{': depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0: return i + 1
        i += 1
    raise SystemExit('unterminated Java helper method')
func_end = java_method_end(renderer, func_start)
new_shading_helpers = (P / 'fragments/nativeab1a-shading.javafrag').read_text()
renderer = renderer[:class_start] + new_shading_helpers + renderer[func_end:]

# Update prospective diagnostics to make isolation explicit.
renderer = renderer.replace('"m9cam.renderer.nativeprospective.v1a.sourceadapter1a"', '"m9cam.renderer.nativeab.v1a.main.fixedgain"')
renderer = renderer.replace('"NATIVEPROSPECTIVE1A additive Cobalt-source-bypass branch; frozen primary renderCore preserved"',
                            '"NATIVEAB1A corrected native source adapter; same-RAW fixed-primary-gain experimental branch"')
renderer = renderer.replace('"physical live Bayer GainMap once -> EA demosaic -> native Camera2 dual-illuminant sensor->XYZ D50 -> ProPhoto identity-HSM -> M9 target bridge -> frozen TC20 -> SAT3 M06/M07 -> curve02 -> exact BT601 4:2:2 -> TG1"',
                            '"optional live Bayer LensShadingMap once -> EA demosaic -> corrected native Camera2 sensor->XYZ D50 -> ProPhoto identity-HSM -> M9 target bridge -> frozen primary gain -> SAT3 M06/M07 -> curve02 -> exact BT601 4:2:2 -> TG1"')
renderer = renderer.replace('            d.put("gainMapAppliedToRender", true);\n',
                            '            d.put("gainMapAppliedToRender", nativeShading.applied);\n')
renderer = renderer.replace('            d.put("gainMapApplicationCount", 1);\n',
                            '            d.put("gainMapApplicationCount", nativeShading.applied ? 1 : 0);\n')
renderer = renderer.replace('            d.put("gainMapApplicationStage", "normalized_linear_Bayer_pre_demosaic");\n',
                            '            d.put("gainMapApplicationStage", nativeShading.applied ? "normalized_linear_Bayer_pre_demosaic_headroom_preserved" : "none");\n')
extra_diag_anchor = '            d.put("gainMapCorrectedPixelCount", nativeShading.correctedPixels);\n'
extra_diag = extra_diag_anchor + '''            d.put("gainMapRepresentationScale", nativeShading.representationScale);\n            d.put("gainMapAboveNominalBeforeRepresentationScale", nativeShading.aboveNominalBeforeScale);\n            d.put("gainMapPostScaleClipCount", nativeShading.postScaleClipCount);\n            d.put("singleFrameLinearHeadroomPreserved", nativeShading.postScaleClipCount == 0);\n            d.put("tc20DecisionSource", "frozen_primary_same_frame");\n            d.put("prospectiveMeterRecomputed", false);\n            d.put("fixedPrimaryGainBeforeRepresentationScale", fixedPrimaryGain);\n            d.put("effectiveRenderGainAfterRepresentationScale", effectiveRenderGain);\n            d.put("colorMatrixConvention", "row_major_DNG_XYZ_to_reference_camera_unchanged");\n            d.put("forwardMatrixConvention", "D50_normalized_only");\n'''
if extra_diag_anchor not in renderer:
    raise SystemExit('NATIVEAB1A prospective diagnostic gainMap anchor missing')
renderer = renderer.replace(extra_diag_anchor, extra_diag, 1)

# The old diagnostic text still says Cobalt matrices bypassed; keep that fact but clarify target asset use.
renderer = renderer.replace('"Camera2_native_dual_illuminant_no_Cobalt_source_matrices"',
                            '"Camera2_native_dual_illuminant_CMFIX_no_Cobalt_source_matrices"')

# Clean version suffix if the transformed old script appended it to an already-tagged build.
gradle = read(gradle_rel)
gradle = gradle.replace('-nativeprospective1a', '')
if '-nohdr1a-sourcecal2a-cmfix-fixedgain1a-nativeab1a' not in gradle:
    m = re.search(r"(versionName\s+['\"])([^'\"]+)(['\"])", gradle)
    if not m:
        raise SystemExit('NATIVEAB1A versionName anchor missing')
    gradle = gradle[:m.start(2)] + m.group(2) + '-nohdr1a-sourcecal2a-cmfix-fixedgain1a-nativeab1a' + gradle[m.end(2):]
write(gradle_rel, gradle)
write(renderer_rel, renderer)

# Final invariants: primary photographic core and all frozen seams are byte-identical.
renderer_after = read(renderer_rel)
_, _, primary_render_core_after = extract_top_method(renderer_after, '    private static RenderCore renderCore(')
if hashlib.sha256(primary_render_core_after.encode('utf-8')).hexdigest() != primary_render_core_sha:
    raise SystemExit('NATIVEAB1A unexpectedly changed frozen primary renderCore')
for rel, before in frozen_before.items():
    if sha(rel) != before:
        raise SystemExit('NATIVEAB1A changed frozen photographic seam: ' + rel)

print('M9 FIXEDGAIN1A + NATIVEAB1A applied')
print(' - primary renderCore sha256 preserved:', primary_render_core_sha)
print(' - prospective TC20 selection removed; same-frame primary gain injected')
print(' - MAIN physical ID 2 only; source-only + source+shading outputs')
print(' - shading headroom preserved by representation scaling')
