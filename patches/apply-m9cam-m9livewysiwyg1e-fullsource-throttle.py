#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m9livewysiwyg1e-fullsource-throttle.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
controller = root / 'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
preview = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle = root / 'app/build.gradle'
for p in (controller, preview, renderer, gradle):
    if not p.exists():
        raise SystemExit('M9LIVEWYSIWYG1E missing assembled file: ' + str(p))

def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'M9LIVEWYSIWYG1E {label}: expected 1 anchor, found {n}')
    return text.replace(old, new, 1)

c = controller.read_text()
p = preview.read_text()
r = renderer.read_text()

# This branch must start from the known-good 1C photographic path and 1B exposure lock.
for marker in (
        'M9LIVEWYSIWYG1C_FULLSOURCE_FINALBOUNDARY',
        'packFullRawPreservingSamples1C(raw)',
        'FULL_PRODUCTION_RENDER_FULL_SOURCE_FINAL_BITMAP',
        'preRenderSourceReduction", false'):
    if marker not in p and marker not in r:
        raise SystemExit('M9LIVEWYSIWYG1E requires 1C marker: ' + marker)
for marker in (
        'M9LIVEWYSIWYG1B_DISPLAYEDCAPTURELOCK',
        'm9LiveWysiwygDisplayedIso1B',
        'm9LiveWysiwygDisplayedExposureNs1B'):
    if marker not in c:
        raise SystemExit('M9LIVEWYSIWYG1E requires 1B marker: ' + marker)

# Keep the polling lightweight but guarantee a real idle interval after every expensive
# full-resolution render. This prevents the 1C renderer from running effectively back-to-back.
c = replace_once(
    c,
    '    private static final long M9_LIVE_PREVIEW_INTERVAL_MS = 140L;',
    '    private static final long M9_LIVE_PREVIEW_INTERVAL_MS = 180L;\\n'
    '    // M9LIVEWYSIWYG1E_FULLSOURCE_THROTTLE: preserve exact 1C pixels, reduce duty cycle only.\\n'
    '    private static final long M9_LIVE_PREVIEW_MIN_IDLE_AFTER_RENDER_MS = 800L;',
    'interval constants')

c = replace_once(
    c,
    '    private final AtomicBoolean m9LivePreviewRenderBusy = new AtomicBoolean(false);',
    '    private final AtomicBoolean m9LivePreviewRenderBusy = new AtomicBoolean(false);\\n'
    '    private volatile long m9LivePreviewLastRenderEndElapsedMs1E = 0L;',
    'last render timestamp')

guard_old = '''        if (!M9LivePreview1A.ENABLED || isZslMode() || burst || isProcessing
                || mState != STATE_PREVIEW || mCameraDevice == null || mCaptureSession == null
                || mPreviewRequestBuilder == null || mImageReaderRaw == null
                || m9LivePreviewRenderBusy.get()) return;
'''
guard_new = '''        if (!M9LivePreview1A.ENABLED || isZslMode() || burst || isProcessing
                || mState != STATE_PREVIEW || mCameraDevice == null || mCaptureSession == null
                || mPreviewRequestBuilder == null || mImageReaderRaw == null
                || m9LivePreviewRenderBusy.get()) return;
        // M9LIVEWYSIWYG1E_FULLSOURCE_THROTTLE
        // Never change the RAW or renderer to gain speed. Instead, leave a bounded idle window
        // after each completed 12 MP production render so UI/camera threads can breathe.
        final long nowElapsed1E = android.os.SystemClock.elapsedRealtime();
        final long lastRenderEnd1E = m9LivePreviewLastRenderEndElapsedMs1E;
        if (lastRenderEnd1E > 0L
                && nowElapsed1E - lastRenderEnd1E < M9_LIVE_PREVIEW_MIN_IDLE_AFTER_RENDER_MS) {
            return;
        }
'''
c = replace_once(c, guard_old, guard_new, 'request throttle guard')

exec_old = '''        m9LivePreviewExecutor.execute(() -> {
            android.graphics.Bitmap rendered = null;
            try {
'''
exec_new = '''        m9LivePreviewExecutor.execute(() -> {
            android.graphics.Bitmap rendered = null;
            try {
                // The full-source M9 renderer is intentionally expensive. Run the preview worker
                // below interactive/UI priority rather than changing a single photographic pixel.
                try {
                    android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_BACKGROUND);
                } catch (Throwable ignored) {}
'''
c = replace_once(c, exec_old, exec_new, 'background priority')

finally_old = '''                if (rendered != null && !rendered.isRecycled()) rendered.recycle();
                m9LivePreviewRenderBusy.set(false);
            }
        });
'''
finally_new = '''                if (rendered != null && !rendered.isRecycled()) rendered.recycle();
                m9LivePreviewLastRenderEndElapsedMs1E = android.os.SystemClock.elapsedRealtime();
                m9LivePreviewRenderBusy.set(false);
            }
        });
'''
c = replace_once(c, finally_old, finally_new, 'render completion idle timestamp')

stop_old = '''        m9LivePreviewProbeInFlight.set(false);
        m9LivePreviewProbeResult = null;
'''
stop_new = '''        m9LivePreviewProbeInFlight.set(false);
        m9LivePreviewLastRenderEndElapsedMs1E = 0L;
        m9LivePreviewProbeResult = null;
'''
c = replace_once(c, stop_old, stop_new, 'stop reset')

controller.write_text(c)

g = gradle.read_text()
import re
m = re.search(r'versionName\\s+["\\']([^"\\']+)["\\']', g)
if not m:
    raise SystemExit('M9LIVEWYSIWYG1E versionName missing')
if 'm9livewysiwyg1e' not in m.group(1).lower():
    old = m.group(0)
    quote = '"' if '"' in old else "'"
    g = g.replace(old, 'versionName ' + quote + m.group(1)
                  + '-m9livewysiwyg1e-fullsource-throttle' + quote, 1)
    gradle.write_text(g)

print('M9LIVEWYSIWYG1E_FULLSOURCE_THROTTLE applied')
print(' - exact 1C full-resolution RAW -> production M9 renderer path retained')
print(' - no pre-render source reduction or alternate preview renderer')
print(' - minimum 800 ms idle interval after each completed full-source render')
print(' - preview render worker moved below interactive/UI thread priority')
print(' - 1B displayed ISO/shutter still-capture lock unchanged')
