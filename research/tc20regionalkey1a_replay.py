#!/usr/bin/env python3
"""TC20REGIONALKEY1A offline replay harness.

Research-only. No live camera or renderer code is modified.

Purpose
-------
Test whether the TC20 fixed weighted-median display key can be restrained by a
third, global regional-upper-body guard while preserving the existing TC20
highlight guard and frozen M9 colour/tone path.

The experiment intentionally separates three ideas:
  1. frozen TC20 median request,
  2. frozen TC20 physical RAW-tail highlight guard,
  3. a research-only 4x6 regional upper-body guard.

The regional guard is NOT local tone mapping. It only selects one global
pre-curve gain.  It uses the same linear sRGB proxy used by frozen TC20, split
into a 4x6 grid.  The robust upper-body statistic is the mean of the four
highest regional q95 values.

A capture-normalized scene-key diagnostic is also computed:

    sceneKeyEv = log2(weightedMedian / (physicalISO * exposureSeconds))

This is an uncalibrated sensor/lens-specific relative scene-illumination
coordinate, not an ISO trigger and not a Leica EV/BV claim.  It exists to test
whether genuinely darker ambient scenes should receive a lower regional upper
placement target.  The physical ISO and exposure time must come from the exact
captureResult metadata for the DNG.

Variants
--------
R0       exact frozen TC20 reference
RFIX045  regional q95 target 0.45, gated to median-limited low-scene-key frames
RK018    adaptive regional target, beta 0.18
RK030    adaptive regional target, beta 0.30
RK042    adaptive regional target, beta 0.42

Adaptive target:

    target = clamp(0.52 * 2^(beta * (sceneKeyEv - (-9.0))), 0.28, 0.54)

Activation requires:
    frozen TC20 branch == median
    sceneKeyEv < -9.0

Candidate gain:
    min(frozen median gain, frozen RAW-tail guard, regional target / top4Q95)
with a regional gain floor of 1.0.

All thresholds/targets are research probes only. They are not production
calibration and must not be promoted without broader blinded regression.
"""
from __future__ import annotations
import argparse, csv, hashlib, importlib.util, json, math, random
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

SCENE_KEY_REF_EV=-9.0
REGIONAL_TARGET_BASE=0.52
REGIONAL_TARGET_MIN=0.28
REGIONAL_TARGET_MAX=0.54
FIXED_TARGET=0.45
BETAS=(0.18,0.30,0.42)
A0_PARITY_EPS=1.0e-9


def load_renderer(path:Path):
    spec=importlib.util.spec_from_file_location('m9frozen',str(path))
    if spec is None or spec.loader is None: raise RuntimeError('cannot load renderer')
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def get_path(obj,path):
    cur=obj
    for key in path:
        if not isinstance(cur,dict) or key not in cur:return None
        cur=cur[key]
    return cur


def capture_dng_name(record):
    if not isinstance(record,dict): return None
    d=record.get('dng')
    if isinstance(d,str) and d.strip(): return Path(d).name
    ci=get_path(record,('m9ExactIdentity','captureIdentity'))
    if isinstance(ci,str) and ci.lower().endswith('.dng'): return Path(ci).name
    return None


def iter_capture_records(jp:Path):
    try: root=json.loads(jp.read_text(errors='replace'))
    except Exception:return
    if not isinstance(root,dict):return
    if capture_dng_name(root):yield root,{'source':str(jp),'kind':'standalone_capture_json'}
    entries=root.get('entries')
    if isinstance(entries,list):
        for i,e in enumerate(entries):
            if not isinstance(e,dict) or e.get('role')!='capture_metadata':continue
            p=e.get('payload')
            if isinstance(p,dict) and capture_dng_name(p):
                yield p,{'source':str(jp),'kind':'diagnostic_bundle_capture_payload','entry':i}


