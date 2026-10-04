#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-nativec2parity1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit('NATIVEAPIORDER1A: not a PhotonCamera root')

renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
audit_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9SourceCalibrationAudit1A.java'
gradle_path = root / 'app/build.gradle'
if not renderer_path.exists() or not audit_path.exists() or not gradle_path.exists():
    raise SystemExit('NATIVEAPIORDER1A: assembled renderer/audit/build.gradle missing')

renderer = renderer_path.read_text()
audit = audit_path.read_text()
gradle = gradle_path.read_text()


def extract_method(src, marker):
    start = src.find(marker)
    if start < 0:
        raise SystemExit('NATIVEAPIORDER1A method marker missing: ' + marker)
    brace = src.find('{', start)
    if brace < 0:
        raise SystemExit('NATIVEAPIORDER1A opening brace missing: ' + marker)
    depth = 0
    i = brace
    state = 'code'
    quote = ''
    escape = False
    while i < len(src):
        ch = src[i]
        nxt = src[i + 1] if i + 1 < len(src) else ''
        if state == 'line_comment':
            if ch == '\n': state = 'code'
        elif state == 'block_comment':
            if ch == '*' and nxt == '/': state = 'code'; i += 1
        elif state == 'string':
            if escape: escape = False
            elif ch == '\\': escape = True
            elif ch == quote: state = 'code'
        else:
            if ch == '/' and nxt == '/': state = 'line_comment'; i += 1
            elif ch == '/' and nxt == '*': state = 'block_comment'; i += 1
            elif ch in ('"', "'"): state = 'string'; quote = ch; escape = False
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return start, i + 1, src[start:i + 1]
        i += 1
    raise SystemExit('NATIVEAPIORDER1A unterminated method: ' + marker)


# Frozen production M9 photographic core must remain byte-identical.
_, _, primary_before = extract_method(renderer, '    private static RenderCore renderCore(')
primary_sha = hashlib.sha256(primary_before.encode('utf-8')).hexdigest()

# Android ColorSpaceTransform stores values row-major, but getElement takes
# (column,row), not (row,column). Avoid that API-order trap entirely by using
# copyElements(), whose contract is explicitly row-major. Apply the SAME extraction
# to the experimental renderer and SOURCECAL audit so their numeric oracle can match.
renderer_start, renderer_end, _ = extract_method(
    renderer, '    private static float[] nativeProspectiveTransform(')
renderer_helper = '''    private static float[] nativeProspectiveTransform(ColorSpaceTransform transform) {
        // NATIVEAPIORDER1A: Android-safe row-major extraction.
        // copyElements() avoids getElement argument-order ambiguity and returns
        // the documented row-major sequence.
        if (transform == null) return null;
        Rational[] elements = new Rational[9];
        transform.copyElements(elements, 0);
        float[] out = new float[9];
        for (int i = 0; i < 9; i++) {
            Rational v = elements[i];
            out[i] = v != null ? v.floatValue() : Float.NaN;
        }
        return out;
    }'''
renderer = renderer[:renderer_start] + renderer_helper + renderer[renderer_end:]

audit_start, audit_end, _ = extract_method(
    audit, '    private static float[] transform(')
audit_helper = '''    private static float[] transform(ColorSpaceTransform t) {
        // NATIVEAPIORDER1A: same Android-safe row-major extraction as renderer.
        // copyElements() is specified to emit the 3x3 matrix in row-major order.
        if (t == null) return null;
        Rational[] elements = new Rational[9];
        t.copyElements(elements, 0);
        float[] out = new float[9];
        for (int i = 0; i < 9; i++) {
            Rational v = elements[i];
            out[i] = v != null ? v.floatValue() : Float.NaN;
        }
        return out;
    }'''
audit = audit[:audit_start] + audit_helper + audit[audit_end:]

# Correct the misleading SOURCECAL2A convention label. The old text claimed
# getElement(row,column), which is not Android's method signature/semantics.
old_audit_label = 'out.put("matrixStorageConvention", "row_major_getElement_row_column");'
new_audit_label = 'out.put("matrixStorageConvention", "android_ColorSpaceTransform_copyElements_row_major");'
if audit.count(old_audit_label) != 1:
    raise SystemExit('NATIVEAPIORDER1A SOURCECAL matrixStorageConvention anchor missing/non-unique')
audit = audit.replace(old_audit_label, new_audit_label, 1)

