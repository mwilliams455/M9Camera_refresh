"""Verify reconstruction and freeze all paths outside the regional clip change."""
from pathlib import Path
import gzip, hashlib, json, shutil, subprocess, sys, tempfile
parent,root=(Path(x).resolve() for x in sys.argv[1:]);here=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def files(r):
 return {p.relative_to(r).as_posix():sha(p.read_bytes())for d in ['app/src','circularbarlib/src']for p in (r/d).rglob('*')if p.is_file()}|{'app/build.gradle':sha((r/'app/build.gradle').read_bytes())}
a,b=files(parent),files(root);m=json.loads((here/'manifest.json').read_text())
fingerprint=lambda f:sha(json.dumps(f,sort_keys=True,separators=(',',':')).encode())
assert fingerprint(a)==m['parentScopedSha256'] and fingerprint(b)==m['candidateScopedSha256']
changed=sorted(n for n in a.keys()|b.keys()if a.get(n)!=b.get(n))
assert changed==sorted(m['fileOverrides']) and len(changed)==4 and len(m['newFiles'])==1
for n,d in m['parentFiles'].items():assert a[n]==d,n
for n,d in m['fileOverrides'].items():assert b[n]==d,n
with tempfile.TemporaryDirectory() as tmp:
 t=Path(tmp)
 for n in changed:(t/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/n,t/n)
 subprocess.run(['git','apply','--reverse','--whitespace=nowarn','-'],cwd=t,input=gzip.decompress((here/'regionalclip1a.patch.gz').read_bytes()),check=True)
 for n in changed:
  if n in m['newFiles']:assert not (t/n).exists(),n
  else:assert (t/n).read_bytes()==(parent/n).read_bytes(),n
pkg='app/src/main/java/com/particlesdevs/photoncamera/m9/preview/'
old=(parent/pkg/'M9AutoExposure2D.java').read_text();new=(root/pkg/'M9AutoExposure2D.java').read_text()
start='    private static BodyCandidate stabilizeBodyCandidate('
restored=new.replace('    static boolean deferBackgroundChannelClip(', '    private static boolean deferBackgroundChannelClip(')
assert old[old.index(start):]==restored[restored.index(start):], 'raw spatial/headroom/tap policy changed'
start='    public static final class Stats {';end='    public static synchronized Decision decide('
assert old[old.index(start):old.index(end)]==new[new.index(start):new.index(end)],'statistics, sampling, raw targets changed'
start='            double current=haveAuto?heldAutoEv:boundedLegacy;';end='            if(useBacklight) {'
assert old[old.index(start):old.index(end,old.index(start))]==new[new.index(start):new.index(end,new.index(start))], 'controller cut/rise/descent policy changed'
assert 'Math.min(highlightRetentionLimit,qualifiedRegionalClipCap)' in new
report={'status':'PASS','parent':'2.66-exposuresettle1a','candidate':'2.67-regionalclip1a',
 'changedFiles':changed,'unchangedScopedFiles':len(b)-4,'totalScopedFiles':len(b),
 'reversePatchExactlyRestoresParent':True,'rawHeadroomBodyTargetsAnchorAndTapRulesByteIdentical':True,
 'existingImmediateCutAndRisePoliciesByteIdentical':True,'gpuSamplingToneMathSensorMeteringAfWbAndSavedRenderersUnchanged':True,
 'nativeAssetsMonochromAndExportQueuesUnchanged':True,
 'change':'Regional channel clipping enters at the same thresholds, with one-sampled-pixel clearance before releasing a field; bounded per-step masks are traced.'}
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