def build_metadata_index(root:Path):
    idx={}
    for jp in root.rglob('*.json'):
        for rec,src in iter_capture_records(jp):
            dng=capture_dng_name(rec)
            cr=rec.get('captureResult') if isinstance(rec.get('captureResult'),dict) else {}
            try: iso=float(cr.get('iso'))
            except Exception:iso=None
            try: exp_ns=float(cr.get('exposureTimeNs'))
            except Exception:exp_ns=None
            if iso is None or exp_ns is None or iso<=0 or exp_ns<=0:continue
            idx.setdefault(dng,[]).append({'record':rec,'source':src,'iso':iso,'exposureTimeNs':exp_ns})
    return idx


def select_metadata(dng:Path,idx):
    c=idx.get(dng.name,[])
    if not c:return None
    isos=[x['iso'] for x in c]; exps=[x['exposureTimeNs'] for x in c]
    if max(isos)-min(isos)>1e-6 or max(exps)-min(exps)>1.0:
        raise RuntimeError(f'conflicting captureResult ISO/exposureTime for {dng.name}')
    c.sort(key=lambda x:(0 if x['source']['kind']=='standalone_capture_json' else 1,x['source']['source']))
    q=c[0].copy();q['candidateCount']=len(c);return q


def weighted_median_y(m,y):
    h,w=y.shape;yy,xx=np.mgrid[0:h,0:w]
    r=np.sqrt(((yy-h/2)/(h/2))**2+((xx-w/2)/(w/2))**2)
    wg=np.exp(-(r**2)/(2*m.METER_CW**2)).ravel();yf=y.ravel();mask=yf>1e-5
    if not mask.any():return 0.0
    o=np.argsort(yf[mask]);ys=yf[mask][o];ws=wg[mask][o];cu=np.cumsum(ws)
    return float(ys[np.searchsorted(cu,cu[-1]*.5)])


def linear_regional_metrics(y,rows=4,cols=6):
    h,w=y.shape;q90=[];q95=[];med=[]
    for ry in range(rows):
        y0=(ry*h)//rows;y1=((ry+1)*h)//rows
        for rx in range(cols):
            x0=(rx*w)//cols;x1=((rx+1)*w)//cols;r=y[y0:y1,x0:x1]
            med.append(float(np.median(r)));q90.append(float(np.quantile(r,.90)));q95.append(float(np.quantile(r,.95)))
    order=np.argsort(q95)[::-1]
    return {
        'linearRegionMedian4x6':json.dumps(med,separators=(',',':')),
        'linearRegionQ90_4x6':json.dumps(q90,separators=(',',':')),
        'linearRegionQ95_4x6':json.dumps(q95,separators=(',',':')),
        'linearRegionQ95Top4Mean':float(np.mean([q95[i] for i in order[:4]])),
        'linearRegionQ95Max':float(max(q95)),
        'linearRegionQ90Top4Mean':float(np.mean(sorted(q90,reverse=True)[:4])),
        'linearRegionMedianMean':float(np.mean(med)),
        'linearRegionMedianMax':float(max(med)),
    }


