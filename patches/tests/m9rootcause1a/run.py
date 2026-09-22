from pathlib import Path
import hashlib,re,subprocess,sys,tempfile,urllib.request
root=Path(sys.argv[1]).resolve();j=root/'app/src/main/java/com/particlesdevs/photoncamera';here=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);out=d/'classes';out.mkdir()
 for rel in ['m9/M9ExposurePlan1A','m9/preview/M9AutoExposure2D','m9/preview/M9RootCausePixels1A','m9/preview/M9RootCauseTrace1A']:
  (d/(rel.rsplit('/',1)[-1]+'.java')).write_text((j/(rel+'.java')).read_text())
 text=(d/'M9RootCausePixels1A.java').read_text()
 constants=sorted(set(re.findall(r'GLES30\.(GL_\w+)',text)))
 code='package android.opengl;import java.nio.*;import java.util.*;public class GLES30 {\n'
 code+='\n'.join('public static final int '+c+'='+str(i+1)+';' for i,c in enumerate(constants))
 code+='''
 public static int draws,reads,maps,peaking=1,stage=0;public static java.util.List<Integer> stages=new ArrayList<>();public static java.util.List<Float> scales=new ArrayList<>();static int id=100,draw=3,read=4,pack=7,active=0;
 static int[] viewport={2,3,1080,1920},box={4,5,6,7}; public static java.util.List<String> crops=new ArrayList<>();static Map<Integer,Integer> tex=new TreeMap<>();
 public static Map<Integer,Float> uniforms=new TreeMap<>();
 static boolean scissor=true;public static boolean signalled,complete=true;
 static ByteBuffer bytes=ByteBuffer.allocateDirect(96*96*3*4);
 static {tex.put(GL_TEXTURE3,97);for(int y=0;y<96;y++)for(int s=0;s<3;s++)for(int x=0;x<96;x++){int v=10+s*30;bytes.put((byte)v).put((byte)v).put((byte)v).put((byte)255);}bytes.position(0);}
 public static String snapshot(){return draw+":"+read+":"+pack+":"+active+":"+tex+":"+Arrays.toString(viewport)+":"+Arrays.toString(box)+":"+scissor+":"+uniforms+":"+peaking+":"+stage;}
 public static void glGetIntegerv(int key,int[] a,int off) {
 if(key==GL_SCISSOR_BOX){System.arraycopy(box,0,a,off,4);return;}
 if(key==GL_VIEWPORT){System.arraycopy(viewport,0,a,off,4);return;}
 a[off]=key==GL_DRAW_FRAMEBUFFER_BINDING?draw:key==GL_READ_FRAMEBUFFER_BINDING?read:key==GL_PIXEL_PACK_BUFFER_BINDING?pack:key==GL_ACTIVE_TEXTURE?active:tex.getOrDefault(active,0);}
 public static void glActiveTexture(int v){active=v;}
 public static boolean glIsEnabled(int k){return scissor;}
 public static int glGetError(){return GL_NO_ERROR;}
 public static void glBindFramebuffer(int target,int value){if(target==GL_FRAMEBUFFER||target==GL_DRAW_FRAMEBUFFER)draw=value;if(target==GL_FRAMEBUFFER||target==GL_READ_FRAMEBUFFER)read=value;}
 public static int glCheckFramebufferStatus(int t){return complete?GL_FRAMEBUFFER_COMPLETE:-1;}
 public static void glDisable(int k){scissor=false;}public static void glEnable(int k){scissor=true;}
 public static void glUniform1i(int k,int v){if(k==12)stage=v;else peaking=v;}public static void glUniform1f(int k,float v){uniforms.put(k,v);}
 public static void glScissor(int x,int y,int w,int h){box=new int[]{x,y,w,h};}
 public static void glViewport(int x,int y,int w,int h){viewport=new int[]{x,y,w,h};}
 public static void glDrawArrays(int mode,int first,int count){draws++;crops.add(Arrays.toString(viewport)+"|"+Arrays.toString(box));stages.add(stage);scales.add(uniforms.get(10));if(count!=4)throw new AssertionError();}
 public static void glBindBuffer(int target,int value){pack=value;}
 public static void glReadPixels(int x,int y,int w,int h,int format,int type,int offset){reads++;if(w!=288||h!=96||offset!=0)throw new AssertionError();}
 public static long glFenceSync(int a,int b){return 12;}public static void glFlush(){}
 public static void glBindTexture(int target,int value){tex.put(active,value);}
 public static void glGenTextures(int n,int[] a,int off){a[off]=id++;}
 public static void glGenFramebuffers(int n,int[] a,int off){a[off]=id++;}
 public static void glGenBuffers(int n,int[] a,int off){a[off]=id++;}
 public static void glTexParameteri(int a,int b,int c){}
 public static void glTexImage2D(int a,int b,int c,int w,int h,int border,int f,int t,Buffer data){}
 public static void glFramebufferTexture2D(int a,int b,int c,int d,int e){}
 public static void glBufferData(int a,int bytes,Buffer data,int usage){if(bytes!=110592)throw new AssertionError();}
 public static int glClientWaitSync(long f,int flags,long timeout){if(flags!=0||timeout!=0)throw new AssertionError("blocking fence");return signalled?GL_ALREADY_SIGNALED:GL_TIMEOUT_EXPIRED;}
 public static Buffer glMapBufferRange(int a,int off,int length,int access){if(!signalled)throw new AssertionError("premature map");maps++;return bytes;}
 public static boolean glUnmapBuffer(int a){return true;}public static void glDeleteSync(long f){}
 }
 '''
 (d/'GLES30.java').write_text(code)
 (d/'SystemClock.java').write_text('package android.os;public class SystemClock {public static long now;public static long elapsedRealtimeNanos(){return now;}}')
 (d/'SurfaceTexture.java').write_text('package android.graphics;public class SurfaceTexture {public int getDataSpace(){return 142671872;}}')
 (d/'Build.java').write_text('package android.os;public class Build {public static class VERSION {public static int SDK_INT=35;}}')
 (d/'Log.java').write_text('package com.particlesdevs.photoncamera.util;public class Log {public static void w(String a,String b){}}')
 (d/'M9GpuPreview2A.java').write_text('package com.particlesdevs.photoncamera.m9.preview;public class M9GpuPreview2A {public static class Frame {public final boolean ready;public final String cameraId;public Frame(boolean r,String c){ready=r;cameraId=c;}public org.json.JSONObject diagnostics(){return new org.json.JSONObject();}}}')
 (d/'M9PreviewFrameState1W.java').write_text('''package com.particlesdevs.photoncamera.m9.preview;import com.particlesdevs.photoncamera.m9.M9ExposurePlan1A;
 public class M9PreviewFrameState1W {public final M9ExposurePlan1A plan;public M9GpuPreview2A.Frame source2A;public final long resultTimestampNs;public final float exposureScale;
 public M9PreviewFrameState1W(M9ExposurePlan1A p,M9GpuPreview2A.Frame f,long t,float e){plan=p;source2A=f;resultTimestampNs=t;exposureScale=e;}}
 ''')
 (d/'EvidenceTest.java').write_text((here/'EvidenceTest.java').read_text())
 exec((here/'metadata_stubs.py').read_text())
 jar=d/'json.jar';urllib.request.urlretrieve('https://repo.maven.apache.org/maven2/org/json/json/20240303/json-20240303.jar',jar)
 assert hashlib.sha256(jar.read_bytes()).hexdigest()=='3cf6cd6892e32e2b4c1c39e0f52f5248a2f5b37646fdfbb79a66b46b618414ed'
 subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-cp',str(jar),'-d',str(out),*[str(p) for p in d.glob('*.java')]],check=True)
 subprocess.run(['java','-ea','-cp',str(out)+':'+str(jar),'EvidenceTest'],check=True)
