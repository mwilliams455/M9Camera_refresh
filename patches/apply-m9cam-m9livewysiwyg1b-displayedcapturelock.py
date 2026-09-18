#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m9livewysiwyg1b-displayedcapturelock.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
controller = root / 'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
selector = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
gradle = root / 'app/build.gradle'
for p in (controller, selector):
    if not p.exists():
        raise SystemExit('M9LIVEWYSIWYG1B missing assembled file: ' + str(p))

def method_span(text, signature):
    start = text.find(signature)
    if start < 0:
        raise SystemExit('M9LIVEWYSIWYG1B method missing: ' + signature)
    brace = text.find('{', start)
    if brace < 0:
        raise SystemExit('M9LIVEWYSIWYG1B opening brace missing: ' + signature)
    depth = 0
    state = 'code'
    quote = ''
    escape = False
    i = brace
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ''
        if state == 'line':
            if ch == '\n':
                state = 'code'
        elif state == 'block':
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
                state = 'line'
                i += 1
            elif ch == '/' and nxt == '*':
                state = 'block'
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
                    return start, i + 1
        i += 1
    raise SystemExit('M9LIVEWYSIWYG1B unterminated method: ' + signature)

def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'M9LIVEWYSIWYG1B {label}: expected 1 anchor, found {n}')
    return text.replace(old, new, 1)

# ---------------------------------------------------------------------------
# IsoExpoSelector: exact capture exposure setter.
# ---------------------------------------------------------------------------
s = selector.read_text()
if 'M9LIVEWYSIWYG1B_DISPLAYEDCAPTURELOCK' in s:
    raise SystemExit('M9LIVEWYSIWYG1B already applied to IsoExpoSelector')

set_start, set_end = method_span(
    s, '    public static void setExpo(CaptureRequest.Builder builder, int step, CaptureController captureController) {')
insert = r'''

    /**
     * M9LIVEWYSIWYG1B_DISPLAYEDCAPTURELOCK
     *
     * Capture the exact sensor exposure that produced the last M9 Bitmap actually shown
     * to the photographer. No shutter-priority redistribution, exposure compensation
     * remapping, bracketing multiplier, stability curve, or alternate still exposure
     * selection is permitted here.
     */
    public static void setExactExposureM9Wysiwyg1B(
            CaptureRequest.Builder builder, int step, long exposureNs, int iso) {
        if (builder == null) {
            throw new IllegalArgumentException("M9LIVEWYSIWYG1B missing capture builder");
        }
        if (exposureNs <= 0L || iso <= 0) {
            throw new IllegalArgumentException(
                    "M9LIVEWYSIWYG1B invalid exact exposure " + exposureNs + "ns ISO " + iso);
        }

        if (step == 0) {
            fullpairs.clear();
            pairs.clear();
        }

        ExpoPair pair = new ExpoPair(
                exposureNs, getEXPLOW(), getEXPHIGH(),
                iso, getISOLOW(), getISOHIGH(), getISOAnalog());
        pair.curlayer = ExpoPair.exposureLayer.Normal;
        pair.layerMpy = 1.f;
        fullpairs.add(pair);
        if (pairs.size() < patternSize) {
            pairs.add(new ExpoPair(pair));
        }

        builder.set(CaptureRequest.CONTROL_AE_MODE, CaptureRequest.CONTROL_AE_MODE_OFF);
        builder.set(CaptureRequest.SENSOR_EXPOSURE_TIME, exposureNs);
        builder.set(CaptureRequest.SENSOR_SENSITIVITY, iso);
        lastSelectedExposure = exposureNs;

        Log.v(TAG, "M9LIVEWYSIWYG1B_DISPLAYEDCAPTURELOCK exact displayed exposure: ISO="
                + iso + " exposureNs=" + exposureNs + " step=" + step);
    }
'''
s = s[:set_end] + insert + s[set_end:]
selector.write_text(s)

# ---------------------------------------------------------------------------
# CaptureController: remember the exact exposure of the Bitmap committed to ImageView,
# then use that exposure for the still capture request.
# ---------------------------------------------------------------------------
c = controller.read_text()
for marker in (
        'M9LIVEWYSIWYG1A_CURRENTEXPOSURE',
        'tryDispatchM9LiveWysiwygPair1A()',
        'M9LivePreview1A.markDisplayedWysiwyg1A('):
    if marker not in c:
        raise SystemExit('M9LIVEWYSIWYG1B requires 1A baseline marker: ' + marker)
if 'M9LIVEWYSIWYG1B_DISPLAYEDCAPTURELOCK' in c:
    raise SystemExit('M9LIVEWYSIWYG1B already applied to CaptureController')

field_anchor = '''    private CaptureRequest m9LiveWysiwygPendingRequest1A = null;
'''
fields = field_anchor + '''    // M9LIVEWYSIWYG1B_DISPLAYEDCAPTURELOCK
    // Updated only when the exact M9 Bitmap is committed to ImageView.
    private volatile int m9LiveWysiwygDisplayedIso1B = -1;
    private volatile long m9LiveWysiwygDisplayedExposureNs1B = -1L;
    private volatile long m9LiveWysiwygDisplayedRawTimestampNs1B = -1L;
'''
c = replace_once(c, field_anchor, fields, 'displayed exposure fields')

