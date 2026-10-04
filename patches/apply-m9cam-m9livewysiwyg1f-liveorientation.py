#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m9livewysiwyg1f-liveorientation.py <PhotonCamera-root>')

root=Path(sys.argv[1]).resolve()
controller=root/'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
preview=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
renderer=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
selector=root/'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
gradle=root/'app/build.gradle'
for p in (controller,preview,renderer,selector,gradle):
    if not p.exists():
        raise SystemExit('M9LIVEWYSIWYG1F missing assembled file: '+str(p))

def replace_once(text, old, new, label):
    n=text.count(old)
    if n!=1:
        raise SystemExit(f'M9LIVEWYSIWYG1F {label}: expected 1 anchor, found {n}')
    return text.replace(old,new,1)

c=controller.read_text()
p=preview.read_text()
r=renderer.read_text()
s=selector.read_text()

# Require the good 1C + 1E architecture.
for token in (
    'M9LIVEWYSIWYG1C_FULLSOURCE_FINALBOUNDARY',
    'packFullRawPreservingSamples1C(raw)',
):
    if token not in p:
        raise SystemExit('M9LIVEWYSIWYG1F missing 1C preview token: '+token)
for token in (
    'FULL_PRODUCTION_RENDER_FULL_SOURCE_FINAL_BITMAP',
    'preRenderSourceReduction", false',
):
    if token not in r:
        raise SystemExit('M9LIVEWYSIWYG1F missing 1C renderer token: '+token)
for token in (
    'M9LIVEWYSIWYG1E_FULLSOURCE_THROTTLE',
    'M9_LIVE_PREVIEW_MIN_IDLE_AFTER_RENDER_MS = 800L',
    'm9LivePreviewLastRenderEndElapsedMs1E',
):
    if token not in c:
        raise SystemExit('M9LIVEWYSIWYG1F missing 1E scheduling token: '+token)
if 'setExactExposureM9Wysiwyg1B(' not in s:
    raise SystemExit('M9LIVEWYSIWYG1F exact exposure lock missing')

old='''        final CameraCharacteristics previewChars = mCameraCharacteristics;
        final int previewRotation = cameraRotation;
        m9LivePreviewExecutor.execute(() -> {
'''
new='''        final CameraCharacteristics previewChars = mCameraCharacteristics;
        // M9LIVEWYSIWYG1F_LIVEORIENTATION:
        // cameraRotation is a still-capture field and is only refreshed when a still
        // sequence starts. The live M9 overlay must not inherit that stale value.
        // Snapshot the current physical camera orientation for the RAW frame being
        // rendered so the finished M9 bitmap is committed to ImageView upright.
        final int previewRotation =
                PhotonCamera.getGravity().getCameraRotation(mSensorOrientation);
        Log.d(TAG, "M9LIVEWYSIWYG1F liveRotation=" + previewRotation
                + " staleStillRotation=" + cameraRotation
                + " sensorOrientation=" + mSensorOrientation);
        m9LivePreviewExecutor.execute(() -> {
'''
c=replace_once(c,old,new,'live preview rotation source')

controller.write_text(c)

# Distinct build identity only.
g=gradle.read_text()
lines=g.splitlines()
changed=False
for i,line in enumerate(lines):
    stripped=line.strip()
    if stripped.startswith('versionName '):
        if 'm9livewysiwyg1f' not in stripped.lower():
            prefix=line[:len(line)-len(line.lstrip())]
            value=stripped[len('versionName '):].strip()
            quote='"' if value.startswith('"') else "'"
            if not (value.startswith(quote) and value.endswith(quote)):
                raise SystemExit('M9LIVEWYSIWYG1F unsupported versionName syntax: '+line)
            base=value[1:-1]
            lines[i]=prefix+'versionName '+quote+base+'-m9livewysiwyg1f-liveorientation'+quote
            changed=True
        break
else:
    raise SystemExit('M9LIVEWYSIWYG1F versionName missing')
if changed:
    gradle.write_text('\n'.join(lines)+('\n' if g.endswith('\n') else ''))

print('M9LIVEWYSIWYG1F_LIVEORIENTATION applied')
print(' - full-source 1C M9 render untouched')
print(' - 1E throttle untouched')
print(' - live preview orientation now snapshots current gravity-derived camera rotation')
print(' - stale still-capture cameraRotation no longer drives viewfinder bitmap orientation')
print(' - still capture orientation/exposure lock remain unchanged')
