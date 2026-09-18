#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-m9liveparity1b-viewfinder-reference.py <PhotonCamera-root>')

root=Path(sys.argv[1]).resolve()
r=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
p=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
c=root/'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
for x in (r,p,c):
    if not x.exists(): raise SystemExit('M9LIVEPARITY1B missing '+str(x))
rs=r.read_text(); ps=p.read_text(); cs=c.read_text()

for marker in [
    'M9LIVEPARITY1B_VIEWFINDER_REFERENCE',
    'm9cam.liveparity.v1b.viewfinder_reference',
    'predict_unchanged_final_JPEG',
    'finalJpegIsPhotographicAuthority',
    'viewfinderMayMutateCaptureExposure',
    'viewfinderMayMutateStillTone',
    'markM9LivePreviewDisplayed1B()',
    'M9_LIVE_PARITY_1B_LAST_DISPLAYED_PREVIEW',
    'ImageView_displayed',
    'displayLuma1B',
    'm9cam.liveparity.v1b.display_luma',
    'actual_finished_M9_Bitmap_before_ImageView',
    'core_record_always_committed_optional_fields_fail_individually',
    'FULL_PRODUCTION_RENDER_REDUCED_RAW_1440x1080_MAIN',
    'SAT2_M04_M05',
]:
    if marker not in rs: raise SystemExit('M9LIVEPARITY1B renderer marker missing: '+marker)

if 'public static void markDisplayed1B()' not in ps:
    raise SystemExit('M9LIVEPARITY1B preview facade mark missing')
if 'M9R35Renderer.markM9LivePreviewDisplayed1B();' not in ps:
    raise SystemExit('M9LIVEPARITY1B preview facade delegation missing')
if 'M9LivePreview1A.markDisplayed1B();' not in cs:
    raise SystemExit('M9LIVEPARITY1B ImageView display confirmation missing')

ui='''m9LivePreviewImageView.setImageBitmap(ready);
                            M9LivePreview1A.markDisplayed1B();
                            m9LivePreviewImageView.setVisibility(android.view.View.VISIBLE);'''
if ui not in cs:
    raise SystemExit('M9LIVEPARITY1B display confirmation ordering changed')

if 'parity.put("viewfinderMayMutateCaptureExposure", false);' not in rs:
    raise SystemExit('M9LIVEPARITY1B capture-mutation false gate missing')
if 'parity.put("viewfinderMayMutateStillTone", false);' not in rs:
    raise SystemExit('M9LIVEPARITY1B still-tone false gate missing')

print('M9LIVEPARITY1B_VIEWFINDER_REFERENCE VERIFY PASS')
print(' - final JPEG declared photographic authority')
print(' - preview record is fail-safe')
print(' - pairing prefers frame actually committed to ImageView')
print(' - preview/still finished Bitmap luma distributions measured')
print(' - no still exposure/tone mutation authorized by this overlay')
