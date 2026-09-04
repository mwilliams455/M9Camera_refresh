#!/usr/bin/env python3
"""TC20INTENT1A offline replay harness.

Research-only. It does not modify Camera2, the Android renderer, colour science,
curve02, SAT3, TG1, JPEG quality, or DNGs.

The harness dynamically loads the authoritative frozen Python R3.5 renderer,
discovers DNGs recursively, and indexes BOTH standalone *_M9.json records and
capture_metadata payloads embedded inside M9_DIAGNOSTICS_BURST_*.json bundles.

Exposure intent is taken from the authoritative capture audit:

    m9ExposureAudit.derived.captureEnergyVsPhotonOnlyEv

not from requested MFM EV and not from the overwrite-prone MFM snapshot.

Variants:
  A0       frozen TC20
  A1_010   full virtual TC20 measurement, max preserved intent 0.10 EV
  A1_020   full virtual TC20 measurement, max preserved intent 0.20 EV
  A1_030   full virtual TC20 measurement, max preserved intent 0.30 EV
  A2_020   same A1 0.20 gain, but defers the current pre-matrix per-channel
           RAW_MAX clamp until matrix/LUT indexing. This is a clipping-location
           experiment, not a production highlight policy.

Physical RAW median/tail/clipping remain separately logged in every variant.
A0 is asserted against the frozen renderer's own tc20_meter() result before any
experimental output is accepted.
"""
from __future__ import annotations
import argparse, csv, hashlib, importlib.util, json, math, random
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

CAPS=(0.0,0.10,0.20,0.30)
A0_PARITY_EPS=1.0e-9
INTENT_CONFLICT_EPS=1.0e-6


