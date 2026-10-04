"""Small deterministic ABI invariants. Photographic acceptance is separate."""
import json, sys
from pathlib import Path
import numpy as np
from control import Reconstruction

def main():
    model = Reconstruction(Path(sys.argv[1])); rng = np.random.default_rng(230924)
    shape = (80, 96); y, x = np.indices(shape)
    flags = np.zeros(shape, np.uint8); variance = np.full(shape, 100., np.float32)
    raw = rng.integers(1000, 40000, shape, dtype=np.uint16)
    assert np.array_equal(model.noise(raw, variance*0, flags), raw)
    flat = np.array([8000, 12000, 14000, 19000], np.uint16)[2*(y%2)+x%2]
    assert np.array_equal(model.noise(flat, variance, flags), flat)
    flags[20:40, 30:50] = 1
    one = model.noise(raw, variance, flags, 1)
    assert np.array_equal(one, model.noise(raw, variance, flags, 4))
    assert np.array_equal(one[:6], raw[:6]) and np.array_equal(one[-6:], raw[-6:])
    assert np.array_equal(one[:, :6], raw[:, :6]) and np.array_equal(one[:, -6:], raw[:, -6:])
    noisy = np.clip(np.rint(flat.astype(float)+rng.normal(0,20,shape)),0,65535).astype(np.uint16)
    filtered = model.noise(noisy, variance*4, flags*0)
    inner = np.s_[8:-8,8:-8]
    before = np.mean((noisy[inner].astype(float)-flat[inner])**2)
    after = np.mean((filtered[inner].astype(float)-flat[inner])**2)
    assert after < .5*before, (before, after)
    bounded = model.blend(noisy,filtered,.25)
    delta = np.abs(filtered.astype(float)-noisy)
    assert np.all(np.abs(bounded.astype(float)-noisy) <= .25*delta+.5)
    assert np.array_equal(model.blend(noisy,filtered,0),noisy)
    assert np.array_equal(model.blend(noisy,filtered,1),filtered)
    rgb = np.repeat(raw[..., None], 3, -1)
    for cfa in range(4):
        neutral = [0.4, 1., 0.6]
        assert np.array_equal(model.highlights(raw, rgb, variance, flags*0, cfa, neutral), raw)
        a = model.highlights(raw, rgb, variance, flags, cfa, neutral, 1)
        assert np.array_equal(a, model.highlights(raw, rgb, variance, flags, cfa, neutral, 4))
        pattern = np.array([[0,1,1,2],[1,0,2,1],[1,2,0,1],[2,1,1,0]])[cfa]
        ch = pattern[2*(y%2)+x%2]
        # Known neutral edge: remaining channels contain valid highlight detail.
        truth = np.where(x[...,None]>48,1.4,.8)*np.array(neutral)
        full = np.rint(truth*32767.5).astype(np.uint16)
        bounded = np.rint(np.minimum(truth,1.)*32767.5).astype(np.uint16)
        samples = np.take_along_axis(bounded,ch[...,None],-1)[...,0]
        expected = np.take_along_axis(full,ch[...,None],-1)[...,0]
        mask = np.take_along_axis(truth,ch[...,None],-1)[...,0]>=1.
        lifted = model.highlights(samples,bounded,variance*0,mask,cfa,neutral)
        assert (lifted>samples).any()
        assert np.mean((lifted.astype(float)-expected)**2)<np.mean((samples.astype(float)-expected)**2)
    print(json.dumps(dict(zero_noise_exact=True, four_flat_phases_exact=True,
          noise_censored_exact=True, noise_border_exact=True, worker_parity=True,
          no_clip_exact_all_cfas=True, highlight_unclipped_exact_all_cfas=True,
          highlight_lower_bounds_all_cfas=True,known_noise_mse_ratio=after/before,
          known_neutral_highlight_recovery_all_cfas=True,quarter_raw_correction_bound=True)))

if __name__ == '__main__': main()
