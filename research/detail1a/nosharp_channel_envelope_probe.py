"""M9DETAIL1Z: no-Sharp D/direct interpolation consensus with per-channel RAW evidence.

DETAIL1Y reduced the remaining false-green regressions to eight. All eight are
the same neutral sigma=.5 bright-cool edge/fine-branch fixture across four CFAs.
The common-chroma certificate is insufficient there because R-G and B-G carry
strong opposite/channel-specific evidence.

This probe retains the DETAIL1X common/opponent decomposition but requires any
common-component correction to be non-worsening for R-G AND B-G separately
against nearby fully uncensored native CFA anchors.

Evidence options:
  envelope: candidate distance to each channel's local measured [min,max] may
            not exceed current D distance.
  mean:     candidate absolute error to each channel's local measured mean may
            not exceed current D error.
  both:     both requirements.

Sharp/Noise2 remain disabled. D opponent R-vs-B component is preserved to one
q14 parity unit. No hue, subject, foliage or wildlife classifier.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from scipy.ndimage import gaussian_filter,convolve,minimum_filter,maximum_filter

from green_guide2_probe import cfa_masks,BACKGROUNDS,SUBJECTS
from nosharp_uncensored_consensus_probe import (
    NativePair, fields_from_D, fields_direct, fields_to_rgb, metrics,
    uncensored_masks, llround
)
from rb_domain import DomainProbe

SPECS={
    'r4_c2_env_a25':dict(radius=4,count=2,rule='envelope',alpha=.25),
    'r4_c2_mean_a25':dict(radius=4,count=2,rule='mean',alpha=.25),
    'r4_c2_both_a25':dict(radius=4,count=2,rule='both',alpha=.25),
    'r8_c2_env_a25':dict(radius=8,count=2,rule='envelope',alpha=.25),
    'r8_c2_mean_a25':dict(radius=8,count=2,rule='mean',alpha=.25),
    'r8_c2_both_a25':dict(radius=8,count=2,rule='both',alpha=.25),
    'r4_c4_both_a25':dict(radius=4,count=4,rule='both',alpha=.25),
    'r8_c4_both_a25':dict(radius=8,count=4,rule='both',alpha=.25),
    'r4_c2_both_a50':dict(radius=4,count=2,rule='both',alpha=.50),
    'r8_c2_both_a50':dict(radius=8,count=2,rule='both',alpha=.50),
}

def local_channel_evidence(diff,sensor,cfa,radius,min_count):
    vr,vb=uncensored_masks(sensor,cfa)
    d=np.asarray(diff,np.float64)
    size=2*radius+1
    k=np.ones((size,size),np.float64)
    def one(mask):
        cnt=convolve(mask.astype(np.float64),k,mode='constant',cval=0.)
        sm=convolve(d*mask,k,mode='constant',cval=0.)
        mean=np.divide(sm,cnt,out=np.zeros_like(sm),where=cnt>0)
        big=1e30
        lo=minimum_filter(np.where(mask,d,big),size=size,mode='constant',cval=big)
        hi=maximum_filter(np.where(mask,d,-big),size=size,mode='constant',cval=-big)
        return mean,lo,hi,cnt
    mr,lor,hir,cr=one(vr)
    mb,lob,hib,cb=one(vb)
    available=(cr>=min_count)&(cb>=min_count)
    return mr,lor,hir,cr,mb,lob,hib,cb,available

def interval_distance(x,lo,hi):
    x=np.asarray(x,np.float64)
    return np.maximum(np.maximum(lo-x,0.),x-hi)

def candidate(rD,bD,rI,bI,evidence,spec):
    mr,lor,hir,cr,mb,lob,hib,cb,available=evidence
    sD=rD.astype(np.int64)+bD.astype(np.int64)
    oD=rD.astype(np.int64)-bD.astype(np.int64)
    sI=rI.astype(np.int64)+bI.astype(np.int64)
    conflict=(sD==0)|(sI==0)|((sD<0)&(sI>0))|((sD>0)&(sI<0))

    sp=llround(sD+spec['alpha']*(sI-sD))
    rp=llround((sp+oD)/2.)
    bp=llround((sp-oD)/2.)

    eps=1e-12
    env=(interval_distance(rp,lor,hir)<=interval_distance(rD,lor,hir)+eps)&(
         interval_distance(bp,lob,hib)<=interval_distance(bD,lob,hib)+eps)
    mean=(np.abs(rp-mr)<=np.abs(rD-mr)+eps)&(
          np.abs(bp-mb)<=np.abs(bD-mb)+eps)
    rule=env if spec['rule']=='envelope' else mean if spec['rule']=='mean' else env&mean
    gate=conflict&available&rule

    s=sD.copy();s[gate]=sp[gate]
    r=llround((s+oD)/2.);b=llround((s-oD)/2.)
    assert np.max(np.abs((r-b)-oD))<=1
    return r,b,gate,conflict,available,env,mean,cr,cb

def synthetic(native,probe,cfas):
    yy,xx=np.indices((160,192))
    n=np.array([.41796875,1.,.6435546875]);scale=1.6105431518598052
    rows=[];d_parity=True
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
                        _,du,_,_=probe.stages(norm,cfa,n[0],n[2],shrink=False)
                        _,d,carrier,_=probe.stages(norm,cfa,n[0],n[2],shrink=True)
                        dcam=probe.consume(carrier,base,cfa,n[0],n[2])
                        rD,bD=fields_from_D(carrier,cfa)
                        dcheck=fields_to_rgb(rD,bD,base,n[0],n[2])
                        d_parity &= np.array_equal(dcheck,dcam)
                        assert np.array_equal(dcheck,dcam)
                        rI,bI=fields_direct(d,cfa)
                        truth=np.clip(scene,0,1)
                        mm={'D':metrics(dcam,truth,scale,n)};stats={}
                        cache={}
                        for name,spec in SPECS.items():
                            key=(spec['radius'],spec['count'])
                            if key not in cache:
                                cache[key]=local_channel_evidence(du,sensor,cfa,*key)
                            r,b,gate,conflict,avail,env,mean,cr,cb=candidate(rD,bD,rI,bI,cache[key],spec)
                            cam=fields_to_rgb(r,b,base,n[0],n[2])
                            mm[name]=metrics(cam,truth,scale,n)
                            stats[name]=dict(
                                gate_fraction=float(gate.mean()),
                                conflict_fraction=float(conflict.mean()),
                                evidence_available_fraction=float(avail.mean()),
                                envelope_pass_fraction=float((conflict&avail&env).mean()),
                                mean_pass_fraction=float((conflict&avail&mean).mean()),
                                changed_pixels=int(gate.sum()),
                                mean_red_anchor_count=float(cr.mean()),
                                mean_blue_anchor_count=float(cb.mean()))
                        rows.append(dict(cfa=cfa,shape=shape,sigma=sigma,background=bgname,subject=subject,
                            raw_clipped_fraction=float((sensor>=1023).mean()),metrics=mm,gates=stats))
        print('CFA',cfa,'cases',len(rows),flush=True)

    summary={}
    for mode,spec in SPECS.items():
        summary[mode]={'spec':spec}
        for key in ('scene_rgb_rms','chroma_rms','false_magenta_excess_fraction','false_green_excess_fraction'):
            a=np.array([r['metrics']['D'][key] for r in rows])
            b=np.array([r['metrics'][mode][key] for r in rows]);delta=b-a
            summary[mode][key]=dict(cases_improved=int((delta<-1e-12).sum()),
                cases_worse=int((delta>1e-12).sum()),mean_D=float(a.mean()),
                mean_candidate=float(b.mean()),mean_change=float(delta.mean()),
                max_increase=float(delta.max()),max_reduction=float((-delta).max()),
                worst_case_index=int(delta.argmax()),best_case_index=int(delta.argmin()))
        clipped=np.array([r['raw_clipped_fraction']>0 for r in rows])
        neutral=np.array([r['subject']=='neutral' for r in rows])
        green=np.array([r['subject']=='green' for r in rows])
        mag=np.array([r['subject'] in ('magenta','bright_magenta') for r in rows])
        for subset,sel in [('clipped',clipped),('clipped_neutral',clipped&neutral),
                           ('clipped_green',clipped&green),('clipped_magenta',clipped&mag),
                           ('unclipped',~clipped)]:
            vals={'case_count':int(sel.sum())}
            for key in ('false_magenta_excess_fraction','false_green_excess_fraction'):
                a=np.array([r['metrics']['D'][key] for r in rows])[sel]
                b=np.array([r['metrics'][mode][key] for r in rows])[sel]
                vals[key+'_cases_improved']=int((b<a-1e-12).sum())
                vals[key+'_cases_worse']=int((b>a+1e-12).sum())
                vals[key+'_mean_D']=float(a.mean()) if a.size else 0.
                vals[key+'_mean_candidate']=float(b.mean()) if b.size else 0.
            summary[mode][subset]=vals
        summary[mode]['gate']=dict(
            mean_gate_fraction=float(np.mean([r['gates'][mode]['gate_fraction'] for r in rows])),
            mean_evidence_available_fraction=float(np.mean([r['gates'][mode]['evidence_available_fraction'] for r in rows])),
            changed_pixels_total=int(sum(r['gates'][mode]['changed_pixels'] for r in rows)))

    strict=[m for m in SPECS
            if summary[m]['false_magenta_excess_fraction']['cases_worse']==0
            and summary[m]['false_green_excess_fraction']['cases_worse']==0]
    return dict(schema='m9.detail1z.nosharp_channel_envelope.v1',case_count=len(rows),cfas=list(cfas),
        neutral=n.tolist(),representation_scale=scale,specs=SPECS,
        d_field_rgb_byte_parity=bool(d_parity),strict_zero_false_chroma_regression=strict,
        backgrounds=BACKGROUNDS,subjects=SUBJECTS,summary=summary,cases=rows,
        scope='Sharp disabled. D/direct common-component correction allowed only when per-channel R-G and B-G proposals are non-worsening against local fully uncensored RAW anchor ranges and/or means. D opponent component preserved to <=1 q14 parity unit. No Noise2/hue/subject classifier or APK mutation.')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--assembled',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--cfas',type=int,nargs='+',default=[0,1,2,3])
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    repo=Path(__file__).resolve().parents[2]
    native=NativePair(repo,a.assembled,a.out/'native');probe=DomainProbe(a.out/'native')
    result=synthetic(native,probe,a.cfas)
    result['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['native_source_sha256']=native.source_sha256
    cases=result.pop('cases')
    (a.out/'report.json').write_text(json.dumps(result,indent=2)[:-2]+',\n  "cases": [\n'+
        ',\n'.join('    '+json.dumps(r) for r in cases)+'\n  ]\n}\n')
    print(json.dumps(dict(d_field_rgb_byte_parity=result['d_field_rgb_byte_parity'],
        strict_zero_false_chroma_regression=result['strict_zero_false_chroma_regression'],
        summary=result['summary']),indent=2))

if __name__=='__main__':main()
