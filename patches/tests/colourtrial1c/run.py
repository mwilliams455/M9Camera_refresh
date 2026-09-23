"""Compile actual Android JNI source; check selected kernels and block parity."""
from pathlib import Path
import sys,subprocess,ctypes as C,hashlib,json,os,re,shutil
import numpy as np
REPO=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent

def build(root,out):
 out.mkdir(parents=True,exist_ok=True);inc=out/'android';inc.mkdir(exist_ok=True)
 (inc/'bitmap.h').write_text('''#pragma once
#include <jni.h>
#include <cstdint>
#define ANDROID_BITMAP_FORMAT_RGBA_8888 1
#define ANDROID_BITMAP_RESULT_SUCCESS 0
struct AndroidBitmapInfo {uint32_t width,height,stride;int32_t format;uint32_t flags;};
inline int AndroidBitmap_getInfo(JNIEnv* e,jobject b,AndroidBitmapInfo* i){
 jclass c=e->GetObjectClass(b);i->width=e->GetIntField(b,e->GetFieldID(c,"width","I"));i->height=e->GetIntField(b,e->GetFieldID(c,"height","I"));i->stride=i->width*4;
 i->format=e->GetBooleanField(b,e->GetFieldID(c,"invalid","Z"))?0:1;return 0;}
inline int AndroidBitmap_lockPixels(JNIEnv* e,jobject b,void** p){jclass c=e->GetObjectClass(b);auto buf=e->GetObjectField(b,e->GetFieldID(c,"pixels","Ljava/nio/ByteBuffer;"));*p=e->GetDirectBufferAddress(buf);e->DeleteLocalRef(buf);return *p?0:-1;}
inline int AndroidBitmap_unlockPixels(JNIEnv*,jobject){return 0;}
''')
 java=Path(os.environ.get('JAVA_HOME','/usr/lib/jvm/java-17-openjdk-amd64'));
 if not (java/'include/jni.h').exists():java=Path('/usr/lib/jvm/java-17-openjdk-amd64')
 include=Path(os.environ.get('M9_TRIAL_JNI_INCLUDE',str(java/'include')))
 cpp=root/'app/src/main/cpp';p=cpp/'colourtrial1c';lib=out/'libtrial.so'
 cmd=['g++','-std=c++17','-O2','-fPIC','-shared','-pthread','-fopenmp','-ffp-contract=off','-fno-fast-math',
      '-I'+str(out),'-I'+str(include),'-I'+str(include/'linux'),'-I'+str(cpp),'-I'+str(p/'upstream/include'),
      str(HERE/'host.cpp'),*[str(p/f) for f in ['reconstruct.cpp','phase_noise.cpp','chroma.cpp','upstream/amaze.cc','upstream/border.cc']],'-o',str(lib)]
 subprocess.run(cmd,check=True)
 # Independent previously selected source kernels.
 ref=out/'libreference.so'
 subprocess.run(['g++','-std=c++17','-O2','-shared','-fPIC','-fopenmp','-ffp-contract=off','-fno-fast-math',str(REPO/'research/colourtrial1a/chroma.cpp'),str(REPO/'research/colourtrial1b/reconstruct.cpp'),'-o',str(ref)],check=True)
 return lib,ref

def configure(lib):
 def fn(name,args,ret=C.c_int):
  f=getattr(lib,name);f.argtypes=args;f.restype=ret;return f
 P=C.c_void_p;I=C.c_int;D=C.c_double
 fn('trial_context',[P,P],P);fn('trial_destroy',[P],None)
 fn('trial_prepare',[P,P,I,I,D,P,I]);fn('trial_fields',[P,P,I,D,P],None)
 fn('trial_border',[P,I,I,I,D,D,P],None);fn('trial_colour',[P,P,I,I,I,D,D,P],None)
 fn('trial_variance',[P,I,I,I,I,P,I,P,P,I,I,D,P,P]);fn('trial_reconstruct',[P,P,P,I,I,I,D,D,D,P,I,P])
 fn('phase_noise',[P,P,P,I,I,P,I]);fn('partial_chroma',[P,I,I,D,P])
 return lib