def candidate_pack(m,y,rawm,baseline_ev,physical_iso,exposure_ns,variant):
    med=weighted_median_y(m,y);tail=max(float(rawm['tc20_tail_value']),1e-9);scale=2.0**baseline_ev
    base=float(np.clip(m.METER_TARGET_RENORM/max(med,1e-6),.5,16.0))*scale
    guard=max(1.0,float(m.TC_HEADROOM_TARGET)/tail)
    frozen=float(min(base,guard));binding='guard' if guard<=base else 'median'
    reg=linear_regional_metrics(y);upper=max(reg['linearRegionQ95Top4Mean'],1e-9)
    exp_s=float(exposure_ns)*1e-9;capture_energy=float(physical_iso)*exp_s
    scene_key=math.log2(max(med,1e-12)/max(capture_energy,1e-12))
    active=(binding=='median' and scene_key<SCENE_KEY_REF_EV)
    if variant=='R0':
        target=None;reg_guard=float('inf');gain=frozen;active_effective=False;beta=None
    elif variant=='RFIX045':
        target=FIXED_TARGET;reg_guard=max(1.0,target/upper);gain=min(frozen,reg_guard) if active else frozen;active_effective=active and gain<frozen-1e-12;beta=None
    elif variant.startswith('RK'):
        beta={'RK018':.18,'RK030':.30,'RK042':.42}[variant]
        target=float(np.clip(REGIONAL_TARGET_BASE*(2.0**(beta*(scene_key-SCENE_KEY_REF_EV))),REGIONAL_TARGET_MIN,REGIONAL_TARGET_MAX))
        reg_guard=max(1.0,target/upper);gain=min(frozen,reg_guard) if active else frozen;active_effective=active and gain<frozen-1e-12
    else:raise ValueError(variant)
    return {**reg,
        'physicalIso':float(physical_iso),'exposureTimeNs':float(exposure_ns),'captureEnergyIsoSeconds':capture_energy,
        'sceneKeyEvRelative':scene_key,'sceneKeyActivationEligible':bool(active),'regionalGuardEffective':bool(active_effective),
        'regionalTarget':target,'regionalGuardGain':reg_guard,'regionalBeta':beta,
        'physicalMedian':med,'physicalTail':tail,'baseMedianGain':base,'rawTailGuardGain':guard,
        'frozenBinding':binding,'gainA0':frozen,'gainCandidate':float(gain),
        'gainDeltaVsA0Ev':math.log2(max(gain,1e-12)/max(frozen,1e-12)),
        'upperBodyTimesCandidateGain':upper*gain,'physicalTailTimesCandidateGain':tail*gain}


def m9_stage(m,post_wb_m9,gain,curve,sat=3):
    scaled=post_wb_m9*gain*m.RAW_MAX;rounded=np.rint(scaled)
    pre_any=float(np.mean(np.any(rounded>m.RAW_MAX,axis=-1)))
    x=np.clip(rounded,0,m.RAW_MAX).astype(np.int64);flat=x.reshape(-1,3);mask=flat[:,0]>=flat[:,1]
    Qe,Qo=m.MATRIX_BANK[sat];acc=np.empty_like(flat);acc[mask]=flat[mask]@Qe.T;acc[~mask]=flat[~mask]@Qo.T
    rawidx=acc>>16;idx_hi=float(np.mean(np.any(rawidx>m.LUT_MAX,axis=1)));idx=np.clip(rawidx,0,m.LUT_MAX).astype(np.int32)
    rgb8=curve[idx].reshape(x.shape).astype(np.uint8);out=m.exact_fpga_422(rgb8)
    return out,{'preMatrixAnyChannelClipFraction':pre_any,'matrixIndexHighClipFraction':idx_hi}


def oriented_render_metrics(m,img,orientation):
    pil=m.orient_image(Image.fromarray((img*255+.5).astype(np.uint8)),orientation)
    a=np.asarray(pil,dtype=np.float64)/255.0;lum=.2126*a[...,0]+.7152*a[...,1]+.0722*a[...,2];mx=np.max(a,axis=-1)
    h,w=lum.shape;cy0,cy1=int(.25*h),int(.75*h);cx0,cx1=int(.25*w),int(.75*w);center=lum[cy0:cy1,cx0:cx1]
    reg=linear_regional_metrics(lum)
    return pil,{
        'renderGlobalMedian':float(np.median(lum)),'renderCenterMedian':float(np.median(center)),
        'renderCenterQ90':float(np.quantile(center,.90)),'renderCenterQ95':float(np.quantile(center,.95)),
        'renderQ95':float(np.quantile(lum,.95)),'renderQ99':float(np.quantile(lum,.99)),
        'renderNearWhiteFraction':float(np.mean(mx>=250/255)),'renderAnyChannelFullClipFraction':float(np.mean(np.any(a>=1.0-1e-12,axis=-1))),
        'deepBlackFraction':float(np.mean(lum<=8/255)),
        'renderRegionQ95Top4Mean':reg['linearRegionQ95Top4Mean'],'renderRegionQ95Max':reg['linearRegionQ95Max'],
        'renderRegionQ90Top4Mean':reg['linearRegionQ90Top4Mean']}


