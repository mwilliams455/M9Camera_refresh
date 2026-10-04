#!/usr/bin/env python3
"""TC20PLACEMENTSTAGE1A offline matched-density stage probe.

Research-only. The purpose is to isolate *where* a density correction belongs,
not to choose a production strength.

For each RAW:
  S0_FROZEN    exact frozen TC20 + frozen M9 renderer
  S1_PRE       frozen TC20 gain reduced by TEST_HOLD_EV before RAW clamp/matrix/curve02
  S2_POSTCURVE frozen TC20 through matrix+curve02, then a global RGB-code scale
               is solved to match S1's final global luminance median
  S3_POSTLUMA  frozen TC20 through matrix+curve02, then only BT.601 luma Y is
               scaled (Cb/Cr unchanged) to match S1's final global median

S2/S3 are diagnostic stages, not production proposals. Frozen colour/tone math
is otherwise unchanged; outputs remain global (no local tone mapping).
"""
from __future__ import annotations
import argparse, csv, hashlib, importlib.util, json, math, random
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

TEST_HOLD_EV=-0.35
VARIANTS=('S0_FROZEN','S1_PRE','S2_POSTCURVE','S3_POSTLUMA')
PARITY_EPS=1e-9


def load_renderer(path:Path):
    spec=importlib.util.spec_from_file_location('m9frozen',str(path))
    if spec is None or spec.loader is None: raise RuntimeError('cannot load renderer')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def curve_rgb8(m,post_wb_m9,gain,curve,sat=3):
    scaled=post_wb_m9*gain*m.RAW_MAX
    rounded=np.rint(scaled)
    pre_any=float(np.mean(np.any(rounded>m.RAW_MAX,axis=-1)))
    pre_all=float(np.mean(np.all(rounded>m.RAW_MAX,axis=-1)))
    x=np.clip(rounded,0,m.RAW_MAX).astype(np.int64)
    flat=x.reshape(-1,3);mask=flat[:,0]>=flat[:,1]
    Qe,Qo=m.MATRIX_BANK[sat];acc=np.empty_like(flat)
    acc[mask]=flat[mask]@Qe.T;acc[~mask]=flat[~mask]@Qo.T
    rawidx=acc>>16
    idx_hi=float(np.mean(np.any(rawidx>m.LUT_MAX,axis=1)))
    idx_lo=float(np.mean(np.any(rawidx<0,axis=1)))
    idx=np.clip(rawidx,0,m.LUT_MAX).astype(np.int32)
    rgb8=curve[idx].reshape(x.shape).astype(np.uint8)
    return rgb8,{'preMatrixAnyChannelClipFraction':pre_any,'preMatrixAllChannelClipFraction':pre_all,
                 'matrixIndexHighClipFraction':idx_hi,'matrixIndexLowClipFraction':idx_lo,
                 'curveCodeEdgeFraction':float(np.mean((rgb8==0)|(rgb8==255)))}


def exact_fpga_luma_scale(rgb8,k):
    """Frozen exact 4:2:2 chroma arithmetic, but research-only scaling of Y."""
    h,w,_=rgb8.shape;w2=w-(w%2)
    R=rgb8[:,:w2,0].astype(np.int64);G=rgb8[:,:w2,1].astype(np.int64);B=rgb8[:,:w2,2].astype(np.int64)
    Y=((4899*R+9617*G+1868*B)>>14).astype(np.float64)
    Rs=R[:,0::2]+R[:,1::2];Gs=G[:,0::2]+G[:,1::2];Bs=B[:,0::2]+B[:,1::2]
    CbS=((((-2765*Rs+1)>>1)-((5427*Gs)>>1)+((8192*Bs)>>1)))>>14
    CrS=((((8192*Rs)>>1)-((6860*Gs)>>1)-((1332*Bs)>>1)))>>14
    Cb=(CbS+128)&0xff;Cr=(CrS+128)&0xff
    cb=np.repeat(Cb,2,axis=1).astype(np.float64)-128.;cr=np.repeat(Cr,2,axis=1).astype(np.float64)-128.
    Y=np.clip(Y*float(k),0,255)
    out=np.stack([Y+1.402*cr,Y-.344136*cb-.714136*cr,Y+1.772*cb],-1)/255.0
    if w2!=w:
        tail=rgb8[:,w2:,:].astype(np.float64)/255.0
        tail=np.clip(tail*float(k),0,1)
        out=np.concatenate([out,tail],axis=1)
    return np.clip(out,0,1)


