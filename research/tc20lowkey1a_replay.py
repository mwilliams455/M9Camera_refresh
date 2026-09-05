#!/usr/bin/env python3
"""TC20LOWKEY1A offline replay harness.

Research-only. No live Camera2 or Android renderer code is modified.

TC20REGIONALKEY1A showed that capture-normalized sceneKeyEv is not selective
enough on a broader control corpus. TC20LOWKEY1A therefore removes sceneKeyEv
from authority and tests the already-existing preview structuralLowKeyScore as
a research activation signal.

Frozen TC20:
    base  = weighted-median request
    guard = physical RAW-tail guard
    L0    = min(base, guard)

Activation:
    frozen branch == median
    structuralLowKeyScore >= 0.50

Variants:
    L0     exact frozen TC20
    LH045  shift TC20 median target by -0.45 * score EV
    LR020  global 4x6 upper-body guard target = 0.52 - 0.20*score^2
    LR024  global 4x6 upper-body guard target = 0.52 - 0.24*score^2

Regional target is clamped to [0.28, 0.54]. The regional statistic is the mean
of the four highest q95 cells in a 4x6 grid in the same linear sRGB proxy used
for TC20 measurement. It selects one GLOBAL pre-curve gain only; there is no
local tone mapping.

All constants are research probes, not production calibration.
"""
from __future__ import annotations
import argparse, csv, hashlib, importlib.util, json, math, random
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

LOWKEY_GATE=0.50
HOLD_SCALE=0.45
REG_BASE=0.52
REG_MIN=0.28
REG_MAX=0.54
REG_COEFFS={'LR020':0.20,'LR024':0.24}
VARIANTS=('L0','LH045','LR020','LR024')
PARITY_EPS=1.0e-9


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


def num_at(obj,path):
    v=get_path(obj,path)
    try:return float(v) if v is not None else None
    except Exception:return None


def capture_dng_name(record):
    if not isinstance(record,dict):return None
    d=record.get('dng')
    if isinstance(d,str) and d.strip():return Path(d).name
    ci=get_path(record,('m9ExactIdentity','captureIdentity'))
    if isinstance(ci,str) and ci.lower().endswith('.dng'):return Path(ci).name
    return None


def iter_capture_records(jp:Path):
    try:root=json.loads(jp.read_text(errors='replace'))
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


def extract_lowkey(rec):
    score=num_at(rec,('m9SceneExposureDiagnostic','positiveBodyPressure','structuralLowKeyScore'))
    att=num_at(rec,('m9SceneExposureDiagnostic','positiveBodyPressure','structuralLowKeyAttenuation'))
    inp=get_path(rec,('m9SceneExposureDiagnostic','inputs'))
    if not isinstance(inp,dict):inp={}
    vals={}
    for k in ('globalMedian','globalQ95','globalQ99','darkFractionLE64','brightFractionGE192','brightFractionGE224','brightFractionGE240','centerMedian','centerMedianMinusGlobalMedian'):
        try:vals['preview_'+k]=float(inp[k]) if k in inp and inp[k] is not None else None
        except Exception:vals['preview_'+k]=None
    return score,att,vals


def build_metadata_index(root:Path):
    idx={}
    for jp in root.rglob('*.json'):
        for rec,src in iter_capture_records(jp):
            dng=capture_dng_name(rec);score,att,prev=extract_lowkey(rec)
            if score is None:continue
            idx.setdefault(dng,[]).append({'record':rec,'source':src,'score':score,'attenuation':att,**prev})
    return idx


def select_metadata(dng:Path,idx):
    c=idx.get(dng.name,[])
    if not c:return None
    scores=[x['score'] for x in c]
    if max(scores)-min(scores)>1e-6:raise RuntimeError(f'conflicting structuralLowKeyScore for {dng.name}: {scores}')
    c.sort(key=lambda x:(0 if x['source']['kind']=='standalone_capture_json' else 1,x['source']['source']))
    q=c[0].copy();q['candidateCount']=len(c);return q


def weighted_median_y(m,y):
    h,w=y.shape;yy,xx=np.mgrid[0:h,0:w]
    r=np.sqrt(((yy-h/2)/(h/2))**2+((xx-w/2)/(w/2))**2)
    wg=np.exp(-(r**2)/(2*m.METER_CW**2)).ravel();yf=y.ravel();mask=yf>1e-5
    if not mask.any():return 0.0
    o=np.argsort(yf[mask]);ys=yf[mask][o];ws=wg[mask][o];cu=np.cumsum(ws)
    return float(ys[np.searchsorted(cu,cu[-1]*.5)])


