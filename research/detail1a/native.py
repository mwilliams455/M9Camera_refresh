"""Host execution of the GL2G native demosaic/Sharp functions, with a slot probe.

Production source is hash checked. JNI memory access alone is stubbed; both
actual CFA entry points and their threaded pixel loops are compiled unchanged.
The candidate replaces only the shared Sharp coefficient lookup. No APK edit.
"""
from pathlib import Path
import ctypes as C
import hashlib
import json
import subprocess
import numpy as np

ISOS = np.array([160,200,250,320,400,500,640,800,1000,1250,1600,2000,2500])

def function(s, marker):
    start=s.index(marker); pos=s.index('{',start); depth=0
    for i in range(pos,len(s)):
        depth += (s[i]=='{')-(s[i]=='}')
        if depth==0:return s[start:i+1]
    raise ValueError(marker)

PREAMBLE=r'''
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <chrono>
#include <thread>
#include <vector>
#include <cstring>
using jshort=int16_t; using jint=int; using jsize=int; using jlong=int64_t;
using jfloat=float; using jboolean=bool;
struct Memory {void* data; int64_t length;};
using jshortArray=Memory*; using jlongArray=Memory*; using jobject=Memory*; using jclass=void*;
constexpr bool JNI_FALSE=false; constexpr int JNI_ABORT=2;
#define JNIEXPORT
#define JNICALL
struct JNIEnv {
 int GetArrayLength(Memory* a){return a->length;}
 void* GetDirectBufferAddress(Memory* a){return a->data;}
 int64_t GetDirectBufferCapacity(Memory* a){return a->length;}
 void* GetPrimitiveArrayCritical(Memory* a,bool*){return a->data;}
 void ReleasePrimitiveArrayCritical(Memory*,void*,int){}
 void SetLongArrayRegion(Memory* a,int off,int n,const int64_t* v){std::memcpy(static_cast<int64_t*>(a->data)+off,v,n*sizeof(int64_t));}
};
static thread_local int selected_slot=0;
'''
FOOTER=r'''
extern "C" int replay(const uint16_t* raw,int w,int h,int cfa,int ox,int oy,
 float nr,float nb,int slot,uint16_t* output,int workers){
 if(slot<0||slot>12)return -100;
 selected_slot=slot; JNIEnv env; Memory a{const_cast<uint16_t*>(raw),int64_t(w)*h};
 Memory b{output,int64_t(w)*h*6}; int64_t ns;
 if(cfa==0&&ox==0&&oy==0)
 ns=Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_demosaicMhcRggb(&env,nullptr,&a,w,h,&b,workers,nr,1.f,nb,true,nullptr);
 else ns=Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_demosaicMhcBayer(&env,nullptr,&a,w,h,cfa,ox,oy,&b,workers,nr,1.f,nb,true,nullptr);
 return ns<0?int(ns):0;
}
extern "C" void sharp(const uint16_t* in,int w,int h,int slot,uint16_t* out){
 selected_slot=slot;std::vector<uint16_t>a(in,in+w*h),b;
 m9ClosureSharpIso160Standard(a,b,w,h);std::copy(b.begin(),b.end(),out);
}
'''

