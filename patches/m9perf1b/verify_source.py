"""Verify the entire source delta is limited to report early exits and lazy fallback storage."""
from pathlib import Path
import hashlib,json,sys
parent,root=(Path(p).resolve() for p in sys.argv[1:]);here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def files(r):return {p.relative_to(r).as_posix():sha(p) for d in ['app/src','circularbarlib/src'] for p in (r/d).rglob('*') if p.is_file()}|{'app/build.gradle':sha(r/'app/build.gradle')}
a,b=files(parent),files(root)
base='app/src/main/java/com/particlesdevs/photoncamera/m9/render/'
audits=['M9DevicePortAudit1A.java','M9RawShadingAudit1A.java','M9SourceCalibrationAudit1A.java']
renderer=base+'M9R35Renderer.java'
test='app/src/test/java/com/particlesdevs/photoncamera/m9/render/M9SetupAuditGateTest.java'
allowed=['app/build.gradle',renderer,test]+[base+n for n in audits]
changed=sorted(p for p in a.keys()|b.keys() if a.get(p)!=b.get(p))
assert changed==sorted(allowed),changed
m=json.loads((here/'manifest.json').read_text())
for n,d in m['parentFiles'].items():assert a[n]==d,n
for n,d in m['fileOverrides'].items():assert b[n]==d,n
gate='''            // M9PERF1B: omit report computation as well as persistence when disabled.
            if (!M9OutputSettings.diagnosticsEnabled()) {
                out.put("executed", false);
                out.put("valid", false);
                out.put("reason", "diagnostic_files_disabled");
                return out;
            }
'''
for name in audits:
 old=(parent/base/name).read_text();new=(root/base/name).read_text()
 assert new.count(gate)==1,name
 restored=new.replace(gate,'').replace('import com.particlesdevs.photoncamera.m9.M9OutputSettings;\n','')
 assert restored==old,name
old=(parent/renderer).read_text();new=(root/renderer).read_text()
restored=new.replace('            // M9PERF1B: the direct Bitmap path needs no Java output buffer.\n            int[] argbBlock = null;',
                     '            final int[] argbBlock = new int[maxBlockPixels];')
assert new.count('if (argbBlock == null) argbBlock = new int[maxBlockPixels];')==3
restored='\n'.join(line for line in restored.split('\n') if 'if (argbBlock == null) argbBlock = new int[maxBlockPixels];' not in line
                  and 'd.put("nativeColorArgbFallbackAllocatedBytes"' not in line)
assert restored==old,'Photographic processing or another renderer operation changed'
old=(parent/'app/build.gradle').read_text();new=(root/'app/build.gradle').read_text()
assert new.replace('27251','27250').replace('2.51-m9perf1b','2.50-m9perf1a').replace('2.51_M9PERF1B','2.50_M9PERF1A')==old
report=dict(status='PASS',parent='2.50-m9perf1a',version='2.51-m9perf1b',changedFiles=changed,
 unchangedScopedFiles=sum(a.get(n)==b.get(n) for n in a),allPhotographicOperationsUnchanged=True,
 enabledAuditBodiesUnchanged=True,allNativeSourcesAndAssetsUnchanged=True,monochromSourceUnchanged=True,
 exposureMeteringShadingAndDngProfileSourceUnchanged=True,fallbackPixelCallsAndCommitOrderUnchanged=True)
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
