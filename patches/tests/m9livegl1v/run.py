#!/usr/bin/env python3
"""Exercise actual regional statistics, analyzer transport and preview model with host stubs."""
from pathlib import Path
import hashlib,shutil,subprocess,sys,tempfile,urllib.request
root=Path(sys.argv[1]).resolve();j=root/'app/src/main/java/com/particlesdevs/photoncamera'
here=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='m9-gl1v-test-') as tmp:
 d=Path(tmp);src=d/'src';src.mkdir();out=d/'classes';out.mkdir()
 for name in ['M9LiveToneModel1F','M9PreviewSpatialStats1V']:
  shutil.copyfile(j/'m9/preview'/f'{name}.java',src/f'{name}.java')
 text=(j/'m9/M9SubjectMotionAnalyzer.java').read_text()
 names=['fillLiveToneStats1R','exposureMapCode1R','histogramPercentile','histogramFractionAtMost','histogramFractionAtLeast']
 # Find declarations, not earlier calls.
 import re
 def declared(name):
  match=re.search(r'^    (?:public|private) static (?:synchronized )?\w+ '+name+r'\(',text,re.M)
  assert match,name
  tail=text[match.start():];br=tail.index('{');depth=1;end=br+1
  while depth:
   if tail[end]=='{':depth+=1
   elif tail[end]=='}':depth-=1
   end+=1
  return tail[:end]
 fields='''import com.particlesdevs.photoncamera.m9.preview.*;
 public class AnalyzerProbe {
 static final int W=96,H=72;static byte[] latestLumaFrame;static long lumaFramesAnalyzed;
 static double emaMedian,emaQ95,emaQ99,emaCenterMedian,lumaDark64,lumaBright224,lumaBright240;
 static int[] liveToneGlobalHist1R=new int[256],liveToneCenterHist1R=new int[256],liveToneMap1R=new int[256];
 static M9PreviewSpatialStats1V liveToneSpatialStats1V=new M9PreviewSpatialStats1V();
 static boolean liveToneExposureDomainValid1R;
 static double liveToneExposureScale1R,liveToneExposureEv1R,liveToneVirtualMedian1R,liveToneVirtualQ951R,liveToneVirtualQ991R,liveToneVirtualCenterMedian1R,liveToneVirtualDark641R,liveToneVirtualBright2241R,liveToneVirtualBright2401R,liveToneVirtualClip2551R;
 public static void seed(byte[] frame,float[] s){latestLumaFrame=frame;lumaFramesAnalyzed=(long)s[0];emaMedian=s[1];emaQ95=s[2];emaQ99=s[3];emaCenterMedian=s[4];lumaDark64=s[5];lumaBright224=s[6];lumaBright240=s[7];}
 '''
 (src/'AnalyzerProbe.java').write_text(fields+'\n'.join(declared(n) for n in names)+'\n}')
 shutil.copyfile(here/'SpatialPreviewTest.java',src/'SpatialPreviewTest.java')
 jar=d/'json.jar'
 if len(sys.argv)>2:shutil.copyfile(sys.argv[2],jar)
 else:urllib.request.urlretrieve('https://repo.maven.apache.org/maven2/org/json/json/20240303/json-20240303.jar',jar)
 assert hashlib.sha256(jar.read_bytes()).hexdigest()=='3cf6cd6892e32e2b4c1c39e0f52f5248a2f5b37646fdfbb79a66b46b618414ed'
 subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-cp',str(jar),'-d',str(out),*[str(p) for p in src.glob('*.java')]],check=True)
 subprocess.run(['java','-ea','-cp',str(out)+':'+str(jar),'SpatialPreviewTest',str(here/'window_fixture.json')],check=True)