class Native:
    def __init__(self,repo,assembled,header,build):
        build.mkdir(parents=True,exist_ok=True)
        manifest=json.loads((repo/'patches/m9cam-m9livegl2g-manifest.json').read_text())
        self.source_hashes={}
        for rel in ['app/src/main/cpp/m9color_jni.cpp','app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java']:
            raw=(assembled/rel).read_bytes();h=hashlib.sha256(raw).hexdigest()
            assert h==manifest['frozen'][rel],(rel,h)
            self.source_hashes[rel]=h
        s=(assembled/'app/src/main/cpp/m9color_jni.cpp').read_text()
        helpers=s[s.index('inline int64_t clipl'):s.index('// SKYCHROMA1A diagnostic only')]
        spatial=s[s.index('// SHARPNESS_CLOSURETEST1A'):s.index('extern "C" JNIEXPORT jlong JNICALL\nJava_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_normalizeRawDirect')]
        # End selection explicitly includes the two real JNI demosaic entry points.
        assert spatial.count('Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_demosaic')==2
        self.libs=[]
        old='''const int baseCorr=m9ClosureSlot0Coeff(1024+r);
            const int doubledCorr=baseCorr*2;
            const int corr=doubledCorr < -2048 ? -2048 : (doubledCorr > 2048 ? 2048 : doubledCorr);'''
        replacement='''int v=M9_SHARP_BASE[selected_slot][1024+r];
            const int mode=M9_SHARP_STANDARD_MODE[selected_slot];
            if(mode==4)v*=2;
            else if(mode==2)v=v>=0?v/2:-((-v+1)/2);
            const int corr=std::max(-2048,std::min(2048,v));'''
        assert spatial.count(old)==1
        for candidate in [False,True]:
            code=PREAMBLE+'\n'+(header.read_text() if candidate else '')+'\n'+helpers+'\n'+(spatial.replace(old,replacement) if candidate else spatial)+FOOTER
            name='candidate' if candidate else 'baseline'
            cp=build/(name+'.cpp'); cp.write_text(code); so=build/(name+'.so')
            subprocess.run(['g++','-std=c++17','-O2','-fno-fast-math','-fPIC','-shared','-pthread',str(cp),'-o',str(so)],check=True,capture_output=True)
            lib=C.CDLL(str(so),mode=C.RTLD_LOCAL)
            lib.replay.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,C.c_float,C.c_float,C.c_int,C.c_void_p,C.c_int]
            lib.replay.restype=C.c_int
            lib.sharp.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_void_p]
            self.libs.append(lib)
    def render(self,raw,nr,nb,cfa=0,slot=0,candidate=True,ox=0,oy=0,workers=4):
        raw=np.ascontiguousarray(raw,dtype=np.uint16);h,w=raw.shape
        out=np.empty((h,w,3),np.uint16)
        status=self.libs[int(candidate)].replay(raw.ctypes.data,w,h,cfa,ox,oy,nr,nb,slot,out.ctypes.data,workers)
        if status:raise RuntimeError(('native replay',status))
        return out
    def sharp(self,a,slot,candidate=True):
        a=np.ascontiguousarray(a,dtype=np.uint16);h,w=a.shape;out=np.empty_like(a)
        self.libs[int(candidate)].sharp(a.ctypes.data,w,h,slot,out.ctypes.data)
        return out

def checks(native,bank,modes):
    rng=np.random.default_rng(91221);count=0; samples=0
    for cfa in range(4):
        for shape in [(17,19),(32,38),(65,67)]:
            a=rng.integers(0,65536,shape,dtype=np.uint16)
            b=native.render(a,.37,.61,cfa,candidate=False)
            for slot in [0,1,2]:
                q=native.render(a,.37,.61,cfa,slot)
                assert np.array_equal(b,q),('baseline parity',shape,cfa,slot)
                count+=1;samples+=q.size
            for slot in range(13):
                q=native.render(a,.37,.61,cfa,slot)
                border=np.ones(shape,bool);border[9:-9,9:-9]=False
                assert np.array_equal(b[border],q[border]),('border',slot,cfa)
    a=rng.integers(0,16384,(96,97),dtype=np.uint16)
    z=a.astype(np.int64);g=(z[:-2,:-2]+2*z[:-2,1:-1]+z[:-2,2:]+2*z[1:-1,:-2]+4*z[1:-1,1:-1]+2*z[1:-1,2:]+z[2:,:-2]+2*z[2:,1:-1]+z[2:,2:])//16
    residual=np.clip(z[1:-1,1:-1]-g,-1024,1024)
    for slot in range(13):
        row=bank[slot].astype(np.int64)
        coeff=np.clip(row*2 if modes[slot]==4 else row//2 if modes[slot]==2 else row,-2048,2048)
        expected=z.copy();expected[2:-2,2:-2]=np.clip(z[2:-2,2:-2]+coeff[1024+residual[1:-1,1:-1]],0,16383)
        got=native.sharp(a,slot)
        assert np.array_equal(got,expected),('independent sharp oracle',slot)
        assert np.array_equal(native.sharp(np.full((35,37),4096,np.uint16),slot),np.full((35,37),4096,np.uint16))
    return dict(slot0_1_2_rgb_parity_cases=count,rgb_samples=samples,all_four_cfa_patterns=True,all_13_rows_independent_integer_oracle=True,border9_unchanged_all_rows=True,constant_input_unchanged=True)
