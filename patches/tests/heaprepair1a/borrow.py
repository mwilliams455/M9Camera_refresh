from pathlib import Path
import sys,subprocess,importlib.util,os,json
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
repo=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('repair',repo/'patches/heaprepair1a/apply.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert (root/m.NATIVE).read_text().endswith(m.JNI);assert m.JAVA in (root/m.HELPER).read_text()
# Compile exact production JNI wrapper and exact Java transport method, with a native owner test fixture.
cpp='#include <jni.h>\n#include <cstdint>\n#include <cstdlib>\n'+m.JNI+r'''
static void* owner=nullptr;
extern "C" JNIEXPORT jlong JNICALL Java_com_particlesdevs_photoncamera_m9_render_BorrowCheck_allocate(JNIEnv*,jclass,jint bytes){if(owner)return 0;owner=std::calloc(1,bytes);return reinterpret_cast<jlong>(owner);}
extern "C" JNIEXPORT void JNICALL Java_com_particlesdevs_photoncamera_m9_render_BorrowCheck_release(JNIEnv*,jclass){std::free(owner);owner=nullptr;}
'''
(out/'borrow.cpp').write_text(cpp)
java_home=Path(os.environ.get('JAVA_HOME','/usr/lib/jvm/java-17-openjdk-amd64'))
if not (java_home/'include/jni.h').exists():
 import glob
 java_home=Path(glob.glob('/usr/lib/jvm/*/include/jni.h')[0]).parents[1]
lib=out/'libborrow.so'
subprocess.run(['g++','-shared','-fPIC','-O2','-I'+str(java_home/'include'),'-I'+str(java_home/'include/linux'),str(out/'borrow.cpp'),'-o',str(lib)],check=True)
pkg='com.particlesdevs.photoncamera.m9.render';(out/'M9ColourTrial1C.java').write_text('package '+pkg+';import java.nio.*;final class M9ColourTrial1C{'+m.JAVA+'}')
(out/'BorrowCheck.java').write_text('package '+pkg+';'+r'''
import java.nio.*;
public class BorrowCheck {
 static native long allocate(int bytes);static native void release();
 static void check(boolean b,String s){if(!b)throw new AssertionError(s);}
 public static void main(String[] args) {
  System.load(args[0]);int w=4096,h=3072,bytes=w*h*6;
  try{ByteBuffer.allocateDirect(bytes);throw new AssertionError("old allocation should exceed direct memory limit");}catch(OutOfMemoryError expected){}
  for(int shot=0;shot<32;shot++) {
   long address=allocate(bytes);check(address!=0,"native owner allocation");
   try {
    ByteBuffer a=M9ColourTrial1C.borrowCameraStorage(address,w,h),b=M9ColourTrial1C.borrowCameraStorage(address,w,h);
    check(a.isDirect()&&a.capacity()==bytes&&a.order()==ByteOrder.nativeOrder(),"buffer contract");
    for(int i=0;i<bytes;i+=4096)a.put(i,(byte)(shot+i));
    for(int i=0;i<bytes;i+=4096)check(b.get(i)==(byte)(shot+i),"borrowed address identity");
    a.putShort(bytes-2,(short)0xBEEF);check(b.getShort(bytes-2)==(short)0xBEEF,"last RGB sample");
   } finally {release();}
  }
  try{M9ColourTrial1C.borrowCameraStorage(0,w,h);throw new AssertionError("null accepted");}catch(IllegalStateException expected){}
  System.out.println("PASS exact transport: 32 native-owned 72 MiB frames under 24 MiB heap/8 MiB direct limit; same-address exact samples, deterministic release");
 }
}
''')
subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-d',str(out),str(out/'M9ColourTrial1C.java'),str(out/'BorrowCheck.java')],check=True)
subprocess.run(['java','-Xmx24m','-XX:MaxDirectMemorySize=8m','-Xcheck:jni','-cp',str(out),pkg+'.BorrowCheck',str(lib)],check=True,timeout=60)
(out/'checks.json').write_text(json.dumps({'native_frames':32,'RGB16_MiB':72,'Java_heap_MiB':24,'direct_limit_MiB':8,'exact_production_transport_methods':True,'owner_fixture':'calloc/free; Android OpenCV lifetime also requires device test'},indent=2)+'\n')
