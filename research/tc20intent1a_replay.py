#!/usr/bin/env python3
"""TC20INTENT1A offline replay harness.

Research-only. It does not modify Camera2, the Android renderer, colour science,
curve02, SAT3, TG1, JPEG quality, or DNGs.

It dynamically loads the authoritative frozen Python renderer supplied with
--renderer (m9render_v26r35_tc20_frozen.py), discovers DNGs recursively, finds
the matching _M9.json capture audit, and uses the achieved
captureEnergyVsPhotonOnlyEv as the only exposure-intent source.

Variants:
  A0       frozen TC20
  A1_010   full virtual TC20 measurement, max preserved intent 0.10 EV
  A1_020   full virtual TC20 measurement, max preserved intent 0.20 EV
  A1_030   full virtual TC20 measurement, max preserved intent 0.30 EV
  A2_020   same A1 0.20 gain, but defers the current pre-matrix per-channel
           RAW_MAX clamp until matrix/LUT indexing. This is a clipping-location
           experiment, not a production highlight policy.

Physical RAW median/tail/clipping remain separately logged in every variant.
"""
from __future__ import annotations
import argparse, csv, hashlib, importlib.util, json, math, random
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

CAPS=(0.0,0.10,0.20,0.30)


def load_renderer(path: Path):
    spec=importlib.util.spec_from_file_location('m9frozen', str(path))
    if spec is None or spec.loader is None: raise RuntimeError('cannot load renderer')
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def walk_key(x,key):
    if isinstance(x,dict):
        if key in x:
            try:return float(x[key])
            except Exception:pass
        for v in x.values():
            q=walk_key(v,key)
            if q is not None:return q
    elif isinstance(x,list):
        for v in x:
            q=walk_key(v,key)
            if q is not None:return q
    return None


def matching_json(dng:Path):
    stem=dng.stem
    candidates=list(dng.parent.glob(stem+'*_M9.json'))+list(dng.parent.glob(stem+'*.json'))
    for p in candidates:
        if p.name.endswith('_PRIMARY.json'):continue
        try:
            j=json.loads(p.read_text(errors='replace'))
        except Exception:continue
        ev=walk_key(j,'captureEnergyVsPhotonOnlyEv')
        if ev is not None:return p,j,ev
    return None,None,None


def weighted_median_y(m,y):
    h,w=y.shape; yy,xx=np.mgrid[0:h,0:w]
    r=np.sqrt(((yy-h/2)/(h/2))**2+((xx-w/2)/(w/2))**2)
    wg=np.exp(-(r**2)/(2*m.METER_CW**2)).ravel(); yf=y.ravel(); mask=yf>1e-5
    if not mask.any():return 0.0
    order=np.argsort(yf[mask]); ys=yf[mask][order]; ws=wg[mask][order]
    cu=np.cumsum(ws); return float(ys[np.searchsorted(cu,cu[-1]*.5)])


def gain_pack(m,y,rawm,baseline_ev,intent_ev,cap):
    physical_median=weighted_median_y(m,y)
    physical_tail=float(rawm['tc20_tail_value'])
    achieved=max(float(intent_ev),0.0); preserved=min(achieved,float(cap))
    k=2.0**preserved
    virtual_median=physical_median/k
    virtual_tail=physical_tail/k
    scale=2.0**baseline_ev
    base_physical=float(np.clip(m.METER_TARGET_RENORM/max(physical_median,1e-6),.5,16.0))*scale
    guard_physical=max(1.0,m.TC_HEADROOM_TARGET/max(physical_tail,1e-9))
    base_virtual=float(np.clip(m.METER_TARGET_RENORM/max(virtual_median,1e-6),.5,16.0))*scale
    guard_virtual=max(1.0,m.TC_HEADROOM_TARGET/max(virtual_tail,1e-9))
    gain_physical=float(min(base_physical,guard_physical))
    gain_virtual=float(min(base_virtual,guard_virtual))
    return dict(achievedIntentEv=achieved,preservedIntentEv=preserved,
        physicalMedian=physical_median,physicalTail=physical_tail,
        virtualMedian=virtual_median,virtualTail=virtual_tail,
        baseMedianGainPhysical=base_physical,guardGainPhysical=guard_physical,
        baseMedianGainVirtual=base_virtual,guardGainVirtual=guard_virtual,
        gainA0=gain_physical,gainCandidate=gain_virtual,
        gainDeltaVsA0Ev=math.log2(max(gain_virtual,1e-12)/max(gain_physical,1e-12)),
        physicalTailTimesGain=physical_tail*gain_virtual)