def lum_metrics(img):
    a=np.asarray(img,dtype=np.float64)
    if a.dtype==np.uint8 or np.nanmax(a)>1.5:a=a/255.0
    lum=.2126*a[...,0]+.7152*a[...,1]+.0722*a[...,2]
    mx=np.max(a,axis=-1);mn=np.min(a,axis=-1)
    sat=np.divide(mx-mn,np.maximum(mx,1e-9),out=np.zeros_like(mx),where=mx>1e-9)
    h,w=lum.shape;cy0,cy1=int(.25*h),int(.75*h);cx0,cx1=int(.25*w),int(.75*w)
    c=lum[cy0:cy1,cx0:cx1];cs=sat[cy0:cy1,cx0:cx1]
    return {'globalMedian':float(np.median(lum)),'globalQ90':float(np.quantile(lum,.90)),'globalQ95':float(np.quantile(lum,.95)),'globalQ99':float(np.quantile(lum,.99)),
            'centerMedian':float(np.median(c)),'centerQ90':float(np.quantile(c,.90)),'centerQ95':float(np.quantile(c,.95)),
            'nearWhiteFraction':float(np.mean(mx>=250/255)),'fullChannelClipFraction':float(np.mean(np.any(a>=1.0-1e-12,axis=-1))),
            'deepBlackFraction':float(np.mean(lum<=8/255)),'medianSaturation':float(np.median(sat)),'centerMedianSaturation':float(np.median(cs))}


