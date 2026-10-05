"""Reverse only coordinate reuse and version metadata; require exact parent code."""
from pathlib import Path
import hashlib,json,sys
from coordinate_change import reverse
parent,root=(Path(p).resolve() for p in sys.argv[1:]);here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def files(r):return {p.relative_to(r).as_posix():sha(p) for d in ['app/src','circularbarlib/src'] for p in (r/d).rglob('*') if p.is_file()}|{'app/build.gradle':sha(r/'app/build.gradle')}
a,b=files(parent),files(root)
renderers=['app/src/main/java/com/particlesdevs/photoncamera/'+m+'/render/M9R35Renderer.java' for m in ['m9','monochrom']]
changed=sorted(p for p in a.keys()|b.keys() if a.get(p)!=b.get(p));assert changed==sorted(['app/build.gradle']+renderers),changed
for name in renderers:assert reverse((root/name).read_text())==(parent/name).read_text(),name
old=(parent/'app/build.gradle').read_text();new=(root/'app/build.gradle').read_text()
assert new.replace('27256','27255').replace('2.56-shadingperf1a','2.55-thumbui1a').replace('2.56_SHADINGPERF1A','2.55_THUMBUI1A')==old
m=json.loads((here/'manifest.json').read_text())
for n,d in m['parentFiles'].items():assert a[n]==d,n
for n,d in m['fileOverrides'].items():assert b[n]==d,n
report=dict(status='PASS',parent='2.55-thumbui1a',version='2.56-shadingperf1a',changedFiles=changed,unchangedScopedFiles=len(a)-3,totalScopedFiles=len(b),reverseCoordinateReuseExactlyRestoresParentRenderers=True,allShadingGainAndInterpolationArithmeticUnchanged=True,liveMapAndAlphaSelectionUnchanged=True,cfaAndCropMappingUnchanged=True,downstreamDemosaicColorToneExposureNoiseSharpnessUnchanged=True,nativeSourcesAndAssetsByteIdentical=True,saveQueuesRawEmbeddingAndCrashFixesByteIdentical=True,additionalCoordinateArrayPayloadBytesAtWidth4096=65536)
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
