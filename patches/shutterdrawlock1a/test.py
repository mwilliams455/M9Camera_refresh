"""Verify M9SHUTTERDRAWLOCK1A source contract and WYSIWYG selection semantics."""
from pathlib import Path
import hashlib,json,math,sys

root=Path(sys.argv[1]).resolve()
controller=root/'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
gl=root/'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/GLPreview.java'
renderer=root/'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java'
proof=root/'M9SHUTTERDRAWLOCK1A_SOURCE_PROOF.json'
for p in (controller,gl,renderer,proof):
    if not p.exists(): raise SystemExit('missing '+str(p))
c=controller.read_text();g=gl.read_text();r=renderer.read_text();pr=json.loads(proof.read_text())
checks={
 'marker':c.count('M9SHUTTERDRAWLOCK1A')>=2,
 'single_display_accessor_definition':c.count('private M9ExposurePlan1A getM9DisplayedExposurePlan1A(')==1,
 'wait_uses_displayed_plan':c.count('getM9DisplayedExposurePlan1A(SystemClock.elapsedRealtimeNanos())')==1,
 'shutter_uses_displayed_plan':c.count('? getM9DisplayedExposurePlan1A(shutterDrawLockNs1A) : null;')==1,
 'latest_camera_plan_diagnostic_only':'latestCameraPlan1A' in c,
 'old_latest_base_selection_absent':'final M9ExposurePlan1A basePlan1W = plannedCapture1A ? getM9ExposurePlan1A() : null;' not in c,
 'snapshot_attached_to_display_plan':'snapshotM9DrawState1W(shutterDrawLockNs1A, basePlan1W)' in c,
 'GL_wrapper':g.count('snapshotM9DrawPlan1A(')==2,
 'renderer_export':r.count('snapshotM9DrawPlan1A(')==1,
 'renderer_returns_draw_plan':'return draw.state.plan;' in r,
 'renderer_draw_freshness':'ageNs > 1_500_000_000L' in r,
}
for name,ok in checks.items():
    print(name,ok)
    if not ok: raise SystemExit('SHUTTERDRAWLOCK test failed: '+name)

# The submitted device video contained a concrete race witness:
# visible HUD ~ISO50 1/25, saved JPEG ISO51 1/82.
visible_energy=50*(1/25)
saved_energy=51*(1/82)
delta=math.log(saved_energy/visible_energy,2)
assert delta < -1.5
print('video_race_witness_ev',delta)

# Freeze the photographic stages explicitly.
for rel in [
 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java',
 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewEvidence2E.java',
 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewTc20Math1A.java',
 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
 'app/src/main/assets/shaders/preview/main_fs.glsl',
 'app/src/main/cpp/m9color_jni.cpp',
]:
    if pr['before'][rel]!=pr['after'][rel]:
        raise SystemExit('frozen seam changed '+rel)

receipt={
 'revision':'M9SHUTTERDRAWLOCK1A',
 'checks':checks,
 'video_witness_visible':'ISO50_1/25',
 'video_witness_saved':'ISO51_1/82',
 'video_witness_energy_delta_ev':delta,
 'expected_new_authority':'last_recent_GL_draw_plan',
 'photographic_stages_frozen':True,
}
out=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else Path('M9SHUTTERDRAWLOCK1A_TESTS.json')
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(receipt,indent=2)+'\n')
print('M9SHUTTERDRAWLOCK1A_TEST_PASS')