def regional_metrics(y,rows=4,cols=6):
    h,w=y.shape;med=[];q90=[];q95=[]
    for ry in range(rows):
        y0=(ry*h)//rows;y1=((ry+1)*h)//rows
        for rx in range(cols):
            x0=(rx*w)//cols;x1=((rx+1)*w)//cols;r=y[y0:y1,x0:x1]
            med.append(float(np.median(r)));q90.append(float(np.quantile(r,.90)));q95.append(float(np.quantile(r,.95)))
    order=np.argsort(q95)[::-1]
    return {'regionMedian4x6':json.dumps(med,separators=(',',':')),
            'regionQ90_4x6':json.dumps(q90,separators=(',',':')),
            'regionQ95_4x6':json.dumps(q95,separators=(',',':')),
            'regionQ95Top4Mean':float(np.mean([q95[i] for i in order[:4]])),
            'regionQ95Max':float(max(q95)),'regionQ90Top4Mean':float(np.mean(sorted(q90,reverse=True)[:4]))}


def gain_pack(m,y,rawm,baseline_ev,score,variant):
    med=weighted_median_y(m,y);tail=max(float(rawm['tc20_tail_value']),1e-9);scale=2.0**baseline_ev
    base=float(np.clip(m.METER_TARGET_RENORM/max(med,1e-6),.5,16.0))*scale
    guard=max(1.0,float(m.TC_HEADROOM_TARGET)/tail)
    frozen=float(min(base,guard));binding='guard' if guard<=base else 'median'
    reg=regional_metrics(y);upper=max(reg['regionQ95Top4Mean'],1e-9)
    eligible=(binding=='median' and score>=LOWKEY_GATE)
    hold_ev=0.0;target=None;reg_guard=float('inf');mechanism='frozen';gain=frozen
    if variant=='L0':pass
    elif variant=='LH045':
        mechanism='median_target_hold';hold_ev=-HOLD_SCALE*score
        gain=float(min(base*(2.0**hold_ev),guard)) if eligible else frozen
    elif variant in REG_COEFFS:
        mechanism='regional_upper_body_guard';coef=REG_COEFFS[variant]
        target=float(np.clip(REG_BASE-coef*(score**2),REG_MIN,REG_MAX));reg_guard=max(1.0,target/upper)
        gain=float(min(base,guard,reg_guard)) if eligible else frozen
    else:raise ValueError(variant)
    effective=eligible and gain<frozen-1e-12
    return {**reg,'structuralLowKeyScore':float(score),'lowKeyActivationEligible':bool(eligible),'lowKeyConstraintEffective':bool(effective),
            'mechanism':mechanism,'medianTargetHoldEv':hold_ev,'regionalTarget':target,'regionalGuardGain':reg_guard,
            'physicalMedian':med,'physicalTail':tail,'baseMedianGain':base,'rawTailGuardGain':guard,'frozenBinding':binding,
            'guardMarginAboveBaseEv':math.log2(max(guard,1e-12)/max(base,1e-12)),
            'gainA0':frozen,'gainCandidate':gain,'gainDeltaVsA0Ev':math.log2(max(gain,1e-12)/max(frozen,1e-12)),
            'upperBodyTimesGain':upper*gain,'physicalTailTimesGain':tail*gain}


def m9_stage(m,post_wb_m9,gain,curve,sat=3):
    scaled=post_wb_m9*gain*m.RAW_MAX;rounded=np.rint(scaled);pre_any=float(np.mean(np.any(rounded>m.RAW_MAX,axis=-1)))
    x=np.clip(rounded,0,m.RAW_MAX).astype(np.int64);flat=x.reshape(-1,3);mask=flat[:,0]>=flat[:,1]
    Qe,Qo=m.MATRIX_BANK[sat];acc=np.empty_like(flat);acc[mask]=flat[mask]@Qe.T;acc[~mask]=flat[~mask]@Qo.T
    rawidx=acc>>16;idx_hi=float(np.mean(np.any(rawidx>m.LUT_MAX,axis=1)));idx=np.clip(rawidx,0,m.LUT_MAX).astype(np.int32)
    rgb8=curve[idx].reshape(x.shape).astype(np.uint8);out=m.exact_fpga_422(rgb8)
    return out,{'preMatrixAnyChannelClipFraction':pre_any,'matrixIndexHighClipFraction':idx_hi}


