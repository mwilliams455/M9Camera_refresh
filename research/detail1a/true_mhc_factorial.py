"""Corrected W: true internal MHC control, no-Sharp 2x2x2 factorial.

Original W's no-Sharp output still contained SHARPSOURCE1C green replacement.
This probe bypasses that replacement in both native Bayer entry points and
checks every RGB sample against a direct call to the frozen internal MHC.
Axes: difference guide D/MHC; interpolation Cross/Direct; output green Leica/MHC.
Co shrink and its original uncertainty are held fixed, Noise2 is absent.
No Android/app mutation. W helper arithmetic retained for result comparability.
"""
AUDIT_FOOTER = r'''
extern "C" void internal_mhc(const uint16_t* src,int w,int h,int cfa,float r,float b,uint16_t* out){
    const jshort* raw=reinterpret_cast<const jshort*>(src);
    const double nr=r,nb=b,ir=1.0/nr,ib=1.0/nb;
    for(int y=0;y<h;++y)for(int x=0;x<w;++x){
        uint16_t* p=out+3*(y*w+x);
        if(cfa==0){
            const auto g=mhcNeutralGreenRggb(raw,w,h,y,x,ir,ib);
            mhcPixelNeutralRbCompleteRggb(raw,w,h,y,x,g,p,nr,nb,ir,ib);
        }else{
            const auto g=mhcNeutralGreenBayerPhase(raw,w,h,y,x,ir,ib,cfa&1,cfa>>1);
            mhcPixelNeutralRbCompleteBayerPhase(raw,w,h,y,x,g,p,nr,nb,ir,ib,cfa&1,cfa>>1);
        }
    }
}
'''
from pathlib import Path
import argparse,ctypes as C,hashlib,json,subprocess
import numpy as np
from scipy.ndimage import gaussian_filter

from green_guide2_probe import PREAMBLE,FOOTER,cfa_masks,BACKGROUNDS,SUBJECTS,restored
from rb_domain import DomainProbe

BASE='gD_iCross_oLeica'
METRICS=('scene_rgb_rms','chroma_rms','false_magenta_excess_fraction','false_green_excess_fraction')

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

class NativePair:
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
        assert spatial.count('Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_demosaic')==2
        old='''const int baseCorr=m9ClosureSlot0Coeff(1024+r);
            const int doubledCorr=baseCorr*2;
            const int corr=doubledCorr < -2048 ? -2048 : (doubledCorr > 2048 ? 2048 : doubledCorr);'''
        assert spatial.count(old)==1,'native Sharp block changed'
        no=spatial.replace(old,'const int corr=0;')
        import re
        true,count=re.subn(r'if\(x>=9\s*&&\s*x<width-9\s*&&\s*y>=9\s*&&\s*y<height-9\)\{',
                           'if(false){ // audit: return internal MHC RGB before Leica replacement',no)
        assert count==2,('expected both frozen Bayer entry points',count)
        variants={'sharp':spatial,'nosharp':no,'true_mhc':true}
        self.libs={};self.source_sha256=h
        for name,body in variants.items():
            cp=build/(name+'.cpp');so=build/(name+'.so')
            cp.write_text(PREAMBLE+'\n'+helpers+'\n'+body+FOOTER+AUDIT_FOOTER)
            subprocess.run(['g++','-std=c++17','-O2','-fno-fast-math','-fPIC','-shared','-pthread',
                            str(cp),'-o',str(so)],check=True)
            lib=C.CDLL(str(so),mode=C.RTLD_LOCAL)
            lib.replay.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,
                                 C.c_float,C.c_float,C.c_void_p,C.c_int]
            lib.replay.restype=C.c_int
            lib.internal_mhc.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_float,C.c_float,C.c_void_p]
            self.libs[name]=lib

    def render(self,name,raw,nr,nb,cfa=0,workers=4):
        raw=np.ascontiguousarray(raw,dtype=np.uint16);h,w=raw.shape
        out=np.empty((h,w,3),np.uint16)
        rc=self.libs[name].replay(raw.ctypes.data,w,h,cfa,0,0,nr,nb,out.ctypes.data,workers)
        if rc:raise RuntimeError((name,'native replay',rc))
        return out

