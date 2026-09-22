"""M9DETAIL1J research: edge-directed diagonal R/B carrier.

The current reconstruction averages four diagonal opposite-colour differences at
every R/B site.  This probe keeps the existing difference producer, native
green/ISO160 Sharp, colour and exposure fixed, and changes only that diagonal
carrier.  A two-diagonal choice uses the existing green estimate as an edge
cost.  Clipping-gated variants act only near original sensor-white samples.

Synthetic falsification only.  No Android source/APK change.
"""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
from scipy.ndimage import gaussian_filter, maximum_filter

from rb_domain import DomainProbe
from green_guide2_probe import NativeBaseline,cfa_masks,BACKGROUNDS,SUBJECTS,restored

VARIANTS=('pair_global','pair_clip2','pair_clip4','pair_conf2_clip4','pair_conf4_clip4','pair_valid_clip4','pair_valid_conf2_clip4')

def shifted(a,dy,dx):
    return np.roll(np.roll(a,dy,axis=0),dx,axis=1)

def carrier_controls(green,diff,current,sensor,cfa,white):
    g=green.astype(np.int64); d=diff.astype(np.int64)
    gnw,gne,gsw,gse=[shifted(g,dy,dx) for dy,dx in ((1,1),(1,-1),(-1,1),(-1,-1))]
    dnw,dne,dsw,dse=[shifted(d,dy,dx) for dy,dx in ((1,1),(1,-1),(-1,1),(-1,-1))]
    snw,sne,ssw,sse=[shifted(sensor,dy,dx) for dy,dx in ((1,1),(1,-1),(-1,1),(-1,-1))]
    cost_main=np.abs(gnw-gse)+np.abs(gnw-g)+np.abs(gse-g)
    cost_anti=np.abs(gne-gsw)+np.abs(gne-g)+np.abs(gsw-g)
    main=(dnw+dse)//2; anti=(dne+dsw)//2
    choose_main=cost_main<cost_anti; choose_anti=cost_anti<cost_main
    pair=np.where(choose_main,main,np.where(choose_anti,anti,current.astype(np.int64)))
    best=np.minimum(cost_main,cost_anti); other=np.maximum(cost_main,cost_anti)
    conf2=(2*best<other)&(best<other)
    conf4=(4*best<other)&(best<other)
    valid_main=(snw<white)&(sse<white)
    valid_anti=(sne<white)&(ssw<white)
    one_main=valid_main&~valid_anti; one_anti=valid_anti&~valid_main
    both=valid_main&valid_anti
    valid_pair=np.where(one_main,main,np.where(one_anti,anti,
        np.where(both&choose_main,main,np.where(both&choose_anti,anti,current.astype(np.int64)))))
    valid_available=valid_main|valid_anti
    valid_conf=(one_main|one_anti)|(both&conf2)
    _,_,green_sites=cfa_masks(g.shape,cfa)
    inner=np.zeros(g.shape,bool); inner[3:-3,3:-3]=True
    rb=(~green_sites)&inner
    return dict(pair=np.where(rb,pair,current).astype(np.int32),
        conf2=rb&conf2,conf4=rb&conf4,
        valid_pair=np.where(rb,valid_pair,current).astype(np.int32),
        valid_available=rb&valid_available,valid_conf=rb&valid_conf)

def variants(probe,norm,sensor,cfa,nr,nb,white):
    green,diff,current,_=probe.stages(norm,cfa,nr,nb,shrink=True)
    ctl=carrier_controls(green,diff,current,sensor,cfa,white)
    clipped=sensor>=white
    support2=maximum_filter(clipped,size=5,mode='constant')
    support4=maximum_filter(clipped,size=9,mode='constant')
    specs={
        'pair_global':(np.ones(norm.shape,bool),ctl['pair']),
        'pair_clip2':(support2,ctl['pair']),
        'pair_clip4':(support4,ctl['pair']),
        'pair_conf2_clip4':(support4&ctl['conf2'],ctl['pair']),
        'pair_conf4_clip4':(support4&ctl['conf4'],ctl['pair']),
        'pair_valid_clip4':(support4&ctl['valid_available'],ctl['valid_pair']),
        'pair_valid_conf2_clip4':(support4&ctl['valid_conf'],ctl['valid_pair']),
    }
    for name in VARIANTS:
        support,candidate=specs[name]
        carrier=np.where(support,candidate,current).astype(np.int32)
        yield name,carrier,support

def variants(probe,norm,sensor,cfa,nr,nb,white):
    green,diff,current,_=probe.stages(norm,cfa,nr,nb,shrink=True)
    pair=pair_carrier(green,diff,current,cfa)
    clipped=sensor>=white
    supports={
        'pair_global':np.ones(norm.shape,bool),
        'pair_clip2':maximum_filter(clipped,size=5,mode='constant'),
        'pair_clip4':maximum_filter(clipped,size=9,mode='constant'),
    }
    for name in VARIANTS:
        carrier=np.where(supports[name],pair,current).astype(np.int32)
        yield name,carrier,supports[name]

