#!/usr/bin/env python3
"""Apply M9 3.06 AFTRACKING3A on the exact reconstructed 3.05 source.

Three visual-only changes: bounded multi-scale patch matching, local occlusion
hold, and an explicit no-AF-request HOLD decision. Original M9/Mono photo,
video, AE/AWB, RAW, DNG, JPEG, colour and human/pet detection stay untouched.
"""
from pathlib import Path
import argparse,hashlib,shutil,json
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--report',type=Path)
a=p.parse_args()
root=a.source.resolve();here=Path(__file__).resolve().parent
prefix=Path('app/src/main/java/com/particlesdevs/photoncamera')
changed=[]
def patch(rel,old,new):
    f=root/rel
    s=f.read_text()
    count=s.count(old)
    if count != 1:raise ValueError(f'{rel}: anchor count {count} for {old[:100]!r}')
    f.write_text(s.replace(old,new))
    changed.append(rel.as_posix())
def add(rel):
    f=root/prefix/rel
    src=here/'src/com/particlesdevs/photoncamera'/rel
    assert src.is_file(),src
    assert not f.exists(),f
    f.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(src,f);changed.append(f.relative_to(root).as_posix())
# Replace only the pure-Java matcher; original template identity is fixed.
tracker=prefix/'control/tracking/PatchTracker.java'
old_file=root/tracker
assert hashlib.sha256(old_file.read_bytes()).hexdigest()=='4fa2434ff7e31b50b2eda8cfdd95df1c6ee5d5de0a8b406bb30ebae0046691ab','Expected exact 3.05 patch tracker parent'
shutil.copyfile(here/'src/com/particlesdevs/photoncamera/control/tracking/PatchTracker.java',old_file)
changed.append(tracker.as_posix())
add('control/tracking/TrackingFrameDecision.java')
# Changed only in legacy arbitrary tracker. Human/pet and AF-regions remain intact.
controller=prefix/'ui/camera/FocusTrackingController.java'
patch(controller,
    'import com.particlesdevs.photoncamera.control.tracking.PatchTracker;',
    'import com.particlesdevs.photoncamera.control.tracking.PatchTracker;\nimport com.particlesdevs.photoncamera.control.tracking.TrackingFrameDecision;')
patch(controller,
    '    private boolean running, destroyed, busy, selected, acquiring;',
    '    private boolean running, destroyed, busy, selected, acquiring, holding;\n    private long holdSince;')
patch(controller,
    '    void clear() {\n        epoch++; selected = false; acquiring = false;',
    '    void clear() {\n        epoch++; selected = false; acquiring = false; holding = false; holdSince = 0;')
patch(controller,
    '        selected = true; acquiring = true; x = u; y = v; hx = hy = .06f;',
    '        selected = true; acquiring = true; holding = false; holdSince = 0;\n        x = u; y = v; hx = hy = .06f;')
patch(controller,
    '                    if (selected && (now - lastProgress > 600 || now - lastSuccess > 600)) lost();',
    '                    // Preview freshness remains the original strict 600 ms.\n'
    '                    // An occluded subject freezes the last AF region; its\n'
    '                    // extra window is time-bounded, never a valid focus claim.\n'
    '                    if (selected && (now - lastProgress > 600\n'
    '                            || (holding ? now - holdSince > 850 : now - lastSuccess > 600))) lost();')
patch(controller,
    '''                        if (tracked == null || !tracked.tracking || SystemClock.elapsedRealtime() - requested > 500) {
                            lost(); finish(); return;
                        }
                        FocusControlPolicyRegion304Holder holder=''',
    '''                        TrackingFrameDecision.Action decision =
                                TrackingFrameDecision.classify(tracked,
                                        SystemClock.elapsedRealtime() - requested);
                        if (decision == TrackingFrameDecision.Action.RETIRE) {
                            lost(); finish(); return;
                        }
                        if (decision == TrackingFrameDecision.Action.HOLD) {
                            // Never submit new AF regions while a subject is
                            // hidden or its identity has not been reconfirmed.
                            if (!holding) { holding = true; holdSince = SystemClock.elapsedRealtime(); }
                            x = tracked.x; y = tracked.y;
                            hx = tracked.halfWidth; hy = tracked.halfHeight;
                            showHolding(); finish(); return;
                        }
                        FocusControlPolicyRegion304Holder holder=''' )
