"""Parity/contract tests for the new C++ boundary, including odd CFA extents."""
from pathlib import Path
import argparse, json
import numpy as np
from scipy.ndimage import gaussian_filter
from noise2 import Noise2, parameters
from noise2_guard import guarded, residual_variance
from noise2_guard_native import NativeGuard

def run(build):
    native = NativeGuard(build); unoptimized = NativeGuard(build, '-O0'); noise = Noise2(build)
    rng = np.random.default_rng(92171); rows = []; samples = 0
    for cfa in range(4):
        for h, w in [(24, 25), (35, 32), (70, 73), (96, 160)]:
            for nr, nb, sigma in [(.0625, 16., 20.), (.37, .61, 80.), (1.5, .8, 400.)]:
                c = np.rint(gaussian_filter(rng.normal(size=(h, w)), 1.)*sigma*5 + rng.normal(size=(h, w))*sigma).astype(np.int32)
                g = rng.integers(0, 16384, (h, w), dtype=np.uint16)
                v = rng.uniform(0, sigma*sigma, (h, w))
                v[15:19, 16:19] = 0
                mask = np.zeros((h, w), bool); mask[12, 14] = True; mask[-1, -1] = True
                before = [z.copy() for z in (c, v, mask)]
                for strength in (.5, 1., 2.):
                    ref, _ = guarded(noise, c, g, cfa, nr, nb, v, mask, strength)
                    actual, sm, vr, conf = native.apply(c, cfa, nr, nb, v, mask, strength)
                    _, sm_ref, _ = noise.apply(c, g, cfa, parameters(0, nr, nb))
                    assert np.array_equal(sm, sm_ref), 'mode1 target differs'
                    assert np.array_equal(vr, residual_variance(v, cfa, nr, nb)*strength), 'variance differs'
                    assert np.array_equal(actual, ref), (cfa, h, w, nr, nb, strength, int(np.max(np.abs(actual-ref))))
                    assert np.all(np.abs(actual.astype(float)-c) <= np.sqrt(vr)*.5+.50001)
                    assert np.all(actual >= np.minimum(c, sm)) and np.all(actual <= np.maximum(c, sm))
                    if strength == 1.:
                        assert all(np.array_equal(a, b) for a, b in zip((actual, sm, vr, conf), unoptimized.apply(c, cfa, nr, nb, v, mask)))
                    samples += c.size
                    rows.append(dict(cfa=cfa, shape=[h,w], nr=nr, nb=nb, variance_factor=strength))
                assert all(np.array_equal(a, b) for a, b in zip(before, (c, v, mask)))
                assert np.array_equal(native.apply(c,cfa,nr,nb,np.zeros_like(v))[0],c)
                assert np.array_equal(native.apply(c,cfa,nr,nb,v,np.ones_like(mask))[0],c)
    # Distinct pairs expose red/blue swaps and either wrong green selection.
    canonical = np.array([[11.,1.], [22.,2.], [44.,4.], [88.,8.]]) # R, Gr, Gb, B
    layouts = [(0,1,2,3), (1,0,3,2), (2,3,0,1), (3,2,1,0)]
    for cfa, layout in enumerate(layouts):
        assert np.array_equal(native.profile_rgb(canonical[list(layout)], cfa), [[11.,1.],[33.,3.],[88.,8.]])
    invalid = 0
    c = np.zeros((24,24),np.int32); v = np.ones(c.shape)
    for kwargs in [dict(cfa=-1),dict(cfa=4),dict(nr=0),dict(nb=float('nan')),dict(strength=3),
                   dict(raw_variance14=-v),dict(raw_variance14=v*float('inf')),dict(raw_variance14=v*1e31),
                   dict(carrier=c+262145),dict(censored=np.zeros((24,23))),dict(raw_variance14=v[:,:23])]:
        args=dict(carrier=c,cfa=0,nr=.37,nb=.61,raw_variance14=v);args.update(kwargs)
        try: native.apply(**args)
        except ValueError: invalid += 1
        else: raise AssertionError('invalid input accepted')
    return dict(cases=rows, exact_carrier_and_smoothing_samples=samples, exact_float32_variance=True,
                optimization_O0_O2_exact_cases=len(rows)//3, correction_bounds=True, inputs_unchanged=True,
                zero_variance_and_all_censored_exact=True, invalid_inputs_rejected=invalid,
                camera2_profile_rgb_all_four_cfa=True)

if __name__ == '__main__':
    ap=argparse.ArgumentParser();ap.add_argument('out',type=Path);ap.add_argument('--header',type=Path);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    report=run(a.out/'native');(a.out/'native_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))
    if a.header:
        import noise2_guard_checks as check
        repo=Path(__file__).resolve().parents[2];port=NativeGuard(a.out/'native')
        def native_guard(noise,carrier,green,cfa,nr,nb,raw_variance14,censored=None,strength=1.):
            return port.apply(carrier,cfa,nr,nb,raw_variance14,censored,strength)[0],{}
        check.guarded=native_guard
        r=check.run(check.Native(repo,repo/'PhotonCamera',a.header,a.out/'native'),check.DomainProbe(a.out/'native'),check.Noise2(a.out/'native'))
        assert r==json.loads((repo/'research/detail1a/results/noise2_guard_report.json').read_text())['checks']
        quality=dict(detail1f_quality_checks_exact=True,neutral_edges=len(r['neutral_edges']),known_colour=len(r['known_colour']),
            worst_noisy_neutral_rms_ratio=r['worst_noisy_neutral_rms_ratio'],worst_colour_rms_ratio=r['worst_colour_rms_ratio'],
            clipped_neighbourhood_rgb_exact_all_cfa=r['clipped_neighbourhood_rgb_exact_all_cfa'])
        (a.out/'native_quality_checks.json').write_text(json.dumps(quality,indent=2)+'\n')
        print(json.dumps(quality,indent=2))