def shrink_co(d,a):
    d=np.asarray(d,np.int64);a=np.asarray(a,np.int64)
    mag=np.abs(d)
    v=np.maximum(mag-(a>>2),0)
    return np.where(mag<a,np.where(d<0,-v,v),d)

def guide_diff(norm,cfa,nr,nb,guide,uncertainty):
    z=q14(norm)
    red,blue,green=cfa_masks(norm.shape,cfa)
    nc=np.where(red,nr,np.where(blue,nb,1.))
    rawc=llround(z.astype(np.float64)/nc)
    d=rawc-np.asarray(guide,np.int64)
    d=shrink_co(d,uncertainty)
    valid=red|blue
    valid[:2]=False;valid[-2:]=False;valid[:,:2]=False;valid[:,-2:]=False
    return np.where(valid,d,0).astype(np.int32)

def diagonal_carrier(diff,cfa):
    d=np.asarray(diff,np.int64)
    red,blue,green=cfa_masks(diff.shape,cfa)
    total=(np.roll(np.roll(d,1,0),1,1)+np.roll(np.roll(d,1,0),-1,1)+
           np.roll(np.roll(d,-1,0),1,1)+np.roll(np.roll(d,-1,0),-1,1))
    ca=total//4
    valid=(red|blue)
    valid[:3]=False;valid[-3:]=False;valid[:,:3]=False;valid[:,-3:]=False
    return np.where(valid,ca,0).astype(np.int32)

def direct_field(diff,py,px):
    """Signed-floor separable 2x Bayer-phase bilinear interpolation."""
    d=np.asarray(diff,np.int64);h,w=d.shape
    row=np.zeros((h,w),np.int64)
    ys=np.arange(h)[:,None];xs=np.arange(w)[None,:]
    phase_row=(ys&1)==py
    phase_col=(xs&1)==px
    exact=phase_row&phase_col
    row[exact]=d[exact]
    # Horizontal half positions are only meaningful on the native phase rows.
    mid=phase_row&~phase_col
    left=np.roll(d,1,1);right=np.roll(d,-1,1)
    hv=floor2(left+right)
    row[mid]=hv[mid]
    # Then vertical interpolation between completed native rows.
    out=row.copy()
    vm=~phase_row
    up=np.roll(row,1,0);down=np.roll(row,-1,0)
    vv=floor2(up+down)
    out[vm.repeat(w,axis=1)]=vv[vm.repeat(w,axis=1)]
    out[:2]=0;out[-2:]=0;out[:,:2]=0;out[:,-2:]=0
    return out

def direct_consume(diff,base,cfa,nr,nb):
    h,w=diff.shape
    ry=int(cfa in (2,3));rx=int(cfa in (1,3))
    red_field=direct_field(diff,ry,rx)
    blue_field=direct_field(diff,1-ry,1-rx)
    sg=q14(base[...,1])
    out=np.array(base,copy=True)
    r=llround(nr*(sg+red_field))
    b=llround(nb*(sg+blue_field))
    out[...,0]=q16(r);out[...,2]=q16(b)
    # Match current consumer's untouched perimeter.
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

