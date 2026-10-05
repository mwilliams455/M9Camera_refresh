"""Check photographic code is byte-identical and the change is limited to queue scheduling."""
from pathlib import Path
import hashlib,json,sys
parent,root=(Path(p).resolve() for p in sys.argv[1:]);here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def files(r):return {p.relative_to(r).as_posix():sha(p) for d in ['app/src','circularbarlib/src'] for p in (r/d).rglob('*') if p.is_file()}|{'app/build.gradle':sha(r/'app/build.gradle')}
a,b=files(parent),files(root)
q='app/src/main/java/com/particlesdevs/photoncamera/m9/render/'
changed=sorted(p for p in a.keys()|b.keys() if a.get(p)!=b.get(p))
assert changed==['app/build.gradle',q+'M9JpegFinalizeQueue.java',q+'M9PrimaryRenderQueue.java'],changed
old=(parent/'app/build.gradle').read_text();new=(root/'app/build.gradle').read_text()
assert new.replace('27253','27252').replace('2.53-jpegqueue1a','2.52-dngnamefix1a').replace('2.53_JPEGQUEUE1A','2.52_DNGNAMEFIX1A')==old
old=(parent/(q+'M9PrimaryRenderQueue.java')).read_text();new=(root/(q+'M9PrimaryRenderQueue.java')).read_text()
# DNG worker code and ownership are preserved, apart from an explanatory comment.
marker='    private static void runAsyncDng('
assert new[new.index(marker):].replace('stage for RAW modes; JPEG-only uses its detached EXIF completion instead.','stage for RAW modes; JPEG-only completes it on the render worker.')==old[old.index(marker):]
# Metadata content/write/publication and exception handling are unchanged.
old=(parent/(q+'M9JpegFinalizeQueue.java')).read_text();new=(root/(q+'M9JpegFinalizeQueue.java')).read_text()
start='        final long startedNs = System.nanoTime();';end='        } finally {'
assert old[old.index(start):old.index(end,old.index(start))]==new[new.index(start):new.index(end,new.index(start))]
m=json.loads((here/'manifest.json').read_text())
for n,d in m['parentFiles'].items():assert a[n]==d,n
for n,d in m['fileOverrides'].items():assert b[n]==d,n
report=dict(status='PASS',parent='2.52-dngnamefix1a',version='2.53-jpegqueue1a',changedFiles=changed,unchangedScopedFiles=len(a)-3,photographicRendererAndExposureByteIdentical=True,nativeSourcesAndAssetsByteIdentical=True,monochromSourcesByteIdentical=True,dngWorkerExecutableBodyByteIdentical=True,exifContentAndPublicationBodyByteIdentical=True,rawProfileNameFixRetained=True)
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
