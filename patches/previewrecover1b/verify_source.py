"""Verify bounded temporal change, metadata plumbing, and untouched photographic paths."""
from pathlib import Path
import hashlib,json,sys,gzip,subprocess,tempfile,shutil
parent,root=(Path(x).resolve() for x in sys.argv[1:]);here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def files(r):
 return {p.relative_to(r).as_posix():sha(p)for d in ['app/src','circularbarlib/src']for p in (r/d).rglob('*')if p.is_file()}|{'app/build.gradle':sha(r/'app/build.gradle')}
a,b=files(parent),files(root);m=json.loads((here/'manifest.json').read_text())
changed=sorted(n for n in a.keys()|b.keys()if a.get(n)!=b.get(n))
assert changed==sorted(m['fileOverrides']) and len(changed)==5,changed
for n,d in m['parentFiles'].items():assert a[n]==d,n
for n,d in m['fileOverrides'].items():assert b[n]==d,n
with tempfile.TemporaryDirectory()as tmp:
 t=Path(tmp)
 for n in changed:(t/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/n,t/n)
 subprocess.run(['git','apply','--reverse','--whitespace=nowarn','-'],cwd=t,input=gzip.decompress((here/'previewrecover1b.patch.gz').read_bytes()),check=True)
 for n in changed:assert (t/n).read_bytes()==(parent/n).read_bytes(),n
pkg='app/src/main/java/com/particlesdevs/photoncamera/'
old=(parent/pkg/'m9/preview/M9AutoExposure2D.java').read_text();new=(root/pkg/'m9/preview/M9AutoExposure2D.java').read_text()
def between(s,start,end):return s[s.index(start):s.index(end,s.index(start))]
for start,end in [
 ('    public static final class Stats {','    public static synchronized Decision decide('),
 ('            sceneChosen=selectSceneKeyQualified','            if(target>current+1e-9) {'),
 ('    private static BodyCandidate stabilizeBodyCandidate(', '    private static void resetHighlightRecovery()'),
 ('    private static void resetLowerTargetHysteresis()', '    private static boolean unsafeBacklight(')]:
 end2='    private static void observeRecoveryTarget(' if 'stabilizeBody' in start else end
 original=between(old,start,end);candidate=between(new,start,end2)
 candidate=candidate.replace('            if(recoveryArmed)positiveRiseStepEv=NORMAL_POSITIVE_SLEW_EV;\n','')
 assert candidate==original,start
start='    private static boolean unsafeBacklight('
assert old[old.index(start):]==new[new.index(start):],'later highlight/tap policy changed'
# All other changed files must be diagnostic-only argument/field plumbing.
n=pkg+'m9/preview/M9PreviewFrameState1W.java'
assert (root/n).read_text().replace('                o.put("stateAutoReason", state.plan != null ? state.plan.autoReason : JSONObject.NULL);\n','')==(parent/n).read_text()
n=pkg+'ui/camera/views/viewfinder/MainRenderer.java'
assert (root/n).read_text().replace('uM9EvidenceStage2E, previewTc20Gain1A);','uM9EvidenceStage2E);')==(parent/n).read_text()
n=pkg+'m9/preview/M9RootCausePixels1A.java';s=(root/n).read_text()
for candidate,original in [
 ('private float pendingReferenceScale,pendingPreviewToneGain=1;','private float pendingReferenceScale;'),
 ('int peakUniform,int peakValue,int evidenceUniform,float previewToneGain) {','int peakUniform,int peakValue,int evidenceUniform) {'),
 ('pendingReferenceScale=referenceScale;pendingPreviewToneGain=previewToneGain;','pendingReferenceScale=referenceScale;'),
 ('pendingMirror,pendingEnabled,pendingPreviewToneGain);','pendingMirror,pendingEnabled);'),
 ('final float referenceScale,previewToneGain;','final float referenceScale;'),
 ('boolean mirror,boolean enabled,float previewToneGain) {','boolean mirror,boolean enabled) {'),
 ('referenceScale=reference;this.previewToneGain=previewToneGain;rgba=pixels.clone();','referenceScale=reference;rgba=pixels.clone();'),
 ('e.textureNs,e.submittedNs,0,e.enabled,e.previewToneGain).snapshot','e.textureNs,e.submittedNs,0,e.enabled).snapshot')]:s=s.replace(candidate,original)
assert s==(parent/n).read_text(),'crop sampling changed beyond diagnostic gain retention'
report=dict(status='PASS',parent='2.62-shutterexport1a',version='2.63-previewrecover1b',changedFiles=changed,unchangedScopedFiles=len(a)-5,totalScopedFiles=len(b),reversePatchExactlyRestoresParent=True,
 classificationMeterStatisticsTargetsAndHeadroomLimitsUnchanged=True,
 renderGlCommandsUnchangedExceptPassingExistingGainToDiagnosticRecorder=True,
 afWbColourToneShadersNativeAssetsSavedRenderersAndMonochromUnchanged=True,
 shutterExporterAndPhotoQueuesUnchanged=True,
 behaviorChange='all post-cut recovery rises capped at .25EV until target reached and four fresh probes agree over >=750ms; transient capture exposure follows displayed plan')
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
