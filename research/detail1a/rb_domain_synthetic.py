"""Neutral edge falsification: no true chroma, fixed native green and Sharp."""
from pathlib import Path
import json
import numpy as np
from scipy.ndimage import gaussian_filter
from native import Native
from rb_probe import RbProbe,q16
from rb_domain import DomainProbe

def neutral_edge_checks(native,old,corrected):
    rows=[];yy,xx=np.indices((96,160));core=np.s_[16:-16,16:-16]
    for cfa in range(4):
        rx=cfa in [1,3];ry=cfa in [2,3]
        red=(xx%2==rx)&(yy%2==ry);blue=(xx%2!=rx)&(yy%2!=ry)
        for nr,nb in [(.25,.5),(.37,.61),(.8,1.5)]:
            factor=np.where(red,nr,np.where(blue,nb,1.))
            for shape in ['vertical','horizontal','diagonal']:
                coord=xx if shape=='vertical' else yy*1.7 if shape=='horizontal' else xx+yy*.7
                lum=gaussian_filter(np.where(coord>80.,8000.,800.),2.)
                raw=q16(np.floor(lum*factor+.5))
                base=native.render(raw,nr,nb,cfa,candidate=False)
                before=old.consume(old.stages(raw,cfa,True)[2],base,cfa)
                after=corrected.consume(corrected.stages(raw,cfa,nr,nb,True)[2],base,cfa,nr,nb)
                stats=[]
                for rgb in [base,before,after]:
                    z=rgb[core].astype(float)/65535*16383
                    # Neutral in camera space is (nr*G,G,nb*G), not equal camera RGB.
                    err=z[:,:,[0,2]]/np.array([nr,nb])-z[:,:,[1]]
                    stats.append(dict(rms=float(np.sqrt(np.mean(err**2))),max=float(np.abs(err).max())))
                assert stats[2]['rms']<stats[1]['rms']*.2,(cfa,nr,nb,shape,stats)
                rows.append(dict(cfa=cfa,nr=nr,nb=nb,edge=shape,baseline=stats[0],failed=stats[1],corrected=stats[2]))
    return dict(cases=len(rows),metric='R/nr-G and B/nb-G error in green-domain14 units; quantization and Bayer interpolation included',
                worst_rms_ratio_corrected_to_failed=max(r['corrected']['rms']/r['failed']['rms'] for r in rows),rows=rows)

if __name__=='__main__':
    import sys
    repo=Path(__file__).resolve().parents[2];out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
    header=Path(sys.argv[2]);native=Native(repo,repo/'PhotonCamera',header,out/'native')
    r=neutral_edge_checks(native,RbProbe(out/'native'),DomainProbe(out/'native'))
    (out/'neutral_edges.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k!='rows'},indent=2))
