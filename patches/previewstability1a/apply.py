"""Serialize live GPU probes, remove TC20 heap churn and close known HUD null path on exact 1.72."""
from pathlib import Path
import hashlib,json,shutil,sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

GRADLE='app/build.gradle'
MAIN='app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java'
METER='app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewMeter2D.java'
EVIDENCE='app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewEvidence2E.java'
MATH='app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewTc20Math1A.java'
CAMERA='app/src/main/java/com/particlesdevs/photoncamera/ui/camera/CameraFragment.java'
ID='M9PREVIEWSTABILITY1A'

BASELINE={
 GRADLE:'36a5cb8ccfbf3149eb68de32494206e90f579df88824b69d2d595cb3b9e72c34',
 MAIN:'265a1657f97ab70d0c84f18a356e8659d6a3d964c16a965d9e64cccfa6294782',
 METER:'cb7e247eaba40855043cd6d9320f1ec9d162499516cc821242b965308acc5691',
 EVIDENCE:'8571aced3d483bc0d28b8fabd649a1c4e4e0713895ca84af08d0078aba4046df',
 MATH:'f377332766158f7338003d24ce18d282fbf0cf205174196f01b7260a4dc23dd9',
 CAMERA:'8a2c302cb2f7b5e48bdc1de80d576547f6e64ca63434f0d2c16f7b2f55c89063',
}
CHANGED=set(BASELINE)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def method_span(text,signature):
    start=text.index(signature)
    brace=text.index('{',start)
    depth=0
    for i in range(brace,len(text)):
        if text[i]=='{': depth+=1
        elif text[i]=='}':
            depth-=1
            if depth==0:return start,i+1
    raise SystemExit('unbalanced method '+signature)

def transform_meter(s):
    field='''    private boolean disabled;

    public void sample(M9PreviewFrameState1W frame,long textureNs,int exposureUniform,
            int peakUniform,int peakValue,int tc20Uniform,float displayTc20Gain) {'''
    repl='''    private boolean disabled;

    /** GL-thread state only: used to guarantee at most one preview readback is in flight. */
    public boolean isBusy() { return fence != 0; }

    public boolean sample(M9PreviewFrameState1W frame,long textureNs,int exposureUniform,
            int peakUniform,int peakValue,int tc20Uniform,float displayTc20Gain) {'''
    s=one(s,field,repl,'meter signature/busy')
    sig='''    public boolean sample(M9PreviewFrameState1W frame,long textureNs,int exposureUniform,
            int peakUniform,int peakValue,int tc20Uniform,float displayTc20Gain) {'''
    a,b=method_span(s,sig)
    m=s[a:b]
    m=m.replace('if(disabled)return;','if(disabled)return false;',1)
    # Only sample-method early-return guards have this compact spelling.
    m=m.replace('|| Math.abs(textureNs-frame.resultTimestampNs)>150000000L)return;',
                '|| Math.abs(textureNs-frame.resultTimestampNs)>150000000L)return false;',1)
    m=m.replace('|| referenceScale*Math.pow(2,M9AutoExposure2D.ev(STEPS-1))>16)return;',
                '|| referenceScale*Math.pow(2,M9AutoExposure2D.ev(STEPS-1))>16)return false;',1)
    if 'return;' in m:
        raise SystemExit('unconverted bare return in meter sample')
    m=m.replace('            GLES30.glFlush(); // Submit only; readback is mapped after a later zero-timeout fence poll.',
                '            GLES30.glFlush(); // Submit only; readback is mapped after a later zero-timeout fence poll.\n            return true;',1)
    # Error path reaches here after catch/finally.
    m=m[:-1]+'        return false;\n    }'
    return s[:a]+m+s[b:]

def transform_evidence(s):
    anchor='''    private volatile float appliedTc20Gain=1.0f;

    /**'''
    repl='''    private volatile float appliedTc20Gain=1.0f;

    /** GL-thread state only: lets MainRenderer serialize the two PBO/fence probes. */
    public boolean isBusy() { return fence != 0; }

    /**'''
    return one(s,anchor,repl,'evidence busy')

def transform_main(s):
    old='''        if (mM9CurveTex != 0 && mM9Meter2D != null)
            mM9Meter2D.sample(frame1W, textureTimestamp1W, uM9ExposureScale1B,
                    enablePeak, peakEnabled, uM9PreviewTc20Gain1A, previewTc20Gain1A);
        if (mM9Evidence2E != null)
            mM9Evidence2E.sample(frame1W, textureTimestamp1W, mSTexture,
                    uM9ExposureScale1B, enablePeak, peakEnabled, uM9EvidenceStage2E,
                    uM9PreviewTc20Gain1A, previewTc20Gain1A);'''
    new='''        // M9PREVIEWSTABILITY1A: never have both preview readbacks outstanding.
        // Their old shared 250ms cadence could submit/map both PBOs on the same GL frame.
        final boolean m9EvidenceBusy1A = mM9Evidence2E != null && mM9Evidence2E.isBusy();
        boolean m9AutoProbeSubmitted1A = false;
        if (!m9EvidenceBusy1A && mM9CurveTex != 0 && mM9Meter2D != null)
            m9AutoProbeSubmitted1A = mM9Meter2D.sample(frame1W, textureTimestamp1W,
                    uM9ExposureScale1B, enablePeak, peakEnabled,
                    uM9PreviewTc20Gain1A, previewTc20Gain1A);
        final boolean m9AutoProbeBusy1A = mM9Meter2D != null && mM9Meter2D.isBusy();
        if (!m9AutoProbeSubmitted1A && !m9AutoProbeBusy1A && mM9Evidence2E != null)
            mM9Evidence2E.sample(frame1W, textureTimestamp1W, mSTexture,
                    uM9ExposureScale1B, enablePeak, peakEnabled, uM9EvidenceStage2E,
                    uM9PreviewTc20Gain1A, previewTc20Gain1A);'''
    return one(s,old,new,'MainRenderer probe serialization')