def regional_metrics(img,rows=4,cols=6):
    a=np.asarray(img,dtype=np.float64)
    if np.nanmax(a)>1.5:a=a/255.0
    lum=.2126*a[...,0]+.7152*a[...,1]+.0722*a[...,2];h,w=lum.shape;q95=[];med=[]
    for ry in range(rows):
        for rx in range(cols):
            r=lum[(ry*h)//rows:((ry+1)*h)//rows,(rx*w)//cols:((rx+1)*w)//cols]
            med.append(float(np.median(r)));q95.append(float(np.quantile(r,.95)))
    return {'regionQ95Top4Mean':float(np.mean(sorted(q95,reverse=True)[:4])),'regionQ95Max':float(max(q95)),'regionMedian4x6':json.dumps(med,separators=(',',':')),'regionQ95_4x6':json.dumps(q95,separators=(',',':'))}


def solve_factor(make_img,target_median,lo=0.20,hi=1.0,steps=8):
    best=(1e9,None,None)
    for _ in range(steps):
        mid=(lo+hi)/2
        im=make_img(mid);med=lum_metrics(im)['globalMedian'];err=abs(med-target_median)
        if err<best[0]:best=(err,mid,im)
        if med>target_median:hi=mid
        else:lo=mid
    for k in (lo,hi,(lo+hi)/2):
        im=make_img(k);med=lum_metrics(im)['globalMedian'];err=abs(med-target_median)
        if err<best[0]:best=(err,k,im)
    return best[1],best[2],best[0]


def orient_np(m,img,orientation):
    pil=m.orient_image(Image.fromarray((np.clip(img,0,1)*255+.5).astype(np.uint8)),orientation)
    return pil,np.asarray(pil,dtype=np.float64)/255.0


def contact(items,path,cols=4,W=390,H=300,T=32):
    rows=(len(items)+cols-1)//cols;sh=Image.new('RGB',(W*cols,(H+T)*rows),'white');d=ImageDraw.Draw(sh)
    for i,(lab,p) in enumerate(items):
        im=Image.open(p).convert('RGB');im.thumbnail((W-8,H-6),Image.Resampling.LANCZOS);x=(i%cols)*W;y=(i//cols)*(H+T)
        d.text((x+4,y+5),lab,fill='black');sh.paste(im,(x+(W-im.width)//2,y+T))
    sh.save(path,quality=95,subsampling=0)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);ap.add_argument('--renderer',type=Path,required=True);ap.add_argument('--dcp',type=Path,required=True);ap.add_argument('--curve02',type=Path,required=True);ap.add_argument('--out',type=Path,default=Path('TC20PLACEMENTSTAGE1A_RESULTS'));ap.add_argument('--long-side',type=int,default=1600);ap.add_argument('--seed',type=int,default=202609050600);a=ap.parse_args()
    m=load_renderer(a.renderer);curve=np.frombuffer(a.curve02.read_bytes(),dtype=np.uint8).copy()
    if len(curve)!=2048:raise SystemExit('curve02 must be 2048 bytes')
    dcp=m.CobaltDCP(a.dcp);out=a.out;out.mkdir(parents=True,exist_ok=True);(out/'renders').mkdir(exist_ok=True);(out/'contacts').mkdir(exist_ok=True);(out/'metadata').mkdir(exist_ok=True)
    rows=[];blind=[];parity_max=0.0
    for p in sorted(a.root.glob('*.dng')):
        cam,neutral,orientation,baseline,iso,rawm=m.read_dng(p,a.long_side);xy=dcp.neutral_to_xy(neutral);T=m.cct_from_xy(xy);wA=m.weight_A(T)
        xyz50=dcp.to_xyz50(cam,xy,wA);xyz_scene=xyz50@m.bradford(m.D50_XY,xy).T;M9CM=m.interp(m.M9_CM_A,m.M9_CM_D65,wA);mcam=xyz_scene@M9CM.T;mwhite=M9CM@m.xy_to_xyz(xy);m9=np.maximum(mcam/np.maximum(mwhite[None,None,:],1e-8),0.0)
        xyz65=xyz50@m.bradford(m.D50_XY,m.D65_XY).T;prox=xyz65@m.XYZ2SRGB.T;y=np.maximum(.2126*prox[...,0]+.7152*prox[...,1]+.0722*prox[...,2],0)
        g,meta=m.tc20_meter(y,rawm,baseline);base=meta['base_median_gain'];guard=meta['tc20_guard_gain'];binding='guard' if guard<=base else 'median'
        rgb0,st0=curve_rgb8(m,m9,g,curve,3);img0=m.exact_fpga_422(rgb0)
        frozen_img,_,_=m.m9_stage(m9,g,curve,3);perr=float(np.max(np.abs(img0-frozen_img)));parity_max=max(parity_max,perr)
        if perr>PARITY_EPS:raise RuntimeError(f'pipeline parity failure {p.name}: {perr}')
        gpre=g*(2.0**TEST_HOLD_EV);rgb1,st1=curve_rgb8(m,m9,gpre,curve,3);img1=m.exact_fpga_422(rgb1);target=lum_metrics(img1)['globalMedian']
        k2,img2,err2=solve_factor(lambda k:m.exact_fpga_422(np.clip(np.rint(rgb0.astype(np.float64)*k),0,255).astype(np.uint8)),target)
        k3,img3,err3=solve_factor(lambda k:exact_fpga_luma_scale(rgb0,k),target)
        variants={'S0_FROZEN':(img0,1.0,g,st0,0.0),'S1_PRE':(img1,1.0,gpre,st1,0.0),'S2_POSTCURVE':(img2,k2,g,st0,err2),'S3_POSTLUMA':(img3,k3,g,st0,err3)}
        files=[];base_metrics=None
        for v,(img,k,usedg,stage,matcherr) in variants.items():
            pil,arr=orient_np(m,img,orientation);q=out/'renders'/f'{p.stem}_{v}.jpg';pil.save(q,quality=95,subsampling=0);lm=lum_metrics(arr);rg=regional_metrics(arr)
            if v=='S0_FROZEN':base_metrics={**lm,**rg}
            row={'file':p.name,'variant':v,'iso':iso,'cct':T,'baselineExposureEv':baseline,'tc20GainFrozen':g,'tc20Binding':binding,'baseMedianGain':base,'rawTailGuardGain':guard,'rawHardClipFraction':rawm['raw_hard_clip_fraction'],'rawTail':rawm['tc20_tail_value'],'testHoldEv':TEST_HOLD_EV,'effectivePreGain':usedg,'stageScaleFactor':k,'densityMatchAbsMedianError':matcherr,'pipelineParityMaxAbsError':perr,**stage,**lm,**rg}
            rows.append(row);files.append((v,q))
        fr=[r for r in rows if r['file']==p.name]
        for r in fr:
            for key in ('globalMedian','centerMedian','centerQ95','globalQ95','regionQ95Top4Mean','nearWhiteFraction','fullChannelClipFraction','deepBlackFraction','centerMedianSaturation'):
                r[key+'DeltaVsS0']=r[key]-base_metrics[key]
        rng=random.Random(a.seed+int(hashlib.sha1(p.name.encode()).hexdigest()[:8],16));rng.shuffle(files);coded=[]
        for lab,(v,q) in zip(['P','Q','R','S'],files):coded.append((lab,q));blind.append({'file':p.name,'blind':lab,'variant':v})
        contact(coded,out/'contacts'/f'{p.stem}_blind.jpg')
        print('done',p.name,'binding',binding,'gain',round(g,3),'targetMed',round(target*255,1),'k2',round(k2,4),'k3',round(k3,4),'match',err2,err3,flush=True)
    with (out/'metadata'/'tc20placementstage1a_metrics.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with (out/'metadata'/'blind_key.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['file','blind','variant']);w.writeheader();w.writerows(blind)
    summary={'schema':'m9cam.tc20placementstage1a.summary.v1','researchOnly':True,'testHoldEv':TEST_HOLD_EV,'dngCount':len({r['file'] for r in rows}),'pipelineParityMaxAbsError':parity_max,'variants':{}}
    for v in VARIANTS:
        rr=[r for r in rows if r['variant']==v];summary['variants'][v]={'meanGlobalMedian':float(np.mean([r['globalMedian'] for r in rr])),'meanCenterQ95':float(np.mean([r['centerQ95'] for r in rr])),'meanCenterMedianSaturation':float(np.mean([r['centerMedianSaturation'] for r in rr])),'meanDensityMatchError':float(np.mean([r['densityMatchAbsMedianError'] for r in rr]))}
    (out/'metadata'/'summary.json').write_text(json.dumps(summary,indent=2))
    manifest={'schema':'m9cam.tc20placementstage1a.offline.v1','researchOnly':True,'purpose':'matched-density stage localization; determine whether M9 character loss comes from final brightness or from pre-curve operating point','S0_FROZEN':'exact frozen TC20 + frozen M9 pipeline','S1_PRE':'frozen TC20 gain multiplied by 2^-0.35 before RAW clamp/matrix/curve02','S2_POSTCURVE':'frozen TC20 and matrix+curve02, then RGB code-value scale solved per frame to S1 final global median, then exact BT601','S3_POSTLUMA':'frozen TC20 and matrix+curve02, then BT601 luma Y scaled with Cb/Cr retained, solved per frame to S1 final global median','frozen':'Cobalt/HSM, M9 bridge, SAT3 M06/M07, curve02, exact BT601 arithmetic except explicit stage probe, JPEG95','notProduction':['S2_POSTCURVE','S3_POSTLUMA'],'warning':'Do not infer production correction from the -0.35 EV strength; the experiment isolates stage at matched density.'}
    (out/'metadata'/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print('CREATED',out,'parity',parity_max)

if __name__=='__main__':main()
