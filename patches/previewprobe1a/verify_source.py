"""Check that only the probe-completion yield and app version differ from 2.56."""
from pathlib import Path
import hashlib, json, sys

parent, root = (Path(p).resolve() for p in sys.argv[1:])
here = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def files(r):
    return {p.relative_to(r).as_posix(): sha(p)
            for d in ['app/src', 'circularbarlib/src']
            for p in (r/d).rglob('*') if p.is_file()} | {'app/build.gradle': sha(r/'app/build.gradle')}
a, b = files(parent), files(root)
probe = 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewMeter2D.java'
changed = sorted(p for p in a.keys() | b.keys() if a.get(p) != b.get(p))
assert changed == sorted(['app/build.gradle', probe]), changed
old, new = (parent/probe).read_text(), (root/probe).read_text()
new = new.replace('        final boolean completingProbe = fence != 0;\n', '', 1)
comment = '''        // Yield the completion frame to the paired/tone probe. At <=4 fps the
        // interval can already have elapsed when poll completes, so immediately
        // resubmitting here would starve preview brightness evidence indefinitely.
        // MainRenderer still allows only one readback in flight; a timed-out
        // fence remains busy and cannot be overlapped by the other probe.
'''
new = new.replace(comment, '', 1).replace('disabled || completingProbe || fence!=0', 'disabled || fence!=0', 1)
assert new == old, 'Unexpected probe change'
old, new = (parent/'app/build.gradle').read_text(), (root/'app/build.gradle').read_text()
assert new.replace('27257', '27256').replace('2.57-previewprobe1a', '2.56-shadingperf1a').replace('2.57_PREVIEWPROBE1A', '2.56_SHADINGPERF1A') == old
m = json.loads((here/'manifest.json').read_text())
for n, d in m['parentFiles'].items(): assert a[n] == d, n
for n, d in m['fileOverrides'].items(): assert b[n] == d, n
report = dict(status='PASS', parent='2.56-shadingperf1a', version='2.57-previewprobe1a',
              changedFiles=changed, unchangedScopedFiles=len(a)-2, totalScopedFiles=len(b),
              reverseProbeYieldExactlyRestoresParent=True,
              exposurePolicyAndToneMathByteIdentical=True,
              savedRenderersShadersNativeSourcesAndAssetsByteIdentical=True,
              monochromQueuesRawEmbeddingAndCrashFixesByteIdentical=True)
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
