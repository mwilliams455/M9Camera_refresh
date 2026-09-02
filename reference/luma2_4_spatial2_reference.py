#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math
from pathlib import Path

DARK64_LOW=.20; DARK64_HIGH=.35
BRIGHT192_LOW=.04; BRIGHT192_HIGH=.10
SEP_LOW=60.; SEP_HIGH=110.
ENERGY_FULL=1.; ENERGY_ZERO=2.5
ABS_FLOOR=.62
CENTER_START=16.; CENTER_FULL=28.
CATA_ENERGY_FULL=.03; CATA_ENERGY_ZERO=.12
CATA_MED_FULL=32.; CATA_MED_ZERO=64.
CATA_Q95_FULL=64.; CATA_Q95_ZERO=96.
CATA_Q99_FULL=80.; CATA_Q99_ZERO=112.
LAND_BRIGHT_LOW=.15; LAND_BRIGHT_HIGH=.20
LAND_TOP_SHARE_LOW=.72; LAND_TOP_SHARE_HIGH=.90
LAND_HET_LOW=.28; LAND_HET_HIGH=.55
SP_DARK_LOW=.28; SP_DARK_HIGH=.35
SP_Q95_LOW=135.; SP_Q95_HIGH=175.
SP_BRIGHT_LOW=.008; SP_BRIGHT_HIGH=.035
SP_AXIS_LOW=.30; SP_AXIS_HIGH=.48
SP_LOW_RATIO_FULL=.28; SP_LOW_RATIO_ZERO=.40
APPLY=.50; EV_LOW=.35; EV_HIGH=.85; MAX_EV=.75

def clamp(v): return max(0.,min(1.,v))
def smooth(v,lo,hi):
    if hi<=lo: return 1. if v>=hi else 0.
    t=clamp((v-lo)/(hi-lo)); return t*t*(3-2*t)
def rng3(a,b,c): return max(a,b,c)-min(a,b,c)

def spatial_features(sp,q95):
    if not sp or not sp.get('valid') or q95<=0: return None
    h=sp['displayHorizontalThirds']; v=sp['displayVerticalThirds']; tiles=sp['tiles']
    hm=[float(h[k]['median']) for k in ('top','middle','bottom')]
    vm=[float(v[k]['median']) for k in ('left','center','right')]
    axis=max(max(hm)-min(hm),max(vm)-min(vm))
    low=min(hm+vm)
    names=('topLeft','topCenter','topRight','middleLeft','middleCenter','middleRight','bottomLeft','bottomCenter','bottomRight')
    fs=[max(0.,float(tiles[k]['brightFractionGE192'])) for k in names]
    total=sum(fs); top_share=sum(fs[:3])/total if total>1e-12 else 0.
    topmed=[float(tiles[k]['median']) for k in names[:3]]
    return dict(axis_y=axis,axis_norm=axis/max(1.,q95),low_y=low,low_ratio=low/max(1.,q95),top_share=top_share,top_heter=(max(topmed)-min(topmed))/max(1.,q95))

def score(root):
    p=root['photonExposureDecision']['preview']; l=root['subjectMotion']['previewLuma']; g=l['global']; c=l.get('center50',{})
    energy=float(p['exposureEnergyIsoSeconds']); dark=float(g['darkFractionLE64']); bright=float(g['brightFractionGE192'])
    med=float(g['median']); q95=float(g['q95']); q99=float(g['q99']); sep=float(g.get('q95MinusMedian',q95-med)); cd=float(c.get('medianMinusGlobalMedian',float('nan')))
    darks=smooth(dark,DARK64_LOW,DARK64_HIGH); brs=smooth(bright,BRIGHT192_LOW,BRIGHT192_HIGH); seps=smooth(sep,SEP_LOW,SEP_HIGH)
    rel=(max(0,darks*seps))**(1/3) if darks*seps>0 else 0
    struct=clamp(rel*(ABS_FLOOR+(1-ABS_FLOOR)*brs)); en=1-smooth(energy,ENERGY_FULL,ENERGY_ZERO); rawrel=clamp(struct*en)
    cps=smooth(cd,CENTER_START,CENTER_FULL) if math.isfinite(cd) else 0; center_rel=clamp(rawrel*(1-cps))
    ce=1-smooth(energy,CATA_ENERGY_FULL,CATA_ENERGY_ZERO); cm=1-smooth(med,CATA_MED_FULL,CATA_MED_ZERO); cq95=1-smooth(q95,CATA_Q95_FULL,CATA_Q95_ZERO); cq99=1-smooth(q99,CATA_Q99_FULL,CATA_Q99_ZERO)
    cp=cm*cq95*cq99; cprev=cp**(1/3) if cp>0 else 0; cata=clamp(ce*cprev)
    sf=spatial_features(l.get('spatial3x3'),q95)
    lbb=smooth(bright,LAND_BRIGHT_LOW,LAND_BRIGHT_HIGH)
    lts=smooth(sf['top_share'],LAND_TOP_SHARE_LOW,LAND_TOP_SHARE_HIGH) if sf else 0
    lhet=smooth(sf['top_heter'],LAND_HET_LOW,LAND_HET_HIGH) if sf else 0
    lp=lbb*lts*lhet; guard=lp**(1/3) if lp>0 else 0; lm=1-guard
    prel=clamp(center_rel*lm)
    sd=smooth(dark,SP_DARK_LOW,SP_DARK_HIGH); sq=smooth(q95,SP_Q95_LOW,SP_Q95_HIGH); sb=smooth(bright,SP_BRIGHT_LOW,SP_BRIGHT_HIGH)
    sa=smooth(sf['axis_norm'],SP_AXIS_LOW,SP_AXIS_HIGH) if sf else 0
    sl=1-smooth(sf['low_ratio'],SP_LOW_RATIO_FULL,SP_LOW_RATIO_ZERO) if sf else 0
    prod=sd*sq*sb*sa*sl; rawsp=prod**(1/5) if prod>0 else 0; psp=clamp(rawsp*lm)
    final=max(cata,prel,psp); strength=smooth(final,EV_LOW,EV_HIGH); ev=MAX_EV*strength
    return {'finalScore':final,'recommendedEv':ev,'wouldApply':final>=APPLY,'landscapeGuard':guard,'protectedRelative':prel,'catastrophic':cata,'rawSpatial':rawsp,'protectedSpatial':psp,'spatial':sf}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('json',nargs='+'); a=ap.parse_args()
    for f in a.json:
        p=Path(f); r=score(json.loads(p.read_text()))
        print(f"{p.name}: apply={r['wouldApply']} ev={r['recommendedEv']:.3f} final={r['finalScore']:.3f} spatial={r['protectedSpatial']:.3f} guard={r['landscapeGuard']:.3f}")
if __name__=='__main__': main()
