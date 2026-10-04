"""Read-only temporal evidence on the exact RBROLLBACK1A source."""
from pathlib import Path
import hashlib,json,sys
sys.path.insert(0,str(Path(__file__).parent))
from m9rbrollback1a import verify as verify_parent,inventory

root=Path(sys.argv[1]).resolve();here=Path(__file__).parent
proof=root/'M9ROOTCAUSE1A_SOURCE_PROOF.json'
if proof.exists():
    receipt=json.loads(proof.read_text());assert inventory(root)==receipt['after'];print('ROOTCAUSE1A already applied and verified');sys.exit(0)
verify_parent(root)
before=inventory(root)
base='app/src/main/java/com/particlesdevs/photoncamera/'
changes={
base+'capture/CaptureController.java':[
('            cameraEventsListener.onPreviewCaptureCompleted(result);', '''            // M9ROOTCAUSE1A: read-only frame metadata, before callback updates the display plan.
            if (M9Config.isCaptureTest()) {
                com.particlesdevs.photoncamera.m9.preview.M9RootCauseTrace1A.observe(
                        request, result, PhotonCamera.getSettings().mCameraID, paramController.getM9UserEv1A());
            }
            cameraEventsListener.onPreviewCaptureCompleted(result);''')],
base+'ui/camera/views/viewfinder/MainRenderer.java':[
('            if (evidence != null) out.put("pairedPixels2E", evidence.snapshot(shutterNs, plan));', '''            if (evidence != null) out.put("pairedPixels2E", evidence.snapshot(shutterNs, plan));
            if (plan != null) out.put("rootCauseMetadata1A",
                    com.particlesdevs.photoncamera.m9.preview.M9RootCauseTrace1A.snapshot(shutterNs, plan.cameraId));
            com.particlesdevs.photoncamera.m9.preview.M9RootCausePixels1A pixels = mM9RootCausePixels1A;
            if (pixels != null) out.put("rootCausePixels1A", pixels.snapshot(shutterNs, plan));'''),
('    private int uM9EvidenceStage2E;', '''    private int uM9EvidenceStage2E;
    private volatile com.particlesdevs.photoncamera.m9.preview.M9RootCausePixels1A mM9RootCausePixels1A;'''),
('        mM9Evidence2E = new com.particlesdevs.photoncamera.m9.preview.M9PreviewEvidence2E();', '''        mM9Evidence2E = new com.particlesdevs.photoncamera.m9.preview.M9PreviewEvidence2E();
        mM9RootCausePixels1A = new com.particlesdevs.photoncamera.m9.preview.M9RootCausePixels1A();'''),
('''            mM9Evidence2E.sample(frame1W, textureTimestamp1W, mSTexture,
                    uM9ExposureScale1B, enablePeak, peakEnabled, uM9EvidenceStage2E);''','''            mM9Evidence2E.sample(frame1W, textureTimestamp1W, mSTexture,
                    uM9ExposureScale1B, enablePeak, peakEnabled, uM9EvidenceStage2E);
        if (mM9RootCausePixels1A != null)
            mM9RootCausePixels1A.sample(frame1W, textureTimestamp1W, mSTexture,
                    uM9ExposureScale1B, enablePeak, peakEnabled, uM9EvidenceStage2E);''')],
'app/build.gradle':[('1.61-m9rbrollback1a-tg2still1a','1.62-m9rootcause1a-tg2still1a')]
}
for rel,replacements in changes.items():
    p=root/rel;s=p.read_text()
    for old,new in replacements:
        assert s.count(old)==1,(rel,'anchor',old[:80]);s=s.replace(old,new)
    p.write_text(s)
added=[]
for p in (here/'rootcause1a').glob('*.java'):
    dst=root/base/'m9/preview'/p.name;assert not dst.exists();dst.write_bytes(p.read_bytes());added.append(str(dst.relative_to(root)))
after=inventory(root);changed=sorted(k for k in before if before[k]!=after[k])
assert changed==sorted(changes)
assert sorted(set(after)-set(before))==sorted(added)
assert len(added)==2
receipt={'revision':'M9ROOTCAUSE1A','parent':'ca236b028b6bee915e0092597b1a23c79134a6b2','before':before,'after':after,
         'changed':changed,'added':added,'photographic_code_unchanged':True,'scope':'Read-only metadata and asynchronous centre viewport crops. No exposure/AF/AWB/renderer policy mutation.'}
proof.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k not in ('before','after')},indent=2))
