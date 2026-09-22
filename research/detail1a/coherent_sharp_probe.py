"""M9DETAIL1N: make Leica Sharp chroma-coherent by construction.

The exact frozen GL2G native demosaic is compiled twice: current fixed ISO160
Sharp and an otherwise identical build with the Sharp correction set to zero.
The exact sharpened-green delta is then propagated to R/G/B in camera-neutral
coordinates:

    deltaG = G_sharp - G_unsharp
    Rn' = Rn + deltaG
    G'  = G  + deltaG
    Bn' = Bn + deltaG

R/B are restored to camera scaling afterward. This preserves the exact current
Sharp green plane while leaving normalized colour differences unchanged except
where quantization or physical channel clipping makes that impossible.

The same operation is tested both on the native MHC RGB foundation and after
the current DETAIL1D R/B reconstruction. Known scene false-magenta and
false-green excess are measured. Research only: no Android production/APK.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,json,subprocess
import numpy as np
from scipy.ndimage import gaussian_filter

from rb_domain import DomainProbe
from rb_probe import q14,q16
from green_guide2_probe import PREAMBLE,FOOTER,cfa_masks,BACKGROUNDS,SUBJECTS,restored

MODES=('base_nosharp','base_sharp_current','base_sharp_coherent',
       'D_nosharp','D_sharp_current','D_sharp_coherent')

class SharpPair:
    def __init__(self,repo,assembled,build):
        build.mkdir(parents=True,exist_ok=True)
        manifest=json.loads((repo/'patches/m9cam-m9livegl2g-manifest.json').read_text())
        rel='app/src/main/cpp/m9color_jni.cpp'
        raw=(assembled/rel).read_bytes();h=hashlib.sha256(raw).hexdigest()
        assert h==manifest['frozen'][rel],(h,manifest['frozen'][rel])
        s=raw.decode()
        helpers=s[s.index('inline int64_t clipl'):s.index('// SKYCHROMA1A diagnostic only')]
        spatial=s[s.index('// SHARPNESS_CLOSURETEST1A'):s.index('extern "C" JNIEXPORT jlong JNICALL\nJava_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_normalizeRawDirect')]
        assert spatial.count('Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_demosaic')==2
        old='''const int baseCorr=m9ClosureSlot0Coeff(1024+r);
            const int doubledCorr=baseCorr*2;
            const int corr=doubledCorr < -2048 ? -2048 : (doubledCorr > 2048 ? 2048 : doubledCorr);'''
        assert spatial.count(old)==1,'Sharp block changed'
        variants={'sharp':spatial,'nosharp':spatial.replace(old,'const int corr=0;')}
        self.libs={};self.source_sha256=h
        for name,body in variants.items():
            cp=build/(name+'.cpp');so=build/(name+'.so')
            cp.write_text(PREAMBLE+'\n'+helpers+'\n'+body+FOOTER)
            subprocess.run(['g++','-std=c++17','-O2','-fno-fast-math','-fPIC','-shared','-pthread',str(cp),'-o',str(so)],check=True)
            lib=C.CDLL(str(so),mode=C.RTLD_LOCAL)
            lib.replay.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,C.c_float,C.c_float,C.c_void_p,C.c_int]
            lib.replay.restype=C.c_int;self.libs[name]=lib
    def render(self,name,raw,nr,nb,cfa=0,workers=4):
        raw=np.ascontiguousarray(raw,dtype=np.uint16);h,w=raw.shape
        out=np.empty((h,w,3),np.uint16)
        rc=self.libs[name].replay(raw.ctypes.data,w,h,cfa,0,0,nr,nb,out.ctypes.data,workers)
        if rc:raise RuntimeError((name,'native replay',rc))
        return out

def coherent_sharp(cam_unsharp,base_unsharp,base_sharp,nr,nb):
    """Propagate the exact native Sharp green delta through neutralized RGB."""
    n=np.array([nr,1.,nb],np.float64)
    g0=q14(base_unsharp[...,1]).astype(np.int64)
    g1=q14(base_sharp[...,1]).astype(np.int64)
    delta=g1-g0
    src=q14(cam_unsharp).astype(np.float64)
    out=np.empty_like(cam_unsharp)
    clipped=np.zeros(cam_unsharp.shape[:2],bool)
    for ch in (0,2):
        normalized=src[...,ch]/n[ch]
        target=n[ch]*(normalized+delta)
        rounded=np.floor(target+.5)
        clipped |= (rounded<0)|(rounded>16383)
        out[...,ch]=q16(np.clip(rounded,0,16383).astype(np.int64))
    # Preserve the current Leica Sharp green plane byte-for-byte.
    out[...,1]=base_sharp[...,1]
    return out,delta,clipped

def colour_differences(cam,scale,n):
    z=restored(cam,scale,n)
    return np.stack([z[...,0]-z[...,1],z[...,2]-z[...,1]],axis=-1)

def metrics(cam,truth,scale,n):
    z=restored(cam,scale,n)[16:-16,16:-16]
    t=truth[16:-16,16:-16]
    rd=np.stack([z[...,0]-z[...,1],z[...,2]-z[...,1]],axis=-1)
    td=np.stack([t[...,0]-t[...,1],t[...,2]-t[...,1]],axis=-1)
    false_mag=(np.minimum(rd[...,0],rd[...,1])-np.minimum(td[...,0],td[...,1])>.02)
    rg=np.minimum(z[...,1]-z[...,0],z[...,1]-z[...,2])
    tg=np.minimum(t[...,1]-t[...,0],t[...,1]-t[...,2])
    false_green=(rg-tg>.02)
    return dict(scene_rgb_rms=float(np.sqrt(np.mean((z-t)**2))),
                chroma_rms=float(np.sqrt(np.mean((rd-td)**2))),
                false_magenta_excess_fraction=float(false_mag.mean()),
                false_green_excess_fraction=float(false_green.mean()))

def synthetic(native,probe,cfas):
    yy,xx=np.indices((160,192));n=np.array([.41796875,1.,.6435546875]);scale=1.6105431518598052
    rows=[]; green_exact=True
    for cfa in cfas:
        red,blue,_=cfa_masks(xx.shape,cfa)
        for shape in ('edge','fine_branches'):
            coord=xx+yy*.43;mask=coord>120 if shape=='edge' else coord%15<4
            for sigma in (0.,.5,1.,2.):
                for bgname,bg in BACKGROUNDS.items():
                    for subject,fg in SUBJECTS.items():
                        scene=np.where(mask[...,None],fg,bg).astype(np.float64)
                        if sigma:scene=gaussian_filter(scene,[sigma,sigma,0])
                        observed=np.minimum(scene*n,1.)
                        samples=np.where(red,observed[...,0],np.where(blue,observed[...,2],observed[...,1]))
                        sensor=np.floor(64+samples*959+.5).astype(np.uint16)
                        norm=np.floor((sensor.astype(np.float64)-64)/959/scale*65535+.5).astype(np.uint16)

                        base_no=native.render('nosharp',norm,n[0],n[2],cfa)
                        base_sh=native.render('sharp',norm,n[0],n[2],cfa)
                        carrier=probe.stages(norm,cfa,n[0],n[2],shrink=True)[2]
                        d_no=probe.consume(carrier,base_no,cfa,n[0],n[2])
                        d_sh=probe.consume(carrier,base_sh,cfa,n[0],n[2])

                        base_co,delta,clip_base=coherent_sharp(base_no,base_no,base_sh,n[0],n[2])
                        d_co,delta2,clip_d=coherent_sharp(d_no,base_no,base_sh,n[0],n[2])
                        assert np.array_equal(delta,delta2)
                        assert np.array_equal(base_co[...,1],base_sh[...,1])
                        assert np.array_equal(d_co[...,1],base_sh[...,1])
                        green_exact &= np.array_equal(base_co[...,1],base_sh[...,1]) and np.array_equal(d_co[...,1],base_sh[...,1])

                        truth=np.clip(scene,0,1)
                        cams={'base_nosharp':base_no,'base_sharp_current':base_sh,'base_sharp_coherent':base_co,
                              'D_nosharp':d_no,'D_sharp_current':d_sh,'D_sharp_coherent':d_co}
                        mm={k:metrics(v,truth,scale,n) for k,v in cams.items()}

                        # Measure how well coherent Sharp preserves the unsharp normalized chroma.
                        base_before=colour_differences(base_no,scale,n)
                        base_after=colour_differences(base_co,scale,n)
                        d_before=colour_differences(d_no,scale,n)
                        d_after=colour_differences(d_co,scale,n)
                        inner=np.s_[16:-16,16:-16]
                        base_chroma_delta=np.abs(base_after[inner]-base_before[inner])
                        d_chroma_delta=np.abs(d_after[inner]-d_before[inner])

                        rows.append(dict(cfa=cfa,shape=shape,sigma=sigma,background=bgname,subject=subject,
                            raw_clipped_fraction=float((sensor>=1023).mean()),
                            sharp_green_changed_fraction=float((delta[16:-16,16:-16]!=0).mean()),
                            sharp_green_mean_abs_q14=float(np.abs(delta[16:-16,16:-16]).mean()),
                            coherent_base_channel_clip_fraction=float(clip_base[16:-16,16:-16].mean()),
                            coherent_D_channel_clip_fraction=float(clip_d[16:-16,16:-16].mean()),
                            coherent_base_chroma_mean_abs_change=float(base_chroma_delta.mean()),
                            coherent_base_chroma_max_abs_change=float(base_chroma_delta.max()),
                            coherent_D_chroma_mean_abs_change=float(d_chroma_delta.mean()),
                            coherent_D_chroma_max_abs_change=float(d_chroma_delta.max()),
                            metrics=mm))
        print('CFA',cfa,'cases',len(rows),flush=True)

    comparisons={
      'current_sharp_native':('base_nosharp','base_sharp_current'),
      'coherent_sharp_native':('base_nosharp','base_sharp_coherent'),
      'current_sharp_D':('D_nosharp','D_sharp_current'),
      'coherent_sharp_D':('D_nosharp','D_sharp_coherent'),
      'coherent_vs_current_native':('base_sharp_current','base_sharp_coherent'),
      'coherent_vs_current_D':('D_sharp_current','D_sharp_coherent'),
    }
    summary={}
    for label,(a,b) in comparisons.items():
        summary[label]={}
        for key in ('scene_rgb_rms','chroma_rms','false_magenta_excess_fraction','false_green_excess_fraction'):
            aa=np.array([r['metrics'][a][key] for r in rows]);bb=np.array([r['metrics'][b][key] for r in rows]);delta=bb-aa
            summary[label][key]=dict(cases_improved=int((delta<-1e-12).sum()),cases_worse=int((delta>1e-12).sum()),
                mean_before=float(aa.mean()),mean_after=float(bb.mean()),mean_change=float(delta.mean()),
                max_increase=float(delta.max()),max_reduction=float((-delta).max()),
                worst_case_index=int(delta.argmax()),best_case_index=int(delta.argmin()))
        clipped=np.array([r['raw_clipped_fraction']>0 for r in rows]);neutral=np.array([r['subject']=='neutral' for r in rows])
        for subset,mask in [('clipped',clipped),('clipped_neutral',clipped&neutral),('unclipped',~clipped)]:
            if not mask.any():continue
            vals={}
            for key in ('false_magenta_excess_fraction','false_green_excess_fraction'):
                aa=np.array([r['metrics'][a][key] for r in rows])[mask];bb=np.array([r['metrics'][b][key] for r in rows])[mask]
                vals[key+'_mean_before']=float(aa.mean());vals[key+'_mean_after']=float(bb.mean())
                vals[key+'_cases_worse']=int((bb>aa+1e-12).sum())
            vals['case_count']=int(mask.sum());summary[label][subset]=vals

    preservation=dict(
        green_exact_current_sharp=bool(green_exact),
        mean_base_chroma_abs_change=float(np.mean([r['coherent_base_chroma_mean_abs_change'] for r in rows])),
        max_base_chroma_abs_change=float(max(r['coherent_base_chroma_max_abs_change'] for r in rows)),
        mean_D_chroma_abs_change=float(np.mean([r['coherent_D_chroma_mean_abs_change'] for r in rows])),
        max_D_chroma_abs_change=float(max(r['coherent_D_chroma_max_abs_change'] for r in rows)),
        mean_base_clip_fraction=float(np.mean([r['coherent_base_channel_clip_fraction'] for r in rows])),
        mean_D_clip_fraction=float(np.mean([r['coherent_D_channel_clip_fraction'] for r in rows])))
    return dict(schema='m9.detail1n.coherent_sharp.v1',case_count=len(rows),cfas=list(cfas),
        neutral=n.tolist(),representation_scale=scale,backgrounds=BACKGROUNDS,subjects=SUBJECTS,
        preservation=preservation,summary=summary,cases=rows,
        scope='Exact current ISO160 Sharp green delta; coherent propagation in camera-neutral coordinates. Exact Sharp green preserved. No hue/subject classifier, no exposure/colour/JPEG changes, no Android/APK mutation.')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--assembled',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--cfas',type=int,nargs='+',default=[0,1,2,3])
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);repo=Path(__file__).resolve().parents[2]
    native=SharpPair(repo,a.assembled,a.out/'native');probe=DomainProbe(a.out/'native')
    result=synthetic(native,probe,a.cfas)
    result['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['native_source_sha256']=native.source_sha256
    cases=result.pop('cases')
    (a.out/'report.json').write_text(json.dumps(result,indent=2)[:-2]+',\n  "cases": [\n'+',\n'.join('    '+json.dumps(r) for r in cases)+'\n  ]\n}\n')
    print(json.dumps(dict(preservation=result['preservation'],summary=result['summary']),indent=2))

if __name__=='__main__':main()
