"""Verify exact delta and preserved metering/render/capture paths against 2.64."""
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
assert changed==sorted(m['fileOverrides']) and len(changed)==4,changed
assert len(m['newFiles'])==1
for n,d in m['parentFiles'].items():assert a[n]==d,n
for n,d in m['fileOverrides'].items():assert b[n]==d,n
with tempfile.TemporaryDirectory()as tmp:
 t=Path(tmp)
 for n in changed:(t/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/n,t/n)
 subprocess.run(['git','apply','--reverse','--whitespace=nowarn','-'],cwd=t,input=gzip.decompress((here/'anchorsettle1a.patch.gz').read_bytes()),check=True)
 for n in changed:
  if n in m['newFiles']:assert not (t/n).exists(),n
  else:assert (t/n).read_bytes()==(parent/n).read_bytes(),n
pkg='app/src/main/java/com/particlesdevs/photoncamera/m9/preview/'
old=(parent/pkg/'M9AutoExposure2D.java').read_text();new=(root/pkg/'M9AutoExposure2D.java').read_text()
clean=new.replace('    private static final M9OpenAnchorQualification1A openAnchorQualification=new M9OpenAnchorQualification1A();\n','').replace('openAnchorQualification.reset();','')
start='    public static synchronized Decision decide('
assert old[:old.index(start)]==clean[:clean.index(start)],'sampling/statistics/public headroom changed'
start='    private static BodyCandidate stabilizeBodyCandidate('
assert old[old.index(start):]==new[new.index(start):],'spatial body/anchor/target/headroom/tap calculations changed'
start='            double current=haveAuto?heldAutoEv:boundedLegacy;'
end='            if(useBacklight) {\n                if(backlightRequest>effectivePositiveLimit'
assert old[old.index(start):old.index(end)]==new[new.index(start):new.index(end)],'acquisition, slew, hard clipping cut or post-cut recovery changed'
assert new.index('hardPositiveLimit=positiveLimit;')<new.index('positiveLimit=Math.min(positiveLimit,qualifiedOpenAnchorCap);')
assert 'result=Math.min(target,hardPositiveLimit);' in new
assert 'positiveLimit=Math.min(positiveLimit,qualifiedBackgroundCap);' in new
n=pkg+'M9MeterDecisionHistory1A.java';s=(root/n).read_text()
s=s.replace('"M9METERHISTORY1B"','"M9METERHISTORY1A"').replace('"openAnchorLimitEv","sceneRequestEv","backlightRequestEv",\n        "qualifiedOpenAnchorCapEv","rawOpenAnchorMask","qualifiedOpenAnchorMask",\n        "openAnchorQualificationConfirmations"};','"openAnchorLimitEv","sceneRequestEv","backlightRequestEv"};')
assert s==(parent/n).read_text(),'history changed beyond appended Auto fields and revision'
report=dict(status='PASS',parent='2.64-backgroundsettle1a',version='2.65-anchorsettle1a',changedFiles=changed,
 unchangedScopedFiles=len(b)-4,totalScopedFiles=len(b),reversePatchExactlyRestoresParent=True,
 neutralProbeStatisticsSpatialBodyAndAnchorDetectionTargetsRawHeadroomAndTapCalculationsUnchanged=True,
 acquisitionSlewHardClippingCutAndPostCutRecoveryBlockByteIdentical=True,
 backgroundQualificationTc20MathFreshnessResetSlewAndGlCommandsUnchanged=True,
 afSensorMeteringWbColourToneShadersNativeAssetsSavedRenderersAndMonochromUnchanged=True,
 shutterExporterAndPhotoQueuesUnchanged=True,
 behaviorChange='open-anchor appearance/disappearance/tier changes require four fresh spatially coherent probes agreeing within .25EV over >=750ms; anchor cap excluded from hard clipping ceiling; current hard limits remain immediate',
 diagnosticChange='four appended Auto scalar columns plus anchor qualification reason; history revision M9METERHISTORY1B')
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