def m9_stage_metrics(m,post_wb_m9,gain,curve,sat,defer_clamp=False):
    scaled=post_wb_m9*gain*m.RAW_MAX
    pre_any=float(np.mean(np.any(scaled>m.RAW_MAX,axis=-1)))
    pre_all=float(np.mean(np.all(scaled>m.RAW_MAX,axis=-1)))
    if defer_clamp:
        x=np.rint(np.maximum(scaled,0)).astype(np.int64)
    else:
        x=np.clip(np.rint(scaled),0,m.RAW_MAX).astype(np.int64)
    flat=x.reshape(-1,3); mask=flat[:,0]>=flat[:,1]
    Qe,Qo=m.MATRIX_BANK[sat]; acc=np.empty_like(flat)
    acc[mask]=flat[mask]@Qe.T; acc[~mask]=flat[~mask]@Qo.T
    rawidx=acc>>16
    idx_hi=float(np.mean(np.any(rawidx>m.LUT_MAX,axis=1)))
    idx_lo=float(np.mean(np.any(rawidx<0,axis=1)))
    idx=np.clip(rawidx,0,m.LUT_MAX).astype(np.int32)
    rgb8=curve[idx].reshape(x.shape).astype(np.uint8)
    out=m.exact_fpga_422(rgb8)
    lum=.2126*out[...,0]+.7152*out[...,1]+.0722*out[...,2]
    h,w=lum.shape; cy0,cy1=int(.25*h),int(.75*h); cx0,cx1=int(.25*w),int(.75*w)
    return out,dict(preMatrixAnyChannelClipFraction=pre_any,
        preMatrixAllChannelClipFraction=pre_all,matrixIndexHighClipFraction=idx_hi,
        matrixIndexLowClipFraction=idx_lo,JPEGNearWhiteFraction=float(np.mean(lum>=250/255)),
        JPEGAllChannelWhiteFraction=float(np.mean(np.all(out>=254/255,axis=-1))),
        JPEGAnyChannelFullClipFraction=float(np.mean(np.any(out>=254/255,axis=-1))),
        renderGlobalMedian=float(np.median(lum)),
        renderCenterMedian=float(np.median(lum[cy0:cy1,cx0:cx1])),
        renderQ95=float(np.quantile(lum,.95)),renderQ99=float(np.quantile(lum,.99)),
        deepBlackFraction=float(np.mean(lum<=8/255)))