def synthetic(native,probe,cfas):
    yy,xx=np.indices((160,192)); n=np.array([.41796875,1.,.6435546875]); scale=1.6105431518598052
    rows=[]
    for cfa in cfas:
        red,blue,_=cfa_masks(xx.shape,cfa)
        for shape in ('edge','fine_branches'):
            coord=xx+yy*.43; mask=coord>120 if shape=='edge' else coord%15<4
            for sigma in (0.,.5,1.,2.):
                for bgname,bg in BACKGROUNDS.items():
                    for subject,fg in SUBJECTS.items():
                        scene=np.where(mask[...,None],fg,bg).astype(float)
                        if sigma: scene=gaussian_filter(scene,[sigma,sigma,0])
                        observed=np.minimum(scene*n,1.)
                        samples=np.where(red,observed[...,0],np.where(blue,observed[...,2],observed[...,1]))
                        sensor=np.floor(64+samples*959+.5).astype(np.uint16)
                        norm=np.floor((sensor.astype(float)-64)/959/scale*65535+.5).astype(np.uint16)
                        base=native.render(norm,n[0],n[2],cfa)
                        current=probe.stages(norm,cfa,n[0],n[2],shrink=True)[2]
                        dcam=probe.consume(current,base,cfa,n[0],n[2])
                        clipped=np.clip(scene,0,1); truth=clipped[16:-16,16:-16]
                        sg=base[...,1].astype(float)/65535*scale
                        fixed=np.clip(clipped-clipped[...,[1]]+sg[...,None],0,1)[16:-16,16:-16]
                        cams={'D':dcam}; support_fraction={}
                        for name,carrier,support in variants(probe,norm,sensor,cfa,n[0],n[2],1023):
                            cams[name]=probe.consume(carrier,base,cfa,n[0],n[2])
                            support_fraction[name]=float(support.mean())
                        row=dict(cfa=cfa,shape=shape,sigma=sigma,background=bgname,subject=subject,
                                 support_fraction=support_fraction,metrics={})
                        for name,cam in cams.items():
                            z=restored(cam,scale,n)[16:-16,16:-16]
                            chroma=z[...,[0,2]]-z[...,[1]]
                            pink=(chroma[...,0]>.02)&(chroma[...,1]>.02)
                            row['metrics'][name]=dict(
                                scene_rgb_rms=float(np.sqrt(np.mean((z-truth)**2))),
                                fixed_green_rb_rms=float(np.sqrt(np.mean((z[...,[0,2]]-fixed[...,[0,2]])**2))),
                                pink_fraction=float(pink.mean()))
                        rows.append(row)
        print('CFA',cfa,'cases',len(rows),flush=True)
    summary={}
    for mode in VARIANTS:
        summary[mode]={}
        for metric in ('scene_rgb_rms','fixed_green_rb_rms'):
            delta=np.array([r['metrics'][mode][metric]-r['metrics']['D'][metric] for r in rows])
            coloured=np.array([r['subject']!='neutral' for r in rows])
            summary[mode][metric]=dict(
                cases_worse_than_D=int((delta>1e-12).sum()),
                coloured_cases_worse_than_D=int(((delta>1e-12)&coloured).sum()),
                max_rms_increase=float(delta.max()),mean_rms_change=float(delta.mean()),
                worst_case_index=int(delta.argmax()))
        neutral=[r for r in rows if r['subject']=='neutral']
        d=np.array([r['metrics']['D']['pink_fraction'] for r in neutral])
        c=np.array([r['metrics'][mode]['pink_fraction'] for r in neutral])
        summary[mode]['neutral_false_pink']=dict(
            cases_improved=int((c<d-1e-15).sum()),cases_worse=int((c>d+1e-15).sum()),
            mean_D=float(d.mean()),mean_candidate=float(c.mean()),
            max_D=float(d.max()),max_candidate=float(c.max()))
        summary[mode]['mean_support_fraction']=float(np.mean([r['support_fraction'][mode] for r in rows]))
    return dict(schema='m9.detail1j.edge_directed_carrier.v1',case_count=len(rows),cfas=cfas,
        neutral=n.tolist(),representation_scale=scale,backgrounds=BACKGROUNDS,subjects=SUBJECTS,
        variants=list(VARIANTS),summary=summary,cases=rows,
        scope='Existing difference producer and final native green/Sharp fixed. Pair selection changes only the opposite-colour diagonal carrier. clip2/clip4 gates use original sensor-white proximity. No exposure/colour/JPEG mutation or Leica-firmware claim.')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--assembled',type=Path,required=True); ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--cfas',type=int,nargs='+',default=[0])
    a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True); repo=Path(__file__).resolve().parents[2]
    native=NativeBaseline(repo,a.assembled,a.out/'native'); probe=DomainProbe(a.out/'native')
    result=synthetic(native,probe,a.cfas)
    result['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['native_source_sha256']=native.source_sha256
    cases=result.pop('cases')
    (a.out/'report.json').write_text(json.dumps(result,indent=2)[:-2]+',\n  "cases": [\n'+',\n'.join('    '+json.dumps(r) for r in cases)+'\n  ]\n}\n')
    print(json.dumps(result['summary'],indent=2))

if __name__=='__main__': main()
