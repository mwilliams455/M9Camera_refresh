"""M9DETAIL1I research: alternative co-sited green guides for R/B reconstruction.

The final native green plane and ISO160 Sharp output are never replaced.  This
probe changes only the temporary green estimate used to form measured R-G/B-G
differences before the existing consumer.  It compares Hamilton-Adams-style
edge-directed guides, with/without clamping, shrink, and the historical diagonal
carrier.  Synthetic scene RGB and fixed-native-green references are both kept.
No Android source or APK is changed by this file.
"""
from pathlib import Path
import argparse, ctypes as C, hashlib, json, subprocess
import numpy as np
from scipy.ndimage import gaussian_filter

from rb_domain import DomainProbe
from rb_probe import q14, q16
from fringe_replay import cfa_masks
from censored_chroma_probe import BACKGROUNDS, SUBJECTS

PREAMBLE=r"""
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
"""
FOOTER=r"""
extern "C" int replay(const uint16_t* raw,int w,int h,int cfa,int ox,int oy,
 float nr,float nb,uint16_t* output,int workers){
 JNIEnv env; Memory a{const_cast<uint16_t*>(raw),int64_t(w)*h};
 Memory b{output,int64_t(w)*h*6}; int64_t ns;
 if(cfa==0&&ox==0&&oy==0)
 ns=Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_demosaicMhcRggb(&env,nullptr,&a,w,h,&b,workers,nr,1.f,nb,true,nullptr);
 else ns=Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_demosaicMhcBayer(&env,nullptr,&a,w,h,cfa,ox,oy,&b,workers,nr,1.f,nb,true,nullptr);
 return ns<0?int(ns):0;
}
"""

class NativeBaseline:
    def __init__(self, repo, assembled, build):
        build.mkdir(parents=True,exist_ok=True)
        manifest=json.loads((repo/'patches/m9cam-m9livegl2g-manifest.json').read_text())
        rel='app/src/main/cpp/m9color_jni.cpp'
        raw=(assembled/rel).read_bytes()
        h=hashlib.sha256(raw).hexdigest()
        assert h==manifest['frozen'][rel],(h,manifest['frozen'][rel])
        s=raw.decode()
        helpers=s[s.index('inline int64_t clipl'):s.index('// SKYCHROMA1A diagnostic only')]
        spatial=s[s.index('// SHARPNESS_CLOSURETEST1A'):s.index('extern "C" JNIEXPORT jlong JNICALL\nJava_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_normalizeRawDirect')]
        assert spatial.count('Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_demosaic')==2
        cp=build/'native_baseline.cpp'; so=build/'native_baseline.so'
        cp.write_text(PREAMBLE+'\n'+helpers+'\n'+spatial+FOOTER)
        subprocess.run(['g++','-std=c++17','-O2','-fno-fast-math','-fPIC','-shared','-pthread',str(cp),'-o',str(so)],check=True)
        self.lib=C.CDLL(str(so),mode=C.RTLD_LOCAL)
        self.lib.replay.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,C.c_float,C.c_float,C.c_void_p,C.c_int]
        self.lib.replay.restype=C.c_int
        self.source_sha256=h

    def render(self,raw,nr,nb,cfa=0,workers=4):
        raw=np.ascontiguousarray(raw,dtype=np.uint16); h,w=raw.shape
        out=np.empty((h,w,3),np.uint16)
        rc=self.lib.replay(raw.ctypes.data,w,h,cfa,0,0,nr,nb,out.ctypes.data,workers)
        if rc: raise RuntimeError(('native replay',rc))
        return out

def current_uncertainty(probe, raw, cfa, nr, nb):
    return probe.stages(raw,cfa,nr,nb,shrink=False)[3].astype(np.int64)

