"""Replay the 16:47 DETAIL1H failure and falsify an early-white-limit probe.

Research only. No APK payload is modified. The producer-only cap is deliberately
tested with the noise guard off: clipping changes its variance/censor model.
The saved gain and live Camera2 profile are held fixed; do not remeter variants
or substitute the DNG writer's historically adjusted NoiseProfile.
"""
from pathlib import Path
import argparse
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, maximum_filter
import tifffile

from detail1h import TiledDetail, dng_inputs
from downstream import Downstream
from native import Native
from rb_domain import DomainProbe


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cfa_masks(shape, cfa):
    y, x = np.ogrid[:shape[0], :shape[1]]
    rx, ry = cfa in (1, 3), cfa in (2, 3)
    red = (x % 2 == rx) & (y % 2 == ry)
    blue = (x % 2 != rx) & (y % 2 != ry)
    return red, blue, ~(red | blue)


def white_probe(norm, neutral, scale, cfa, gate_radius=None):
    r, b, g = cfa_masks(norm.shape, cfa)
    factor = np.where(r, neutral[0], np.where(b, neutral[2], 1.))
    limit = np.floor(65535 * factor / scale + .5)
    capped = np.minimum(norm, limit).astype(np.uint16)
    if gate_radius is not None:
        clipped_green = g & (norm >= np.floor(65535 / scale + .5))
        support = maximum_filter(clipped_green, size=2 * gate_radius + 1)
        capped = np.where(support, capped, norm).astype(np.uint16)
    return capped


def pink_mask(rgb):
    z = rgb.astype(np.int16)
    # Diagnostic for this foliage capture only, NEVER used by a correction.
    # Real magenta objects also satisfy this test.
    return (np.minimum(z[..., 0], z[..., 2]) - z[..., 1] > 15) & (z.sum(axis=-1) > 300)


def synthetic(native, probe, neutral, scale):
    """Known camera-domain colour differences with the same sharpened green.

    Scene RGB is white-balanced linear camera RGB, not sRGB. After optical blur,
    the reference clips each channel at physical neutral white. It retains those
    known colour differences and adds the exact native sharpened green. This is
    a declared difference-reconstruction oracle, not a complete camera/JPEG or
    Leica sharpness oracle. All raw samples are noiseless, gain grid is unity,
    normalization uses float64, and an inner-16 border is excluded.
    """
    neutral = np.asarray(neutral)
    yy, xx = np.indices((160, 192))
    rows = []
    subjects = dict(neutral=[.03] * 3, green=[.01, .10, .02],
                    magenta=[.30, .03, .25], red=[.35, .03, .02],
                    blue=[.02, .03, .35], bright_magenta=[1.4, .03, 1.2])
    for cfa in range(4):
        r, b, _ = cfa_masks(xx.shape, cfa)
        for shape in ('edge', 'fine_branches'):
            coord = xx + yy * .43
            mask = coord > 120 if shape == 'edge' else coord % 15 < 4
            for sigma in (0., .5, 1., 2.):
                for top in (.5, 1.2):
                    for name, fg in subjects.items():
                        scene = np.where(mask[..., None], fg, [top] * 3).astype(float)
                        if sigma:
                            scene = gaussian_filter(scene, [sigma, sigma, 0])
                        observed = np.minimum(scene * neutral, 1.)
                        signal = np.where(r, observed[..., 0], np.where(b, observed[..., 2], observed[..., 1]))
                        sensor = np.floor(64 + signal * 959 + .5).astype(np.uint16)
                        norm = np.floor((sensor.astype(float) - 64) / 959 / scale * 65535 + .5).astype(np.uint16)
                        base = native.render(norm, neutral[0], neutral[2], cfa, candidate=False)
                        sg = base[..., 1].astype(float) / 65535 * scale
                        physical = np.clip(scene, 0, 1)
                        truth = np.clip(physical - physical[..., [1]] + sg[..., None], 0, 1)[16:-16, 16:-16]
                        metrics = {}
                        variants = dict(D=norm, prewhite=white_probe(norm, neutral, scale, cfa),
                                        green_clip_gated1=white_probe(norm, neutral, scale, cfa, 1))
                        for variant, raw in variants.items():
                            carrier = probe.stages(raw, cfa, neutral[0], neutral[2])[2]
                            cam = probe.consume(carrier, base, cfa, neutral[0], neutral[2])
                            assert np.array_equal(cam[..., 1], base[..., 1])
                            z = np.clip(cam.astype(float) / 65535 * scale / neutral, 0, 1)[16:-16, 16:-16]
                            error = z[..., [0, 2]] - truth[..., [0, 2]]
                            d = z[..., [0, 2]] - z[..., [1]]
                            metrics[variant] = dict(rb_reference_rms=float(np.sqrt((error ** 2).mean())),
                                                    max_abs_error=float(abs(error).max()),
                                                    pink_fraction=float((np.minimum(d[..., 0], d[..., 1]) > .02).mean()))
                        rows.append(dict(cfa=cfa, shape=shape, sigma=sigma, background=top,
                                         subject=name, metrics=metrics))
    # Absolute 1e-12 tolerance only suppresses float comparison roundoff. This is
    # a deliberately strict screen, not a perceptual just-noticeable threshold.
    failures = {}
    for variant in ('prewhite', 'green_clip_gated1'):
        selected = [r for r in rows if r['subject'] != 'neutral' and
                    r['metrics'][variant]['rb_reference_rms'] > r['metrics']['D']['rb_reference_rms'] + 1e-12]
        failures[variant] = dict(coloured_cases_worse_than_D=len(selected),
                                 coloured_edge_nonregression_passed=not selected)
    return dict(schema='m9.detail1h.highlight_colour_probe.v1',
                purpose=synthetic.__doc__, cfa_count=4, case_count=len(rows),
                neutral=neutral.tolist(), representation_scale=scale,
                all_variant_green_samples_exact=True, candidate_acceptance=failures, cases=rows)