def checks(root,out,lib,ref):
 rng=np.random.default_rng(192309);checks={}
 curve=np.frombuffer((root/'app/src/main/assets/m9/m9_curve02_firmware.bin').read_bytes(),np.uint8).copy();assert curve.size==2048
 context=np.r_[np.ones(3),np.array([[1.1,-.06,-.04],[-.07,1.11,-.04],[-.03,-.07,1.10]]).ravel(),np.eye(3).ravel(),np.eye(3).ravel(),np.eye(3).ravel(),np.eye(3).ravel()].astype(float)
 q=lib.trial_context(context.ctypes.data,curve.ctypes.data)
 assert q
 for w,h in [(129,385),(130,257),(3,3),(1,9)]:
  cam=rng.integers(0,65536,(h,w,3),dtype=np.uint16);pre=np.empty_like(cam)
  lib.trial_fields(q,cam.ctypes.data,w*h,2**.5,pre.ctypes.data)
  expected=np.empty_like(cam);assert ref.partial_chroma(pre.ctypes.data,w,h,.25,expected.ctypes.data)==0
  for band in [1,31,128,384,h]:
   actual=np.empty_like(cam);assert lib.trial_prepare(q,cam.ctypes.data,w,h,2**.5,actual.ctypes.data,band)==0
   assert np.array_equal(actual,expected),('halo seam',w,h,band)
 checks['preSAT_full_vs_5_band_sizes']=20
 # Independent firmware integer matrices + pair arithmetic, including odd width.
 src=(root/'app/src/main/cpp/m9color_jni.cpp').read_text()
 matrices={bank:np.array([[int(v) for v in re.search(r'\b'+name+r'\s*=\s*\{([^}]+)',src).group(1).replace('\n','').split(',') if v.strip()] for name in names],np.int64).reshape(2,3,3) for bank,names in {2:['Q2E','Q2O'],3:['QE','QO'],4:['Q4E','Q4O']}.items()}
 for w in [128,129]:
  a=rng.integers(0,16384,(131,w,3),dtype=np.uint16);z=a.astype(np.int64)
  for bank in [2,3,4]:
   signed=np.where((z[...,0]>=z[...,1])[...,None],z@matrices[bank][0].T,z@matrices[bank][1].T)>>16
   rgb=curve[np.clip(signed,0,2047)]
   for cb,cr in [(1.,1.),(.8,.9)]:
    expected=pair422(rgb,cb,cr);argb=np.empty((131,w),np.uint32)
    lib.trial_colour(q,a.ctypes.data,w,131,bank,cb,cr,argb.ctypes.data)
    got=np.stack([(argb>>16)&255,(argb>>8)&255,argb&255],-1).astype(np.uint8)
    assert np.array_equal(got,expected),('SAT/curve/422',w,bank,cb,np.max(abs(got.astype(int)-expected)))
 checks['SAT2_3_4_TG1_even_odd']=12
 w,h=129,131
 raw=rng.integers(1000,20000,(h,w),dtype=np.uint16);variance=np.full((h,w),30000,np.float32);mask=np.zeros((h,w),np.uint8);mask[60,60]=1
 proposal=np.empty_like(raw);ref.phase_noise(raw.ctypes.data,variance.ctypes.data,mask.ctypes.data,w,h,proposal.ctypes.data,1)
 quarter=((3*raw.astype(np.uint32)+proposal+2)//4).astype(np.uint16)
 for cfa in range(4):
  a=np.empty((h,w,3),np.uint16);b=np.empty_like(a);c=np.empty_like(a);stats=np.empty(4,float)
  assert lib.trial_reconstruct(raw.ctypes.data,variance.ctypes.data,mask.ctypes.data,w,h,cfa,.37,.61,1.7,a.ctypes.data,1,stats.ctypes.data)==0
  assert stats[0]==1 and stats[3]==1
  assert lib.trial_reconstruct(quarter.ctypes.data,None,None,w,h,cfa,.37,.61,1.7,b.ctypes.data,4,stats.ctypes.data)==0
  assert np.array_equal(a,b),('quarter blend/all CFA',cfa)
  assert lib.trial_reconstruct(raw.ctypes.data,variance.ctypes.data,mask.ctypes.data,w,h,cfa,.37,.61,1.7,c.ctypes.data,4,stats.ctypes.data)==0
  assert np.array_equal(a,c),('thread parity',cfa)
 checks['quarter_and_thread_parity_four_CFA']=8
 lib.trial_destroy(q)
 checks['host_library_sha256']=hashlib.sha256((out/'libtrial.so').read_bytes()).hexdigest()
 (out/'checks.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks,indent=2))

def pair422(rgb,cbgain,crgain):
 a=rgb.astype(np.int64);h,w=a.shape[:2];ww=w-w%2;z=a[:,:ww];Y=(z@np.array([4899,9617,1868]))>>14
 rs=z[:,::2,0]+z[:,1::2,0];gs=z[:,::2,1]+z[:,1::2,1];bs=z[:,::2,2]+z[:,1::2,2]
 cb=(((-2765*rs+1)>>1)-((5427*gs)>>1)+((8192*bs)>>1))>>14
 cr=(((8192*rs)>>1)-((6860*gs)>>1)-((1332*bs)>>1))>>14
 cb=((cb+128)&255)-128;cr=((cr+128)&255)-128
 cb=np.repeat(np.where(cb<0,cb*cbgain,cb),2,axis=1);cr=np.repeat(np.where(cr<0,cr*crgain,cr),2,axis=1)
 out=np.floor(np.clip(np.stack([Y+1.402*cr,Y-.344136*cb-.714136*cr,Y+1.772*cb],-1),0,255)+.5).astype(np.uint8)
 return np.concatenate([out,rgb[:,ww:]],axis=1) if ww!=w else out
if __name__=='__main__':
 root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();so,ref=build(root,out)
 lib=configure(C.CDLL(str(so)));ref=C.CDLL(str(ref))
 ref.partial_chroma.argtypes=lib.partial_chroma.argtypes;ref.phase_noise.argtypes=lib.phase_noise.argtypes
 checks(root,out,lib,ref)