patch(controller,
    '                                    acquiring = false; lastSuccess = requested;',
    '                                    acquiring = false; holding = false; holdSince = 0;\n                                    lastSuccess = requested;')
patch(controller,
    '        epoch++; selected = false; acquiring = false;\n        if (focus != null) focus.close(); focus = null;\n        show(true);',
    '        epoch++; selected = false; acquiring = false; holding = false; holdSince = 0;\n        if (focus != null) focus.close(); focus = null;\n        show(true);')
patch(controller,
    '    private void show(boolean lost) {',
    '''    private void showHolding() {
        int[] a = new int[2], b = new int[2];
        source.getLocationInWindow(a); overlay.getLocationInWindow(b);
        overlay.showHolding(a[0] - b[0] + geometry.left + x * geometry.w,
                a[1] - b[1] + geometry.top + y * geometry.h,
                hx * geometry.w, hy * geometry.h);
    }
    private void show(boolean lost) {''')
view=prefix/'ui/camera/views/TrackingFocusView.java'
patch(view,
    '    private boolean lost;',
    '    private boolean lost, holding;')
patch(view,
    '        this.x = x; this.y = y; this.halfX = halfX; this.halfY = halfY; this.lost = lost;',
    '        this.x = x; this.y = y; this.halfX = halfX; this.halfY = halfY;\n'
    '        this.lost = lost; this.holding = false;')
patch(view,
    '    @Override protected void onDraw(Canvas canvas) {',
    '''    /** Read-only amber hold indication, never a claimed focused/locked state. */
    public void showHolding(float x, float y, float halfX, float halfY) {
        this.x = x; this.y = y; this.halfX = halfX; this.halfY = halfY;
        lost = false; holding = true;
        setVisibility(VISIBLE);
        setContentDescription(getContext().getString(R.string.focus_tracking_hold3a));
        invalidate();
    }
    @Override protected void onDraw(Canvas canvas) {''')
patch(view,
    '        paint.setColor(lost ? 0xffffba59 : 0xffffffff);',
    '        paint.setColor(holding ? 0xffffba59 : lost ? 0xffffba59 : 0xffffffff);')
patch(view,
    '        String label = getContext().getString(lost ? R.string.focus_tracking_lost : R.string.focus_tracking_active);',
    '        String label = getContext().getString(holding ? R.string.focus_tracking_hold3a :\n'
    '                lost ? R.string.focus_tracking_lost : R.string.focus_tracking_active);')
resource=Path('app/src/main/res/values/focustrack3a.xml')
assert not (root/resource).exists()
(root/resource).write_text('''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="focus_tracking_hold3a">Tracking obscured - AF area held</string>
</resources>
''')
changed.append(resource.as_posix())
patch(Path('app/build.gradle'),'versionCode 27305','versionCode 27306')
patch(Path('app/build.gradle'),"versionName '3.05-aftracking2a'","versionName '3.06-aftracking3a'")
patch(Path('app/build.gradle'),'M9Cam_3.05_AFTRACKING2A','M9Cam_3.06_AFTRACKING3A')
fc=(root/controller).read_text();v=(root/view).read_text()
assert 'focus = fragment.getCaptureController().newTrackingFocus();' in fc
assert 'focus.enableArbitraryCadence();' in fc
assert 'TrackingFrameDecision.Action.HOLD' in fc
assert 'showHolding(); finish(); return' in fc
assert 'overlay.showHolding(' in fc
assert 'showHolding' in v
assert 'pref_focus_tracking' in fc
assert 'FocusTrackingController.KEY' not in v
assert 'CONTROL_AE_REGIONS' not in fc and 'CONTROL_AWB_REGIONS' not in fc
report=dict(status='STAGED_FOR_BUILD',parent='3.05-aftracking2a',version='3.06-aftracking3a',
    changedFiles=sorted(set(changed)),optInLegacyTrackingOnly=True,
    fixedTemplateRetained=True,multiScaleSearch=True,boundedOcclusionHoldMs=850,
    twoFreshMatchesRequiredToRecover=True,occludedFramesNeverUpdateAf=True,
    userConfirmed305StillAvailable=True,existingAnimalAndHumanAfUntouched=True,
    existingCamera2AfCadenceRetained=True,rawJpegExposureWbRenderingUntouched=True,
    deviceValidationPending=True)
if a.report:
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
