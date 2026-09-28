#!/usr/bin/env python3
"""Compile actual exposure/meter classes; fake only Android/GL platform dependencies.
A second stage runs the inherited synthetic overlap/no-tap suite on both inputs.
No phone pictures, diagnostic fixtures, or private captures belong in this directory.
"""
from pathlib import Path
import argparse,json,subprocess
HERE=Path(__file__).resolve().parent
JAVA='app/src/main/java/com/particlesdevs/photoncamera/'
STUBS={
'org/json/JSONException.java':'package org.json; public class JSONException extends Exception {}',
'org/json/JSONObject.java':'''package org.json; import java.util.*; public class JSONObject {
 public static final Object NULL=new Object(); private final Map<String,Object> d=new LinkedHashMap<>();
 public JSONObject put(String k,Object v) throws JSONException{d.put(k,v);return this;}
 public String toString(){return d.toString();}}''',
'org/json/JSONArray.java':'''package org.json; import java.util.*; public class JSONArray {
 private final List<Object>d=new ArrayList<>();public JSONArray put(Object v){d.add(v);return this;}
 public String toString(){return d.toString();}}''',
'android/os/SystemClock.java':'package android.os; public final class SystemClock {public static long now; public static long elapsedRealtimeNanos(){return now;}}',
'com/particlesdevs/photoncamera/util/Log.java':'package com.particlesdevs.photoncamera.util; public class Log {public static void w(String a,String b){}}',
'com/particlesdevs/photoncamera/m9/preview/M9PreviewFrameState1W.java':'''package com.particlesdevs.photoncamera.m9.preview;
import com.particlesdevs.photoncamera.m9.M9ExposurePlan1A;
public final class M9PreviewFrameState1W {
 public final M9ExposurePlan1A plan;public final long resultTimestampNs;public final float exposureScale=1;
 public final Source source2A;public static class Source {public boolean ready=true;public String cameraId;}
 public M9PreviewFrameState1W(M9ExposurePlan1A p,long t){plan=p;resultTimestampNs=t;source2A=new Source();source2A.cameraId=p.cameraId;}}
''',
'android/opengl/GLES30.java':'''package android.opengl;
import java.nio.*;
public final class GLES30 {
 public static final int GL_VIEWPORT=1,GL_DRAW_FRAMEBUFFER_BINDING=2,GL_READ_FRAMEBUFFER_BINDING=3,
 GL_PIXEL_PACK_BUFFER_BINDING=4,GL_ACTIVE_TEXTURE=5,GL_TEXTURE3=6,GL_TEXTURE_BINDING_2D=7,
 GL_SCISSOR_TEST=8,GL_NO_ERROR=0,GL_FRAMEBUFFER=9,GL_FRAMEBUFFER_COMPLETE=10,GL_TRIANGLE_STRIP=11,
 GL_PIXEL_PACK_BUFFER=12,GL_RGBA=13,GL_UNSIGNED_BYTE=14,GL_SYNC_GPU_COMMANDS_COMPLETE=15,
 GL_DRAW_FRAMEBUFFER=16,GL_READ_FRAMEBUFFER=17,GL_TEXTURE_2D=18,GL_TEXTURE_MIN_FILTER=19,
 GL_TEXTURE_MAG_FILTER=20,GL_NEAREST=21,GL_RGBA8=22,GL_COLOR_ATTACHMENT0=23,GL_STREAM_READ=24,
 GL_TIMEOUT_EXPIRED=25,GL_ALREADY_SIGNALED=26,GL_CONDITION_SATISFIED=27,GL_MAP_READ_BIT=28;
 public static boolean signalled=true,scissor=true;
 public static int draws,reads,maps,live,maxLive,blockingWaits;
 public static int boundDraw=71,boundRead=72,boundPack=73,active=74,boundTex=75;
 private static int[] viewport={1,2,320,240};private static int id=100;
 public static void reset(){draws=reads=maps=live=maxLive=blockingWaits=0;signalled=scissor=true;
 boundDraw=71;boundRead=72;boundPack=73;active=74;boundTex=75;viewport=new int[]{1,2,320,240};}
 public static void glGetIntegerv(int name,int[] out,int offset){
  if(name==GL_VIEWPORT){System.arraycopy(viewport,0,out,offset,4);return;}
  out[offset]=name==GL_DRAW_FRAMEBUFFER_BINDING?boundDraw:name==GL_READ_FRAMEBUFFER_BINDING?boundRead:
   name==GL_PIXEL_PACK_BUFFER_BINDING?boundPack:name==GL_ACTIVE_TEXTURE?active:boundTex;}
 public static void glActiveTexture(int v){active=v;}public static boolean glIsEnabled(int v){return scissor;}
 public static int glGetError(){return 0;}
 public static void glBindFramebuffer(int t,int v){if(t==GL_FRAMEBUFFER||t==GL_DRAW_FRAMEBUFFER)boundDraw=v;if(t==GL_FRAMEBUFFER||t==GL_READ_FRAMEBUFFER)boundRead=v;}
 public static int glCheckFramebufferStatus(int t){return GL_FRAMEBUFFER_COMPLETE;}
 public static void glDisable(int v){scissor=false;}public static void glEnable(int v){scissor=true;}
 public static void glUniform1i(int a,int b){}public static void glUniform1f(int a,float b){}
 public static void glViewport(int a,int b,int c,int d){viewport=new int[]{a,b,c,d};}
 public static void glDrawArrays(int a,int b,int c){draws++;}
 public static void glBindBuffer(int t,int v){boundPack=v;}
 public static void glReadPixels(int x,int y,int w,int h,int fmt,int type,int offset){reads++;if(w!=352||h!=24)throw new AssertionError("probe dimensions changed");}
 public static long glFenceSync(int c,int f){live++;maxLive=Math.max(maxLive,live);return ++id;}
 public static void glDeleteSync(long f){live--;if(live<0)throw new AssertionError("fence double delete");}
 public static int glClientWaitSync(long f,int flags,long timeout){if(flags!=0||timeout!=0){blockingWaits++;throw new AssertionError("blocking GL wait");}return signalled?GL_ALREADY_SIGNALED:GL_TIMEOUT_EXPIRED;}
 public static void glFlush(){}public static void glBindTexture(int t,int v){boundTex=v;}
 public static void glGenTextures(int n,int[] a,int o){a[o]=++id;}
 public static void glTexParameteri(int a,int b,int c){}
 public static void glTexImage2D(int a,int b,int c,int d,int e,int f,int g,int h,Buffer i){}
 public static void glGenFramebuffers(int n,int[] a,int o){a[o]=++id;}
 public static void glFramebufferTexture2D(int a,int b,int c,int d,int e){}
 public static void glGenBuffers(int n,int[] a,int o){a[o]=++id;}
 public static void glBufferData(int a,int b,Buffer c,int d){}
 public static Buffer glMapBufferRange(int t,int o,int n,int access){maps++;ByteBuffer b=ByteBuffer.allocate(n);for(int i=0;i<n;i++)b.put(i,(byte)80);return b;}
 public static boolean glUnmapBuffer(int t){return true;}
}
'''}
def run(app,out):
    out.mkdir(parents=True,exist_ok=True)
    sources=[]
    for path,body in STUBS.items():
        f=out/'stubs'/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(body);sources.append(f)
    root=app/JAVA
    sources += [root/'m9/preview'/n for n in ['M9AutoExposure2D.java','M9TapMeter1A.java','M9PreviewMeter2D.java','M9AeProbeCadence1A.java']]
    sources += [root/'m9/M9ExposurePlan1A.java',HERE/'CadenceTest.java']
    subprocess.run(['javac','--release','17','-d',str(out/'classes'),*map(str,sources)],check=True,timeout=60)
    r=subprocess.run(['java','-ea','-cp',str(out/'classes'),'com.particlesdevs.photoncamera.m9.preview.CadenceTest'],capture_output=True,text=True,check=True,timeout=30)
    (out/'CADENCE_TESTS.txt').write_text(r.stdout)
    print(r.stdout,end='')
    (out/'TEST_SCOPE.json').write_text(json.dumps({'actualSourceClasses':['M9AutoExposure2D','M9TapMeter1A','M9PreviewMeter2D','M9AeProbeCadence1A','M9ExposurePlan1A'],
        'fakePlatform':'Android clock, GLES calls, frame state and JSON','notDeviceBenchmark':True,'phoneValidationPending':True},indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('app',type=Path);p.add_argument('out',type=Path);a=p.parse_args();run(a.app,a.out)
