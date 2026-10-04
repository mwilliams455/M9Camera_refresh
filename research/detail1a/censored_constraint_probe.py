"""Small falsification screen for a rejected clipped-CFA reconstruction prior.

This does not recover lost highlights uniquely. Fixed-iteration TV solutions
preserve the observed samples but can still invent the wrong missing colours.
No Android implementation, noise calibration or photographic acceptance.
"""
from pathlib import Path
import argparse
import ctypes as C
import hashlib
import json
import subprocess
import numpy as np
from scipy.ndimage import gaussian_filter, maximum_filter
from native import Native
from rb_domain import DomainProbe
from fringe_replay import cfa_masks
from censored_chroma_probe import BACKGROUNDS, SUBJECTS

NEUTRAL=np.array([.41796875,1.,.6435546875])
SCALE=1.6105431518598052
CASES=[('white','neutral',.5),('very_white','neutral',.5),('white','green',.5),
       ('very_white','bright_magenta',.5),('bright_magenta','bright_magenta',.5),
       ('very_white','magenta',1.),('blue_sky','green',1.),
       ('bright_magenta','green',1.),('white','magenta',2.)]


class Solver:
    def __init__(self,out):
        source=Path(__file__).with_name('censored_constraint_solver.cpp')
        library=out/'censored_constraint_solver.so'
        subprocess.run(['g++','-std=c++17','-O3','-fPIC','-shared',str(source),'-o',str(library)],check=True)
        self.lib=C.CDLL(str(library))
        self.lib.solve.argtypes=[C.c_void_p]*4+[C.c_int]*3+[C.c_double,C.c_void_p]
        self.lib.solve.restype=None
        self.source_hash=hashlib.sha256(source.read_bytes()).hexdigest()

    def solve(self,norm,sensor,cfa,base,weight,iterations):
        red,blue,_=cfa_masks(norm.shape,cfa)
        nc=np.where(red,NEUTRAL[0],np.where(blue,NEUTRAL[2],1.))
        data=np.ascontiguousarray(norm.astype(float)/65535*SCALE/nc)
        channels=np.where(red,0,np.where(blue,2,1)).astype(np.uint8)
        clipped=(sensor>=1023).astype(np.uint8)
        init=np.ascontiguousarray(base.astype(float)/65535*SCALE/NEUTRAL)
        z=np.empty_like(init)
        self.lib.solve(data.ctypes.data,channels.ctypes.data,clipped.ctypes.data,init.ctypes.data,
                       norm.shape[1],norm.shape[0],iterations,weight,z.ctypes.data)
        sampled=np.take_along_axis(z,channels[...,None],axis=2)[...,0]
        assert np.isfinite(z).all() and z.min()>=0
        assert np.array_equal(sampled[clipped==0],data[clipped==0])
        assert np.all(sampled[clipped!=0]>=data[clipped!=0])
        return z


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--assembled',type=Path,required=True)
    ap.add_argument('--header',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    repo=Path(__file__).resolve().parents[2]
    native=Native(repo,a.assembled,a.header,a.out/'native')
    probe=DomainProbe(a.out/'native');solver=Solver(a.out)
    yy,xx=np.indices((160,192));red,blue,green=cfa_masks(xx.shape,0);rows=[]
    for bgname,subject,sigma in CASES:
        mask=(xx+yy*.43)%15<4
        scene=gaussian_filter(np.where(mask[...,None],SUBJECTS[subject],BACKGROUNDS[bgname]).astype(float),[sigma,sigma,0])
        observed=np.minimum(scene*NEUTRAL,1.)
        samples=np.where(red,observed[...,0],np.where(blue,observed[...,2],observed[...,1]))
        sensor=np.floor(64+samples*959+.5).astype(np.uint16)
        norm=np.floor((sensor.astype(float)-64)/959/SCALE*65535+.5).astype(np.uint16)
        base=native.render(norm,NEUTRAL[0],NEUTRAL[2],0,candidate=False)
        dcam=probe.consume(probe.stages(norm,0,NEUTRAL[0],NEUTRAL[2])[2],base,0,NEUTRAL[0],NEUTRAL[2])
        truth=np.clip(scene,0,1)[16:-16,16:-16]
        def metric(cam):
            z=np.clip(cam.astype(float)/65535*SCALE/NEUTRAL,0,1)[16:-16,16:-16]
            return float(np.sqrt(np.mean((z-truth)**2)))
        row=dict(background=bgname,subject=subject,sigma=sigma,D_scene_rgb_rms=metric(dcam),green_fill={},joint_rgb={})
        for mode,iterations,weights in [('green_fill',300,[.5,1.,2.,4.]),('joint_rgb',800,[.5,1.,2.])]:
            for weight in weights:
                z=solver.solve(norm,sensor,0,base,weight,iterations)
                if mode=='green_fill':
                    fixed=norm.copy();selected=(sensor>=1023)&green
                    fixed[selected]=np.clip(np.floor(z[...,1][selected]/SCALE*65535+.5),0,65535).astype(np.uint16)
                    assert np.array_equal(fixed[~selected],norm[~selected])
                    newbase=native.render(fixed,NEUTRAL[0],NEUTRAL[2],0,candidate=False)
                    cam=probe.consume(probe.stages(fixed,0,NEUTRAL[0],NEUTRAL[2])[2],newbase,0,NEUTRAL[0],NEUTRAL[2])
                else:
                    g14=np.clip(np.floor(z[...,1]/SCALE*16383+.5),0,16383).astype(np.uint16)
                    correction=(native.sharp(g14,0,candidate=False).astype(float)-g14)*SCALE/16383
                    cam=np.clip(np.floor((z+correction[...,None])*NEUTRAL/SCALE*65535+.5),0,65535).astype(np.uint16)
                    cam=np.where(maximum_filter(sensor>=1023,size=17)[...,None],cam,dcam)
                row[mode][str(weight)]=metric(cam)
        rows.append(row);print(bgname,subject,sigma,flush=True)
    report=dict(schema='m9.censored_constraint_probe.v1',cases=rows,case_count=len(rows),
                solver_sha256=solver.source_hash,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                spatial_source_hashes=native.source_hashes,neutral=NEUTRAL.tolist(),representation_scale=SCALE,
                configuration=dict(cfa=0,shape=[160,192],scene='four-pixel diagonal lines, period15, slope0.43',
                    black=64,white=1023,noise=False,shading='unity',primal_step=.16,dual_step=.16,
                    extrapolation=1,green_fill_iterations=300,joint_rgb_iterations=800,metric_border=16),
                observed_sample_constraints_passed=True,
                oracle='Known optically blurred scene, clipped to0..1 per channel. Full scene RGB RMS; not a Leica or perceptual reference.',
                scope='Selected-case rejection screen only. Both probes change native green values. No convergence certificate or unique highlight recovery claim.',
                accepted=False,android_implementation_changed=False)
    (a.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