# At this point the assembled NATIVEAB1A prospective method has only the base
# convention fields. Insert the new API-safe diagnostics directly after that stable
# anchor; do not depend on diagnostics from an older version of this same patch.
pros_start, pros_end, prospective = extract_method(
    renderer, '    private static RenderCore renderNativeProspectiveCore(')
diag_anchor = '            d.put("forwardMatrixConvention", "D50_normalized_only");\n'
diag_insert = diag_anchor + '''            d.put("nativeMatrixExtractionPolicy", "NATIVEAPIORDER1A_ColorSpaceTransform_copyElements_row_major");
            d.put("nativeMatrixApiSemantics", "storage_row_major_getElement_signature_column_row_copyElements_used");
            d.put("nativeMatrixParityOracle", "M9_SOURCECAL1A_same_capture_nativeInterpolationFactor_and_nativeSensorToXYZD50");
            d.put("converterConvertColorspaceTransformUsed", false);
'''
if prospective.count(diag_anchor) != 1:
    raise SystemExit('NATIVEAPIORDER1A prospective forward-matrix diagnostic anchor missing/non-unique')
prospective = prospective.replace(diag_anchor, diag_insert, 1)
renderer = renderer[:pros_start] + prospective + renderer[pros_end:]

# Scientific parity guards: both paths must use the identical row-major extraction
# primitive and the SOURCECAL2A rule of preserving ColorMatrix while normalizing only
# ForwardMatrix must still be present on both sides.
_, _, renderer_helper_after = extract_method(
    renderer, '    private static float[] nativeProspectiveTransform(')
_, _, audit_helper_after = extract_method(audit, '    private static float[] transform(')
for label, helper in [('renderer', renderer_helper_after), ('audit', audit_helper_after)]:
    for required in ['copyElements(elements, 0)', 'Rational[] elements = new Rational[9]']:
        if required not in helper:
            raise SystemExit('NATIVEAPIORDER1A ' + label + ' extraction marker missing: ' + required)
    if '.getElement(' in helper or 'Converter.convertColorspaceTransform(' in helper:
        raise SystemExit('NATIVEAPIORDER1A ' + label + ' ambiguous executable matrix accessor survived')

_, _, source_method = extract_method(renderer, '    private static NativeProspectiveSource buildNativeProspectiveSource(')
for label, body in [('renderer', source_method), ('audit', audit)]:
    if 'Converter.normalizeFM(ncm1);' in body or 'Converter.normalizeFM(ncm2);' in body:
        raise SystemExit('NATIVEAPIORDER1A ' + label + ' incorrectly normalizes ColorMatrix')
    for required in ['Converter.normalizeFM(nfm1);', 'Converter.normalizeFM(nfm2);',
                     'Converter.findDngInterpolationFactor(',
                     'Converter.calculateCameraToXYZD50Transform(']:
        if required not in body:
            raise SystemExit('NATIVEAPIORDER1A ' + label + ' DNG transform marker missing: ' + required)

# Frozen production core remains untouched.
_, _, primary_after = extract_method(renderer, '    private static RenderCore renderCore(')
primary_after_sha = hashlib.sha256(primary_after.encode('utf-8')).hexdigest()
if primary_after_sha != primary_sha:
    raise SystemExit('NATIVEAPIORDER1A changed frozen primary renderCore: before='
                     + primary_sha + ' after=' + primary_after_sha)

# Distinct provenance. APKNAME1A keeps the physical filename short.
if '-nativeapiorder1a' not in gradle:
    if '-nativec2parity1a' in gradle:
        gradle = gradle.replace('-nativec2parity1a', '-nativec2parity1a-nativeapiorder1a', 1)
    else:
        marker = '-nohdr1a-sourcecal2a-cmfix-fixedgain1a-nativeab1a'
        if marker not in gradle:
            raise SystemExit('NATIVEAPIORDER1A build identity anchor missing')
        gradle = gradle.replace(marker, marker + '-nativeapiorder1a', 1)

renderer_path.write_text(renderer)
audit_path.write_text(audit)
gradle_path.write_text(gradle)

print('M9 NATIVEAPIORDER1A applied')
print(' - Android ColorSpaceTransform extracted via copyElements() row-major on BOTH audit and renderer')
print(' - incorrect getElement(row,column) interpretation removed')
print(' - SOURCECAL2A ColorMatrix preserved; ForwardMatrix-only normalization retained')
print(' - next field test must numerically match audit/renderer interpolation + sensorToXYZD50')
print(' - NATIVEWPCLIP1A remains in place; no exposure/HDR/M9 target changes')
print(' - frozen primary renderCore sha256 preserved:', primary_sha)
