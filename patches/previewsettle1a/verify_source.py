"""Require only version metadata and the bounded lower-target transition edit."""
from pathlib import Path
import hashlib,json,sys
parent,root=(Path(x).resolve() for x in sys.argv[1:]);here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def files(r):
 return {p.relative_to(r).as_posix():sha(p) for d in ['app/src','circularbarlib/src']
         for p in (r/d).rglob('*') if p.is_file()}|{'app/build.gradle':sha(r/'app/build.gradle')}
a,b=files(parent),files(root)
auto='app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java'
changed=sorted(n for n in a.keys()|b.keys() if a.get(n)!=b.get(n))
assert changed==sorted(['app/build.gradle',auto]),changed
s=(root/auto).read_text()
s=s.replace('\n    public static final String SETTLING_REVISION="M9PREVIEWSETTLE1A";','')
s=s.replace('result=heldAutoEv;target=result;reason="manual_EV_holds_auto_baseline";\n            resetLowerTargetHysteresis();','result=heldAutoEv;target=result;reason="manual_EV_holds_auto_baseline";')
s=s.replace('''// Confirm an ordinary lower target with two fresh samples. Once
                    // confirmed, continue at 0.25 EV per fresh sample until that
                    // target changes. Do not re-pay the confirmation delay at
                    // every step of the same transition.''','''// Ordinary target/classification noise needs two fresh samples
                    // before stepping down, preventing 0.25-EV preview ping-pong.''')
s=s.replace('lowerTargetConfirmations=Math.min(2,lowerTargetConfirmations+1);','lowerTargetConfirmations++;')
s=s.replace('else {pendingLowerTargetEv=target;}','else {pendingLowerTargetEv=target;lowerTargetConfirmations=0;}')
s=s.replace('\n            // A confirmed target cannot survive a gap in valid meter evidence.\n            resetLowerTargetHysteresis();','')
s=s.replace('.put("settlingRevision",SETTLING_REVISION)','')
assert s==(parent/auto).read_text(),'Unexpected policy change'
v=(root/'app/build.gradle').read_text().replace('27259','27258').replace('2.59-previewsettle1a','2.58-previewpair1a').replace('2.59_PREVIEWSETTLE1A','2.58_PREVIEWPAIR1A')
assert v==(parent/'app/build.gradle').read_text()
m=json.loads((here/'manifest.json').read_text())
for n,d in m['parentFiles'].items():assert a[n]==d,n
for n,d in m['fileOverrides'].items():assert b[n]==d,n
report=dict(status='PASS',parent='2.58-previewpair1a',version='2.59-previewsettle1a',
 changedFiles=changed,unchangedScopedFiles=len(a)-2,totalScopedFiles=len(b),
 reverseTransitionEditExactlyRestoresParent=True,
 exposureTargetsAndHighlightSafetyAndPositiveAcquisitionUnchanged=True,
 isoAllocationAndAeLockAndTapPolicyByteIdentical=True,
 framePairingAndProbeSchedulingAndFreshnessGuardsByteIdentical=True,
 whiteBalanceAndColourAndSavedRenderersAndNativeSourcesAssetsAndMonochromByteIdentical=True,
 queuesAndRecentCrashFixesByteIdentical=True)
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