def transform_camera(s):
    anchor='''                    IsoExpoSelector.ExpoPair expoPair = IsoExpoSelector.getM9LiveHudPair1A(captureController);
'''
    n=s.count(anchor)
    if n!=1: raise SystemExit('HUD pair call count='+str(n))
    repl='''                    // M9PREVIEWSTABILITY1A: HUD callbacks can outlive camera-controller teardown.
                    if (captureController == null) return;
                    IsoExpoSelector.ExpoPair expoPair = IsoExpoSelector.getM9LiveHudPair1A(captureController);
'''
    return s.replace(anchor,repl)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root);before=proof['before']
    if now!=proof['after']: raise SystemExit('PREVIEWSTABILITY assembled source drift')
    changed={k for k in before if now.get(k)!=before[k]}
    added=set(now)-set(before);removed=set(before)-set(now)
    if changed!=CHANGED or added or removed:
        raise SystemExit('unexpected delta changed=%r added=%r removed=%r'%
                         (sorted(changed),sorted(added),sorted(removed)))
    if (root/MATH).read_bytes()!=(HERE/'M9PreviewTc20Math1A.java').read_bytes():
        raise SystemExit('stability math mismatch')

    main=(root/MAIN).read_text();meter=(root/METER).read_text()
    evidence=(root/EVIDENCE).read_text();camera=(root/CAMERA).read_text()
    checks={
      'meter boolean sample':'public boolean sample(M9PreviewFrameState1W frame' in meter,
      'meter busy':'public boolean isBusy() { return fence != 0; }' in meter,
      'evidence busy':'public boolean isBusy() { return fence != 0; }' in evidence,
      'serial main marker':'M9PREVIEWSTABILITY1A' in main,
      'evidence gated by auto busy':'!m9AutoProbeSubmitted1A && !m9AutoProbeBusy1A' in main,
      'auto gated by evidence busy':'!m9EvidenceBusy1A && mM9CurveTex != 0' in main,
      'hud guards':camera.count('if (captureController == null) return;')>=1,
      'no boxed TC20 sort':'Integer[]' not in (root/MATH).read_text(),
      'persistent TC20 histogram':'ThreadLocal<Scratch>' in (root/MATH).read_text(),
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('PREVIEWSTABILITY verify failed: '+name)

    gradle=(root/GRADLE).read_text()
    if "versionName '1.73-m9previewstability1a-tg1'" not in gradle or 'versionCode 26693' not in gradle:
        raise SystemExit('PREVIEWSTABILITY build identity mismatch')

    # Strict photographic/capture freezes. This branch changes scheduling/diagnostics only.
    for rel in [
      'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
      'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
      'app/src/main/assets/shaders/preview/main_fs.glsl',
      'app/src/main/cpp/m9color_jni.cpp',
    ]:
        if before[rel]!=now[rel]: raise SystemExit('frozen photographic seam changed '+rel)

    return {
      'revision':ID,'version':'1.73-m9previewstability1a-tg1','versionCode':26693,
      'changed':sorted(CHANGED),
      'previewReadbacksSerialized':True,
      'tc20BoxedSortAllocationRemoved':True,
      'knownHudNullCrashGuarded':True,
      'auto_JPEG_DNG_shutterDrawLock_shader_frozen':True,
      'currentPanningCrashRootCauseProven':False,
      'device_validation_pending':True,
    }

def main(root):
    root=root.resolve();receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists(): print(json.dumps(verify(root),indent=2));return
    for rel,expected in BASELINE.items():
        actual=sha(root/rel)
        if actual!=expected: raise SystemExit(f'PREVIEWSTABILITY baseline mismatch {rel}: {actual}')
    gradle=(root/GRADLE).read_text()
    if "versionName '1.72-m9previewtc20neutral1a-tg1'" not in gradle or 'versionCode 26692' not in gradle:
        raise SystemExit('PREVIEWSTABILITY requires exact 1.72 parent identity')

    before=inventory(root)
    (root/METER).write_text(transform_meter((root/METER).read_text()))
    (root/EVIDENCE).write_text(transform_evidence((root/EVIDENCE).read_text()))
    (root/MAIN).write_text(transform_main((root/MAIN).read_text()))
    (root/CAMERA).write_text(transform_camera((root/CAMERA).read_text()))
    shutil.copyfile(HERE/'M9PreviewTc20Math1A.java',root/MATH)
    gradle=one(gradle,'versionCode 26692','versionCode 26693','version code')
    gradle=one(gradle,"versionName '1.72-m9previewtc20neutral1a-tg1'",
               "versionName '1.73-m9previewstability1a-tg1'",'version name')
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__': main(Path(sys.argv[1]))
