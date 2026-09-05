#!/usr/bin/env python3
"""TC20PLACEMENT1A offline replay harness.

Research-only. Frozen photographic rendering stays unchanged. This harness keeps
scene-key placement and intentional-EV preservation mathematically separate.

Placement bank:
  A0       frozen TC20
  P1_015   median-target hold -0.15 EV
  P1_030   median-target hold -0.30 EV
  P1_045   median-target hold -0.45 EV
  P1_060   diagnostic endpoint -0.60 EV

Intent bank:
  A0       frozen TC20
  A1_010   preserve up to +0.10 EV achieved capture intent
  A1_020   preserve up to +0.20 EV achieved capture intent
  A1_030   preserve up to +0.30 EV achieved capture intent
  A2_020   A1_020 gain with deferred pre-matrix RAW_MAX clamp

Scene-key hold modifies the TC20 median target BEFORE median-vs-highlight
arbitration. It is not a post-render exposure subtraction. Intent preservation
virtually normalizes both TC20 median and TC20 tail by achieved positive intent
before the meter calculation. Physical RAW evidence is always retained.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, random, sys
from pathlib import Path
import numpy as np
from PIL import Image

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
import tc20intent1a_replay as core

PLACEMENT_HOLDS=(0.0,-0.15,-0.30,-0.45,-0.60)
INTENT_CAPS=(0.10,0.20,0.30)
A0_PARITY_EPS=core.A0_PARITY_EPS


def load_curve(m,firmware,curve02):
    if (firmware is None)==(curve02 is None):
        raise SystemExit('provide exactly one of --firmware or --curve02')
    if firmware is not None:return m.extract_curve02(firmware)
    b=curve02.read_bytes()
    if len(b)!=2048:raise SystemExit(f'--curve02 must be exact 2048-byte curve02, got {len(b)}')
    return np.frombuffer(b,dtype=np.uint8).copy()


def gain_pack(m,y,rawm,baseline_ev,intent_ev,scene_hold_ev=0.0,intent_cap_ev=0.0):
    physical_median=core.weighted_median_y(m,y)
    physical_tail=float(rawm['tc20_tail_value'])
    achieved=max(float(intent_ev),0.0)
    preserved=min(achieved,max(float(intent_cap_ev),0.0))
    k=2.0**preserved
    virtual_median=physical_median/k
    virtual_tail=physical_tail/k
    scale=2.0**baseline_ev

    base_physical=float(np.clip(m.METER_TARGET_RENORM/max(physical_median,1e-6),.5,16.0))*scale
    guard_physical=max(1.0,m.TC_HEADROOM_TARGET/max(physical_tail,1e-9))
    gain_a0=float(min(base_physical,guard_physical))
    binding_a0='guard' if guard_physical<=base_physical else 'median'

    held_target=float(m.METER_TARGET_RENORM)*(2.0**float(scene_hold_ev))
    base_candidate=float(np.clip(held_target/max(virtual_median,1e-6),.5,16.0))*scale
    guard_candidate=max(1.0,m.TC_HEADROOM_TARGET/max(virtual_tail,1e-9))
    gain_candidate=float(min(base_candidate,guard_candidate))
    binding_candidate='guard' if guard_candidate<=base_candidate else 'median'

    return dict(actualCaptureEnergyVsPhotonOnlyEv=float(intent_ev),
        achievedPositiveIntentEv=achieved,preservedIntentEv=preserved,
        sceneKeyHoldEv=float(scene_hold_ev),physicalMedian=physical_median,
        physicalTail=physical_tail,virtualMedian=virtual_median,virtualTail=virtual_tail,
        frozenMedianTarget=float(m.METER_TARGET_RENORM),candidateMedianTarget=held_target,
        baseMedianGainPhysical=base_physical,guardGainPhysical=guard_physical,
        baseMedianGainCandidate=base_candidate,guardGainCandidate=guard_candidate,
        physicalBinding=binding_a0,candidateBinding=binding_candidate,
        gainA0=gain_a0,gainCandidate=gain_candidate,
        gainDeltaVsA0Ev=math.log2(max(gain_candidate,1e-12)/max(gain_a0,1e-12)),
        physicalTailTimesGain=physical_tail*gain_candidate,
        medianTimesGain=physical_median*gain_candidate)


def oriented_luma(m,img,orientation):
    pil=m.orient_image(Image.fromarray((img*255+.5).astype(np.uint8)),orientation)
    a=np.asarray(pil,dtype=np.float64)/255.0
    return pil,.2126*a[...,0]+.7152*a[...,1]+.0722*a[...,2]


def regional_metrics(lum,rows=4,cols=6):
    h,w=lum.shape; med=[]; q90=[]; q95=[]
    for ry in range(rows):
        y0=(ry*h)//rows;y1=((ry+1)*h)//rows
        for rx in range(cols):
            x0=(rx*w)//cols;x1=((rx+1)*w)//cols;r=lum[y0:y1,x0:x1]
            med.append(float(np.median(r)));q90.append(float(np.quantile(r,.90)));q95.append(float(np.quantile(r,.95)))
    cy0,cy1=int(.25*h),int(.75*h);cx0,cx1=int(.25*w),int(.75*w);center=lum[cy0:cy1,cx0:cx1]
    order=np.argsort(q95)[::-1]
    return dict(renderCenterQ90=float(np.quantile(center,.90)),renderCenterQ95=float(np.quantile(center,.95)),
        renderRegionMedian4x6=json.dumps(med,separators=(',',':')),
        renderRegionQ90_4x6=json.dumps(q90,separators=(',',':')),
        renderRegionQ95_4x6=json.dumps(q95,separators=(',',':')),
        renderRegionQ95Max=float(max(q95)),renderRegionQ95Mean=float(np.mean(q95)),
        renderRegionQ95Top4Mean=float(np.mean([q95[i] for i in order[:4]])),
        renderRegionMedianMin=float(min(med)),renderRegionMedianMax=float(max(med)),
        renderRegionMedianSpan=float(max(med)-min(med)))


def math_selfcheck(m):
    B,H=2.0850,1.2941
    placement={f'{h:+.2f}':min(B*(2**h),H) for h in (0.0,-.15,-.30,-.45,-.60)}
    placement_ok=all(abs(v-H)<1e-9 for k,v in placement.items() if k!='+0.00')
    intent={}
    intent_ok=True
    for branch,B0,H0 in [('median',2.0,5.0),('guard',10.0,1.5)]:
        g0=min(B0,H0);vals={}
        for p in (.10,.20,.30):
            g=min(B0*(2**p),H0*(2**p));d=math.log2(g/g0);intent_ok&=abs(d-p)<1e-12
            vals[f'{p:.2f}']={'gain':g,'deltaEv':d,'binding':branch}
        intent[branch]=vals
    out={'placementGuardBoundExample':placement,'placementGuardUnchangedThroughMinus060':placement_ok,
         'placementSwitchHoldEv':math.log2(H/B),'intentScaling':intent,'intentExactScaling':bool(intent_ok),
         'guardTailAfterIntent':{f'{p:.2f}':float(m.TC_HEADROOM_TARGET*(2**p)) for p in (.10,.20,.30)},
         'guardTailUnityCrossingEv':math.log2(1.0/float(m.TC_HEADROOM_TARGET))}
    if not placement_ok or not intent_ok:raise RuntimeError('TC20PLACEMENT1A mathematical self-check failed')
    return out


def mean_or_none(vals):
    vals=[float(v) for v in vals if v is not None and math.isfinite(float(v))]
    return float(np.mean(vals)) if vals else None


def build_summary(rows,corpus):
    out={'schema':'m9cam.tc20placement1a.summary.v1','corpus':corpus,'variants':{}}
    for v in sorted({r['variant'] for r in rows}):
        vr=[r for r in rows if r['variant']==v]
        groups={'all':vr,'zeroIntent':[r for r in vr if not r['positiveIntent']],
                'positiveIntent':[r for r in vr if r['positiveIntent']],
                'a0MedianLimited':[r for r in vr if r['physicalBinding']=='median'],
                'a0GuardLimited':[r for r in vr if r['physicalBinding']=='guard']}
        out['variants'][v]={}
        for name,g in groups.items():
            out['variants'][v][name]={'count':len(g),
                'meanGainDeltaVsA0Ev':mean_or_none([r['gainDeltaVsA0Ev'] for r in g]),
                'meanGlobalMedianDeltaVsA0':mean_or_none([r['renderGlobalMedianDeltaVsA0'] for r in g]),
                'meanCenterMedianDeltaVsA0':mean_or_none([r['renderCenterMedianDeltaVsA0'] for r in g]),
                'meanCenterQ95DeltaVsA0':mean_or_none([r['renderCenterQ95DeltaVsA0'] for r in g]),
                'meanRegionQ95Top4DeltaVsA0':mean_or_none([r['renderRegionQ95Top4MeanDeltaVsA0'] for r in g]),
                'meanNearWhiteDeltaVsA0':mean_or_none([r['renderNearWhiteFractionDeltaVsA0'] for r in g]),
                'meanFullClipDeltaVsA0':mean_or_none([r['renderAnyChannelFullClipFractionDeltaVsA0'] for r in g])}
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('root',type=Path);ap.add_argument('--renderer',type=Path,required=True);ap.add_argument('--dcp',type=Path,required=True)
    src=ap.add_mutually_exclusive_group(required=True);src.add_argument('--firmware',type=Path);src.add_argument('--curve02',type=Path)
    ap.add_argument('--out',type=Path,default=Path('TC20PLACEMENT1A_RESULTS'));ap.add_argument('--long-side',type=int,default=1600);ap.add_argument('--seed',type=int,default=920260905)
    a=ap.parse_args();m=core.load_renderer(a.renderer);curve=load_curve(m,a.firmware,a.curve02);dcp=m.CobaltDCP(a.dcp)
    out=a.out;out.mkdir(parents=True,exist_ok=True)
    for d in ('renders','contacts','metadata'):(out/d).mkdir(exist_ok=True)
    (out/'metadata'/'math_selfcheck.json').write_text(json.dumps(math_selfcheck(m),indent=2))

    meta_index,json_scanned=core.build_metadata_index(a.root);all_dngs=sorted(a.root.rglob('*.dng'));dng_by_name={};duplicates={}
    for p in all_dngs:
        if p.name in dng_by_name:duplicates.setdefault(p.name,[str(dng_by_name[p.name])]).append(str(p));continue
        dng_by_name[p.name]=p
    dngs=[dng_by_name[k] for k in sorted(dng_by_name)]
    variants=[('A0',0.0,0.0,False)]
    variants += [(f'P1_{int(round(abs(h)*100)):03d}',h,0.0,False) for h in PLACEMENT_HOLDS if h<0]
    variants += [(f'A1_{int(round(c*100)):03d}',0.0,c,False) for c in INTENT_CAPS]
    variants += [('A2_020',0.0,0.20,True)]

    rows=[];blind=[];skipped=[];a0_parity_max=0.0
    for p in dngs:
        md=core.select_metadata(p,meta_index)
        if md is None:skipped.append({'file':p.name,'reason':'no_capture_audit_with_captureEnergyVsPhotonOnlyEv'});continue
        ev=float(md['intentEv']);q95=md['previewGlobalQ95'];b240=md['previewBrightFractionGE240'];positive=ev>1e-6;saturated=bool(q95 is not None and q95>=255.0-1e-9)
        cam,neutral,orientation,baseline,iso,rawm=m.read_dng(p,a.long_side);xy=dcp.neutral_to_xy(neutral);T=m.cct_from_xy(xy);wA=m.weight_A(T)
        xyz50=dcp.to_xyz50(cam,xy,wA);xyz_scene=xyz50@m.bradford(m.D50_XY,xy).T;M9CM=m.interp(m.M9_CM_A,m.M9_CM_D65,wA);mcam=xyz_scene@M9CM.T;mwhite=M9CM@m.xy_to_xyz(xy);m9=np.maximum(mcam/np.maximum(mwhite[None,None,:],1e-8),0.0)
        xyz65=xyz50@m.bradford(m.D50_XY,m.D65_XY).T;prox=xyz65@m.XYZ2SRGB.T;y=np.maximum(.2126*prox[...,0]+.7152*prox[...,1]+.0722*prox[...,2],0)
        frozen_gain,_=m.tc20_meter(y,rawm,baseline);parity=gain_pack(m,y,rawm,baseline,ev,0.0,0.0);parity_err=abs(float(frozen_gain)-float(parity['gainA0']));a0_parity_max=max(a0_parity_max,parity_err)
        if parity_err>A0_PARITY_EPS:raise RuntimeError(f'A0 TC20 parity failure {p.name}: {frozen_gain} vs {parity["gainA0"]}')

        frame_rows=[];paths={};a0=None
        for name,hold,cap,defer in variants:
            gp=gain_pack(m,y,rawm,baseline,ev,hold,cap);gain=gp['gainA0'] if name=='A0' else gp['gainCandidate'];img,met=core.m9_stage_metrics(m,m9,gain,curve,3,defer);pil,lum=oriented_luma(m,img,orientation);reg=regional_metrics(lum);q=out/'renders'/f'{p.stem}_{name}.jpg';pil.save(q,quality=95,subsampling=0);paths[name]=q
            row={'file':p.name,'variant':name,'iso':iso,'cct':T,'baselineExposureEv':baseline,'metadataSource':md['source']['metadataSource'],'metadataKind':md['source']['metadataKind'],'intentSourcePath':md['intentSourcePath'],'previewGlobalQ95':q95,'previewBrightFractionGE240':b240,'positiveIntent':positive,'saturatedPreviewSafetyCohort':saturated,'physicalHardClipFraction':rawm['raw_hard_clip_fraction'],'a0FrozenParityAbsError':parity_err,**gp,**met,**reg}
            if name=='A0':a0=row.copy()
            frame_rows.append(row)
        if a0 is None:raise RuntimeError('internal A0 metrics missing')
        for row in frame_rows:
            for key in ('renderGlobalMedian','renderCenterMedian','renderCenterQ95','renderRegionQ95Top4Mean','renderNearWhiteFraction','renderAnyChannelFullClipFraction','deepBlackFraction','matrixIndexHighClipFraction'):
                row[key+'DeltaVsA0']=float(row[key])-float(a0[key])
        rows.extend(frame_rows)
        for bank,names in [('placement',['A0','P1_015','P1_030','P1_045','P1_060']),('intent',['A0','A1_010','A1_020','A1_030','A2_020'])]:
            items=[(n,paths[n]) for n in names];rng=random.Random(a.seed+int(hashlib.sha1((p.name+bank).encode()).hexdigest()[:8],16));rng.shuffle(items);coded=[]
            for lab,(true,path) in zip(['P','Q','R','S','T'],items):coded.append((lab,path));blind.append({'file':p.name,'bank':bank,'blind':lab,'variant':true})
            core.contact(coded,out/'contacts'/f'{p.stem}_{bank}_blind.jpg',cols=5)
        print('done',p.name,'iso',iso,'intent',round(ev,3),'binding',a0['physicalBinding'],'gain',round(a0['gainA0'],3),flush=True)

    if not rows:raise SystemExit('No matching DNG + authoritative capture-audit records found')
    with (out/'metadata'/'tc20placement1a_metrics.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with (out/'metadata'/'blind_key.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=['file','bank','blind','variant']);w.writeheader();w.writerows(blind)
    if skipped:
        with (out/'metadata'/'skipped.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=['file','reason']);w.writeheader();w.writerows(skipped)
    corpus={'jsonFilesScanned':json_scanned,'dngPathsDiscovered':len(all_dngs),'uniqueDngBasenames':len(dngs),'renderedDngCount':len({r['file'] for r in rows}),'skippedDngCount':len(skipped),'duplicateDngBasenameCount':len(duplicates),'positiveIntentCount':len({r['file'] for r in rows if r['positiveIntent']}),'zeroIntentCount':len({r['file'] for r in rows if not r['positiveIntent']}),'a0FrozenParityMaxAbsError':a0_parity_max}
    (out/'metadata'/'summary.json').write_text(json.dumps(build_summary(rows,corpus),indent=2))
    manifest={'schema':'m9cam.tc20placement1a.offline.v1','researchOnly':True,**corpus,'placementVariants':['A0','P1_015','P1_030','P1_045','P1_060'],'intentVariants':['A0','A1_010','A1_020','A1_030','A2_020'],'sceneKeySemantics':'median target multiplied by 2^hold before median-vs-highlight arbitration','intentSemantics':'physical median and tail divided by 2^preservedIntent before TC20 calculation','regionalTelemetry':'oriented rendered 4x6 medians/q90/q95 plus center q90/q95','frozen':'Cobalt/HSM, M9 bridge, SAT3 M06/M07, curve02, exact BT601, JPEG95, DNG pixels'}
    (out/'metadata'/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print('CREATED',out,'rendered',corpus['renderedDngCount'],'positive',corpus['positiveIntentCount'],'zero',corpus['zeroIntentCount'],'A0 parity max',a0_parity_max)

if __name__=='__main__':main()