def contact(items,path,cols=5,W=340,H=270,T=28):
    rows=(len(items)+cols-1)//cols;sh=Image.new('RGB',(W*cols,(H+T)*rows),'white');d=ImageDraw.Draw(sh)
    for i,(lab,p) in enumerate(items):
        im=Image.open(p).convert('RGB');im.thumbnail((W-8,H-4),Image.Resampling.LANCZOS);x=(i%cols)*W;y=(i//cols)*(H+T);d.text((x+4,y+3),lab,fill='black');sh.paste(im,(x+(W-im.width)//2,y+T))
    sh.save(path,quality=95,subsampling=0)


def math_selfcheck(m):
    checks={}
    for beta in BETAS:
        vals=[float(np.clip(REGIONAL_TARGET_BASE*2**(beta*(s-SCENE_KEY_REF_EV)),REGIONAL_TARGET_MIN,REGIONAL_TARGET_MAX)) for s in (-9,-10,-11,-12)]
        assert all(vals[i]>=vals[i+1]-1e-12 for i in range(len(vals)-1));checks[str(beta)]=vals
    checks['formula']='gain=min(frozenMedianGain, frozenRawTailGuard, regionalTarget/top4Q95) only when frozen branch=median and sceneKeyEv<-9'
    return checks


def main():
    ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);ap.add_argument('--renderer',type=Path,required=True);ap.add_argument('--dcp',type=Path,required=True);ap.add_argument('--curve02',type=Path,required=True);ap.add_argument('--out',type=Path,default=Path('TC20REGIONALKEY1A_RESULTS'));ap.add_argument('--long-side',type=int,default=800);ap.add_argument('--seed',type=int,default=202609050423);a=ap.parse_args()
    m=load_renderer(a.renderer);curve=np.frombuffer(a.curve02.read_bytes(),dtype=np.uint8).copy()
    if len(curve)!=2048:raise SystemExit('curve02 must be exact 2048 bytes')
    dcp=m.CobaltDCP(a.dcp);out=a.out;out.mkdir(parents=True,exist_ok=True);(out/'renders').mkdir(exist_ok=True);(out/'contacts').mkdir(exist_ok=True);(out/'metadata').mkdir(exist_ok=True)
    idx=build_metadata_index(a.root);dngs=sorted(a.root.rglob('*.dng'));rows=[];blind=[];skipped=[];parity_max=0.0
    variants=['R0','RFIX045','RK018','RK030','RK042']
    for p in dngs:
        md=select_metadata(p,idx)
        if md is None:skipped.append({'file':p.name,'reason':'missing exact captureResult iso/exposureTimeNs'});continue
        cam,neutral,orientation,baseline,iso_dng,rawm=m.read_dng(p,a.long_side);xy=dcp.neutral_to_xy(neutral);T=m.cct_from_xy(xy);wA=m.weight_A(T);xyz50=dcp.to_xyz50(cam,xy,wA);xyz_scene=xyz50@m.bradford(m.D50_XY,xy).T;M9CM=m.interp(m.M9_CM_A,m.M9_CM_D65,wA);mcam=xyz_scene@M9CM.T;mwhite=M9CM@m.xy_to_xyz(xy);m9=np.maximum(mcam/np.maximum(mwhite[None,None,:],1e-8),0.0);xyz65=xyz50@m.bradford(m.D50_XY,m.D65_XY).T;prox=xyz65@m.XYZ2SRGB.T;y=np.maximum(.2126*prox[...,0]+.7152*prox[...,1]+.0722*prox[...,2],0)
        frozen,_=m.tc20_meter(y,rawm,baseline);gp0=candidate_pack(m,y,rawm,baseline,md['iso'],md['exposureTimeNs'],'R0');err=abs(float(frozen)-gp0['gainA0']);parity_max=max(parity_max,err)
        if err>A0_PARITY_EPS:raise RuntimeError(f'R0 parity failure {p.name}: {err}')
        files=[];frame=[];r0m=None
        for v in variants:
            gp=candidate_pack(m,y,rawm,baseline,md['iso'],md['exposureTimeNs'],v);img,stage=m9_stage(m,m9,gp['gainCandidate'],curve);pil,rm=oriented_render_metrics(m,img,orientation);q=out/'renders'/f'{p.stem}_{v}.jpg';pil.save(q,quality=95,subsampling=0);files.append((v,q))
            if v=='R0':r0m=rm.copy()
            row={'file':p.name,'variant':v,'cct':T,'dngReportedIso':iso_dng,'metadataSource':md['source']['source'],'metadataKind':md['source']['kind'],'metadataCandidateCount':md['candidateCount'],'physicalHardClipFraction':rawm['raw_hard_clip_fraction'],'r0FrozenParityAbsError':err,**gp,**stage,**rm};frame.append(row)
        for r in frame:
            for k in ('renderGlobalMedian','renderCenterMedian','renderCenterQ95','renderRegionQ95Top4Mean','renderNearWhiteFraction','renderAnyChannelFullClipFraction','deepBlackFraction'):
                r[k+'DeltaVsR0']=r[k]-r0m[k]
        rows.extend(frame)
        rng=random.Random(a.seed+int(hashlib.sha1(p.name.encode()).hexdigest()[:8],16));rng.shuffle(files);labs=['P','Q','R','S','T'];coded=[]
        for lab,(v,q) in zip(labs,files):coded.append((lab,q));blind.append({'file':p.name,'blind':lab,'variant':v})
        contact(coded,out/'contacts'/f'{p.stem}_blind.jpg')
        print('done',p.name,'sceneKey',round(gp0['sceneKeyEvRelative'],3),'binding',gp0['frozenBinding'],'gain',round(gp0['gainA0'],3),flush=True)
    if not rows:raise SystemExit('no usable DNGs')
    with (out/'metadata'/'tc20regionalkey1a_metrics.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with (out/'metadata'/'blind_key.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=['file','blind','variant']);w.writeheader();w.writerows(blind)
    if skipped:
        with (out/'metadata'/'skipped.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=['file','reason']);w.writeheader();w.writerows(skipped)
    summary={'schema':'m9cam.tc20regionalkey1a.summary.v1','renderedDngCount':len(set(r['file'] for r in rows)),'R0ParityMaxAbsError':parity_max,'variants':{}}
    for v in variants:
        vr=[r for r in rows if r['variant']==v];summary['variants'][v]={'effectiveGuardCount':sum(bool(r['regionalGuardEffective']) for r in vr),'meanGainDeltaVsR0Ev':float(np.mean([r['gainDeltaVsA0Ev'] for r in vr])),'minGainDeltaVsR0Ev':float(min(r['gainDeltaVsA0Ev'] for r in vr)),'meanGlobalMedianDelta':float(np.mean([r['renderGlobalMedianDeltaVsR0'] for r in vr]))}
    (out/'metadata'/'summary.json').write_text(json.dumps(summary,indent=2));(out/'metadata'/'math_selfcheck.json').write_text(json.dumps(math_selfcheck(m),indent=2));(out/'metadata'/'manifest.json').write_text(json.dumps({'schema':'m9cam.tc20regionalkey1a.offline.v1','researchOnly':True,'variants':variants,'sceneKey':'log2(weightedMedian/(physicalISO*exposureSeconds)); relative sensor/lens coordinate only','activation':'frozen median branch AND sceneKeyEv < -9.0','regionalStatistic':'mean of four highest 4x6 linear-proxy q95 regions','adaptiveTarget':{'base':REGIONAL_TARGET_BASE,'referenceSceneKeyEv':SCENE_KEY_REF_EV,'floor':REGIONAL_TARGET_MIN,'ceiling':REGIONAL_TARGET_MAX,'betas':BETAS},'frozen':'R3.8-H25/TG1, Cobalt, M9 bridge, SAT3, curve02, exact BT601, JPEG95; no local tone mapping'},indent=2))
    print('CREATED',out,'DNGs',summary['renderedDngCount'],'R0 parity',parity_max)

if __name__=='__main__':main()
