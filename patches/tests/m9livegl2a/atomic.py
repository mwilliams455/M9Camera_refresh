#!/usr/bin/env python3
"""Compile the production frame/plan and real GL draw body; force publication mid-draw."""
from pathlib import Path
import hashlib,re,shutil,subprocess,sys,tempfile,urllib.request
root=Path(sys.argv[1]).resolve();j=root/'app/src/main/java/com/particlesdevs/photoncamera'
here=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='m9-gl1w-test-') as tmp:
 d=Path(tmp);src=d/'src';src.mkdir();out=d/'classes';out.mkdir()
 for rel in ['m9/M9ExposurePlan1A','m9/M9ExposurePlanDiagnostics1A','m9/preview/M9PreviewFrameState1W']:
  shutil.copyfile(j/(rel+'.java'),src/(rel.rsplit('/',1)[-1]+'.java'))
 text=(j/'ui/camera/views/viewfinder/MainRenderer.java').read_text()
 def method(name):
  m=re.search(r'^    public (?:void|String) '+name+r'\(',text,re.M);assert m,name
  a=m.start();b=text.index('{',a)+1;depth=1
  while depth:
   if text[b]=='{':depth+=1
   elif text[b]=='}':depth-=1
   b+=1
  return text[a:b]
 body='\n'.join(method(x) for x in ['onDrawFrame','setM9FrameState1W','snapshotM9DrawState1W'])
 # Real renderer constants and distinct locations so the fake GL records uniforms.
 locations=sorted(set(re.findall(r'\b(?:u[A-Z]\w*|enablePeak|mirror|vPosition|vTexCoord)\b',body)))
 constants='\n'.join(re.findall(r'^    private static final float(?:\[\])? (?:[\s\S]*?);',text,re.M))
 probe='''import com.particlesdevs.photoncamera.m9.preview.*;
 public class RendererProbe {
 M9GpuPreview2A.Frame bound;
 Meter mM9Meter2D;static class Meter {void sample(Object... args){}}
 void bindSource2A(M9GpuPreview2A.Frame f){bound=f;}
 volatile M9PreviewFrameState1W mM9FrameState1W=M9PreviewFrameState1W.defaults();
 volatile M9PreviewFrameState1W.Draw mM9LastDraw1W;long mM9DrawSequence1W;
 boolean mGLInit=true,mUpdateST=true,mMirrorPreview;int mM9CurveTex=1,mM9PreviewLutTex1F=2;
 float[] mTexRotateMatrix=new float[16];int[] hTex={3};Object pVertex,pTexCoord;
 Surface mSTexture=new Surface();View mView=new View();int getPeakEnabled(){return 0;}
 static class Surface {long timestamp=900;void updateTexImage(){}long getTimestamp(){return timestamp;}}
 static class View {void requestRender(){}}
 '''+'\n'.join('static final int '+n+'='+str(i+1)+';' for i,n in enumerate(locations))+constants+body+'\n}'
 (src/'RendererProbe.java').write_text(probe)
 (src/'GLES20.java').write_text('''import java.util.*;class GLES20 {
 static final int GL_TEXTURE0=0,GL_TEXTURE1=1,GL_TEXTURE2=2,GL_TEXTURE_2D=3,GL_FLOAT=4,GL_TRIANGLE_STRIP=5;
 static Map<Integer,Float> uniforms=new HashMap<>();static Runnable hook;
 static void glUniform1f(int id,float v){uniforms.put(id,v);if(hook!=null){Runnable h=hook;hook=null;h.run();}}
 static void glUniform1i(Object...a){}static void glUniformMatrix4fv(Object...a){}
 static void glUniformMatrix3fv(Object...a){}static void glActiveTexture(Object...a){}
 static void glBindTexture(Object...a){}static void glVertexAttribPointer(Object...a){}
 static void glDrawArrays(Object...a){}
 } class GLES11Ext {static final int GL_TEXTURE_EXTERNAL_OES=6;}interface GL10 {}''')
 (src/'SystemClock.java').write_text('package android.os;public class SystemClock {public static long elapsedRealtimeNanos(){return 1000000000;}}')
 (src/'M9GpuPreview2A.java').write_text('package com.particlesdevs.photoncamera.m9.preview;\nimport org.json.*;\npublic class M9GpuPreview2A { public static class Frame {\n public final boolean ready=false;\n public static Frame fallback(String s){return new Frame();}\n public JSONObject diagnostics(){return new JSONObject();}\n}}')
 shutil.copyfile(here/'AtomicFrameTest.java',src/'AtomicFrameTest.java')
 jar=d/'json.jar'
 if len(sys.argv)>2:shutil.copyfile(sys.argv[2],jar)
 else:urllib.request.urlretrieve('https://repo.maven.apache.org/maven2/org/json/json/20240303/json-20240303.jar',jar)
 assert hashlib.sha256(jar.read_bytes()).hexdigest()=='3cf6cd6892e32e2b4c1c39e0f52f5248a2f5b37646fdfbb79a66b46b618414ed'
 subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-cp',str(jar),'-d',str(out),*[str(p) for p in src.glob('*.java')]],check=True)
 subprocess.run(['java','-ea','-cp',str(out)+':'+str(jar),'AtomicFrameTest'],check=True)