def oriented_metrics(m,img,orientation):
    pil=m.orient_image(Image.fromarray((img*255+.5).astype(np.uint8)),orientation);a=np.asarray(pil,dtype=np.float64)/255.0
    lum=.2126*a[...,0]+.7152*a[...,1]+.0722*a[...,2];mx=np.max(a,axis=-1);h,w=lum.shape
    cy0,cy1=int(.25*h),int(.75*h);cx0,cx1=int(.25*w),int(.75*w);center=lum[cy0:cy1,cx0:cx1];reg=regional_metrics(lum)
    return pil,{'renderGlobalMedian':float(np.median(lum)),'renderCenterMedian':float(np.median(center)),
                'renderCenterQ90':float(np.quantile(center,.90)),'renderCenterQ95':float(np.quantile(center,.95)),
                'renderQ95':float(np.quantile(lum,.95)),'renderQ99':float(np.quantile(lum,.99)),
                'renderNearWhiteFraction':float(np.mean(mx>=250/255)),'renderAnyChannelFullClipFraction':float(np.mean(np.any(a>=1.0-1e-12,axis=-1))),
                'deepBlackFraction':float(np.mean(lum<=8/255)),'renderRegionQ95Top4Mean':reg['regionQ95Top4Mean'],'renderRegionQ95Max':reg['regionQ95Max']}


