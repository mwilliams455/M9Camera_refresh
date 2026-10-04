#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-m9livewysiwyg1b-displayedcapturelock.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
controller = root / 'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
selector = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle = root / 'app/build.gradle'
for p in (controller, selector, renderer, gradle):
    if not p.exists():
        raise SystemExit('M9LIVEWYSIWYG1B verify missing: ' + str(p))

def method_span(text, signature):
    start = text.find(signature)
    if start < 0:
        raise SystemExit('M9LIVEWYSIWYG1B verify method missing: ' + signature)
    brace = text.find('{', start)
    depth = 0
    state = 'code'
    quote = ''
    escape = False
    i = brace
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ''
        if state == 'line':
            if ch == '\n': state = 'code'
        elif state == 'block':
            if ch == '*' and nxt == '/': state = 'code'; i += 1
        elif state == 'string':
            if escape: escape = False
            elif ch == '\\': escape = True
            elif ch == quote: state = 'code'
        else:
            if ch == '/' and nxt == '/': state = 'line'; i += 1
            elif ch == '/' and nxt == '*': state = 'block'; i += 1
            elif ch in ('"', "'"): state = 'string'; quote = ch
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: return text[start:i + 1]
        i += 1
    raise SystemExit('M9LIVEWYSIWYG1B verify unterminated: ' + signature)

c = controller.read_text()
s = selector.read_text()
r = renderer.read_text()
g = gradle.read_text()

for token in (
        'M9LIVEWYSIWYG1B_DISPLAYEDCAPTURELOCK',
        'm9LiveWysiwygDisplayedIso1B',
        'm9LiveWysiwygDisplayedExposureNs1B',
        'ImageView_displayed_M9_frame',
        'm9CaptureIso1B',
        'm9CaptureExposureNs1B',
        'setExactExposureM9Wysiwyg1B('):
    if token not in c:
        raise SystemExit('M9LIVEWYSIWYG1B controller marker missing: ' + token)

capture = method_span(c, '    private void captureStillPicture() {')
for forbidden in (
        'IsoExpoSelector.GenerateExpoPair(-1, this)',
        'IsoExpoSelector.setExpo(captureBuilder, i, this)'):
    if forbidden in capture:
        raise SystemExit('M9LIVEWYSIWYG1B forbidden hidden still exposure path remains: ' + forbidden)

if capture.count('IsoExpoSelector.setExactExposureM9Wysiwyg1B(') != 2:
    raise SystemExit(
        'M9LIVEWYSIWYG1B expected two exact exposure capture calls, found '
        + str(capture.count('IsoExpoSelector.setExactExposureM9Wysiwyg1B(')))

if 'double frametime = ExposureIndex.time2sec(m9CaptureExposureNs1B);' not in capture:
    raise SystemExit('M9LIVEWYSIWYG1B still frametime does not use displayed exposure')

if 'latest_real_preview_result' not in capture:
    raise SystemExit('M9LIVEWYSIWYG1B real-preview-only startup fallback marker missing')

# ImageView commit must latch the same exact CaptureResult that rendered the displayed bitmap.
ui_order = '''m9LivePreviewImageView.setImageBitmap(ready);
                    Integer displayedIso1B =
                            result.get(CaptureResult.SENSOR_SENSITIVITY);
                    Long displayedExposure1B =
                            result.get(CaptureResult.SENSOR_EXPOSURE_TIME);'''
if ui_order not in c:
    raise SystemExit('M9LIVEWYSIWYG1B exposure latch is not at ImageView commit boundary')

selector_method = method_span(
    s, '    public static void setExactExposureM9Wysiwyg1B(')
for token in (
        'builder.set(CaptureRequest.CONTROL_AE_MODE, CaptureRequest.CONTROL_AE_MODE_OFF);',
        'builder.set(CaptureRequest.SENSOR_EXPOSURE_TIME, exposureNs);',
        'builder.set(CaptureRequest.SENSOR_SENSITIVITY, iso);',
        'fullpairs.add(pair);',
        'pairs.add(new ExpoPair(pair));',
        'lastSelectedExposure = exposureNs;'):
    if token not in selector_method:
        raise SystemExit('M9LIVEWYSIWYG1B exact selector marker missing: ' + token)

for forbidden in (
        'GenerateExpoPair(',
        'applyShutterPriorityCurve',
        'ExpoCompensateLower',
        'applyExposureBalance',
        'exposureCompensation',
        'bracketingMode'):
    if forbidden in selector_method:
        raise SystemExit('M9LIVEWYSIWYG1B exact selector contains remapping policy: ' + forbidden)

# Preview architecture from 1A remains the current-exposure rendered viewfinder.
for token in (
        'M9LIVEWYSIWYG1A_CURRENTEXPOSURE',
        'current_live_sensor_exposure_through_M9_renderer',
        'actual_M9_Bitmap_at_ImageView_commit',
        'stillActualVsDisplayedPreviewExposureDeltaEv'):
    if token not in r:
        raise SystemExit('M9LIVEWYSIWYG1B lost 1A diagnostic contract: ' + token)

# No photographic renderer mutation is allowed in this patch.
for sig in (
        'private static RenderCore renderNativeSourceProduction1P(',
        'private static RenderCore renderNativeProspectiveCore('):
    core = method_span(r, sig)
    if 'M9LIVEWYSIWYG1B' in core or 'm9LiveWysiwygDisplayed' in core:
        raise SystemExit('M9LIVEWYSIWYG1B leaked into photographic renderer core: ' + sig)

if 'm9livewysiwyg1b-displayedcapturelock' not in g.lower():
    raise SystemExit('M9LIVEWYSIWYG1B versionName marker missing')

print('M9LIVEWYSIWYG1B_DISPLAYEDCAPTURELOCK VERIFY PASS')
print(' - last actually displayed M9 preview exposure is shutter authority')
print(' - captureStillPicture contains no GenerateExpoPair still predictor')
print(' - captureStillPicture contains no legacy setExpo exposure selector')
print(' - exact ISO/shutter are copied into every still frame request')
print(' - exact exposure pair is kept consistent with downstream fullpairs/pairs metadata')
print(' - startup fallback uses latest real preview exposure only')
print(' - M9 render core remains untouched')
