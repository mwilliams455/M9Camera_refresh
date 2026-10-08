"""Verify exact delta and preserved metering/render/capture paths against 2.65."""
from pathlib import Path
import hashlib,json,sys,gzip,subprocess,tempfile,shutil
parent,root=(Path(x).resolve() for x in sys.argv[1:]);here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def files(r):
 return {p.relative_to(r).as_posix():sha(p)for d in ['app/src','circularbarlib/src']for p in (r/d).rglob('*')if p.is_file()}|{'app/build.gradle':sha(r/'app/build.gradle')}
a,b=files(parent),files(root);m=json.loads((here/'manifest.json').read_text())
fingerprint=lambda f:hashlib.sha256(json.dumps(f,sort_keys=True,separators=(',',':')).encode()).hexdigest()
assert fingerprint(a)==m['parentScopedSha256']
assert fingerprint(b)==m['candidateScopedSha256']
changed=sorted(n for n in a.keys()|b.keys()if a.get(n)!=b.get(n))
assert changed==sorted(m['fileOverrides']) and len(changed)==6,changed
assert len(m['newFiles'])==2
for n,d in m['parentFiles'].items():assert a[n]==d,n
for n,d in m['fileOverrides'].items():assert b[n]==d,n
with tempfile.TemporaryDirectory()as tmp:
 t=Path(tmp)
 for n in changed:(t/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/n,t/n)
 subprocess.run(['git','apply','--reverse','--whitespace=nowarn','-'],cwd=t,input=gzip.decompress((here/'exposuresettle1a.patch.gz').read_bytes()),check=True)
 for n in changed:
  if n in m['newFiles']:assert not (t/n).exists(),n
  else:assert (t/n).read_bytes()==(parent/n).read_bytes(),n
pkg='app/src/main/java/com/particlesdevs/photoncamera/m9/preview/'
old=(parent/pkg/'M9AutoExposure2D.java').read_text();new=(root/pkg/'M9AutoExposure2D.java').read_text()
clean=new.replace('    private static final M9ExposureRise1A placementRise=new M9ExposureRise1A(1e-9);\n','').replace('    private static boolean placementAcquired;\n','').replace('placementRise.reset();placementAcquired=false;','')
start='    public static synchronized Decision decide('
assert old[:old.index(start)]==clean[:clean.index(start)],'sampling/statistics/public headroom changed'
start='    private static BodyCandidate stabilizeBodyCandidate('
assert old[old.index(start):]==new[new.index(start):],'spatial body/anchor/target/headroom/tap calculations changed'
start='                if(hardSafetyRelease) {';end='            if(recoveryArmed&&freshSample) {'
assert old[old.index(start):old.index(end)]==new[new.index(start):new.index(end)],'immediate clipping cut or ordinary descent changed'
start='            sceneChosen=selectSceneKeyQualified';end='            double current=haveAuto?heldAutoEv:boundedLegacy;'
assert old[old.index(start):old.index(end)]==new[new.index(start):new.index(end)],'placement requests or clipping ceilings changed'
assert 'if(placementAcquired)' in new and 'placementRise.limit(current,rawTarget,sample.submittedNs,freshSample)' in new
assert 'if(recoveryArmed||placementAcquired)positiveRiseStepEv=NORMAL_POSITIVE_SLEW_EV;' in new
n=pkg+'M9PreviewEvidence2E.java';old=(parent/n).read_text();new=(root/n).read_text()
start='    public void sample(';end='    private void fail('
assert old[old.index(start):old.index(end)]==new[new.index(start):new.index(end)],'GL sampling or evidence/tone analysis changed'
for rel in ['M9BackgroundQualification1A.java','M9OpenAnchorQualification1A.java','M9PreviewTc20Math1A.java']:
 assert (root/pkg/rel).read_bytes()==(parent/pkg/rel).read_bytes(),rel
report=dict(status='PASS',parent='2.65-anchorsettle1a',version='2.66-exposuresettle1a',changedFiles=changed,
 unchangedScopedFiles=len(b)-6,totalScopedFiles=len(b),reversePatchExactlyRestoresParent=True,
 neutralProbeStatisticsSpatialBodyAndAnchorDetectionTargetsRawHeadroomAndTapCalculationsUnchanged=True,
 immediateHardClippingCutOrdinaryDescentAndRawPlacementRequestBlocksByteIdentical=True,
 tc20PixelMathAndGlSamplingByteIdentical=True,
 afSensorMeteringWbColourToneShadersNativeAssetsSavedRenderersAndMonochromUnchanged=True,
 shutterExporterAndPhotoQueuesUnchanged=True,
 behaviorChange='After initial acquisition all Auto rises require four fresh probes spanning >=750ms and slew at .25 EV. Tone rises use the same qualification and existing .125 EV slew; Auto/user EV changes interrupt pending tone rises. Qualified tone survives a <=1s metadata gap only with valid same-owner sources and reference energy within .25 EV.',
 diagnosticChange='M9METERHISTORY1C retains base/last-safe/first-rejected highlight field summaries plus placement and tone coordination columns in existing bounded rings')
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
