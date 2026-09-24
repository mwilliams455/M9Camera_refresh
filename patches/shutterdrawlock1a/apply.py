"""Apply shutter/display-plan locking after exact M9PREVIEWTC20NEG1A."""
from pathlib import Path
import hashlib,json,sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

GRADLE='app/build.gradle'
CONTROLLER='app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
GLPREVIEW='app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/GLPreview.java'
RENDERER='app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java'
ID='M9SHUTTERDRAWLOCK1A'

BASELINE={
 GRADLE:'87544a6d20909d044cfb8dd60ca4c5aa4cd8b7b58089b6ddf7ea3b7e31e7c685',
 CONTROLLER:'28ab8f3779c94c61243d0723b24f980a9c6689da0702f5731d0b29bef9a416a7',
 GLPREVIEW:'f970109a367deaf116de1875b208ee74fb7f65054700343a9e68d6ebe5f4da24',
 RENDERER:'6c7dbd6f9884986836786f81404615f1827229e8c5167ec10c5ea3480d289a95',
}
CHANGED=set(BASELINE)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def transform_renderer(s):
    anchor='''    public String snapshotM9DrawState1W(long shutterNs,
            com.particlesdevs.photoncamera.m9.M9ExposurePlan1A plan) {
        M9PreviewFrameState1W.Draw draw = mM9LastDraw1W;
'''
    insert='''    /**
     * M9SHUTTERDRAWLOCK1A: return only the plan that actually reached a recent GL draw.
     * A camera-thread plan that has not reached the viewfinder is not shutter authority.
     */
    public com.particlesdevs.photoncamera.m9.M9ExposurePlan1A snapshotM9DrawPlan1A(
            long shutterElapsedNs) {
        M9PreviewFrameState1W.Draw draw = mM9LastDraw1W;
        if (draw == null || draw.state == null || draw.state.plan == null) return null;
        long ageNs = shutterElapsedNs - draw.submittedElapsedNs;
        if (ageNs < 0L || ageNs > 1_500_000_000L) return null;
        return draw.state.plan;
    }

'''
    return one(s,anchor,insert+anchor,'renderer draw-plan export')

def transform_glpreview(s):
    anchor='''    public String snapshotM9DrawState1W(long shutterNs,
            com.particlesdevs.photoncamera.m9.M9ExposurePlan1A plan) {
        return !isAvailable() ? M9PreviewFrameState1W.unavailable("GL_surface_unavailable")
                : mRenderer.snapshotM9DrawState1W(shutterNs, plan);
    }
'''
    new=anchor+'''
    /** M9SHUTTERDRAWLOCK1A: immutable plan of the last recent GL draw. */
    public com.particlesdevs.photoncamera.m9.M9ExposurePlan1A snapshotM9DrawPlan1A(
            long shutterElapsedNs) {
        return !isAvailable() ? null : mRenderer.snapshotM9DrawPlan1A(shutterElapsedNs);
    }
'''
    return one(s,anchor,new,'GLPreview draw-plan wrapper')