def contact(items,path,cols=4,W=360,H=280,T=30):
    rows=(len(items)+cols-1)//cols; sh=Image.new('RGB',(W*cols,(H+T)*rows),'white'); d=ImageDraw.Draw(sh)
    for i,(lab,p) in enumerate(items):
        im=Image.open(p).convert('RGB'); im.thumbnail((W-8,H-6),Image.Resampling.LANCZOS)
        x=(i%cols)*W; y=(i//cols)*(H+T); d.text((x+4,y+4),lab,fill='black'); sh.paste(im,(x+(W-im.width)//2,y+T))
    sh.save(path,quality=95,subsampling=0)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('root',type=Path,help='directory containing extracted test archives')
    ap.add_argument('--renderer',type=Path,required=True)
    ap.add_argument('--dcp',type=Path,required=True); ap.add_argument('--firmware',type=Path,required=True)
    ap.add_argument('--out',type=Path,default=Path('TC20INTENT1A_RESULTS'))
    ap.add_argument('--long-side',type=int,default=1600); ap.add_argument('--seed',type=int,default=920260904)
    a=ap.parse_args(); m=load_renderer(a.renderer); out=a.out; out.mkdir(parents=True,exist_ok=True)
    (out/'renders').mkdir(exist_ok=True); (out/'contacts').mkdir(exist_ok=True); (out/'metadata').mkdir(exist_ok=True)
    curve=m.extract_curve02(a.firmware); dcp=m.CobaltDCP(a.dcp); rows=[]; blind=[]
    dngs=sorted(a.root.rglob('*.dng'))
    for p in dngs:
        jp,j,ev=matching_json(p)
        if ev is None:continue
        cam,neutral,orientation,baseline,iso,rawm=m.read_dng(p,a.long_side)
        xy=dcp.neutral_to_xy(neutral); T=m.cct_from_xy(xy); wA=m.weight_A(T)
        xyz50=dcp.to_xyz50(cam,xy,wA); xyz_scene=xyz50@m.bradford(m.D50_XY,xy).T
        M9CM=m.interp(m.M9_CM_A,m.M9_CM_D65,wA); mcam=xyz_scene@M9CM.T
        mwhite=M9CM@m.xy_to_xyz(xy); m9=np.maximum(mcam/np.maximum(mwhite[None,None,:],1e-8),0.0)
        xyz65=xyz50@m.bradford(m.D50_XY,m.D65_XY).T; prox=xyz65@m.XYZ2SRGB.T
        y=np.maximum(.2126*prox[...,0]+.7152*prox[...,1]+.0722*prox[...,2],0)
        variants=[]
        for cap in CAPS:
            gp=gain_pack(m,y,rawm,baseline,ev,cap); name='A0' if cap==0 else f'A1_{int(round(cap*100)):03d}'
            gain=gp['gainA0'] if cap==0 else gp['gainCandidate']
            img,met=m9_stage_metrics(m,m9,gain,curve,3,False)
            pil=m.orient_image(Image.fromarray((img*255+.5).astype(np.uint8)),orientation)
            q=out/'renders'/f'{p.stem}_{name}.jpg'; pil.save(q,quality=95,subsampling=0)
            row={'file':p.name,'json':jp.name if jp else '', 'variant':name,'iso':iso,'cct':T,
                 'physicalHardClipFraction':rawm['raw_hard_clip_fraction'],**gp,**met}
            rows.append(row); variants.append((name,q))
        gp=gain_pack(m,y,rawm,baseline,ev,.20); img,met=m9_stage_metrics(m,m9,gp['gainCandidate'],curve,3,True)
        pil=m.orient_image(Image.fromarray((img*255+.5).astype(np.uint8)),orientation)
        q=out/'renders'/f'{p.stem}_A2_020.jpg'; pil.save(q,quality=95,subsampling=0)
        rows.append({'file':p.name,'json':jp.name if jp else '','variant':'A2_020','iso':iso,'cct':T,
                     'physicalHardClipFraction':rawm['raw_hard_clip_fraction'],**gp,**met})
        variants.append(('A2_020',q))
        rng=random.Random(a.seed+int(hashlib.sha1(p.name.encode()).hexdigest()[:8],16)); rng.shuffle(variants)
        labels=['P','Q','R','S','T']; coded=[]
        for lab,(true,q) in zip(labels,variants): coded.append((lab,q)); blind.append({'file':p.name,'blind':lab,'variant':true})
        contact(coded,out/'contacts'/f'{p.stem}_blind.jpg',cols=5)
        print('done',p.name,'actualIntent',round(ev,3),'clip%',round(100*rawm['raw_hard_clip_fraction'],3),flush=True)
    if not rows: raise SystemExit('No matching DNG + _M9.json captureEnergyVsPhotonOnlyEv records found')
    with (out/'metadata'/'tc20intent1a_metrics.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with (out/'metadata'/'blind_key.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['file','blind','variant']);w.writeheader();w.writerows(blind)
    manifest={'schema':'m9cam.tc20intent1a.offline.v1','researchOnly':True,'dngCount':len({r['file'] for r in rows}),
      'variants':['A0','A1_010','A1_020','A1_030','A2_020'],
      'intentSource':'captureEnergyVsPhotonOnlyEv from matching _M9.json',
      'preservedIntent':'min(max(actualAchievedEv,0),testCap)',
      'A1':'virtual median and virtual physical-derived TC20 tail; physical RAW safety telemetry retained',
      'A2':'A1_020 gain plus deferred pre-matrix RAW_MAX clamp; research clipping-location probe only',
      'frozen':'Cobalt/HSM, M9 bridge, SAT3 M06/M07, curve02, exact BT601, JPEG95, DNG pixels'}
    (out/'metadata'/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print('CREATED',out)

if __name__=='__main__':main()
