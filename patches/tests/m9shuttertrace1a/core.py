from pathlib import Path
import subprocess,tempfile,sys
from PIL import Image
root=Path(__file__).resolve().parents[3];here=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);classes=d/'classes';classes.mkdir()
 # Deterministic fine colour and grey, including odd image dimensions and progressive scans.
 im=Image.new('RGB',(131,97));im.putdata([((x*19+y*13)%256,(x*7+y*31)%256,(x*43+y*3)%256) for y in range(97) for x in range(131)])
 for name,progressive in [('baseline',False),('progressive',True)]:
  p=d/(name+'.jpg');im.save(p,quality=95,subsampling=2,progressive=progressive);b=p.read_bytes()
  for suffix,marker,payload in [('exif',225,b'Exif\0\0'+b'test_metadata'),('comment',254,b'comment'),('icc',226,b'ICC_PROFILE\0\x01\x01'+b'profile_evidence')]:
   segment=bytes([255,marker])+(len(payload)+2).to_bytes(2,'big')+payload
   candidate=b[:2]+segment+b[2:];(d/(name+'-'+suffix+'.jpg')).write_bytes(candidate)
   if suffix!='icc':
    with Image.open(d/(name+'-'+suffix+'.jpg')) as test,Image.open(p) as ref:assert test.tobytes()==ref.tobytes()
  quant=bytearray(b);i=quant.index(b'\xff\xdb')+5;quant[i]=max(1,quant[i]-1) if quant[i]>1 else 2
  (d/(name+'-quant.jpg')).write_bytes(quant);(d/(name+'-truncated.jpg')).write_bytes(b[:-2])
 files=[root/'patches/shuttertrace1a'/n for n in ['M9TraceLedger1A.java','M9JpegSignature1A.java']]+[here/'LedgerTest.java',here/'JpegTest.java']
 subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-d',str(classes),*map(str,files)],check=True)
 for test in ['LedgerTest','JpegTest']:subprocess.run(['java','-ea','-cp',str(classes),test,str(d)],check=True)