def transform_controller(s):
    # Central validated accessor. This reuses the exact control/age predicates of the
    # camera-thread plan but makes the GL-drawn plan authoritative.
    anchor='''    public M9ExposurePlan1A getM9ExposurePlan1A() {
        M9ExposurePlan1A plan = m9ExposurePlan1A;
        return plan != null && plan.matches(PhotonCamera.getSettings().mCameraID,
                PhotonCamera.getSettings().selectedMode.name(), SystemClock.elapsedRealtime(),
                paramController.getM9UserEv1A(), (long) paramController.getCurrentExposureValue(),
                (int) paramController.getCurrentISOValue()) ? plan : null;
    }
'''
    helper=anchor+'''
    /**
     * M9SHUTTERDRAWLOCK1A.
     * Validate the exact plan whose GL commands were most recently submitted. The latest
     * camera callback may be newer than the pixels still visible to the photographer.
     */
    private M9ExposurePlan1A getM9DisplayedExposurePlan1A(long shutterElapsedNs) {
        if (mTextureView == null) return null;
        M9ExposurePlan1A plan = mTextureView.snapshotM9DrawPlan1A(shutterElapsedNs);
        if (plan == null) return null;
        return plan.matches(PhotonCamera.getSettings().mCameraID,
                PhotonCamera.getSettings().selectedMode.name(), SystemClock.elapsedRealtime(),
                paramController.getM9UserEv1A(), (long) paramController.getCurrentExposureValue(),
                (int) paramController.getCurrentISOValue()) ? plan : null;
    }
'''
    s=one(s,anchor,helper,'controller displayed-plan helper')

    old_wait='''            if (mState == STATE_WAITING_EXPOSURE_PLAN1A && getM9ExposurePlan1A() != null) {
                mState = STATE_PICTURE_TAKEN;
                captureStillPicture();
            }
'''
    new_wait='''            if (mState == STATE_WAITING_EXPOSURE_PLAN1A
                    && getM9DisplayedExposurePlan1A(SystemClock.elapsedRealtimeNanos()) != null) {
                mState = STATE_PICTURE_TAKEN;
                captureStillPicture();
            }
'''
    s=one(s,old_wait,new_wait,'preview wait readiness')

    old='''            final boolean plannedCapture1A = paramController.useM9ExposurePlan1A();
            final M9ExposurePlan1A basePlan1W = plannedCapture1A ? getM9ExposurePlan1A() : null;
            final M9ExposurePlan1A capturePlan1A = basePlan1W == null ? null
                    : basePlan1W.withShutterPreviewSnapshot1W(mTextureView != null
                        ? mTextureView.snapshotM9DrawState1W(m9LivePairShutterElapsedNs1P, basePlan1W)
                        : com.particlesdevs.photoncamera.m9.preview.M9PreviewFrameState1W
                            .unavailable("GL_view_unavailable"));
'''
    new='''            final boolean plannedCapture1A = paramController.useM9ExposurePlan1A();
            final long shutterDrawLockNs1A = m9LivePairShutterElapsedNs1P > 0L
                    ? m9LivePairShutterElapsedNs1P : SystemClock.elapsedRealtimeNanos();
            final M9ExposurePlan1A latestCameraPlan1A = plannedCapture1A
                    ? getM9ExposurePlan1A() : null;
            final M9ExposurePlan1A basePlan1W = plannedCapture1A
                    ? getM9DisplayedExposurePlan1A(shutterDrawLockNs1A) : null;
            final M9ExposurePlan1A capturePlan1A = basePlan1W == null ? null
                    : basePlan1W.withShutterPreviewSnapshot1W(mTextureView != null
                        ? mTextureView.snapshotM9DrawState1W(shutterDrawLockNs1A, basePlan1W)
                        : com.particlesdevs.photoncamera.m9.preview.M9PreviewFrameState1W
                            .unavailable("GL_view_unavailable"));
            if (plannedCapture1A && capturePlan1A != null) {
                Log.d(TAG, "M9SHUTTERDRAWLOCK1A displayedPlanId=" + capturePlan1A.id
                        + " latestCameraPlanId="
                        + (latestCameraPlan1A != null ? latestCameraPlan1A.id : -1L)
                        + " samePlan=" + (latestCameraPlan1A != null
                                && latestCameraPlan1A.id == capturePlan1A.id)
                        + " iso=" + capturePlan1A.iso
                        + " exposureNs=" + capturePlan1A.exposureNs);
            }
'''
    s=one(s,old,new,'capture uses last GL-drawn plan')
    return s

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root);before=proof['before']
    if now!=proof['after']: raise SystemExit('SHUTTERDRAWLOCK assembled source drift')
    changed={k for k in before if now.get(k)!=before[k]}
    added=set(now)-set(before);removed=set(before)-set(now)
    if changed!=CHANGED or added or removed:
        raise SystemExit('unexpected delta changed=%r added=%r removed=%r'%
                         (sorted(changed),sorted(added),sorted(removed)))
    c=(root/CONTROLLER).read_text()
    g=(root/GLPREVIEW).read_text()
    r=(root/RENDERER).read_text()
    checks={
      'controller marker':'M9SHUTTERDRAWLOCK1A' in c,
      'displayed accessor':'getM9DisplayedExposurePlan1A(shutterDrawLockNs1A)' in c,
      'waits for GL draw':'getM9DisplayedExposurePlan1A(SystemClock.elapsedRealtimeNanos())' in c,
      'latest plan diagnostic only':'latestCameraPlan1A' in c,
      'capture base not latest':('final M9ExposurePlan1A basePlan1W = plannedCapture1A' in c\n            and '? getM9DisplayedExposurePlan1A(shutterDrawLockNs1A) : null;' in c\n            and 'final M9ExposurePlan1A basePlan1W = plannedCapture1A ? getM9ExposurePlan1A() : null;' not in c),
      'GL wrapper':'snapshotM9DrawPlan1A' in g,
      'renderer freshness':'ageNs > 1_500_000_000L' in r,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('SHUTTERDRAWLOCK verify failed: '+name)
    gradle=(root/GRADLE).read_text()
    if "versionName '1.71-m9shutterdrawlock1a-tg1'" not in gradle or 'versionCode 26691' not in gradle:
        raise SystemExit('SHUTTERDRAWLOCK build identity mismatch')
    # Explicit photographic freezes.
    for rel in [
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewEvidence2E.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewTc20Math1A.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
      'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
      'app/src/main/assets/shaders/preview/main_fs.glsl',
      'app/src/main/cpp/m9color_jni.cpp',
    ]:
        if before[rel]!=now[rel]: raise SystemExit('frozen photographic seam changed '+rel)
    return {
      'revision':ID,'version':'1.71-m9shutterdrawlock1a-tg1','versionCode':26691,
      'changed':sorted(CHANGED),
      'shutterAuthority':'last_recent_GL_draw_plan',
      'maxDrawAgeMs':1500,
      'latestCameraPlanRole':'diagnostic_only_at_shutter',
      'auto_previewTC20_renderer_JPEG_DNG_frozen':True,
      'device_validation_pending':True,
    }

def main(root):
    root=root.resolve();receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists(): print(json.dumps(verify(root),indent=2));return
    for rel,expected in BASELINE.items():
        actual=sha(root/rel)
        if actual!=expected: raise SystemExit(f'SHUTTERDRAWLOCK baseline mismatch {rel}: {actual}')
    gradle=(root/GRADLE).read_text()
    if "versionName '1.70-m9previewtc20neg1a-tg1'" not in gradle or 'versionCode 26690' not in gradle:
        raise SystemExit('SHUTTERDRAWLOCK requires exact PREVIEWTC20NEG1A parent identity')

    before=inventory(root)
    (root/RENDERER).write_text(transform_renderer((root/RENDERER).read_text()))
    (root/GLPREVIEW).write_text(transform_glpreview((root/GLPREVIEW).read_text()))
    (root/CONTROLLER).write_text(transform_controller((root/CONTROLLER).read_text()))
    gradle=one(gradle,'versionCode 26690','versionCode 26691','version code')
    gradle=one(gradle,"versionName '1.70-m9previewtc20neg1a-tg1'",
               "versionName '1.71-m9shutterdrawlock1a-tg1'",'version name')
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__': main(Path(sys.argv[1]))
