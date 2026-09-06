#!/usr/bin/env python3
from pathlib import Path
import hashlib
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-nativewpclip1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit('NATIVEWPCLIP1A: not a PhotonCamera root')

renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
if not renderer_path.exists() or not gradle_path.exists():
    raise SystemExit('NATIVEWPCLIP1A: assembled renderer/build.gradle missing')

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()


def extract_method(src, marker):
    start = src.find(marker)
    if start < 0:
        raise SystemExit('NATIVEWPCLIP1A method marker missing: ' + marker)
    brace = src.find('{', start)
    if brace < 0:
        raise SystemExit('NATIVEWPCLIP1A opening brace missing: ' + marker)
    depth = 0
    i = brace
    state = 'code'
    quote = ''
    escape = False
    while i < len(src):
        ch = src[i]
        nxt = src[i + 1] if i + 1 < len(src) else ''
        if state == 'line_comment':
            if ch == '\n':
                state = 'code'
        elif state == 'block_comment':
            if ch == '*' and nxt == '/':
                state = 'code'
                i += 1
        elif state == 'string':
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == quote:
                state = 'code'
        else:
            if ch == '/' and nxt == '/':
                state = 'line_comment'
                i += 1
            elif ch == '/' and nxt == '*':
                state = 'block_comment'
                i += 1
            elif ch in ('"', "'"):
                state = 'string'
                quote = ch
                escape = False
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return start, i + 1, src[start:i + 1]
        i += 1
    raise SystemExit('NATIVEWPCLIP1A unterminated method: ' + marker)


# Protect the frozen production photographic core byte-for-byte.
_, _, primary_before = extract_method(renderer, '    private static RenderCore renderCore(')
primary_sha = hashlib.sha256(primary_before.encode('utf-8')).hexdigest()

# The Camera2/DNG forward-matrix transform already contains the live WB scaling.
# ctx.cw is NOT another gain stage: in the frozen M9 kernel it is only the
# pre-transform camera-channel clipping ceiling (min(camera, cw)).  Leaving it
# [1,1,1] allows R/B values above their scene-neutral saturation ceilings to be
# amplified by the embedded WB transform, producing false highlight colour.
source_start, source_end, source_method = extract_method(
    renderer, '    private static NativeProspectiveSource buildNativeProspectiveSource(')
old_cw = '        ctx.cw = new double[]{1.0, 1.0, 1.0};'
new_cw = '''        // NATIVEWPCLIP1A: restore a physical-camera white clipping ceiling without
        // applying a second white balance.  sensorToXyzD50 below already contains the
        // DNG reference-neutral WB gains; cw is consumed only by min(channel, cw).
        double nativeClipWhiteMax = Math.max(neutral[0], Math.max(neutral[1], neutral[2]));
        if (!Double.isFinite(nativeClipWhiteMax) || nativeClipWhiteMax <= 0.0) {
            throw new IllegalStateException("native prospective invalid clip white maximum");
        }
        ctx.cw = new double[]{
                clamp(neutral[0] / nativeClipWhiteMax, 0.001, 1.0),
                clamp(neutral[1] / nativeClipWhiteMax, 0.001, 1.0),
                clamp(neutral[2] / nativeClipWhiteMax, 0.001, 1.0)
        };'''
if source_method.count(old_cw) != 1:
    raise SystemExit('NATIVEWPCLIP1A expected one identity-cw anchor, got '
                     + str(source_method.count(old_cw)))
source_method = source_method.replace(old_cw, new_cw, 1)
renderer = renderer[:source_start] + source_method + renderer[source_end:]

# Make the experiment self-describing in the embedded primary diagnostics.
pros_start, pros_end, prospective = extract_method(
    renderer, '    private static RenderCore renderNativeProspectiveCore(')
diag_anchor = '            d.put("nativeSensorNeutralB", nativeSource.neutral[2]);\n'
diag_insert = diag_anchor + '''            d.put("nativePreTransformClipWhiteR", nativeSource.ctx.cw[0]);
            d.put("nativePreTransformClipWhiteG", nativeSource.ctx.cw[1]);
            d.put("nativePreTransformClipWhiteB", nativeSource.ctx.cw[2]);
            d.put("nativePreTransformClipWhitePolicy", "physical_SENSOR_NEUTRAL_COLOR_POINT_normalized_max1_clip_only");
            d.put("nativeWhiteBalanceGainOwner", "sensorToXYZD50_forward_matrix_path_only_no_double_WB");
'''
if prospective.count(diag_anchor) != 1:
    raise SystemExit('NATIVEWPCLIP1A prospective neutral diagnostic anchor missing/non-unique')
prospective = prospective.replace(diag_anchor, diag_insert, 1)
renderer = renderer[:pros_start] + prospective + renderer[pros_end:]

# Re-check the frozen production renderCore after both additive edits.
_, _, primary_after = extract_method(renderer, '    private static RenderCore renderCore(')
primary_after_sha = hashlib.sha256(primary_after.encode('utf-8')).hexdigest()
if primary_after_sha != primary_sha:
    raise SystemExit('NATIVEWPCLIP1A changed frozen primary renderCore: before='
                     + primary_sha + ' after=' + primary_after_sha)

# Distinct internal provenance; the workflow already uses a compact physical APK filename.
old_suffix = '-nohdr1a-sourcecal2a-cmfix-fixedgain1a-nativeab1a-jsonsafe1a'
new_suffix = old_suffix + '-nativewpclip1a'
if new_suffix not in gradle:
    if gradle.count(old_suffix) != 1:
        raise SystemExit('NATIVEWPCLIP1A build identity anchor missing/non-unique')
    gradle = gradle.replace(old_suffix, new_suffix, 1)

# Static self-checks.
if 'physical_SENSOR_NEUTRAL_COLOR_POINT_normalized_max1_clip_only' not in renderer:
    raise SystemExit('NATIVEWPCLIP1A diagnostic policy marker missing')
if 'ctx.cw = new double[]{1.0, 1.0, 1.0};' in source_method:
    raise SystemExit('NATIVEWPCLIP1A identity clipping ceiling survived')
if 'sensorToXyzD50' not in source_method or 'calculateCameraToXYZD50Transform' not in source_method:
    raise SystemExit('NATIVEWPCLIP1A unexpectedly lost native DNG transform path')

renderer_path.write_text(renderer)
gradle_path.write_text(gradle)

print('M9 NATIVEWPCLIP1A applied')
print(' - experimental native source branches clip camera channels at normalized live sensor neutral')
print(' - sensorToXYZD50 remains sole white-balance gain owner; no double WB introduced')
print(' - SOURCE_ONLY / SOURCE+SHADING transform, gain and shading math otherwise unchanged')
print(' - frozen primary renderCore sha256 preserved:', primary_sha)