def controls(native,probe):
    rng=np.random.default_rng(9222026)
    ncases=nsamples=0
    for cfa in range(4):
        for shape in [(33,35),(64,70)]:
            raw=rng.integers(0,65536,shape,dtype=np.uint16)
            for nr,nb in [(1.,1.),(.41796875,.6435546875)]:
                got=native.render('true_mhc',raw,nr,nb,cfa)
                expected=np.empty_like(got)
                native.libs['true_mhc'].internal_mhc(raw.ctypes.data,shape[1],shape[0],cfa,nr,nb,expected.ctypes.data)
                assert np.array_equal(got,expected),'bypass does not return internal MHC RGB'
                red,blue,green=cfa_masks(shape,cfa)
                for ch,mask in enumerate((red,green,blue)):
                    assert np.array_equal(got[...,ch][mask],raw[mask]),('measured samples',cfa,ch)
                assert np.array_equal(got,native.render('true_mhc',raw,nr,nb,cfa,workers=1))
                ncases+=1;nsamples+=got.size
        # Stable-colour check includes legitimate magenta/green/red/blue.
        for rgb in [(4000,4000,4000),(9000,2000,9000),(1000,8000,1000),(9000,2000,1000),(1000,2000,9000)]:
            red,blue,_=cfa_masks((40,44),cfa)
            raw=q16(np.where(red,rgb[0],np.where(blue,rgb[2],rgb[1])))
            cams,_,_=variants(native,probe,raw,cfa,.41796875,.6435546875)
            for name,cam in cams.items():
                if name in ('MHC_reanchored_Leica','D_sharp_ref'):continue
                delta=np.abs(q14(cam)[16:-16,16:-16]-np.array(rgb))
                assert delta.max()<=1,('flat colour',cfa,name,rgb,int(delta.max()))
    return dict(internal_mhc_rgb_exact_cases=ncases,internal_mhc_rgb_exact_samples=nsamples,
                measured_cfa_samples_preserved=True,one_four_workers_exact=True,
                five_flat_colours_all_four_cfas_all_candidates=True)

def variants(native,probe,norm,cfa,nr,nb,include_sharp=True):
    leica=native.render('nosharp',norm,nr,nb,cfa)
    mhc=native.render('true_mhc',norm,nr,nb,cfa)
    gd,dd,current,unc=probe.stages(norm,cfa,nr,nb,shrink=True)
    gm=q14(mhc[...,1])
    # Keep the base and untouched perimeter identical for every factorial cell.
    out_m=leica.copy();out_m[10:-10,10:-10,1]=mhc[10:-10,10:-10,1]
    bases={'Leica':leica,'MHC':out_m}
    dm=guide_diff(norm,cfa,nr,nb,gm,unc)
    assert np.array_equal(guide_diff(norm,cfa,nr,nb,gd,unc),dd),'D difference parity'
    assert np.array_equal(diagonal_carrier(dd,cfa),current),'D carrier parity'
    cams={}
    for guide,diff,carrier in [('D',dd,current),('M',dm,diagonal_carrier(dm,cfa))]:
        for output,base in bases.items():
            cams[f'g{guide}_iCross_o{output}']=probe.consume(carrier,base,cfa,nr,nb)
            cams[f'g{guide}_iDirect_o{output}']=direct_consume(diff,base,cfa,nr,nb)
    assert np.array_equal(cams[BASE],probe.consume(current,leica,cfa,nr,nb))
    # Explicitly reproduce and expose W's invalid green control.
    assert np.array_equal(q14(leica[...,1])[16:-16,16:-16],gd[16:-16,16:-16])
    cams['MHC_rgb']=mhc;cams['MHC_reanchored_Leica']=leica
    if include_sharp:
        cams['D_sharp_ref']=probe.consume(current,native.render('sharp',norm,nr,nb,cfa),cfa,nr,nb)
    red,blue,_=cfa_masks(norm.shape,cfa)
    rb=(red|blue)[16:-16,16:-16]
    delta=(gm-gd)[16:-16,16:-16][rb]
    diagnostic=dict(actual_MHC_vs_D_changed=int(np.count_nonzero(delta)),rb_sites=int(rb.sum()),
                    actual_MHC_vs_D_mean_abs_q14=float(np.abs(delta).mean()),
                    actual_MHC_vs_D_max_abs_q14=int(np.abs(delta).max()),
                    W_guide_vs_D_changed=0)
    return cams,diagnostic,(gd,gm)

def comparison(rows,ref,candidate,mask=None):
    subset=rows if mask is None else [r for r in rows if mask(r)]
    report={'case_count':len(subset)}
    for key in METRICS:
        a=np.array([r['metrics'][ref][key] for r in subset])
        b=np.array([r['metrics'][candidate][key] for r in subset]);d=b-a
        report[key]=dict(cases_improved=int((d < -1e-12).sum()),cases_worse=int((d > 1e-12).sum()),
            mean_reference=float(a.mean()),mean_candidate=float(b.mean()),mean_change=float(d.mean()),
            max_increase=float(d.max()),max_reduction=float(-d.min()))
    return report

