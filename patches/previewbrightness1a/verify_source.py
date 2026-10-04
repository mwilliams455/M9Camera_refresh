"""Verify the candidate changes preview prediction only."""
from pathlib import Path
import hashlib,json,sys

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(parent,root,out):
    here=Path(__file__).resolve().parent;manifest=json.loads((here/'manifest.json').read_text())
    j='app/src/main/java/com/particlesdevs/photoncamera/'
    allowed={j+'m9/preview/M9PreviewTc20Math1A.java',j+'m9/preview/M9PreviewEvidence2E.java',j+'m9/preview/M9PreviewFrameState1W.java',j+'ui/camera/views/viewfinder/MainRenderer.java','app/src/main/assets/shaders/preview/main_fs.glsl'}
    added={'app/src/test/java/com/particlesdevs/photoncamera/m9/M9PreviewBrightnessTest.java'}
    old={p.relative_to(parent).as_posix():p for p in (parent/'app/src').rglob('*') if p.is_file()}
    new={p.relative_to(root).as_posix():p for p in (root/'app/src').rglob('*') if p.is_file()}
    assert not old.keys()-new.keys();assert new.keys()-old.keys()==added
    changed={n for n in old if digest(old[n])!=digest(new[n])};assert changed==allowed,changed
    for n,d in manifest['parentFiles'].items():assert digest(parent/n)==d,n
    for n,d in manifest['fileOverrides'].items():assert digest(root/n)==d,n
    main=j+'ui/camera/views/viewfinder/MainRenderer.java'
    assert (root/main).read_text().replace('mM9CurveTex != 0, previewTc20Gain1A);','mM9CurveTex != 0);')==(parent/main).read_text()
    evidence=(root/(j+'m9/preview/M9PreviewEvidence2E.java')).read_text()
    for marker in ['(i==1||i==TC20_PANEL)?referenceScale:frame.exposureScale','GLES30.glUniform1f(tc20Uniform,i==2?displayTc20Gain:1.0f);','now-e.submittedNs<=FRESH_NS','frame.plan.cameraId.equals(e.state.plan.cameraId)','Math.abs(frame.resultTimestampNs-e.state.resultTimestampNs)<=RESULT_MATCH_NS','appliedTc20Ev=Math.min(appliedTc20Ev,0.0);','previewTc20AppliedGain",e.displayGain']:
        assert marker in evidence,marker
    meter=(root/(j+'m9/preview/M9PreviewMeter2D.java')).read_text()
    assert 'GLES30.glUniform1f(tc20Uniform,1.0f);' in meter
    shader=(root/'app/src/main/assets/shaders/preview/main_fs.glsl').read_text()
    assert 'clamp(uM9PreviewTc20Gain1A,0.70710678,1.41421356)' in shader
    # Everything before the TC20 probe, including inverse decoding, five saturation
    # matrices, five contrast curves and TG1, is byte-identical except the comment.
    def colour_prefix(path):return path.read_text().split('vec4 previewTc20Probe1A')[0].split('vec3 previewTc20Probe1A')[0].replace('// M9PREVIEWTC20NEG1A: preview-only bounded TC20 darkening prediction.','// M9PREVIEWBRIGHTNESS1A: preview-only bounded JPEG tone prediction.')
    assert colour_prefix(parent/'app/src/main/assets/shaders/preview/main_fs.glsl')==colour_prefix(root/'app/src/main/assets/shaders/preview/main_fs.glsl')
    report=dict(status='passed',unchangedExistingAppSourceFiles=len(old)-len(changed),changedExistingAppSourceFiles=sorted(changed),savedJpegDngAndNativeSourceUnchanged=True,captureExposurePlanAndAutoTapMeterUnchanged=True,autoProbeForcesUnityToneGain=True,previewToneUsesNeutralReference=True,allPreferencesProfilesMenusAndDisplayAidsUnchanged=True,existingColourMathPreserved=True,actualDrawAndSampleGainRecorded=True,phoneValidationPending=True)
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main(*map(lambda p:Path(p).resolve(),sys.argv[1:]))
