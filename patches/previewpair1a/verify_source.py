"""Require the exact frame-pairing integration and unchanged exposure/rendering code."""
from pathlib import Path
import hashlib,json,sys
parent,root=(Path(x).resolve() for x in sys.argv[1:]);here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def files(r):
    return {p.relative_to(r).as_posix():sha(p) for d in ['app/src','circularbarlib/src']
            for p in (r/d).rglob('*') if p.is_file()}|{'app/build.gradle':sha(r/'app/build.gradle')}
a,b=files(parent),files(root)
main='app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java'
new='app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewFrameHistory1A.java'
changed=sorted(n for n in a.keys()|b.keys() if a.get(n)!=b.get(n))
assert changed==sorted(['app/build.gradle',main,new]),changed
s=(root/main).read_text()
s=s.replace('private final com.particlesdevs.photoncamera.m9.preview.M9PreviewFrameHistory1A mM9FrameHistory1A =\n            new com.particlesdevs.photoncamera.m9.preview.M9PreviewFrameHistory1A();',
            'private volatile M9PreviewFrameState1W mM9FrameState1W = M9PreviewFrameState1W.defaults();')
s=s.replace('mM9FrameHistory1A.publish(state, android.os.SystemClock.elapsedRealtimeNanos());','mM9FrameState1W = state;')
s=s.replace('''// Pair exposure/source metadata with the displayed texture when a recent exact
        // match is available. Use this one immutable state for the draw and both probes.
        final long textureTimestamp1W = mSTexture.getTimestamp();
        final M9PreviewFrameState1W frame1W = mM9FrameHistory1A.forTexture(
                textureTimestamp1W, android.os.SystemClock.elapsedRealtimeNanos());''',
        '''// Read one immutable M9 state for the complete sharp draw.
        final M9PreviewFrameState1W frame1W = mM9FrameState1W;
        final long textureTimestamp1W = mSTexture.getTimestamp();''')
s=s.replace('mM9FrameHistory1A.clear();','mM9FrameState1W = M9PreviewFrameState1W.defaults();')
assert s==(parent/main).read_text(),'Unexpected renderer integration change'
v=(root/'app/build.gradle').read_text().replace('27258','27257').replace('2.58-previewpair1a','2.57-previewprobe1a').replace('2.58_PREVIEWPAIR1A','2.57_PREVIEWPROBE1A')
assert v==(parent/'app/build.gradle').read_text()
m=json.loads((here/'manifest.json').read_text())
for n,d in m['parentFiles'].items():assert a[n]==d,n
for n,d in m['fileOverrides'].items():assert b[n]==d,n
report=dict(status='PASS',parent='2.57-previewprobe1a',version='2.58-previewpair1a',
            changedFiles=changed,unchangedScopedFiles=len(a)-2,totalScopedFiles=len(b),
            reverseIntegrationExactlyRestoresParent=True,
            autoExposureAndIsoAllocationAndAeLockByteIdentical=True,
            probeSchedulingAndFreshnessGuardsByteIdentical=True,
            stillRenderersShadersNativeSourcesAssetsAndMonochromByteIdentical=True,
            queuesAndRecentCrashFixesByteIdentical=True)
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