def comparison(out, rendered, rois):
    font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    font = ImageFont.truetype(font_path, 19)
    small = ImageFont.truetype(font_path, 15)
    panel = Image.new('RGB', (1224, 1452), '#16191c')
    d = ImageDraw.Draw(panel)
    d.text((16, 14), 'Same RAW, same exposure and colour — original-resolution crops', fill='white', font=font)
    d.text((16, 45), 'Experimental white limit still leaves fringes and fails coloured-edge checks. Not an accepted fix.',
           fill='#ffc986', font=small)
    for col, (key, title) in enumerate([('base', 'Previous native baseline'), ('H', 'Current DETAIL1H'),
                                       ('prewhite', 'White-limit probe (guard off)')]):
        d.text((col * 408 + 12, 89), title, fill='white', font=font)
        im = np.rot90(rendered[key], 3)
        for row, (x, y) in enumerate(rois):
            top = 153 + row * 432
            d.text((col * 408 + 12, top - 25), f'Portrait crop: x={x}, y={y}', fill='#c2c8ce', font=small)
            panel.paste(Image.fromarray(im[y:y + 384, x:x + 384]), (col * 408 + 12, top))
    panel.save(out / 'Fringe-comparison.png')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raw', type=Path, required=True)
    ap.add_argument('--assembled', type=Path, required=True)
    ap.add_argument('--header', type=Path, required=True)
    ap.add_argument('--fixture', type=Path, default=Path(__file__).parent / 'results/fringe_164710_capture.json')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    repo = Path(__file__).resolve().parents[2]
    fixture = json.loads(a.fixture.read_text())
    # The fixed crop coordinates and exact-stat expectations belong to this RAW.
    raw_sha = sha(a.raw)
    assert raw_sha == '1103f6047dd1e11fcd5defa3ddbb4e24ca5f00221e5672ffd67d5d69a5592903'
    m = fixture['detail1H']
    norm, meta, _, sensor, gains = dng_inputs(a.raw)
    nr, _, nb = meta['neutral']
    scale, cfa = meta['representation_scale'], meta['cfa']
    assert scale == m['representationScale'] and meta['norm030_alpha'] == m['norm030Alpha']
    assert meta['black'] == m['blackLevel'] and meta['white'] == m['whiteLevel']
    assert cfa == m['sourceCfa'] and m['originX'] == m['originY'] == 0
    with tifffile.TiffFile(a.raw) as tf:
        assert int(tf.pages[0].tags['Orientation'].value) == 6
    native = Native(repo, a.assembled, a.header, a.out / 'native')
    probe = DomainProbe(a.out / 'native')
    tiled = TiledDetail(a.out / 'native')
    colour = Downstream(repo, a.assembled, a.out / 'colour')
    colour.configure(a.raw)
    gain = fixture['actual_render_gain']
    base = native.render(norm, nr, nb, cfa, candidate=False)
    common = (norm, sensor, base, cfa, nr, nb, m['blackLevel'], m['whiteLevel'], m['rgbProfile'], gains, scale)
    dcam, dstats = tiled.apply(*common, guard=False)
    hcam, hstats = tiled.apply(*common, guard=True)
    expected = dict(tiles='tiles', supported_rb_samples='supportedRbSamples',
                    changed_carrier_samples='changedCarrierSamples', max_abs_correction='maxAbsCorrection',
                    censored_samples='rawCensoredSamples', mean_confidence='meanConfidence',
                    mean_residual_variance14='meanResidualVariance14', scratch_budget_bytes='scratchBudgetBytes')
    for key, phone in expected.items():
        assert hstats[key] == m[phone], (key, hstats[key], m[phone])
    candidates = {}
    for name, radius in [('prewhite', None), ('green_clip_gated1', 1)]:
        cap = white_probe(norm, meta['neutral'], scale, cfa, radius)
        carrier = probe.stages(cap, cfa, nr, nb)[2]
        candidates[name] = probe.consume(carrier, base, cfa, nr, nb)
    cams = dict(base=base, D=dcam, H=hcam, **candidates)
    rendered, variants = {}, {}
    for name, cam in cams.items():
        assert np.array_equal(cam[..., 1], base[..., 1])
        rgb = colour.render(colour.restore(cam, scale), gain)
        rendered[name] = rgb
        count = int(pink_mask(rgb).sum())
        variants[name] = dict(diagnostic_pink_pixels=count, diagnostic_pink_fraction=count / norm.size,
                              green_exact_native=True, guard=name == 'H')
        Image.fromarray(np.rot90(rgb, 3)).save(a.out / (name + '.jpg'), quality=95, subsampling=2)
        print(name, count, flush=True)
    pink = pink_mask(rendered['H'])
    clipped = sensor >= meta['white']
    proximity = {str(radius): float(maximum_filter(clipped, size=2 * radius + 1)[pink].mean())
                 for radius in (0, 1, 2, 4, 6, 10)}
    rois = [(1765, 1908), (257, 1345), (1447, 1140)]
    comparison(a.out, rendered, rois)
    syn = synthetic(native, probe, meta['neutral'], scale)
    (a.out / 'highlight_colour_probe.json').write_text(json.dumps(syn, indent=2) + '\n')
    report = dict(schema='m9.detail1h.fringe_same_raw_replay.v1', raw_sha256=raw_sha,
                  fixture_sha256=sha(a.fixture), script_sha256=sha(Path(__file__)),
                  metadata=meta, spatial_source_hashes=native.source_hashes,
                  colour_source_hashes=colour.hashes, actual_render_gain=gain,
                  profile_authority='recorded live Camera2 RGB profile, NOT DNG NoiseProfile',
                  rgb_profile=m['rgbProfile'], phone_stat_checks_exact=list(expected),
                  H_stats=hstats, D_stats=dstats, variants=variants,
                  diagnostic_metric='Pre-JPEG RGB8: min(R,B)-G >15 and (R+G+B)>300; foliage-specific, not a hue correction or universal accuracy measure.',
                  H_pink_fraction_with_raw_clip_within_chebyshev_radius=proximity,
                  portrait_crop_xy=rois, crop_size=384,
                  android_full_pixel_parity_proven=False,
                  candidate_acceptance=syn['candidate_acceptance'],
                  photographic_fringe_acceptance_passed=False,
                  android_candidate_created=False, auto_exposure_changed=False)
    (a.out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(phone_stats_exact=True, candidate_acceptance=syn['candidate_acceptance']), indent=2))


if __name__ == '__main__':
    main()
