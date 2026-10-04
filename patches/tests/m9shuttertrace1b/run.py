"""Synthetic-only recorder regressions; no user photographs or identifiers."""
from pathlib import Path
import subprocess,tempfile,sys
from PIL import Image
root=Path(__file__).resolve().parents[3];here=Path(__file__).resolve().parent
photon=Path(sys.argv[1]).resolve();j=photon/'app/src/main/java/com/particlesdevs/photoncamera'
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);classes=d/'classes';classes.mkdir()
 im=Image.new('RGB',(131,97));im.putdata([((x*19+y*13)%256,(x*7+y*31)%256,(x*43+y*3)%256) for y in range(97) for x in range(131)])
 for name,progressive in [('baseline',False),('progressive',True)]:
  p=d/(name+'.jpg');im.save(p,quality=95,subsampling=2,progressive=progressive);b=p.read_bytes()
  for suffix,marker,payload in [('exif',225,b'Exif\0\0'+b'test_metadata'),('comment',254,b'comment'),('icc',226,b'ICC_PROFILE\0\x01\x01'+b'profile_evidence')]:
   segment=bytes([255,marker])+(len(payload)+2).to_bytes(2,'big')+payload
   (d/(name+'-'+suffix+'.jpg')).write_bytes(b[:2]+segment+b[2:])
  quant=bytearray(b);i=quant.index(b'\xff\xdb')+5;quant[i]=2 if quant[i]==1 else quant[i]-1
  (d/(name+'-quant.jpg')).write_bytes(quant);(d/(name+'-truncated.jpg')).write_bytes(b[:-2])
 b=(d/'baseline.jpg').read_bytes()
 # Parser stress stream: stuffed 0xff bytes and restart markers, not a photographic fixture.
 (d/'large-parser-stream.jpg').write_bytes(b[:-2]+(bytes(range(255))+b'\xff\x00\xff\xd0')*24576+b'\xff\xd9')
 old=(root/'patches/shuttertrace1a/M9JpegSignature1A.java').read_text().replace('M9JpegSignature1A','M9JpegSignatureLegacy')
 (d/'M9JpegSignatureLegacy.java').write_text(old)
 (d/'View.java').write_text('package android.view;public class View{public float alpha=1,sx=1,sy=1,tx=0;public int getWidth(){return 800;}public void setAlpha(float x){alpha=x;}public void setScaleX(float x){sx=x;}public void setScaleY(float x){sy=x;}public void setTranslationX(float x){tx=x;}}')
 (d/'ViewPager.java').write_text('package androidx.viewpager.widget;public class ViewPager{public interface PageTransformer{void transformPage(android.view.View view,float position);}}')
 files=[j/'m9/preview'/n for n in ['M9TraceLedger1A.java','M9JpegSignature1A.java','M9TracePolicy1B.java']]+[j/'gallery/adapters/DepthPageTransformer.java',here/'PolicyTest.java',here/'ParityTest.java',here.parent/'m9shuttertrace1a/JpegTest.java',*d.glob('*.java')]
 subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-d',str(classes),*map(str,files)],check=True)
 for test in ['PolicyTest','JpegTest','ParityTest']:subprocess.run(['java','-ea','-cp',str(classes),test,str(d)],check=True)