ui_anchor = '''                    m9LivePreviewImageView.setImageBitmap(ready);
                    M9LivePreview1A.markDisplayedWysiwyg1A(
                            ready, imageTs, result, request, pairDeltaNs);
'''
ui_new = '''                    m9LivePreviewImageView.setImageBitmap(ready);
                    Integer displayedIso1B =
                            result.get(CaptureResult.SENSOR_SENSITIVITY);
                    Long displayedExposure1B =
                            result.get(CaptureResult.SENSOR_EXPOSURE_TIME);
                    if (displayedIso1B != null && displayedIso1B > 0
                            && displayedExposure1B != null && displayedExposure1B > 0L) {
                        // Authoritative shutter state: these values produced the M9 frame
                        // the photographer is looking at right now.
                        m9LiveWysiwygDisplayedIso1B = displayedIso1B;
                        m9LiveWysiwygDisplayedExposureNs1B = displayedExposure1B;
                        m9LiveWysiwygDisplayedRawTimestampNs1B = imageTs;
                    }
                    M9LivePreview1A.markDisplayedWysiwyg1A(
                            ready, imageTs, result, request, pairDeltaNs);
'''
c = replace_once(c, ui_anchor, ui_new, 'ImageView exposure latch')

cs, ce = method_span(c, '    private void captureStillPicture() {')
method = c[cs:ce]

zsl_anchor = '''            if (isZslMode()) {
                triggerZslCapture();
                return;
            }
'''
if method.count(zsl_anchor) != 1:
    raise SystemExit('M9LIVEWYSIWYG1B ZSL anchor count=' + str(method.count(zsl_anchor)))
lock_block = zsl_anchor + '''            // WYSIWYG contract: the still uses the exposure of the last M9 frame
            // actually displayed to the photographer. If the M9 overlay has not yet
            // committed a frame, fall back only to the latest real preview CaptureResult;
            // never to GenerateExpoPair()/setExpo() prediction.
            final boolean m9DisplayedExposureAvailable1B =
                    m9LiveWysiwygDisplayedIso1B > 0
                            && m9LiveWysiwygDisplayedExposureNs1B > 0L;
            final int m9CaptureIso1B = m9DisplayedExposureAvailable1B
                    ? m9LiveWysiwygDisplayedIso1B : mPreviewIso;
            final long m9CaptureExposureNs1B = m9DisplayedExposureAvailable1B
                    ? m9LiveWysiwygDisplayedExposureNs1B : mPreviewExposureTime;
            final long m9CapturePreviewTimestampNs1B =
                    m9DisplayedExposureAvailable1B
                            ? m9LiveWysiwygDisplayedRawTimestampNs1B : -1L;
            if (m9CaptureIso1B <= 0 || m9CaptureExposureNs1B <= 0L) {
                throw new IllegalStateException(
                        "M9LIVEWYSIWYG1B no real preview exposure available for shutter");
            }
            Log.d(TAG, "M9LIVEWYSIWYG1B capture lock source="
                    + (m9DisplayedExposureAvailable1B
                            ? "ImageView_displayed_M9_frame" : "latest_real_preview_result")
                    + " iso=" + m9CaptureIso1B
                    + " exposureNs=" + m9CaptureExposureNs1B
                    + " displayedRawTimestampNs=" + m9CapturePreviewTimestampNs1B);
'''
method = method.replace(zsl_anchor, lock_block, 1)

# This value affects whether the preview surface is also attached to the still request.
# It must describe the actual WYSIWYG capture shutter, not a newly predicted one.
old_frametime = '''            double frametime = ExposureIndex.time2sec(IsoExpoSelector.GenerateExpoPair(-1, this).exposure);
'''
if method.count(old_frametime) != 1:
    raise SystemExit(
        'M9LIVEWYSIWYG1B still frametime predictor count='
        + str(method.count(old_frametime)))
method = method.replace(
    old_frametime,
    '''            double frametime = ExposureIndex.time2sec(m9CaptureExposureNs1B);
''', 1)

old_set = 'IsoExpoSelector.setExpo(captureBuilder, i, this);'
count = method.count(old_set)
if count != 2:
    raise SystemExit('M9LIVEWYSIWYG1B still setExpo count=' + str(count))
method = method.replace(
    old_set,
    '''IsoExpoSelector.setExactExposureM9Wysiwyg1B(
                            captureBuilder, i, m9CaptureExposureNs1B, m9CaptureIso1B);''')

c = c[:cs] + method + c[ce:]
controller.write_text(c)

if gradle.exists():
    g = gradle.read_text()
    m = re.search(r'versionName\s+["\']([^"\']+)["\']', g)
    if m and 'm9livewysiwyg1b' not in m.group(1).lower():
        old = m.group(0)
        quote = '"' if '"' in old else "'"
        g = g.replace(
            old,
            'versionName ' + quote + m.group(1)
            + '-m9livewysiwyg1b-displayedcapturelock' + quote,
            1)
        gradle.write_text(g)

print('M9LIVEWYSIWYG1B_DISPLAYEDCAPTURELOCK applied')
print(' - last ImageView-displayed M9 frame is authoritative for still ISO/shutter')
print(' - still capture does not call GenerateExpoPair() for exposure selection')
print(' - still capture does not call IsoExpoSelector.setExpo()')
print(' - exact capture pair recorded into IsoExpoSelector fullpairs/pairs')
print(' - AE disabled only on still request after exact ISO/shutter are copied')
print(' - fallback, if M9 overlay has not displayed yet, is latest real preview result only')