def contact(items,path,cols=4,W=390,H=300,T=30):
    rows=(len(items)+cols-1)//cols;sh=Image.new('RGB',(W*cols,(H+T)*rows),'white');d=ImageDraw.Draw(sh)
    for i,(lab,p) in enumerate(items):
        im=Image.open(p).convert('RGB');im.thumbnail((W-8,H-5),Image.Resampling.LANCZOS);x=(i%cols)*W;y=(i//cols)*(H+T)
        d.text((x+4,y+4),lab,fill='black');sh.paste(im,(x+(W-im.width)//2,y+T))
    sh.save(path,quality=95,subsampling=0)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);ap.add_argument('--renderer',type=Path,required=True);ap.add_argument('--dcp',type=Path,required=True);ap.add_argument('--curve02',type=Path,required=True);ap.add_argument('--out',type=Path,default=Path('TC20LOWKEY1A_RESULTS'));ap.add_argument('--long-side',type=int,default=800);ap.add_argument('--seed',type=int,default=202609050445);a=ap.parse_args()
    m=load_renderer(a.renderer);curve=np.frombuffer(a.curve02.read_bytes(),dtype=np.uint8).copy()
    if len(curve)!=2048:raise SystemExit('curve02 must be exact 2048 bytes')
    dcp=m.CobaltDCP(a.dcp);out=a.out;out.mkdir(parents=True,exist_ok=True);(out/'renders').mkdir(exist_ok=True);(out/'contacts').mkdir(exist_ok=True);(out/'metadata').mkdir(exist_ok=True)
    idx=build_metadata_index(a.root);dngs=sorted(a.root.rglob('*.dng'));rows=[];blind=[];skipped=[];parity_max=0.0
    for p in dngs:
        md=select_metadata(p,idx)
        if md is None:skipped.append({'file':p.name,'reason':'missing structuralLowKeyScore metadata'});continue
        cam,neutral,orientation,baseline,iso_dng,rawm=m.read_dng(p,a.long_side);xy=dcp.neutral_to_xy(neutral);T=m.cct_from_xy(xy);wA=m.weight_A(T)
        xyz50=dcp.to_xyz50(cam,xy,wA);xyz_scene=xyz50@m.bradford(m.D50_XY,xy).T;M9CM=m.interp(m.M9_CM_A,m.M9_CM_D65,wA)
        mcam=xyz_scene@M9CM.T;mwhite=M9CM@m.xy_to_xyz(xy);m9=np.maximum(mcam/np.maximum(mwhite[None,None,:],1e-8),0.0)
        xyz65=xyz50@m.bradford(m.D50_XY,m.D65_XY).T;prox=xyz65@m.XYZ2SRGB.T;y=np.maximum(.2126*prox[...,0]+.7152*prox[...,1]+.0722*prox[...,2],0)
        frozen,_=m.tc20_meter(y,rawm,baseline);gp0=gain_pack(m,y,rawm,baseline,md['score'],'L0');err=abs(float(frozen)-gp0['gainA0']);parity_max=max(parity_max,err)
        if err>PARITY_EPS:raise RuntimeError(f'L0 parity failure {p.name}: {err}')
        files=[];frame=[];r0m=None
        for v in VARIANTS:
            gp=gain_pack(m,y,rawm,baseline,md['score'],v);img,stage=m9_stage(m,m9,gp['gainCandidate'],curve);pil,rm=oriented_metrics(m,img,orientation);q=out/'renders'/f'{p.stem}_{v}.jpg';pil.save(q,quality=95,subsampling=0);files.append((v,q))
            if v=='L0':r0m=rm.copy()
            frame.append({'file':p.name,'variant':v,'cct':T,'dngReportedIso':iso_dng,'metadataSource':md['source']['source'],'metadataKind':md['source']['kind'],'metadataCandidateCount':md['candidateCount'],'structuralLowKeyAttenuation':md['attenuation'],'physicalHardClipFraction':rawm['raw_hard_clip_fraction'],'l0FrozenParityAbsError':err,**{k:v0 for k,v0 in md.items() if k.startswith('preview_')},**gp,**stage,**rm})
        for r in frame:
            for k in ('renderGlobalMedian','renderCenterMedian','renderCenterQ95','renderRegionQ95Top4Mean','renderNearWhiteFraction','renderAnyChannelFullClipFraction','deepBlackFraction'):
                r[k+'DeltaVsL0']=r[k]-r0m[k]
        rows.extend(frame);rng=random.Random(a.seed+int(hashlib.sha1(p.name.encode()).hexdigest()[:8],16));rng.shuffle(files);coded=[]
        for lab,(v,q) in zip(['P','Q','R','S'],files):coded.append((lab,q));blind.append({'file':p.name,'blind':lab,'variant':v})
        contact(coded,out/'contacts'/f'{p.stem}_blind.jpg')
        print('done',p.name,'score',round(md['score'],3),'binding',gp0['frozenBinding'],'gain',round(gp0['gainA0'],3),flush=True)
    if not rows:raise SystemExit('no usable DNGs with structuralLowKeyScore')
    with (out/'metadata'/'tc20lowkey1a_metrics.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with (out/'metadata'/'blind_key.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['file','blind','variant']);w.writeheader();w.writerows(blind)
    if skipped:
        with (out/'metadata'/'skipped.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['file','reason']);w.writeheader();w.writerows(skipped)
    summary={'schema':'m9cam.tc20lowkey1a.summary.v1','researchOnly':True,'renderedDngCount':len({r['file'] for r in rows}),'skippedDngCount':len(skipped),'l0FrozenParityMaxAbsError':parity_max,'variants':{}}
    for v in VARIANTS:
        rr=[r for r in rows if r['variant']==v];summary['variants'][v]={'effectiveCount':sum(bool(r['lowKeyConstraintEffective']) for r in rr),'meanGainDeltaEv':float(np.mean([r['gainDeltaVsA0Ev'] for r in rr]))}
    (out/'metadata'/'summary.json').write_text(json.dumps(summary,indent=2))
    manifest={'schema':'m9cam.tc20lowkey1a.offline.v1','researchOnly':True,'activation':'frozen branch median AND existing structuralLowKeyScore >= 0.50','sceneKeyAuthority':'REMOVED: capture-normalized sceneKeyEv failed broader-control selectivity','variants':list(VARIANTS),'LH045':'median target hold -0.45*structuralLowKeyScore','LR020':'4x6 top-four-q95 global guard target 0.52-0.20*score^2','LR024':'4x6 top-four-q95 global guard target 0.52-0.24*score^2','regionalTargetClamp':[REG_MIN,REG_MAX],'frozen':'R3.8-H25/TG1, Cobalt main, M9 bridge, SAT3 M06/M07, curve02, exact BT601, JPEG95; no local tone mapping','warning':'research discrimination only; not production calibration'}
    (out/'metadata'/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print('CREATED',out,'rendered',summary['renderedDngCount'],'skipped',summary['skippedDngCount'],'parity',parity_max)

if __name__=='__main__':main()
