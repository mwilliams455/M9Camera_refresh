"""M9DETAIL1M: isolate Sharp from the R/B reconstruction colour fringe.

Compile the exact frozen GL2G native demosaic twice: current fixed ISO160 Leica
Sharp, and an otherwise identical build with the Sharp correction forced to zero.
Feed the same camera-neutral DETAIL1D R/B carrier into each base. This separates:

  base_sharp vs base_nosharp       -> Sharp effect in the native MHC foundation
  D_sharp vs D_nosharp             -> Sharp/reference interaction in D R/B
  D_sharp vs base_sharp            -> added D reconstruction effect with Sharp on

Known scene colour is retained, including genuine green/magenta. False-magenta
and false-green excess metrics measure only *added* chroma beyond that known
scene. Synthetic research only; no Android production source/APK change.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,json,subprocess
import numpy as np
from scipy.ndimage import gaussian_filter
from rb_domain import DomainProbe
from green_guide2_probe import PREAMBLE,FOOTER,cfa_masks,BACKGROUNDS,SUBJECTS,restored

MODES=('base_nosharp','base_sharp','D_nosharp','D_sharp')

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
        assert spatial.count(old)==1,'Sharp coefficient block changed'
        variants={
            'sharp':spatial,
            'nosharp':spatial.replace(old,'const int corr=0;')
        }
        self.libs={};self.source_sha256=h
        for name,body in variants.items():
            cp=build/(name+'.cpp');so=build/(name+'.so')
            cp.write_text(PREAMBLE+'\n'+helpers+'\n'+body+FOOTER)
            subprocess.run(['g++','-std=c++17','-O2','-fno-fast-math','-fPIC','-shared','-pthread',str(cp),'-o',str(so)],check=True)
            lib=C.CDLL(str(so),mode=C.RTLD_LOCAL)
            lib.replay.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,C.c_float,C.c_float,C.c_void_p,C.c_int]
            lib.replay.restype=C.c_int
            self.libs[name]=lib

    def render(self,name,raw,nr,nb,cfa=0,workers=4):
        raw=np.ascontiguousarray(raw,dtype=np.uint16);h,w=raw.shape
        out=np.empty((h,w,3),np.uint16)
        rc=self.libs[name].replay(raw.ctypes.data,w,h,cfa,0,0,nr,nb,out.ctypes.data,workers)
        if rc:raise RuntimeError((name,'native replay',rc))
        return out

def metrics(cam,truth,scale,n):
    z=restored(cam,scale,n)[16:-16,16:-16]
    t=truth[16:-16,16:-16]
    rd=np.stack([z[...,0]-z[...,1],z[...,2]-z[...,1]],axis=-1)
    td=np.stack([t[...,0]-t[...,1],t[...,2]-t[...,1]],axis=-1)
    false_mag=(np.minimum(rd[...,0],rd[...,1])-np.minimum(td[...,0],td[...,1])>.02)
    # Green excess is the opposite chroma polarity: G above both R and B.
    rg=np.minimum(z[...,1]-z[...,0],z[...,1]-z[...,2])
    tg=np.minimum(t[...,1]-t[...,0],t[...,1]-t[...,2])
    false_green=(rg-tg>.02)
    return dict(
        scene_rgb_rms=float(np.sqrt(np.mean((z-t)**2))),
        chroma_rms=float(np.sqrt(np.mean((rd-td)**2))),
        false_magenta_excess_fraction=float(false_mag.mean()),
        false_green_excess_fraction=float(false_green.mean()))

def synthetic(native,probe,cfas):
    yy,xx=np.indices((160,192));n=np.array([.41796875,1.,.6435546875]);scale=1.6105431518598052
    rows=[]
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
                        # Sharp must only alter the interior and must leave constant scenes exact.
                        carrier=probe.stages(norm,cfa,n[0],n[2],shrink=True)[2]
                        d_no=probe.consume(carrier,base_no,cfa,n[0],n[2])
                        d_sh=probe.consume(carrier,base_sh,cfa,n[0],n[2])
                        truth=np.clip(scene,0,1)
                        mm={
                            'base_nosharp':metrics(base_no,truth,scale,n),
                            'base_sharp':metrics(base_sh,truth,scale,n),
                            'D_nosharp':metrics(d_no,truth,scale,n),
                            'D_sharp':metrics(d_sh,truth,scale,n),
                        }
                        gdelta=(base_sh[...,1].astype(np.int32)-base_no[...,1].astype(np.int32))[16:-16,16:-16]
                        rows.append(dict(cfa=cfa,shape=shape,sigma=sigma,background=bgname,subject=subject,
                            raw_clipped_fraction=float((sensor>=1023).mean()),
                            sharp_green_changed_fraction=float((gdelta!=0).mean()),
                            sharp_green_mean_abs_codes=float(np.abs(gdelta).mean()),
                            metrics=mm))
        print('CFA',cfa,'cases',len(rows),flush=True)
    summary={}
    pairs={
      'sharp_native_effect':('base_nosharp','base_sharp'),
      'sharp_D_effect':('D_nosharp','D_sharp'),
      'D_added_with_sharp':('base_sharp','D_sharp'),
      'D_added_without_sharp':('base_nosharp','D_nosharp'),
    }
    for label,(a,b) in pairs.items():
        summary[label]={}
        for key in ('scene_rgb_rms','chroma_rms','false_magenta_excess_fraction','false_green_excess_fraction'):
            aa=np.array([r['metrics'][a][key] for r in rows]);bb=np.array([r['metrics'][b][key] for r in rows]);delta=bb-aa
            summary[label][key]=dict(cases_improved=int((delta<-1e-12).sum()),cases_worse=int((delta>1e-12).sum()),
                mean_before=float(aa.mean()),mean_after=float(bb.mean()),mean_change=float(delta.mean()),
                max_increase=float(delta.max()),max_reduction=float((-delta).max()),
                worst_case_index=int(delta.argmax()),best_case_index=int(delta.argmin()))
        clipped=np.array([r['raw_clipped_fraction']>0 for r in rows])
        neutral=np.array([r['subject']=='neutral' for r in rows])
        for subset,mask in [('clipped',clipped),('clipped_neutral',clipped&neutral),('unclipped',~clipped)]:
            if not mask.any():continue
            aa=np.array([r['metrics'][a]['false_magenta_excess_fraction'] for r in rows])[mask]
            bb=np.array([r['metrics'][b]['false_magenta_excess_fraction'] for r in rows])[mask]
            gg0=np.array([r['metrics'][a]['false_green_excess_fraction'] for r in rows])[mask]
            gg1=np.array([r['metrics'][b]['false_green_excess_fraction'] for r in rows])[mask]
            summary[label][subset]=dict(
                case_count=int(mask.sum()),
                false_magenta_mean_before=float(aa.mean()),false_magenta_mean_after=float(bb.mean()),
                false_magenta_cases_worse=int((bb>aa+1e-12).sum()),
                false_green_mean_before=float(gg0.mean()),false_green_mean_after=float(gg1.mean()),
                false_green_cases_worse=int((gg1>gg0+1e-12).sum()))
    return dict(schema='m9.detail1m.sharp_chroma_boundary.v1',case_count=len(rows),cfas=list(cfas),
        neutral=n.tolist(),representation_scale=scale,backgrounds=BACKGROUNDS,subjects=SUBJECTS,
        summary=summary,cases=rows,
        scope='Exact frozen native demosaic compiled twice; only Sharp correction differs (current ISO160 vs corr=0). Same D carrier fed to both. Known scene colour metrics; no hue/subject correction and no Android/APK mutation.')

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
    print(json.dumps(result['summary'],indent=2))

if __name__=='__main__':main()