def load_renderer(path: Path):
    spec=importlib.util.spec_from_file_location('m9frozen', str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError('cannot load renderer')
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def get_path(obj, path):
    cur=obj
    for key in path:
        if not isinstance(cur,dict) or key not in cur:
            return None
        cur=cur[key]
    return cur


def number_at(obj, path):
    v=get_path(obj,path)
    try:
        return float(v) if v is not None else None
    except Exception:
        return None


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


def capture_dng_name(record):
    if not isinstance(record,dict):return None
    d=record.get('dng')
    if isinstance(d,str) and d.strip():return Path(d).name
    ci=get_path(record,('m9ExactIdentity','captureIdentity'))
    if isinstance(ci,str) and ci.lower().endswith('.dng'):return Path(ci).name
    return None


def extract_intent(record):
    """Return achieved intent and exact source path.

    The first path is authoritative for the current corpus. The secondary audit
    path tolerates an older schema shape. Recursive fallback is retained only for
    compatibility and is surfaced explicitly in telemetry.
    """
    paths=(
        ('m9ExposureAudit','derived','captureEnergyVsPhotonOnlyEv'),
        ('m9ExposureAudit','captureEnergyVsPhotonOnlyEv'),
    )
    for p in paths:
        v=number_at(record,p)
        if v is not None:return v,'.'.join(p)
    v=walk_key(record,'captureEnergyVsPhotonOnlyEv')
    if v is not None:return v,'recursive_fallback.captureEnergyVsPhotonOnlyEv'
    return None,None


def first_number(record, paths, fallback_key=None):
    for p in paths:
        v=number_at(record,p)
        if v is not None:return v,'.'.join(p)
    if fallback_key:
        v=walk_key(record,fallback_key)
        if v is not None:return v,'recursive_fallback.'+fallback_key
    return None,None


def extract_preview_highlights(record):
    q95,q95src=first_number(record,(
        ('subjectMotion','previewLuma','global','q95'),
        ('m9ExposureFeedback','classifierAtDecision','inputs','globalQ95'),
        ('m9BacklightDiagnostic','inputs','globalQ95'),
        ('m9SceneExposureDiagnostic','inputs','globalQ95'),
    ),'globalQ95')
    b240,b240src=first_number(record,(
        ('subjectMotion','previewLuma','global','brightFractionGE240'),
        ('m9ExposureFeedback','classifierAtDecision','inputs','brightFractionGE240'),
        ('m9BacklightDiagnostic','inputs','brightFractionGE240'),
        ('m9SceneExposureDiagnostic','inputs','brightFractionGE240'),
    ),'brightFractionGE240')
    return q95,q95src,b240,b240src


def iter_capture_records(json_path:Path):
    try:
        root=json.loads(json_path.read_text(errors='replace'))
    except Exception:
        return
    if not isinstance(root,dict):return

    # Standalone capture metadata.
    if capture_dng_name(root):
        yield root,dict(metadataSource=str(json_path),metadataKind='standalone_capture_json',
                        bundleEntryIndex=-1,bundleSequence='')

    # SIDECAR diagnostic bundle. Recover the exact capture payload; this is
    # essential for burst archives where no standalone *_M9.json was exported.
    entries=root.get('entries')
    if isinstance(entries,list):
        for i,e in enumerate(entries):
            if not isinstance(e,dict):continue
            if e.get('role')!='capture_metadata':continue
            payload=e.get('payload')
            if not isinstance(payload,dict) or not capture_dng_name(payload):continue
            yield payload,dict(metadataSource=str(json_path),metadataKind='diagnostic_bundle_capture_payload',
                               bundleEntryIndex=i,bundleSequence=e.get('sequence',''))


def build_metadata_index(root:Path):
    idx={}
    scanned=0
    for jp in sorted(root.rglob('*.json')):
        scanned+=1
        for rec,src in iter_capture_records(jp):
            dng=capture_dng_name(rec)
            ev,evsrc=extract_intent(rec)
            q95,q95src,b240,b240src=extract_preview_highlights(rec)
            item=dict(record=rec,source=src,intentEv=ev,intentSourcePath=evsrc,
                      previewGlobalQ95=q95,previewGlobalQ95Source=q95src,
                      previewBrightFractionGE240=b240,previewBrightFractionGE240Source=b240src)
            idx.setdefault(dng,[]).append(item)
    return idx,scanned


def select_metadata(dng:Path, index):
    candidates=index.get(dng.name,[])
    usable=[x for x in candidates if x['intentEv'] is not None]
    if not usable:return None
    vals=[float(x['intentEv']) for x in usable]
    if max(vals)-min(vals)>INTENT_CONFLICT_EPS:
        detail=', '.join(f"{x['source']['metadataKind']}:{x['intentEv']:+.9f}" for x in usable)
        raise RuntimeError(f'conflicting captureEnergyVsPhotonOnlyEv for {dng.name}: {detail}')
    # Prefer standalone capture JSON when both representations are identical.
    usable.sort(key=lambda x:(0 if x['source']['metadataKind']=='standalone_capture_json' else 1,
                              x['source']['metadataSource']))
    chosen=usable[0].copy()
    chosen['metadataCandidateCount']=len(candidates)
    chosen['metadataUsableIntentCount']=len(usable)
    return chosen


def weighted_median_y(m,y):
    h,w=y.shape
    yy,xx=np.mgrid[0:h,0:w]
    r=np.sqrt(((yy-h/2)/(h/2))**2+((xx-w/2)/(w/2))**2)
    wg=np.exp(-(r**2)/(2*m.METER_CW**2)).ravel()
    yf=y.ravel(); mask=yf>1e-5
    if not mask.any():return 0.0
    order=np.argsort(yf[mask]); ys=yf[mask][order]; ws=wg[mask][order]
    cu=np.cumsum(ws)
    return float(ys[np.searchsorted(cu,cu[-1]*.5)])


def gain_pack(m,y,rawm,baseline_ev,intent_ev,cap):
    physical_median=weighted_median_y(m,y)
    physical_tail=float(rawm['tc20_tail_value'])
    achieved=max(float(intent_ev),0.0)
    preserved=min(achieved,float(cap))
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
    physical_binding='guard' if guard_physical<=base_physical else 'median'
    virtual_binding='guard' if guard_virtual<=base_virtual else 'median'
    return dict(actualCaptureEnergyVsPhotonOnlyEv=float(intent_ev),
        achievedPositiveIntentEv=achieved,preservedIntentEv=preserved,
        physicalMedian=physical_median,physicalTail=physical_tail,
        virtualMedian=virtual_median,virtualTail=virtual_tail,
        baseMedianGainPhysical=base_physical,guardGainPhysical=guard_physical,
        baseMedianGainVirtual=base_virtual,guardGainVirtual=guard_virtual,
        physicalBinding=physical_binding,virtualBinding=virtual_binding,
        gainA0=gain_physical,gainCandidate=gain_virtual,
        gainDeltaVsA0Ev=math.log2(max(gain_virtual,1e-12)/max(gain_physical,1e-12)),
        physicalTailTimesGain=physical_tail*gain_virtual)


def m9_stage_metrics(m,post_wb_m9,gain,curve,sat,defer_clamp=False):
    scaled=post_wb_m9*gain*m.RAW_MAX
    rounded=np.rint(scaled)
    pre_any=float(np.mean(np.any(rounded>m.RAW_MAX,axis=-1)))
    pre_all=float(np.mean(np.all(rounded>m.RAW_MAX,axis=-1)))
    if defer_clamp:
        x=np.maximum(rounded,0).astype(np.int64)
    else:
        x=np.clip(rounded,0,m.RAW_MAX).astype(np.int64)
    flat=x.reshape(-1,3)
    mask=flat[:,0]>=flat[:,1]
    Qe,Qo=m.MATRIX_BANK[sat]
    acc=np.empty_like(flat)
    acc[mask]=flat[mask]@Qe.T
    acc[~mask]=flat[~mask]@Qo.T
    rawidx=acc>>16
    idx_hi=float(np.mean(np.any(rawidx>m.LUT_MAX,axis=1)))
    idx_lo=float(np.mean(np.any(rawidx<0,axis=1)))
    idx=np.clip(rawidx,0,m.LUT_MAX).astype(np.int32)
    rgb8=curve[idx].reshape(x.shape).astype(np.uint8)
    out=m.exact_fpga_422(rgb8)
    lum=.2126*out[...,0]+.7152*out[...,1]+.0722*out[...,2]
    mx=np.max(out,axis=-1)
    h,w=lum.shape
    cy0,cy1=int(.25*h),int(.75*h); cx0,cx1=int(.25*w),int(.75*w)
    return out,dict(preMatrixAnyChannelClipFraction=pre_any,
        preMatrixAllChannelClipFraction=pre_all,
        matrixIndexHighClipFraction=idx_hi,matrixIndexLowClipFraction=idx_lo,
        renderNearWhiteFraction=float(np.mean(mx>=250/255)),
        renderAnyChannelFullClipFraction=float(np.mean(np.any(out>=1.0-1e-12,axis=-1))),
        renderAllChannelFullWhiteFraction=float(np.mean(np.all(out>=1.0-1e-12,axis=-1))),
        renderGlobalMedian=float(np.median(lum)),
        renderCenterMedian=float(np.median(lum[cy0:cy1,cx0:cx1])),
        renderQ95=float(np.quantile(lum,.95)),renderQ99=float(np.quantile(lum,.99)),
        deepBlackFraction=float(np.mean(lum<=8/255)))


def contact(items,path,cols=4,W=360,H=280,T=30):
    rows=(len(items)+cols-1)//cols
    sh=Image.new('RGB',(W*cols,(H+T)*rows),'white'); d=ImageDraw.Draw(sh)
    for i,(lab,p) in enumerate(items):
        im=Image.open(p).convert('RGB'); im.thumbnail((W-8,H-6),Image.Resampling.LANCZOS)
        x=(i%cols)*W; y=(i//cols)*(H+T)
        d.text((x+4,y+4),lab,fill='black'); sh.paste(im,(x+(W-im.width)//2,y+T))
    sh.save(path,quality=95,subsampling=0)


def mean_or_none(vals):
    vals=[float(v) for v in vals if v is not None and math.isfinite(float(v))]
    return float(np.mean(vals)) if vals else None


def build_summary(rows, corpus):
    variants=sorted({r['variant'] for r in rows})
    out={'schema':'m9cam.tc20intent1a.summary.v1','corpus':corpus,'variants':{}}
    for v in variants:
        vr=[r for r in rows if r['variant']==v]
        groups={
            'all':vr,
            'positiveIntent':[r for r in vr if r['positiveIntent']],
            'saturatedPreviewSafety':[r for r in vr if r['saturatedPreviewSafetyCohort']],
            'positiveIntentOrdinary':[r for r in vr if r['positiveIntent'] and not r['saturatedPreviewSafetyCohort']],
        }
        out['variants'][v]={}
        for name,g in groups.items():
            out['variants'][v][name]={
                'count':len(g),
                'meanPreservedIntentEv':mean_or_none([r['preservedIntentEv'] for r in g]),
                'meanGainDeltaVsA0Ev':mean_or_none([r['gainDeltaVsA0Ev'] for r in g]),
                'meanCenterMedianDeltaVsA0':mean_or_none([r['renderCenterMedianDeltaVsA0'] for r in g]),
                'meanGlobalMedianDeltaVsA0':mean_or_none([r['renderGlobalMedianDeltaVsA0'] for r in g]),
                'meanNearWhiteDeltaVsA0':mean_or_none([r['renderNearWhiteDeltaVsA0'] for r in g]),
                'meanFullClipDeltaVsA0':mean_or_none([r['renderAnyChannelFullClipDeltaVsA0'] for r in g]),
                'meanDeepBlackDeltaVsA0':mean_or_none([r['deepBlackDeltaVsA0'] for r in g]),
                'meanMatrixHighClipDeltaVsA0':mean_or_none([r['matrixIndexHighClipDeltaVsA0'] for r in g]),
            }
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('root',type=Path,help='directory containing extracted test archives')
    ap.add_argument('--renderer',type=Path,required=True)
    ap.add_argument('--dcp',type=Path,required=True)
    ap.add_argument('--firmware',type=Path,required=True)
    ap.add_argument('--out',type=Path,default=Path('TC20INTENT1A_RESULTS'))
    ap.add_argument('--long-side',type=int,default=1600)
    ap.add_argument('--seed',type=int,default=920260904)
    a=ap.parse_args()
    m=load_renderer(a.renderer)
    out=a.out; out.mkdir(parents=True,exist_ok=True)
    (out/'renders').mkdir(exist_ok=True); (out/'contacts').mkdir(exist_ok=True); (out/'metadata').mkdir(exist_ok=True)
    curve=m.extract_curve02(a.firmware); dcp=m.CobaltDCP(a.dcp)

    meta_index,json_scanned=build_metadata_index(a.root)
    all_dngs=sorted(a.root.rglob('*.dng'))
    dng_by_name={}
    duplicate_dng_names={}
    for p in all_dngs:
        if p.name in dng_by_name:
            duplicate_dng_names.setdefault(p.name,[str(dng_by_name[p.name])]).append(str(p))
            continue
        dng_by_name[p.name]=p
    dngs=[dng_by_name[k] for k in sorted(dng_by_name)]

    rows=[]; blind=[]; skipped=[]; a0_parity_max=0.0
    for p in dngs:
        md=select_metadata(p,meta_index)
        if md is None:
            skipped.append({'file':p.name,'reason':'no_capture_audit_with_captureEnergyVsPhotonOnlyEv'})
            continue
        ev=float(md['intentEv'])
        q95=md['previewGlobalQ95']; b240=md['previewBrightFractionGE240']
        positive_intent=ev>1.0e-6
        saturated=bool(q95 is not None and q95>=255.0-1.0e-9)

        cam,neutral,orientation,baseline,iso,rawm=m.read_dng(p,a.long_side)
        xy=dcp.neutral_to_xy(neutral); T=m.cct_from_xy(xy); wA=m.weight_A(T)
        xyz50=dcp.to_xyz50(cam,xy,wA); xyz_scene=xyz50@m.bradford(m.D50_XY,xy).T
        M9CM=m.interp(m.M9_CM_A,m.M9_CM_D65,wA); mcam=xyz_scene@M9CM.T
        mwhite=M9CM@m.xy_to_xyz(xy); m9=np.maximum(mcam/np.maximum(mwhite[None,None,:],1e-8),0.0)
        xyz65=xyz50@m.bradford(m.D50_XY,m.D65_XY).T; prox=xyz65@m.XYZ2SRGB.T
        y=np.maximum(.2126*prox[...,0]+.7152*prox[...,1]+.0722*prox[...,2],0)

        # A0 must be numerically identical to the frozen renderer meter.
        frozen_gain,_=m.tc20_meter(y,rawm,baseline)
        parity_gp=gain_pack(m,y,rawm,baseline,ev,0.0)
        parity_err=abs(float(frozen_gain)-float(parity_gp['gainA0']))
        a0_parity_max=max(a0_parity_max,parity_err)
        if parity_err>A0_PARITY_EPS:
            raise RuntimeError(f'A0 TC20 parity failure {p.name}: frozen={frozen_gain:.12g} replay={parity_gp["gainA0"]:.12g} err={parity_err:.3g}')

        variants=[]; frame_rows=[]; a0_metrics=None
        for cap in CAPS:
            gp=gain_pack(m,y,rawm,baseline,ev,cap)
            name='A0' if cap==0 else f'A1_{int(round(cap*100)):03d}'
            gain=gp['gainA0'] if cap==0 else gp['gainCandidate']
            img,met=m9_stage_metrics(m,m9,gain,curve,3,False)
            if name=='A0':a0_metrics=met.copy()
            pil=m.orient_image(Image.fromarray((img*255+.5).astype(np.uint8)),orientation)
            q=out/'renders'/f'{p.stem}_{name}.jpg'; pil.save(q,quality=95,subsampling=0)
            row={'file':p.name,'variant':name,'iso':iso,'cct':T,'baselineExposureEv':baseline,
                 'metadataSource':md['source']['metadataSource'],'metadataKind':md['source']['metadataKind'],
                 'metadataCandidateCount':md['metadataCandidateCount'],'metadataUsableIntentCount':md['metadataUsableIntentCount'],
                 'intentSourcePath':md['intentSourcePath'],'previewGlobalQ95':q95,
                 'previewGlobalQ95Source':md['previewGlobalQ95Source'],'previewBrightFractionGE240':b240,
                 'previewBrightFractionGE240Source':md['previewBrightFractionGE240Source'],
                 'positiveIntent':positive_intent,'saturatedPreviewSafetyCohort':saturated,
                 'physicalHardClipFraction':rawm['raw_hard_clip_fraction'],'a0FrozenParityAbsError':parity_err,
                 **gp,**met}
            frame_rows.append(row); variants.append((name,q))

        gp=gain_pack(m,y,rawm,baseline,ev,.20)
        img,met=m9_stage_metrics(m,m9,gp['gainCandidate'],curve,3,True)
        pil=m.orient_image(Image.fromarray((img*255+.5).astype(np.uint8)),orientation)
        q=out/'renders'/f'{p.stem}_A2_020.jpg'; pil.save(q,quality=95,subsampling=0)
        frame_rows.append({'file':p.name,'variant':'A2_020','iso':iso,'cct':T,'baselineExposureEv':baseline,
                 'metadataSource':md['source']['metadataSource'],'metadataKind':md['source']['metadataKind'],
                 'metadataCandidateCount':md['metadataCandidateCount'],'metadataUsableIntentCount':md['metadataUsableIntentCount'],
                 'intentSourcePath':md['intentSourcePath'],'previewGlobalQ95':q95,
                 'previewGlobalQ95Source':md['previewGlobalQ95Source'],'previewBrightFractionGE240':b240,
                 'previewBrightFractionGE240Source':md['previewBrightFractionGE240Source'],
                 'positiveIntent':positive_intent,'saturatedPreviewSafetyCohort':saturated,
                 'physicalHardClipFraction':rawm['raw_hard_clip_fraction'],'a0FrozenParityAbsError':parity_err,
                 **gp,**met})
        variants.append(('A2_020',q))

        if a0_metrics is None:raise RuntimeError('internal A0 metrics missing')
        for row in frame_rows:
            row['renderCenterMedianDeltaVsA0']=row['renderCenterMedian']-a0_metrics['renderCenterMedian']
            row['renderGlobalMedianDeltaVsA0']=row['renderGlobalMedian']-a0_metrics['renderGlobalMedian']
            row['renderNearWhiteDeltaVsA0']=row['renderNearWhiteFraction']-a0_metrics['renderNearWhiteFraction']
            row['renderAnyChannelFullClipDeltaVsA0']=row['renderAnyChannelFullClipFraction']-a0_metrics['renderAnyChannelFullClipFraction']
            row['deepBlackDeltaVsA0']=row['deepBlackFraction']-a0_metrics['deepBlackFraction']
            row['matrixIndexHighClipDeltaVsA0']=row['matrixIndexHighClipFraction']-a0_metrics['matrixIndexHighClipFraction']
        rows.extend(frame_rows)

        rng=random.Random(a.seed+int(hashlib.sha1(p.name.encode()).hexdigest()[:8],16)); rng.shuffle(variants)
        labels=['P','Q','R','S','T']; coded=[]
        for lab,(true,q) in zip(labels,variants):
            coded.append((lab,q)); blind.append({'file':p.name,'blind':lab,'variant':true})
        contact(coded,out/'contacts'/f'{p.stem}_blind.jpg',cols=5)
        print('done',p.name,'actualIntent',round(ev,3),'q95',q95,'clip%',round(100*rawm['raw_hard_clip_fraction'],3),flush=True)

    if not rows:
        raise SystemExit('No matching DNG + authoritative m9ExposureAudit captureEnergyVsPhotonOnlyEv records found')

    with (out/'metadata'/'tc20intent1a_metrics.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with (out/'metadata'/'blind_key.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['file','blind','variant']);w.writeheader();w.writerows(blind)
    if skipped:
        with (out/'metadata'/'skipped.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['file','reason']);w.writeheader();w.writerows(skipped)

    corpus={
        'jsonFilesScanned':json_scanned,
        'dngPathsDiscovered':len(all_dngs),
        'uniqueDngBasenames':len(dngs),
        'renderedDngCount':len({r['file'] for r in rows}),
        'skippedDngCount':len(skipped),
        'duplicateDngBasenameCount':len(duplicate_dng_names),
        'positiveIntentCount':len({r['file'] for r in rows if r['positiveIntent']}),
        'saturatedPreviewSafetyCount':len({r['file'] for r in rows if r['saturatedPreviewSafetyCohort']}),
        'positiveSaturatedPreviewSafetyCount':len({r['file'] for r in rows if r['positiveIntent'] and r['saturatedPreviewSafetyCohort']}),
        'a0FrozenParityMaxAbsError':a0_parity_max,
    }
    (out/'metadata'/'summary.json').write_text(json.dumps(build_summary(rows,corpus),indent=2))
    manifest={'schema':'m9cam.tc20intent1a.offline.v2','researchOnly':True,**corpus,
      'variants':['A0','A1_010','A1_020','A1_030','A2_020'],
      'intentSource':'m9ExposureAudit.derived.captureEnergyVsPhotonOnlyEv from exact DNG-matched capture metadata',
      'metadataRecovery':'standalone capture JSON plus SIDECAR diagnostic-bundle capture_metadata payload indexing',
      'preservedIntent':'min(max(actualAchievedEv,0),testCap)',
      'A0':'frozen TC20 and asserted against authoritative renderer tc20_meter',
      'A1':'virtual median and virtual physical-derived TC20 tail; physical RAW safety telemetry retained',
      'A2':'A1_020 gain plus deferred pre-matrix RAW_MAX clamp; research clipping-location probe only',
      'safetyCohort':'preview globalQ95 == 255 reported separately; does not vote on ordinary preferred strength',
      'frozen':'Cobalt/HSM, M9 bridge, SAT3 M06/M07, curve02, exact BT601, JPEG95, DNG pixels'}
    (out/'metadata'/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print('CREATED',out,'rendered',corpus['renderedDngCount'],'positive',corpus['positiveIntentCount'],
          'safety',corpus['saturatedPreviewSafetyCount'],'A0 parity max',a0_parity_max)

if __name__=='__main__':main()
