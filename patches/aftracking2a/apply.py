#!/usr/bin/env python3
"""M9Cam 3.05 AFTRACKING2A: opt-in arbitrary-tracker Camera2 AF cadence.

Apply only after the verified 3.04 FocusControl1A stage. This affects only
handles opened by the legacy arbitrary-patch tracker; human/pet/area handles
retain the exact 3.04 behaviour. Does not alter RAW, JPEG, exposure, WB,
rendering, AE/AWB regions or any other AF mode.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('source', type=Path)
p.add_argument('--report', type=Path)
a = p.parse_args()
root = a.source.resolve()
here = Path(__file__).resolve().parent
prefix = Path('app/src/main/java/com/particlesdevs/photoncamera')
changed = []

def patch(rel, before, after):
    file = root / rel
    old = file.read_text()
    count = old.count(before)
    if count != 1:
        raise RuntimeError(f'{rel}: expected exactly one anchor, got {count}: {before[:125]!r}')
    file.write_text(old.replace(before, after))
    changed.append(rel.as_posix())

new = prefix / 'control/tracking/ArbitraryAfUpdateGate.java'
if (root / new).exists():
    raise RuntimeError('3.05 already applied: ' + str(new))
(root / new).parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(here / 'src/com/particlesdevs/photoncamera/control/tracking/ArbitraryAfUpdateGate.java',root / new)
changed.append(new.as_posix())

capture = prefix / 'capture/CaptureController.java'
# This public API intentionally leaves the existing newTrackingFocus()
# untouched for all other human, cat/dog, and focus-area controllers.
patch(capture,
    '    /** AF-only ownership for one selected tracking target. All submissions run on the camera handler. */',
    '''    /**
     * Dedicated focus handle for the opt-in arbitrary patch tracker.
     * The human, pet and fixed-area focus handles retain the 3.04 requests.
     */
    public TrackingFocus newTrackingFocusArbitrary() {
        TrackingFocus handle = newTrackingFocus();
        if (handle != null) handle.enableArbitraryCadence();
        return handle;
    }

    /** AF-only ownership for one selected tracking target. All submissions run on the camera handler. */''')
patch(capture,
    '        public boolean matchesFocusSample(FocusStateSnapshot sample) {',
    '''        private volatile boolean arbitraryCadenceEnabled;
        private final com.particlesdevs.photoncamera.control.tracking.ArbitraryAfUpdateGate
                arbitraryRegionGate = new com.particlesdevs.photoncamera.control.tracking.ArbitraryAfUpdateGate();

        /** Enabled once, before the first update; the gate is private to this handle. */
        public void enableArbitraryCadence() { arbitraryCadenceEnabled = true; }

        public boolean matchesFocusSample(FocusStateSnapshot sample) {''')
patch(capture,
    '                            MeteringRectangle[] region={new MeteringRectangle(regionX,regionY,regionW,regionH,1000)};',
    '''                            // The patch box may move 10 Hz, but repeatedly moving
                            // Camera2's AF region for tiny viewfinder changes can
                            // cause needless lens hunting. Limit only this opt-in
                            // arbitrary-tracker handle, on its camera handler.
                            // Human/animal subject handles and Spot/Custom are unchanged.
                            if (arbitraryCadenceEnabled && !arbitraryRegionGate.shouldSubmit(
                                    SystemClock.elapsedRealtime(),regionX,regionY,regionW,regionH)) {
                                completed.accept(true); // still tracking; no Camera2 mutation
                                return;
                            }
                            MeteringRectangle[] region={new MeteringRectangle(regionX,regionY,regionW,regionH,1000)};''')

# Existing 3.04 source installs a patch tracker with a separate Camera2 handle.
# Keep its template matcher, PixelCopy, confidence, tracking box, coordinates,
# lifecycle and detector priority byte-for-byte. Change only handle construction.
tracker = prefix / 'ui/camera/FocusTrackingController.java'
patch(tracker, '.newTrackingFocus()', '.newTrackingFocusArbitrary()')

gradle = Path('app/build.gradle')
patch(gradle, 'versionCode 27304', 'versionCode 27305')
patch(gradle, "versionName '3.04-focuscontrol1a'", "versionName '3.05-aftracking2a'")
patch(gradle, 'M9Cam_3.04_FOCUSCONTROL1A', 'M9Cam_3.05_AFTRACKING2A')

src_capture = (root / capture).read_text()
src_tracker = (root / tracker).read_text()
assert 'public TrackingFocus newTrackingFocusArbitrary()' in src_capture
assert '.newTrackingFocusArbitrary()' in src_tracker
assert src_tracker.count('.newTrackingFocusArbitrary()') == 1
assert 'SystemClock.elapsedRealtime(),regionX,regionY,regionW,regionH' in src_capture
assert 'if (arbitraryCadenceEnabled && !arbitraryRegionGate.shouldSubmit' in src_capture
assert 'CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE' in src_capture
assert (root / 'app/src/main/res/xml/preferences_m9.xml').exists()
assert (root / 'app/src/main/res/xml/preferences_monochrom.xml').exists()

report = dict(
    status='STAGED_FOR_ANDROID_BUILD',
    stage='3.05-aftracking2a', parent='3.04-focuscontrol1a',
    changedFiles=sorted(set(changed)),
    origin='M9 existing 2.72 local visual-patch tracker',
    arbitraryPatchTrackingOptInOnly=True,
    subjectDetectorChanges=False,
    humanAnimalSpotCustomUnchanged=True,
    continuousPictureAfRegionRequestsRetained=True,
    aeAwbExposureAndRenderingUnchanged=True,
    firstOpticalDeviceTestPending=True,
    gateSha256=hashlib.sha256((root/new).read_bytes()).hexdigest(),
)
if a.report:
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