def summarize(rows):
    names=list(rows[0]['metrics'])
    summary={name:{'all':comparison(rows,BASE,name),
                   'unclipped':comparison(rows,BASE,name,lambda r:r['raw_clipped_fraction']==0),
                   'clipped':comparison(rows,BASE,name,lambda r:r['raw_clipped_fraction']>0)}
             for name in names}
    contrasts={}
    for i in ('Cross','Direct'):
        for o in ('Leica','MHC'):
            contrasts[f'guide_at_{i}_{o}']=comparison(rows,f'gD_i{i}_o{o}',f'gM_i{i}_o{o}')
    for g in ('D','M'):
        for o in ('Leica','MHC'):
            contrasts[f'interpolation_at_{g}_{o}']=comparison(rows,f'g{g}_iCross_o{o}',f'g{g}_iDirect_o{o}')
        for i in ('Cross','Direct'):
            contrasts[f'output_at_{g}_{i}']=comparison(rows,f'g{g}_i{i}_oLeica',f'g{g}_i{i}_oMHC')
    passers=[name for name in names if name!=BASE and all(summary[name]['all'][key]['cases_worse']==0
                for key in ('false_magenta_excess_fraction','false_green_excess_fraction'))]
    return summary,contrasts,passers

def synthetic(native,probe,cfas,out,w_report=None):
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
                        cams,audit,_=variants(native,probe,norm,cfa,n[0],n[2])
                        mm={k:metrics(v,np.clip(scene,0,1),scale,n) for k,v in cams.items()}
                        row=dict(cfa=cfa,shape=shape,sigma=sigma,background=bgname,subject=subject,
                                 raw_clipped_fraction=float((sensor>=1023).mean()),guide_audit=audit,metrics=mm)
                        if w_report is not None:
                            old=w_report['cases'][len(rows)]
                            for key in ('cfa','shape','sigma','background','subject'):assert old[key]==row[key]
                            for name,oldname in [(BASE,'D_nosharp'),('gD_iDirect_oLeica','Dguide_direct'),
                                                ('MHC_reanchored_Leica','MHC_nosharp'),('D_sharp_ref','D_sharp_ref')]:
                                for key in METRICS:assert abs(mm[name][key]-old['metrics'][oldname][key])<1e-14,(name,key)
                        rows.append(row)
        (out/'checkpoint.json').write_text(json.dumps(dict(cases_completed=len(rows),cfa_completed=cfa)))
        print('CFA',cfa,'cases',len(rows),flush=True)
    summary,contrasts,passers=summarize(rows)
    return dict(schema='m9.true_mhc.factorial.v1',case_count=len(rows),cfas=cfas,neutral=n.tolist(),
        representation_scale=scale,backgrounds=BACKGROUNDS,subjects=SUBJECTS,baseline=BASE,
        source_commit='9b6d9f41c00055fdf3ac30a3de0bb9d3531ce9cd',
        summary=summary,contrasts=contrasts,strict_zero_false_chroma_regression=passers,
        W_control_metrics_exact=w_report is not None,all_D_extraction_parity=True,
        scope='No Sharp in 8 factorial cells. Fixed D Co uncertainty/shrink; no Noise2. True MHC RGB is frozen neutral-aware internal demosaic before Leica replacement. Synthetic truth is clipped white-balanced linear camera RGB; not sRGB. Crop16 excludes border. No app changes.',cases=rows)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--assembled',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--w-report',type=Path);ap.add_argument('--cfas',type=int,nargs='+',default=[0,1,2,3])
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);repo=Path(__file__).resolve().parents[2]
    native=NativePair(repo,a.assembled,a.out/'native');probe=DomainProbe(a.out/'native')
    checks=controls(native,probe);print('Controls passed',checks,flush=True)
    result=synthetic(native,probe,a.cfas,a.out,json.loads(a.w_report.read_text()) if a.w_report else None)
    result.update(controls=checks,native_source_sha256=native.source_sha256,
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (a.out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASSERS',result['strict_zero_false_chroma_regression'],flush=True)

if __name__=='__main__':main()
