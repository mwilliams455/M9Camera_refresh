"""Independent variance transport and photographic falsification for DETAIL1F."""
from pathlib import Path
import argparse,json
import numpy as np
from scipy.ndimage import gaussian_filter,maximum_filter
from native import Native
from rb_domain import DomainProbe
from rb_probe import q16
from noise2 import Noise2,parameters
from noise2_guard import guarded,residual_variance

def run(native,domain,noise):
    rng=np.random.default_rng(92141);yy,xx=np.indices((96,160));core=np.s_[16:-16,16:-16]
    variance_checks=[];edges=[];colour=[]
    for cfa in range(4):
        rx=cfa in [1,3];ry=cfa in [2,3];red=(xx%2==rx)&(yy%2==ry);blue=(xx%2!=rx)&(yy%2!=ry)
        nr,nb=.37,.61;factor=np.where(red,nr,np.where(blue,nb,1.))
        sigma=np.where(red,100.,np.where(blue,70.,40.));var=(factor*sigma)**2
        prediction=residual_variance(var,cfa,nr,nb);sq=[]
        for rep in range(12):
            raw=q16(np.floor(4096*factor+rng.normal(size=xx.shape)*sigma*factor+.5));g,_,c,_=domain.stages(raw,cfa,nr,nb,False)
            _,sm,_=noise.apply(c,g,cfa,parameters(0,nr,nb));sq.append((c[core].astype(float)-sm[core])**2)
        mask=(red|blue)[core];ratio=float(np.mean(np.stack(sq)[:,mask])/np.mean(prediction[core][mask]))
        assert .93<ratio<1.07,(cfa,ratio)
        variance_checks.append(dict(cfa=cfa,observed_to_predicted_second_moment=ratio,samples=12*int(mask.sum())))
        for nr,nb in [(.25,.5),(.37,.61),(.8,1.5)]:
            factor=np.where(red,nr,np.where(blue,nb,1.));var=np.where(red|blue,(factor*100)**2,0.)
            for shape in ['vertical','horizontal','diagonal']:
                coord=xx if shape=='vertical' else yy*1.7 if shape=='horizontal' else xx+yy*.7
                lum=gaussian_filter(np.where(coord>80.,8000.,800.),2.)
                raw=q16(np.floor(lum*factor+rng.normal(size=xx.shape)*np.sqrt(var)+.5))
                base=native.render(raw,nr,nb,cfa,candidate=False);g,_,c,_=domain.stages(raw,cfa,nr,nb)
                changed,stats=guarded(noise,c,g,cfa,nr,nb,var)
                values=[]
                for ca in [c,changed]:
                    cam=domain.consume(ca,base,cfa,nr,nb);assert np.array_equal(cam[...,1],base[...,1])
                    z=cam[core].astype(float)/65535*16383;err=z[:,:,[0,2]]/np.array([nr,nb])-z[:,:,[1]]
                    values.append(float(np.sqrt(np.mean(err**2))))
                edges.append(dict(cfa=cfa,nr=nr,nb=nb,shape=shape,corrected_rms=values[0],guarded_rms=values[1]))
        nr,nb=.37,.61;factor=np.where(red,nr,np.where(blue,nb,1.));var=np.where(red|blue,(factor*100)**2,0.)
        for name in ['neutral','flat_colour','colour_edge','fine8','fine16','fine32']:
            d=np.zeros_like(xx,dtype=float) if name=='neutral' else np.full_like(xx,1200.,dtype=float) if name=='flat_colour' else (
                np.where(xx>80,1400.,-1400.) if name=='colour_edge' else 1000*np.sin(xx*2*np.pi/int(name[4:])))
            truth=np.stack([4096+d,np.full_like(d,4096),4096-d],axis=-1)
            raw14=(4096+np.where(red,d,np.where(blue,-d,0)))*factor
            raw=q16(np.floor(raw14+rng.normal(size=xx.shape)*np.sqrt(var)+.5));base=native.render(raw,nr,nb,cfa,candidate=False)
            g,_,c,_=domain.stages(raw,cfa,nr,nb);row=dict(cfa=cfa,scene=name,variants={})
            for label,factor_v in [('corrected',None),('guard_half',.5),('guard',1.),('guard_double',2.)]:
                ca=c if factor_v is None else guarded(noise,c,g,cfa,nr,nb,var,strength=factor_v)[0]
                rgb=domain.consume(ca,base,cfa,nr,nb).astype(float)/65535*16383/np.array([nr,1,nb])
                error=rgb[core][:,:,[0,2]]-truth[core][:,:,[0,2]]
                row['variants'][label]=float(np.sqrt(np.mean(error**2)))
            colour.append(row)
        assert np.array_equal(guarded(noise,c,g,cfa,nr,nb,np.zeros_like(var))[0],c),'zero-noise must bypass'
        assert np.array_equal(guarded(noise,c,g,cfa,nr,nb,var,np.ones(c.shape,bool))[0],c),'censored data must bypass'
        censored=np.zeros(c.shape,bool);censored[40:44,70:75]=True
        ca,_=guarded(noise,c,g,cfa,nr,nb,var,censored)
        protected=maximum_filter(censored.astype(np.uint8),size=11)>0
        before=domain.consume(c,base,cfa,nr,nb);after=domain.consume(ca,base,cfa,nr,nb)
        assert np.array_equal(before[protected],after[protected]),'clipped-neighbourhood RGB must remain exact'
    return dict(variance_checks=variance_checks,neutral_edges=edges,known_colour=colour,
        worst_noisy_neutral_rms_ratio=max(x['guarded_rms']/x['corrected_rms'] for x in edges),
        worst_colour_rms_ratio={k:max(x['variants'][k]/x['variants']['corrected'] for x in colour) for k in ['guard_half','guard','guard_double']},
        zero_variance_and_all_censored_exact_bypass=True,clipped_neighbourhood_rgb_exact_all_cfa=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('out',type=Path);ap.add_argument('header',type=Path);a=ap.parse_args()
    repo=Path(__file__).resolve().parents[2];a.out.mkdir(parents=True,exist_ok=True)
    r=run(Native(repo,repo/'PhotonCamera',a.header,a.out/'native'),DomainProbe(a.out/'native'),Noise2(a.out/'native'))
    (a.out/'guard_checks.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r,indent=2))
