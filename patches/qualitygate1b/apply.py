#!/usr/bin/env python3
"""QUALITYGATE1B: enable the already-existing SAT-domain audit on ordinary 2.05 captures.
Diagnostic only. No native code, matrix, curve, exposure, demosaic, noise or pixel math changes.
"""
from pathlib import Path
import hashlib, json, sys

RENDER='app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
GRADLE='app/build.gradle'
BASE_RENDER='591c04688b18cb0797ed92b24dd7316409aac8425ee623abdb4beefd4ae9547b'
NEW_RENDER='a6c269e89ad802ed6aeb65c4c14c4adface9a65ffe3a639d55020bac9223a24e'
BASE_GRADLE='0b1014a6fc776794a495077214c72cda95f89a8b6c8589da23bf8e8d36e19cb4'
NEW_GRADLE='99db2a530540682f40c7868c515f3116b964d22407c03f55705c171a7f4824e2'
VERSION='2.06-m9qualitygate1b-satdiag-exactpatch1b'
CODE=26726
ID='M9QUALITYGATE1B_SATDOMAIN_READONLY'

def sha(b): return hashlib.sha256(b).hexdigest()
def need(ok,msg):
    if not ok: raise SystemExit(msg)
def once(s,old,new,label):
    need(s.count(old)==1,f'{label}: expected one anchor, got {s.count(old)}')
    return s.replace(old,new,1)

def transform_renderer(raw):
    need(sha(raw)==BASE_RENDER,'QUALITYGATE1B requires exact assembled 2.05 renderer')
    s=raw.decode()
    s=once(s,
'''            String satDomainTelemetryJson1A = null;
            long satDomainAuditElapsedMs1A = -1L;''',
'''            // QUALITYGATE1B: force the existing full-frame SAT-domain audit on ordinary
            // production captures. Read-only: no context, gain, matrix, curve or pixel mutation.
            final boolean qualityGate1BSatAuditEnabled = true;
            String satDomainTelemetryJson1A = null;
            long satDomainAuditElapsedMs1A = -1L;''','audit flag')
    s=once(s,
'''            if (skySatDiagnosticEncoded1A && skyChromaMode1A == 0 && satDomainAuditInputEligible1A) {''',
'''            if ((skySatDiagnosticEncoded1A || qualityGate1BSatAuditEnabled)
                    && skyChromaMode1A == 0 && satDomainAuditInputEligible1A) {''','audit condition')
    s=once(s,
'''            d.put("satDomain1A", skySatDiagnosticEncoded1A);
            d.put("satDomainAuditReadOnly", true);''',
'''            d.put("satDomain1A", skySatDiagnosticEncoded1A || qualityGate1BSatAuditEnabled);
            d.put("qualityGate1B", "M9QUALITYGATE1B_SATDOMAIN_READONLY");
            d.put("qualityGate1BPhotographicPixelChange", false);
            d.put("qualityGate1BSatAuditForced", qualityGate1BSatAuditEnabled);
            d.put("satDomainAuditReadOnly", true);''','diagnostics')
    out=s.encode()
    need(sha(out)==NEW_RENDER,'QUALITYGATE1B renderer candidate checksum mismatch')
    return out

def main(root):
    root=Path(root).resolve()
    r=root/RENDER; g=root/GRADLE
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        proof=json.loads(receipt.read_text())
        need(sha(r.read_bytes())==NEW_RENDER,'renderer drift after QUALITYGATE1B')
        need(sha(g.read_bytes())==NEW_GRADLE,'Gradle drift after QUALITYGATE1B')
        print(json.dumps(proof,indent=2)); return
    need(r.exists() and g.exists(),'assembled source missing')
    need(sha(g.read_bytes())==BASE_GRADLE,'QUALITYGATE1B requires exact assembled 2.05 Gradle')
    r.write_bytes(transform_renderer(r.read_bytes()))
    gs=g.read_text()
    gs=once(gs,'versionCode 26725',f'versionCode {CODE}','version code')
    gs=once(gs,"versionName '2.05-m9exactpatch1b-ae1n-perf3i'",f"versionName '{VERSION}'",'version name')
    g.write_text(gs)
    need(sha(g.read_bytes())==NEW_GRADLE,'Gradle candidate checksum mismatch')
    proof={
      'revision':ID,'version':VERSION,'versionCode':CODE,
      'parent':'2.05_EXACTPATCHCLIP1B',
      'changedProductionFiles':[RENDER,GRADLE],
      'satDomainAuditForcedOnOrdinaryProductionCaptures':True,
      'auditInput':'same_full_resolution_cam16_and_final_effective_render_gain',
      'auditFamilies':['SAT2_STANDARD_M04_M05','SAT3_M06_M07','SAT4_HIGH_M08_M09'],
      'photographicPixelChange':False,'nativeCodeChanged':False,'exposureChanged':False,
      'tc20Changed':False,'sat2Changed':False,'curve02Changed':False,'bt601Changed':False,
      'tg1Changed':False,'demosaicChanged':False,'noiseChanged':False,'jpegQualityChanged':False,
      'rendererSha256':NEW_RENDER,'gradleSha256':NEW_GRADLE
    }
    receipt.write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(proof,indent=2))

if __name__=='__main__': main(sys.argv[1])
