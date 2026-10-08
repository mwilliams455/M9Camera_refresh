"""Verify exact source delta, reconstruction and preserved photographic paths."""
from pathlib import Path
import hashlib,json,sys,gzip,subprocess,tempfile,shutil
parent,root=(Path(x).resolve() for x in sys.argv[1:]);here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def files(r):
 return {p.relative_to(r).as_posix():sha(p)for d in ['app/src','circularbarlib/src']for p in (r/d).rglob('*')if p.is_file()}|{'app/build.gradle':sha(r/'app/build.gradle')}
a,b=files(parent),files(root);m=json.loads((here/'manifest.json').read_text())
fingerprint=lambda files:hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
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
 subprocess.run(['git','apply','--reverse','--whitespace=nowarn','-'],cwd=t,input=gzip.decompress((here/'backgroundsettle1a.patch.gz').read_bytes()),check=True)
 for n in changed:
  if n in m['newFiles']:assert not (t/n).exists(),n
  else:assert (t/n).read_bytes()==(parent/n).read_bytes(),n
pkg='app/src/main/java/com/particlesdevs/photoncamera/'
old=(parent/pkg/'m9/preview/M9AutoExposure2D.java').read_text();new=(root/pkg/'m9/preview/M9AutoExposure2D.java').read_text()
clean=new.replace('    private static final M9BackgroundQualification1A backgroundQualification=new M9BackgroundQualification1A();\n    private static String historyStatus="";\n    private static long historySampleNs=-1;\n','').replace('        backgroundQualification.reset();\n','')
start='    public static synchronized Decision decide('
assert old[:old.index(start)]==clean[:clean.index(start)],'sampling/statistics/public headroom changed'
start='    private static BodyCandidate stabilizeBodyCandidate('
assert old[old.index(start):]==clean[clean.index(start):],'spatial body/target/headroom/tap calculations changed'
assert 'boolean hardSafetyRelease=hardPositiveLimit<current-1e-9;' in new
assert 'result=Math.min(target,hardPositiveLimit);' in new
assert 'positiveLimit=Math.min(positiveLimit,qualifiedBackgroundCap);' in new
n=pkg+'m9/preview/M9PreviewEvidence2E.java';s=(root/n).read_text()
s=s.replace('    private long historySampleNs=-1;\n    private String historyStatus="";\n','').replace('        boolean liftLimited=false;\n','').replace('                liftLimited=true;\n','').replace('        recordToneDecision(frame,e,now,target,fresh,liftLimited);\n','')
a0=s.index('    private void recordToneDecision(');b0=s.index('    public void sample(',a0);s=s[:a0]+s[b0:]
assert s==(parent/n).read_text(),'tone math, freshness/reset or GL sampling changed beyond evidence recording'
n=pkg+'m9/preview/M9ShutterTrace1A.java';s=(root/n).read_text()
for line in ['                s.root.put("preMeterDecisions",M9MeterDecisionHistory1A.range(ns-3000000000L,ns,camera));\n','                s.root.put("initialPostMeterDecisions",s.root.optJSONObject("postMeterDecisions"));\n','        s.root.put("postMeterDecisions",M9MeterDecisionHistory1A.range(s.join.shutterNs,now,s.join.camera));\n']:s=s.replace(line,'')
assert s==(parent/n).read_text(),'shutter trace changed beyond asynchronous scalar history snapshots'
report=dict(status='PASS',parent='2.63-previewrecover1b',version='2.64-backgroundsettle1a',changedFiles=changed,
 unchangedScopedFiles=len(b)-6,totalScopedFiles=len(b),reversePatchExactlyRestoresParent=True,
 neutralProbeStatisticsSpatialBodyClassificationTargetsAndRawHeadroomCalculationsUnchanged=True,
 tc20MathFreshnessResetSlewAndGlCommandsUnchanged=True,
 afSensorMeteringWbColourToneShadersNativeAssetsSavedRenderersAndMonochromUnchanged=True,
 shutterExporterAndPhotoQueuesUnchanged=True,
 behaviorChange='background qualification requires four fresh probes agreeing within .25 EV over >=750ms; raw clipping/headroom limits remain immediate; background-only lower targets use existing ordinary confirmation and .25EV settling',
 diagnosticChange='separate Auto and TC20 scalar histories, 128 rows each, copied and serialized on existing asynchronous trace worker')
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