def ha_difference(raw,cfa,nr,nb,uncertainty,clamp_guide=True,shrink=True):
    z=q14(raw).astype(np.int64); h,w=z.shape
    red,blue,green=cfa_masks(z.shape,cfa)
    diff=np.zeros((h,w),np.int64)
    guide=np.zeros((h,w),np.int64)
    guide[green]=z[green]
    for y in range(2,h-2):
        for x in range(2,w-2):
            if green[y,x]: continue
            nc=nr if red[y,x] else nb
            c0=z[y,x]/nc
            l2=z[y,x-2]/nc; r2=z[y,x+2]/nc
            u2=z[y-2,x]/nc; d2=z[y+2,x]/nc
            gl=float(z[y,x-1]); gr=float(z[y,x+1])
            gu=float(z[y-1,x]); gd=float(z[y+1,x])
            gh=.5*(gl+gr)+.25*(2*c0-l2-r2)
            gv=.5*(gu+gd)+.25*(2*c0-u2-d2)
            dh=abs(gl-gr)+abs(2*c0-l2-r2)
            dv=abs(gu-gd)+abs(2*c0-u2-d2)
            if dh<dv: g=gh
            elif dv<dh: g=gv
            else: g=.5*(gh+gv)
            if clamp_guide:
                g=min(max(g,min(gl,gr,gu,gd)),max(gl,gr,gu,gd))
            gi=int(np.floor(g+.5)); guide[y,x]=gi
            d=int(np.floor(c0+.5))-gi
            a=int(uncertainty[y,x])
            if shrink and abs(d)<a:
                v=max(abs(d)-(a>>2),0); d=-v if d<0 else v
            diff[y,x]=d
    return diff,guide

def diagonal_carrier(diff,cfa):
    h,w=diff.shape; out=np.zeros((h,w),np.int64)
    red,blue,green=cfa_masks(diff.shape,cfa)
    for y in range(3,h-3):
        for x in range(3,w-3):
            if green[y,x]: continue
            out[y,x]=(int(diff[y-1,x-1])+int(diff[y-1,x+1])+int(diff[y+1,x-1])+int(diff[y+1,x+1]))//4
    return out.astype(np.int32)

VARIANTS=(
    'ha_clamp_shrink_diag','ha_clamp_noshrink_diag',
    'ha_free_shrink_diag','ha_free_noshrink_diag',
    'ha_clamp_shrink_direct','ha_clamp_noshrink_direct'
)

def candidates(probe,raw,base,cfa,nr,nb):
    uncertainty=current_uncertainty(probe,raw,cfa,nr,nb)
    cache={}
    for clamp in (True,False):
        for shrink in (True,False):
            d,g=ha_difference(raw,cfa,nr,nb,uncertainty,clamp,shrink)
            cache[(clamp,shrink)]=(d,g)
    for name in VARIANTS:
        clamp='clamp' in name; shrink='noshrink' not in name; direct='direct' in name
        d,g=cache[(clamp,shrink)]
        carrier=d.astype(np.int32) if direct else diagonal_carrier(d,cfa)
        cam=probe.consume(carrier,base,cfa,nr,nb)
        yield name,cam,g

def restored(cam,scale,n):
    return np.clip(cam.astype(float)/65535*scale/np.asarray(n),0,1)

