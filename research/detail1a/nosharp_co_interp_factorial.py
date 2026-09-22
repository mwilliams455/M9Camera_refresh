"""M9DETAIL2B: no-Sharp 2x2 factorial of Co shrink and R/B interpolation.

Sharp is disabled. The exact same DETAIL1D green guide and native no-Sharp final
green are used everywhere.

Axes:
  producer:
    shrink   = recovered Co=2 uncertainty shrink
    noshrink = raw camera-neutral C-G anchor differences
  interpolation:
    D      = recovered opposite-phase diagonal carrier + D consumer
    direct = same-phase separable interpolation directly from native C-G anchors

Controls include exact native no-Sharp MHC RGB. This isolates whether the green
bias seen in DETAIL1W direct interpolation comes from interpolation itself or
from applying Co shrink before that interpolation.

No Noise2, hue/subject/foliage classifier, Android change or APK.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,json,subprocess
import numpy as np
from scipy.ndimage import gaussian_filter

from green_guide2_probe import PREAMBLE,FOOTER,cfa_masks,BACKGROUNDS,SUBJECTS,restored
from rb_domain import DomainProbe

MODES=('MHC_nosharp','D_shrink','D_noshrink','direct_shrink','direct_noshrink')

def q14(v):
    a=np.asarray(v,dtype=np.uint64)
    return ((a*16383+32767)//65535).astype(np.int64)

def q16(v):
    a=np.clip(np.asarray(v,dtype=np.int64),0,16383)
    return ((a*65535+8191)//16383).astype(np.uint16)

def llround(a):
    a=np.asarray(a,np.float64)
    return np.where(a>=0,np.floor(a+.5),np.ceil(a-.5)).astype(np.int64)

def floor2(a):
    a=np.asarray(a,np.int64)
    return np.where(a>=0,a//2,-((-a+1)//2))

class NativeNoSharp:
    def __init__(self,repo,assembled,build):
        build.mkdir(parents=True,exist_ok=True)
        manifest=json.loads((repo/'patches/m9cam-m9livegl2g-manifest.json').read_text())
        rel='app/src/main/cpp/m9color_jni.cpp'
        raw=(assembled/rel).read_bytes();h=hashlib.sha256(raw).hexdigest()
        assert h==manifest['frozen'][rel],(h,manifest['frozen'][rel])
        s=raw.decode()
        helpers=s[s.index('inline int64_t clipl'):s.index('// SKYCHROMA1A diagnostic only')]
        spatial=s[s.index('// SHARPNESS_CLOSURETEST1A'):s.index(
            'extern "C" JNIEXPORT jlong JNICALL\nJava_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_normalizeRawDirect')]
        old='''const int baseCorr=m9ClosureSlot0Coeff(1024+r);
            const int doubledCorr=baseCorr*2;
            const int corr=doubledCorr < -2048 ? -2048 : (doubledCorr > 2048 ? 2048 : doubledCorr);'''
        assert spatial.count(old)==1
        body=spatial.replace(old,'const int corr=0;')
        cp=build/'nosharp.cpp';so=build/'nosharp.so'
        cp.write_text(PREAMBLE+'\n'+helpers+'\n'+body+FOOTER)
        subprocess.run(['g++','-std=c++17','-O2','-fno-fast-math','-fPIC','-shared','-pthread',
                        str(cp),'-o',str(so)],check=True)
        self.lib=C.CDLL(str(so),mode=C.RTLD_LOCAL)
        self.lib.replay.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,
                                  C.c_float,C.c_float,C.c_void_p,C.c_int]
        self.lib.replay.restype=C.c_int;self.source_sha256=h

    def render(self,raw,nr,nb,cfa=0,workers=4):
        raw=np.ascontiguousarray(raw,dtype=np.uint16);h,w=raw.shape
        out=np.empty((h,w,3),np.uint16)
        rc=self.lib.replay(raw.ctypes.data,w,h,cfa,0,0,nr,nb,out.ctypes.data,workers)
        if rc:raise RuntimeError(('native noSharp replay',rc))
        return out

def phase_field(src,py,px):
    a=np.asarray(src,np.int64);h,w=a.shape
    ys=np.arange(h)[:,None];xs=np.arange(w)[None,:]
    prow=(ys&1)==py;pcol=(xs&1)==px
    row=np.zeros((h,w),np.int64)
    exact=prow&pcol;row[exact]=a[exact]
    mid=prow&~pcol
    hv=floor2(np.roll(a,1,1)+np.roll(a,-1,1));row[mid]=hv[mid]
    out=row.copy()
    vm=(~prow).repeat(w,axis=1)
    vv=floor2(np.roll(row,1,0)+np.roll(row,-1,0));out[vm]=vv[vm]
    out[:2]=0;out[-2:]=0;out[:,:2]=0;out[:,-2:]=0
    return out

def direct_consume(diff,base,cfa,nr,nb):
    ry=int(cfa in (2,3));rx=int(cfa in (1,3))
    rf=phase_field(diff,ry,rx)
    bf=phase_field(diff,1-ry,1-rx)
    sg=q14(base[...,1])
    out=np.array(base,copy=True)
    out[...,0]=q16(llround(nr*(sg+rf)))
    out[...,2]=q16(llround(nb*(sg+bf)))
    out[:10]=base[:10];out[-10:]=base[-10:];out[:,:10]=base[:,:10];out[:,-10:]=base[:,-10:]
    assert np.array_equal(out[...,1],base[...,1])
    return out

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
    yy,xx=np.indices((160,192))
    n=np.array([.41796875,1.,.6435546875]);scale=1.6105431518598052
    rows=[];green_exact=True
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
                        norm=np.floor((sensor.astype(float)-64)/959/scale*65535+.5).astype(np.uint16)

                        base=native.render(norm,n[0],n[2],cfa)
                        g0,d0,c0,_=probe.stages(norm,cfa,n[0],n[2],shrink=False)
                        g1,d1,c1,_=probe.stages(norm,cfa,n[0],n[2],shrink=True)
                        assert np.array_equal(g0,g1)
                        d_sh=probe.consume(c1,base,cfa,n[0],n[2])
                        d_no=probe.consume(c0,base,cfa,n[0],n[2])
                        dir_sh=direct_consume(d1,base,cfa,n[0],n[2])
                        dir_no=direct_consume(d0,base,cfa,n[0],n[2])
                        for cam in (d_sh,d_no,dir_sh,dir_no):
                            green_exact &= np.array_equal(cam[...,1],base[...,1])
                        truth=np.clip(scene,0,1)
                        cams={'MHC_nosharp':base,'D_shrink':d_sh,'D_noshrink':d_no,
                              'direct_shrink':dir_sh,'direct_noshrink':dir_no}
                        mm={k:metrics(v,truth,scale,n) for k,v in cams.items()}
                        rows.append(dict(cfa=cfa,shape=shape,sigma=sigma,background=bgname,subject=subject,
                                         raw_clipped_fraction=float((sensor>=1023).mean()),metrics=mm))
        print('CFA',cfa,'cases',len(rows),flush=True)

    summary={}
    for mode in MODES:
        summary[mode]={}
        for ref in ('D_shrink','MHC_nosharp'):
            summary[mode][ref]={}
            for key in ('scene_rgb_rms','chroma_rms','false_magenta_excess_fraction','false_green_excess_fraction'):
                a=np.array([r['metrics'][ref][key] for r in rows]);b=np.array([r['metrics'][mode][key] for r in rows]);d=b-a
                summary[mode][ref][key]=dict(cases_improved=int((d<-1e-12).sum()),cases_worse=int((d>1e-12).sum()),
                    mean_reference=float(a.mean()),mean_candidate=float(b.mean()),mean_change=float(d.mean()),
                    max_increase=float(d.max()),max_reduction=float((-d).max()),
                    worst_case_index=int(d.argmax()),best_case_index=int(d.argmin()))
        clipped=np.array([r['raw_clipped_fraction']>0 for r in rows])
        neutral=np.array([r['subject']=='neutral' for r in rows])
        green=np.array([r['subject']=='green' for r in rows])
        mag=np.array([r['subject'] in ('magenta','bright_magenta') for r in rows])
        for subset,sel in [('clipped',clipped),('clipped_neutral',clipped&neutral),
                           ('clipped_green',clipped&green),('clipped_magenta',clipped&mag),('unclipped',~clipped)]:
            vals={'case_count':int(sel.sum())}
            for key in ('false_magenta_excess_fraction','false_green_excess_fraction'):
                vals[key]={m:float(np.mean([r['metrics'][m][key] for r in np.array(rows,dtype=object)[sel]]))
                           for m in MODES}
            summary[mode][subset]=vals

    contrasts={}
    for name,a,b in [
        ('Co_effect_D','D_noshrink','D_shrink'),
        ('Co_effect_direct','direct_noshrink','direct_shrink'),
        ('interp_effect_shrink','D_shrink','direct_shrink'),
        ('interp_effect_noshrink','D_noshrink','direct_noshrink')]:
        contrasts[name]={}
        for key in ('scene_rgb_rms','chroma_rms','false_magenta_excess_fraction','false_green_excess_fraction'):
            aa=np.array([r['metrics'][a][key] for r in rows]);bb=np.array([r['metrics'][b][key] for r in rows]);d=bb-aa
            contrasts[name][key]=dict(cases_improved=int((d<-1e-12).sum()),cases_worse=int((d>1e-12).sum()),
                mean_change=float(d.mean()),max_increase=float(d.max()),max_reduction=float((-d).max()))
    return dict(schema='m9.detail2b.nosharp_co_interp_factorial.v1',case_count=len(rows),cfas=list(cfas),
        neutral=n.tolist(),representation_scale=scale,green_exact=bool(green_exact),
        backgrounds=BACKGROUNDS,subjects=SUBJECTS,summary=summary,contrasts=contrasts,cases=rows,
        scope='Sharp/Noise2 disabled. Exact same no-Sharp base green. Factorial isolates Co=2 shrink versus D cross-phase or direct same-phase interpolation. No hue/subject classifier or APK mutation.')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--assembled',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--cfas',type=int,nargs='+',default=[0,1,2,3])
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    repo=Path(__file__).resolve().parents[2]
    native=NativeNoSharp(repo,a.assembled,a.out/'native');probe=DomainProbe(a.out/'native')
    result=synthetic(native,probe,a.cfas)
    result['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['native_source_sha256']=native.source_sha256
    cases=result.pop('cases')
    (a.out/'report.json').write_text(json.dumps(result,indent=2)[:-2]+',\n  "cases": [\n'+
        ',\n'.join('    '+json.dumps(r) for r in cases)+'\n  ]\n}\n')
    print(json.dumps(dict(green_exact=result['green_exact'],contrasts=result['contrasts'],summary=result['summary']),indent=2))

if __name__=='__main__':main()
