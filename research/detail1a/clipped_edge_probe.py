"""Falsification probe for remaining pink edges in DETAIL1H, not a correction.

Execute the shipped native stages on noiseless neutral Bayer edges. The fixture
supplies the failing capture's CFA, neutral, scale and live noise profile. Lens
gains are deliberately unity: this is not a replay of that capture or its JPEG.
"""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
from scipy.ndimage import gaussian_filter
from native import Native
from detail1h import TiledDetail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--assembled', type=Path, required=True)
    ap.add_argument('--header', type=Path, required=True)
    ap.add_argument('--fixture', type=Path, default=Path(__file__).parent / 'results/fringe_164710_capture.json')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    repo = Path(__file__).resolve().parents[2]
    fixture = json.loads(a.fixture.read_text())
    m = fixture['detail1H']
    native = Native(repo, a.assembled, a.header, a.out / 'native')
    tiled = TiledDetail(a.out / 'native')
    nr, _, nb = m['neutral']
    scale = m['representationScale']
    cfa = m['sourceCfa']
    yy, xx = np.indices((160, 192))
    rx, ry = cfa in (1, 3), cfa in (2, 3)
    red = (xx % 2 == rx) & (yy % 2 == ry)
    blue = (xx % 2 != rx) & (yy % 2 != ry)
    factor = np.where(red, nr, np.where(blue, nb, 1.))
    # This capture has equal static black levels. Do not silently approximate
    # another fixture with unequal black levels or a non-unity green neutral.
    assert m['blackLevel'] == [64] * 4 and m['whiteLevel'] == 1023
    assert m['neutral'][1] == 1
    rows = []
    for shape in ('edge', 'fine_branches'):
        for sigma in (0., .5, 1., 2.):
            for top in (.5, 1.2):
                coord = xx + yy * .43
                lum = (np.where(coord > 120, .03, top) if shape == 'edge'
                       else np.where((coord % 15) < 4, .03, top))
                if sigma:
                    lum = gaussian_filter(lum, sigma)
                signal = np.minimum(lum * factor, 1.)
                sensor = np.floor(64 + signal * 959 + .5).astype(np.uint16)
                # Synthetic float64 normalization; exact shipped native spatial
                # code below. This is not Android preprocessing byte parity.
                norm = np.floor((sensor.astype(float) - 64) / 959 / scale * 65535 + .5).astype(np.uint16)
                base = native.render(norm, nr, nb, cfa, candidate=False)
                args = (norm, sensor, base, cfa, nr, nb, [64] * 4, 1023,
                        m['rgbProfile'], np.ones((1, 1, 4)), scale)
                corrected, _ = tiled.apply(*args, guard=False)
                guarded, stats = tiled.apply(*args, guard=True)
                assert np.array_equal(base[..., 1], guarded[..., 1])
                metrics = {}
                for name, rgb in [('base', base), ('D', corrected), ('H', guarded)]:
                    # WB-normalized camera channels, with physical neutral-white
                    # clipping. No M9 matrices, SAT2, tone curve or JPEG here.
                    z = np.clip(rgb.astype(float) / 65535 * scale / np.array([nr, 1., nb]), 0., 1.)[16:-16, 16:-16]
                    err = z[:, :, [0, 2]] - z[:, :, [1]]
                    metrics[name] = dict(
                        neutral_error_rms=float(np.sqrt((err ** 2).mean())),
                        max_abs=float(abs(err).max()),
                        pink_fraction_excess_gt_0p02=float((np.minimum(err[..., 0], err[..., 1]) > .02).mean()))
                rows.append(dict(shape=shape, blur_sigma_sensor_pixels=sigma,
                                 neutral_bright_level=top,
                                 raw_clipped_fraction=float((sensor >= 1023).mean()),
                                 metrics=metrics,
                                 guard_max_carrier_correction=stats['max_abs_correction']))
    # Regression evidence: do not assert that an intentionally unfixed candidate
    # has no fringe. Make the failed acceptance condition explicit in the report.
    failing = [r for r in rows if r['neutral_bright_level'] > 1 and
               r['metrics']['H']['pink_fraction_excess_gt_0p02'] > r['metrics']['base']['pink_fraction_excess_gt_0p02']]
    report = dict(schema='m9.detail1h.clipped_neutral_probe.v1',
                  purpose='Synthetic neutral edges; not the supplied RAW or final JPEG; unity gain grid; no sensor noise added.',
                  metric='Fraction of interior pixels with both R/nr and B/nb exceeding G by >0.02 after representation restoration and neutral-white clipping.',
                  source_hashes=native.source_hashes,
                  probe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  fixture_sha256=hashlib.sha256(a.fixture.read_bytes()).hexdigest(),
                  clipped_cases_with_more_pink_than_base=len(failing),
                  clipped_neutral_pink_nonregression_passed=not failing,
                  same_raw_cause_proven=False, cases=rows)
    (a.out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('cases', 'source_hashes')}, indent=2))


if __name__ == '__main__':
    main()
