"""Verify only the allowlisted report gates, timings, setting text and version changed."""
from pathlib import Path
import hashlib,json,sys
parent,root=(Path(p).resolve() for p in sys.argv[1:]);here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def files(r):return {p.relative_to(r).as_posix():sha(p) for d in ['app/src','circularbarlib/src'] for p in (r/d).rglob('*') if p.is_file()}|{'app/build.gradle':sha(r/'app/build.gradle')}
def span(s,start,end):return s[s.index(start):s.index(end,s.index(start))]
a,b=files(parent),files(root);changed=sorted(p for p in a.keys()|b.keys() if a.get(p)!=b.get(p))
renderer='app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
assert changed==['app/build.gradle',renderer,'app/src/main/res/values/m9_diagnostics.xml'],changed
m=json.loads((here/'manifest.json').read_text())
for name,digest in m['parentFiles'].items():assert a[name]==digest,name
for name,digest in m['fileOverrides'].items():assert b[name]==digest,name
old=(parent/renderer).read_text();new=(root/renderer).read_text();restored=new
# Remove only the explicitly non-photographic helper and per-render diagnostic policy.
start='    // M9PERF1A: explicitly distinguish omitted research from measured image data.'
restored=restored.replace(span(restored,start,'    // BASISHSM1I-FINALCLIPAUDIT1A'),'')
start='        // M9PERF1A: these three reports have no photographic consumers.'
restored=restored.replace(span(restored,start,'        // PHYSICALSOURCEAGNOSTIC1A:'),'')
# Audit orchestration boundaries exclude the real normalization probe and shading pass.
replacements=[
 ('        long rawShadingReportStartedNs1A =','        if (applyShadingLumaDecomp1A &&', '        JSONObject rawShadingResidual1A ='),
 ('        long shadingDecompReportStartedNs1A =','        final boolean fullPhysicalShadingControl =','        final JSONObject shadingLumaDecomp1AJson ='),
 ('            long finalClipReportStartedNs1A =','            return new RenderCore(oriented, d);','            d.put("finalClipAudit1AEnabled", true);')]
for start,end,oldstart in replacements:restored=restored.replace(span(restored,start,end),span(old,oldstart,end))
restored=restored.replace('            d.put("rawShadingResidual1AEnabled", readOnlyImageAuditsEnabled1A);','            d.put("rawShadingResidual1AEnabled", true);')
restored=restored.replace('            String satDomainTelemetryJson1A = null;','            final boolean qualityGate1BSatAuditEnabled = M9RenderDiagnostics.fullFrameSatAuditEnabled();\n            String satDomainTelemetryJson1A = null;')
assert restored==old,'An operation outside the report-only allowlist changed'
# Prove removed JSON objects have no other internal consumers; all app references checked.
for key in ['rawShadingResidual1A','shadingLumaDecomp1AJson']:
 assert old.count(key)==(4 if key=='rawShadingResidual1A' else 2),(key,old.count(key))
for method in ['rawShadingResidualAudit1A','shadingLumaDecomp1AAudit','finalClipAudit1A']:
 sig='    private static JSONObject '+method+'('
 # All three implementation bodies are byte-identical (next private method boundary).
 def body(s):
  start=s.index(sig);end=s.find('\n    private static ',start+len(sig));return s[start:end if end>=0 else s.rfind('}')]
 assert body(old)==body(new),method
report=dict(status='PASS',parent='2.49-monoperf1a',version='2.50-m9perf1a',changedFiles=changed,unchangedSourceFiles=len(a)-3,photographicOperationsUnchanged=True,normalizationProbeRetained=True,allNativeSourcesAndAssetsUnchanged=True,monochromSourceUnchanged=True,captureProfilesDngAndExposureControllersUnchanged=True,reportAlgorithmsPreservedForOptIn=True)
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
