"""Add bounded read-only shutter/JPEG/display evidence to exact DETAIL1H TG1ROLLBACK1A."""
from pathlib import Path
import hashlib,json,sys
root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent
sys.path.insert(0,str(here))
from m9rbrollback1a import inventory
base='app/src/main/java/com/particlesdevs/photoncamera/'
manifest=json.loads((here/'m9shuttertrace1a-parent.json').read_text())
proof=root/'M9SHUTTERTRACE1A_SOURCE_PROOF.json'
if proof.exists():
 p=json.loads(proof.read_text());assert inventory(root)==p['after'];print('SHUTTERTRACE1A already applied and verified');sys.exit(0)
for rel,digest in manifest.items():
 assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==digest,('TG1 parent mismatch',rel)
before=inventory(root)
changes={
base+'capture/CaptureController.java':[
('            cameraEventsListener.onPreviewCaptureCompleted(result);','''            if (M9Config.isCaptureTest()) {
                com.particlesdevs.photoncamera.m9.preview.M9RootCauseTrace1A.observe(
                    request, result, PhotonCamera.getSettings().mCameraID, paramController.getM9UserEv1A());
            }
            cameraEventsListener.onPreviewCaptureCompleted(result);'''),
('            final AtomicBoolean m9LivePairWritten1P = new AtomicBoolean(false);','''            com.particlesdevs.photoncamera.m9.preview.M9ShutterTrace1A.begin(m9LivePairPreviewSnapshot1P, mTextureView);
            final AtomicBoolean m9LivePairWritten1P = new AtomicBoolean(false);'''),
('''                    if (m9LivePairWritten1P.compareAndSet(false, true)) {
                        processExecutor.execute''','''                    if (m9LivePairWritten1P.compareAndSet(false, true)) {
                        com.particlesdevs.photoncamera.m9.preview.M9ShutterTrace1A.completed(
                            m9LivePairPreviewSnapshot1P, result, m9LivePairPhysicalId1P);
                        processExecutor.execute''')],
base+'ui/camera/views/viewfinder/MainRenderer.java':[
('    private int uM9EvidenceStage2E;','''    private int uM9EvidenceStage2E;
    private com.particlesdevs.photoncamera.m9.preview.M9RootCausePixels1A mM9ShutterPixels;'''),
('        mM9Evidence2E = new com.particlesdevs.photoncamera.m9.preview.M9PreviewEvidence2E();','''        mM9Evidence2E = new com.particlesdevs.photoncamera.m9.preview.M9PreviewEvidence2E();
        mM9ShutterPixels = new com.particlesdevs.photoncamera.m9.preview.M9RootCausePixels1A();
        com.particlesdevs.photoncamera.m9.preview.M9ShutterTrace1A.registerPixels(mM9ShutterPixels);'''),
('''            mM9Evidence2E.sample(frame1W, textureTimestamp1W, mSTexture,
                    uM9ExposureScale1B, enablePeak, peakEnabled, uM9EvidenceStage2E);''','''            mM9Evidence2E.sample(frame1W, textureTimestamp1W, mSTexture,
                    uM9ExposureScale1B, enablePeak, peakEnabled, uM9EvidenceStage2E);
        com.particlesdevs.photoncamera.m9.preview.M9ShutterTrace1A.draw(mM9LastDraw1W);
        if (mM9ShutterPixels != null) {
            mM9ShutterPixels.geometry(mTexRotateMatrix, mMirrorPreview, mM9CurveTex != 0);
            mM9ShutterPixels.sample(frame1W, textureTimestamp1W, mSTexture,
                uM9ExposureScale1B, enablePeak, peakEnabled, uM9EvidenceStage2E);
        }''')],
base+'m9/render/M9R35Renderer.java':[
('            long jpegStartedNs = System.nanoTime();','''            com.particlesdevs.photoncamera.m9.preview.M9ShutterTrace1A.beforeEncode(jpgPath, bitmap, captureResult);
            long jpegStartedNs = System.nanoTime();'''),
('            if (!jpgSaved) throw new IllegalStateException("M9 JPEG payload save failed");','''            if (!jpgSaved) throw new IllegalStateException("M9 JPEG payload save failed");
            com.particlesdevs.photoncamera.m9.preview.M9ShutterTrace1A.payloadWritten(jpgPath);''')],
base+'m9/render/M9JpegFinalizeQueue.java':[
('            ticket.done.countDown();','''            com.particlesdevs.photoncamera.m9.preview.M9ShutterTrace1A.finalized(jpegPath, ticket.success);
            ticket.done.countDown();''')],
base+'gallery/adapters/ImageAdapter.java':[
('        container.addView(scaleImageView);','''        container.addView(scaleImageView);
        com.particlesdevs.photoncamera.m9.preview.M9ShutterSurface1A.gallery(scaleImageView, galleryItem.getFile().getDisplayName());''')],
base+'ui/camera/viewmodel/CameraFragmentViewModel.java':[
('''        if (lastImageUri != null) {
            Glide.with''','''        if (lastImageUri != null) {
            final Uri m9TraceThumbUri = lastImageUri;
            Glide.with'''),
('                            cameraFragmentModel.setBitmap(resource);','''                            cameraFragmentModel.setBitmap(resource);
                            com.particlesdevs.photoncamera.m9.preview.M9ShutterTrace1A.thumbnail(getApplication(), m9TraceThumbUri, resource);''')],
'app/build.gradle':[("versionName '1.61-m9detail1h-tg1rollback1a'","versionName '1.63-m9shuttertrace1a-tg1'"),("        versionCode versionBuild","        versionCode 26683")]
}
# Check every anchor before writing any source file.
updated={}
for rel,replacements in changes.items():
 s=(root/rel).read_text()
 for old,new in replacements:
  assert s.count(old)==1,(rel,'anchor_count',s.count(old),old[:90]);s=s.replace(old,new,1)
 updated[rel]=s
added=[]
for p in sorted((here/'shuttertrace1a').glob('*.java')):
 dst=root/base/'m9/preview'/p.name;assert not dst.exists(),dst
 added.append(str(dst.relative_to(root)))
for rel,s in updated.items():(root/rel).write_text(s)
for p in sorted((here/'shuttertrace1a').glob('*.java')):(root/base/'m9/preview'/p.name).write_bytes(p.read_bytes())
after=inventory(root)
assert sorted(k for k in before if before[k]!=after[k])==sorted(changes)
assert sorted(set(after)-set(before))==sorted(added)
for rel,replacements in changes.items():
 s=(root/rel).read_text()
 for old,new in reversed(replacements):assert s.count(new)==1;s=s.replace(new,old,1)
 assert hashlib.sha256(s.encode()).hexdigest()==before[rel]
receipt=dict(revision='M9SHUTTERTRACE1A',parent='DETAIL1H_TG1ROLLBACK1A',before=before,after=after,
 changed=sorted(changes),added=added,reverse_transform_exact=True,photographic_math_assets_and_requests_unchanged=True)
proof.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k not in ('before','after')},indent=2))
