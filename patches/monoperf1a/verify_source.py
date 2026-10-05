"""Verify only four dead audit gates, diagnostic timings and version identity changed."""
from pathlib import Path
import hashlib,json,sys
parent,root=(Path(p).resolve() for p in sys.argv[1:]);here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def files(r):
 return {p.relative_to(r).as_posix():sha(p) for d in ['app/src','circularbarlib/src'] for p in (r/d).rglob('*') if p.is_file()}|{'app/build.gradle':sha(r/'app/build.gradle')}
a,b=files(parent),files(root)
changed=sorted(p for p in a.keys()|b.keys() if a.get(p)!=b.get(p))
renderer='app/src/main/java/com/particlesdevs/photoncamera/monochrom/render/M9R35Renderer.java'
assert changed==['app/build.gradle',renderer],changed
m=json.loads((here/'manifest.json').read_text())
for name,digest in m['parentFiles'].items():assert a[name]==digest,name
for name,digest in m['fileOverrides'].items():assert b[name]==digest,name
before=(parent/renderer).read_text();after=(root/renderer).read_text()
# Reverse only the complete allowlisted non-photographic edit, then compare the whole file.
restored=after.replace('MONO1A_ENABLED ? null : ','')
lines=restored.splitlines(keepends=True)
remove=['// MONOPERF1A:','// MONO1A early return.','// clones. The physical shading pass',
 'final long physicalShadingStartedNs =','final double physicalShadingElapsedMs =',
 'd.put("renderPerformanceRevision",','d.put("discardedLegacyShadingAuditsExecuted",',
 'd.put("physicalShadingElapsedMs",','d.put("nativeWeightedRenderElapsedMs",']
lines=[s for s in lines if not any(s.strip().startswith(t) for t in remove)]
restored=''.join(lines)
# These two existing timers are now also emitted by the Monochrom branch.
for key in ['normalizeRawElapsedMs','demosaicElapsedMs']:
 restored=restored.replace('                d.put("'+key+'", '+key+');\n','',1)
assert restored==before,'Unexpected renderer operation changed'
assert after.count('MONO1A_ENABLED ? null : ')==4
# None of the report results is used before the Monochrom early return.
early=after.index('                return result1A;')
for name in ['rawShadingResidual1A','shadingLumaDecomp1AJson','shadedTailAuditStats','shadedTailSpatial1AJson']:
 assert after[:early].count(name)==1,(name,'used by Monochrom')
assert 'private static final boolean MONO1A_ENABLED = true;' in after
report=dict(status='PASS',parent='2.48-monoprofiles1a',version='2.49-monoperf1a',changedFiles=changed,unchangedSourceFiles=len(a)-2,m9SourceUnchanged=True,nativeSourcesAndAssetsUnchanged=True,monochromPhotographicOperationsUnchanged=True,removedAuditsHaveNoConsumerBeforeMonochromReturn=True,profilesCaptureAndDngUnchanged=True)
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