def synthetic(native,probe,cfas):
    yy,xx=np.indices((160,192)); n=np.array([.41796875,1.,.6435546875]); scale=1.6105431518598052
    rows=[]
    for cfa in cfas:
        red,blue,_=cfa_masks(xx.shape,cfa)
        for shape in ('edge','fine_branches'):
            coord=xx+yy*.43; mask=coord>120 if shape=='edge' else coord%15<4
            for sigma in (0.,.5,1.,2.):
                for bgname,bg in BACKGROUNDS.items():
                    for subject,fg in SUBJECTS.items():
                        scene=np.where(mask[...,None],fg,bg).astype(float)
                        if sigma: scene=gaussian_filter(scene,[sigma,sigma,0])
                        observed=np.minimum(scene*n,1.)
                        samples=np.where(red,observed[...,0],np.where(blue,observed[...,2],observed[...,1]))
                        sensor=np.floor(64+samples*959+.5).astype(np.uint16)
                        norm=np.floor((sensor.astype(float)-64)/959/scale*65535+.5).astype(np.uint16)
                        base=native.render(norm,n[0],n[2],cfa)
                        dcam=probe.consume(probe.stages(norm,cfa,n[0],n[2],shrink=True)[2],base,cfa,n[0],n[2])
                        clipped=np.clip(scene,0,1); truth=clipped[16:-16,16:-16]
                        sg=base[...,1].astype(float)/65535*scale
                        fixed=np.clip(clipped-clipped[...,[1]]+sg[...,None],0,1)[16:-16,16:-16]
                        cams={'D':dcam}; guides={}
                        for name,cam,g in candidates(probe,norm,base,cfa,n[0],n[2]):
                            cams[name]=cam; guides[name]=g
                        row=dict(cfa=cfa,shape=shape,sigma=sigma,background=bgname,subject=subject,metrics={})
                        for name,cam in cams.items():
                            z=restored(cam,scale,n)[16:-16,16:-16]
                            d=z[...,[0,2]]-z[...,[1]]
                            pink=(d[...,0]>.02)&(d[...,1]>.02)
                            row['metrics'][name]=dict(
                                scene_rgb_rms=float(np.sqrt(np.mean((z-truth)**2))),
                                fixed_green_rb_rms=float(np.sqrt(np.mean((z[...,[0,2]]-fixed[...,[0,2]])**2))),
                                pink_fraction=float(pink.mean()))
                        rows.append(row)
        print('CFA',cfa,'cases',len(rows),flush=True)
    summary={}
    for mode in VARIANTS:
        summary[mode]={}
        for metric in ('scene_rgb_rms','fixed_green_rb_rms'):
            delta=np.array([r['metrics'][mode][metric]-r['metrics']['D'][metric] for r in rows])
            summary[mode][metric]=dict(cases_worse_than_D=int((delta>1e-12).sum()),
                max_rms_increase=float(delta.max()),mean_rms_change=float(delta.mean()),
                worst_case_index=int(delta.argmax()))
        neutral=[r for r in rows if r['subject']=='neutral']
        d=np.array([r['metrics']['D']['pink_fraction'] for r in neutral])
        c=np.array([r['metrics'][mode]['pink_fraction'] for r in neutral])
        summary[mode]['neutral_false_pink']=dict(
            cases_improved=int((c<d-1e-15).sum()),cases_worse=int((c>d+1e-15).sum()),
            mean_D=float(d.mean()),mean_candidate=float(c.mean()),
            max_D=float(d.max()),max_candidate=float(c.max()))
    return dict(schema='m9.detail1i.green_guide_probe.v1',case_count=len(rows),cfas=cfas,
        neutral=n.tolist(),representation_scale=scale,backgrounds=BACKGROUNDS,subjects=SUBJECTS,
        variants=list(VARIANTS),summary=summary,cases=rows,
        scope='Synthetic camera-domain falsification only. Final native green/Sharp fixed; no exposure/colour/JPEG mutation. HA guide is temporary R/B difference guidance, not recovered Leica firmware.')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--assembled',type=Path,required=True); ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--cfas',type=int,nargs='+',default=[0])
    a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True); repo=Path(__file__).resolve().parents[2]
    native=NativeBaseline(repo,a.assembled,a.out/'native'); probe=DomainProbe(a.out/'native')
    result=synthetic(native,probe,a.cfas)
    result['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['native_source_sha256']=native.source_sha256
    cases=result.pop('cases')
    (a.out/'report.json').write_text(json.dumps(result,indent=2)[:-2]+',\n  "cases": [\n'+',\n'.join('    '+json.dumps(r) for r in cases)+'\n  ]\n}\n')
    print(json.dumps(result['summary'],indent=2))

if __name__=='__main__': main()
