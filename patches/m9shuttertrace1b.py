"""Exact diagnostic-only successor to SHUTTERTRACE1A; photographic pipeline unchanged."""
from pathlib import Path
import hashlib,json
from m9rbrollback1a import inventory
BASE='app/src/main/java/com/particlesdevs/photoncamera/'
HERE=Path(__file__).resolve().parent
CHANGES={
 BASE+'gallery/adapters/ImageAdapter.java':[
 ('M9ShutterSurface1A.gallery(scaleImageView, galleryItem.getFile().getDisplayName());',
  'M9ShutterSurface1A.gallery(scaleImageView, galleryItem.getFile().getDisplayName(),\n            () -> container instanceof androidx.viewpager.widget.ViewPager\n                && ((androidx.viewpager.widget.ViewPager) container).getCurrentItem() == position);')],
 'app/build.gradle':[("versionName '1.63-m9shuttertrace1a-tg1'","versionName '1.64-m9shuttertrace1b-tg1'"),('versionCode 26683','versionCode 26684')]
}
def sha(data):return hashlib.sha256(data).hexdigest()
def verify(root):
 proof=json.loads((root/'M9SHUTTERTRACE1B_SOURCE_PROOF.json').read_text())
 parent=json.loads((root/'M9SHUTTERTRACE1A_SOURCE_PROOF.json').read_text())
 assert proof['before']==parent['after']
 now=inventory(root);assert now==proof['after']
 helpers={BASE+'m9/preview/'+p.name:p for p in (HERE/'shuttertrace1b').glob('*.java')}
 assert len(helpers)==5
 assert sorted(k for k in proof['before'] if proof['before'][k]!=now[k])==sorted(set(CHANGES)|{k for k in helpers if k in proof['before']})
 assert set(now)-set(proof['before'])=={BASE+'m9/preview/M9TracePolicy1B.java'}
 for rel,p in helpers.items():
  assert (root/rel).read_bytes()==p.read_bytes()
  if rel in proof['before']:assert proof['before'][rel]==sha((HERE/'shuttertrace1a'/p.name).read_bytes())
 for rel,replacements in CHANGES.items():
  s=(root/rel).read_text()
  for old,new in reversed(replacements):assert s.count(new)==1;s=s.replace(new,old,1)
  assert sha(s.encode())==proof['before'][rel]
 assert all(now[k]==v for k,v in parent['before'].items() if k.startswith(('app/src/main/assets/','app/src/main/cpp/')))
 assert now[BASE+'api/ParseExif.java']==parent['before'][BASE+'api/ParseExif.java']
 for rel in ['m9/render/M9R35Renderer.java','m9/render/M9JpegFinalizeQueue.java','capture/CaptureController.java','ui/camera/views/viewfinder/MainRenderer.java']:
  assert now[BASE+rel]==proof['before'][BASE+rel]
 return dict(revision='M9SHUTTERTRACE1B',source_files=len(now),source_inventory_exact=True,
   parent='M9SHUTTERTRACE1A',photographic_assets_native_renderer_and_requests_unchanged=True,
   exif_writer_unchanged=True,android_device_validation_pending=True)
