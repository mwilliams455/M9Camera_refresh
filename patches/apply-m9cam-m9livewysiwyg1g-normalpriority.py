#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m9livewysiwyg1g-normalpriority.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
controller = root / 'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
preview = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
selector = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
gradle = root / 'app/build.gradle'
for p in (controller, preview, renderer, selector, gradle):
    if not p.exists():
        raise SystemExit('M9LIVEWYSIWYG1G missing assembled file: ' + str(p))

def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'M9LIVEWYSIWYG1G {label}: expected 1 anchor, found {n}')
    return text.replace(old, new, 1)

c = controller.read_text()
p = preview.read_text()
r = renderer.read_text()
s = selector.read_text()

# Require exact 1C pixels + 1F orientation + 1B exposure lock.
for token in (
        'M9LIVEWYSIWYG1C_FULLSOURCE_FINALBOUNDARY',
        'packFullRawPreservingSamples1C(raw)'):
    if token not in p:
        raise SystemExit('M9LIVEWYSIWYG1G missing 1C preview token: ' + token)
for token in (
        'FULL_PRODUCTION_RENDER_FULL_SOURCE_FINAL_BITMAP',
        'preRenderSourceReduction", false'):
    if token not in r:
        raise SystemExit('M9LIVEWYSIWYG1G missing 1C renderer token: ' + token)
for token in (
        'M9LIVEWYSIWYG1F_LIVEORIENTATION',
        'PhotonCamera.getGravity().getCameraRotation(mSensorOrientation)'):
    if token not in c:
        raise SystemExit('M9LIVEWYSIWYG1G missing 1F orientation token: ' + token)
if 'setExactExposureM9Wysiwyg1B(' not in s:
    raise SystemExit('M9LIVEWYSIWYG1G missing exact exposure setter')

# The 1E throttle was deliberately conservative. Device video shows ~4-5 s between
# rendered frames, so stop demoting the renderer to background CPU priority and leave
# only a short idle gap after completion. Single-flight still prevents queue buildup.
c = replace_once(
    c,
    '    private static final long M9_LIVE_PREVIEW_INTERVAL_MS = 180L;',
    '    private static final long M9_LIVE_PREVIEW_INTERVAL_MS = 120L;',
    'poll interval')

c = replace_once(
    c,
    '    private static final long M9_LIVE_PREVIEW_MIN_IDLE_AFTER_RENDER_MS = 800L;',
    '    private static final long M9_LIVE_PREVIEW_MIN_IDLE_AFTER_RENDER_MS = 200L;\n'
    '    // M9LIVEWYSIWYG1G_NORMALPRIORITY: scheduling-only speed recovery; pixels frozen.',
    'idle interval')

old_priority = '''                // The full-source M9 renderer is intentionally expensive. Run the preview worker
                // below interactive/UI priority rather than changing a single photographic pixel.
                try {
                    android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_BACKGROUND);
                } catch (Throwable ignored) {}
'''
new_priority = '''                // M9LIVEWYSIWYG1G_NORMALPRIORITY
                // 1F device video measured multi-second live-frame cadence. The persistent
                // BACKGROUND priority was starving the already-heavy 12 MP render. Restore
                // normal worker priority; single-flight + the bounded post-render idle interval
                // remain the UI protection. This does not change renderer inputs or pixels.
                try {
                    android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_DEFAULT);
                } catch (Throwable ignored) {}
                final long m9LiveRenderStartedElapsedMs1G =
                        android.os.SystemClock.elapsedRealtime();
'''
c = replace_once(c, old_priority, new_priority, 'worker priority')

old_finally = '''                if (rendered != null && !rendered.isRecycled()) rendered.recycle();
                m9LivePreviewLastRenderEndElapsedMs1E = android.os.SystemClock.elapsedRealtime();
                m9LivePreviewRenderBusy.set(false);
'''
new_finally = '''                if (rendered != null && !rendered.isRecycled()) rendered.recycle();
                final long m9LiveRenderEndedElapsedMs1G =
                        android.os.SystemClock.elapsedRealtime();
                final long m9LiveRenderWallMs1G =
                        Math.max(0L, m9LiveRenderEndedElapsedMs1G - m9LiveRenderStartedElapsedMs1G);
                m9LivePreviewLastRenderEndElapsedMs1E = m9LiveRenderEndedElapsedMs1G;
                Log.d(TAG, "M9LIVEWYSIWYG1G renderWallMs=" + m9LiveRenderWallMs1G
                        + " idleAfterMs=" + M9_LIVE_PREVIEW_MIN_IDLE_AFTER_RENDER_MS
                        + " workerPriority=DEFAULT");
                m9LivePreviewRenderBusy.set(false);
'''
c = replace_once(c, old_finally, new_finally, 'timing log')

controller.write_text(c)

g = gradle.read_text()
lines = g.splitlines()
changed = False
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith('versionName '):
        if 'm9livewysiwyg1g' not in stripped.lower():
            prefix = line[:len(line) - len(line.lstrip())]
            value = stripped[len('versionName '):].strip()
            quote = '"' if value.startswith('"') else "'"
            if not (value.startswith(quote) and value.endswith(quote)):
                raise SystemExit('M9LIVEWYSIWYG1G unsupported versionName syntax: ' + line)
            base = value[1:-1]
            lines[i] = prefix + 'versionName ' + quote + base + '-m9livewysiwyg1g-normalpriority' + quote
            changed = True
        break
else:
    raise SystemExit('M9LIVEWYSIWYG1G versionName missing')
if changed:
    gradle.write_text('\n'.join(lines) + ('\n' if g.endswith('\n') else ''))

print('M9LIVEWYSIWYG1G_NORMALPRIORITY applied')
print(' - exact 1C full-source render retained')
print(' - 1F live orientation retained')
print(' - 1B displayed ISO/shutter lock retained')
print(' - preview worker restored from BACKGROUND to DEFAULT priority')
print(' - post-render idle reduced from 800 ms to 200 ms')
print(' - poll interval reduced from 180 ms to 120 ms')
print(' - per-frame live render wall time logged')
