"""Falsification of local clipped-highlight cleanup; research only, no APK change.

The unbounded image-quality task is not solved by passing the initial neutral
fixtures. This probe adds coloured and severely clipped backgrounds and retains
the failures. The conservative certificate is a heuristic, not a recovered M9
operation or a universal preservation guarantee.
"""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, maximum_filter, minimum_filter
from fringe_replay import cfa_masks, pink_mask
from native import Native
from rb_domain import DomainProbe
from rb_probe import q14, q16
from detail1h import dng_inputs, TiledDetail
from downstream import Downstream

MODES = ('independent4', 'joint2', 'joint4', 'certificate8')
BACKGROUNDS = dict(white=[1.2]*3, very_white=[3.]*3,
                  bright_warm=[3., 1.2, .8], bright_cool=[.8, 1.2, 3.],
                  bright_magenta=[3., 1.2, 3.], blue_sky=[.8, 1.2, 1.5],
                  warm=[1.5, 1.2, .8], green=[.8, 1.2, .8], magenta=[1.5, .8, 1.5],
                  cyan=[.2, 1.4, 2.], red=[3., .5, .3], blue=[.3, .5, 2.])
SUBJECTS = dict(neutral=[.03]*3, green=[.01, .1, .02],
                magenta=[.3, .03, .25], bright_magenta=[1.4, .03, 1.2])


def constraints(probe, norm, sensor, cfa, nr, nb, mode, black, white):
    """Local R-G/B-G intervals with a neutral anchor and an optional abstention.

    No RGB8 hue mask is used. Nevertheless, these are deliberately labelled
    heuristics: sparse/partially censored Bayer samples do not establish the true
    colour of every structure crossing a clipped highlight.
    """
    red, blue, green = cfa_masks(norm.shape, cfa)
    g, difference, _, _ = probe.stages(norm, cfa, nr, nb, shrink=False)
    carrier = probe.stages(norm, cfa, nr, nb, shrink=True)[2]
    yy, xx = np.ogrid[:norm.shape[0], :norm.shape[1]]
    clipped = sensor >= white
    low = sensor <= np.asarray(black)[(yy % 2)*2 + xx % 2]
    bounds, colour_evidence = [], []
    certificate = mode == 'certificate8'
    radius = 4 if mode in ('independent4', 'joint4') else 2
    if certificate:
        bad_green = green & (clipped | low)
        invalid = sum(np.roll(bad_green, s, axis) for axis in (0, 1) for s in (-1, 1)) > 0
    else:
        invalid = maximum_filter(clipped, size=3)
    for mask in (red, blue):
        possible = mask & ~invalid & ~low
        valid = possible & ~clipped
        high = maximum_filter(np.where(valid, difference, 0), size=2*radius+1)
        low_bound = minimum_filter(np.where(valid, difference, 0), size=2*radius+1)
        available = maximum_filter(valid, size=2*radius+1)
        bounds.append((low_bound, high, available))
        if certificate:
            # A clipped C with uncensored green still supplies a lower bound
            # on C-G. Pair nearby positive evidence before the wider abstention.
            colour_evidence.append(maximum_filter(np.where(possible, difference, 0), size=3))
    support = maximum_filter(clipped if mode == 'independent4' else clipped & green, size=9)
    if certificate:
        paired_positive = (colour_evidence[0] > 0) & (colour_evidence[1] > 0)
        support &= ~maximum_filter(paired_positive, size=17)
    return carrier, bounds, support


def consume(probe, constraint, base, cfa, nr, nb, mode):
    carrier, bounds, support = constraint
    out = probe.consume(carrier, base, cfa, nr, nb)
    h, w = carrier.shape
    yy, xx = np.ogrid[:h, :w]
    rx, ry = cfa in (1, 3), cfa in (2, 3)
    difference = []
    for ax, ay in ((1-rx, 1-ry), (rx, ry)):
        horizontal = np.where(xx % 2 == ax, carrier,
                              (np.roll(carrier, 1, 1).astype(np.int64) + np.roll(carrier, -1, 1)) // 2)
        difference.append(np.where(yy % 2 == ay, horizontal,
                                   (np.roll(horizontal, 1, 0) + np.roll(horizontal, -1, 0)) // 2))
    joint = (support & bounds[0][2] & bounds[1][2] &
             (difference[0] > bounds[0][1]) & (difference[1] > bounds[1][1]))
    sg = q14(base[..., 1])
    for k, (channel, nc) in enumerate(((0, nr), (2, nb))):
        lo, hi, available = bounds[k]
        d = difference[k]
        if mode == 'independent4':
            d = np.where(support & available, np.clip(d, lo, hi), d)
        else:
            d = np.where(joint, hi, d)
        out[..., channel] = q16(np.clip(np.floor(nc*(sg+d)+.5), 0, 16383).astype(np.int64))
    out[:10] = base[:10]
    out[-10:] = base[-10:]
    out[:, :10] = base[:, :10]
    out[:, -10:] = base[:, -10:]
    assert np.array_equal(out[..., 1], base[..., 1])
    return out


def synthetic(native, probe, neutral, scale):
    yy, xx = np.indices((160, 192))
    nr, _, nb = neutral
    neutral = np.asarray(neutral)
    rows = []
    for cfa in range(4):
        red, blue, _ = cfa_masks(xx.shape, cfa)
        for shape in ('edge', 'fine_branches'):
            coord = xx + yy*.43
            mask = coord > 120 if shape == 'edge' else coord % 15 < 4
            for sigma in (0., .5, 1., 2.):
                for bgname, bg in BACKGROUNDS.items():
                    for subject, fg in SUBJECTS.items():
                        scene = np.where(mask[..., None], fg, bg).astype(float)
                        if sigma:
                            scene = gaussian_filter(scene, [sigma, sigma, 0])
                        observed = np.minimum(scene*neutral, 1.)
                        samples = np.where(red, observed[..., 0], np.where(blue, observed[..., 2], observed[..., 1]))
                        sensor = np.floor(64+samples*959+.5).astype(np.uint16)
                        norm = np.floor((sensor.astype(float)-64)/959/scale*65535+.5).astype(np.uint16)
                        base = native.render(norm, nr, nb, cfa, candidate=False)
                        clipped = np.clip(scene, 0, 1)
                        sg = base[..., 1].astype(float)/65535*scale
                        truth = np.clip(clipped-clipped[..., [1]]+sg[..., None], 0, 1)[16:-16, 16:-16]
                        row = dict(cfa=cfa, shape=shape, sigma=sigma, background=bgname, subject=subject, rms={})
                        dcam = probe.consume(probe.stages(norm, cfa, nr, nb)[2], base, cfa, nr, nb)
                        for mode in ('D', *MODES):
                            cam = dcam if mode == 'D' else consume(probe, constraints(probe, norm, sensor, cfa, nr, nb, mode, [64]*4, 1023), base, cfa, nr, nb, mode)
                            z = np.clip(cam.astype(float)/65535*scale/neutral, 0, 1)[16:-16, 16:-16]
                            row['rms'][mode] = float(np.sqrt(((z[..., [0, 2]]-truth[..., [0, 2]])**2).mean()))
                        rows.append(row)
    summary = {}
    for mode in MODES:
        delta = [r['rms'][mode]-r['rms']['D'] for r in rows]
        summary[mode] = dict(cases_worse_than_D=sum(d > 1e-12 for d in delta),
                             max_rms_increase=max(delta), mean_rms_change=float(np.mean(delta)))
    return dict(schema='m9.censored_chroma.rejection.v1', cases=rows, case_count=len(rows),
                backgrounds=BACKGROUNDS, subjects=SUBJECTS, neutral=neutral.tolist(), representation_scale=scale,
                summary=summary, purpose='Same declared camera-domain difference oracle as fringe_replay.py; no noise, unity shading, synthetic float64 normalization. Passing is not universal preservation or photographic acceptance.')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raw', type=Path, required=True)
    ap.add_argument('--assembled', type=Path, required=True)
    ap.add_argument('--header', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    repo = Path(__file__).resolve().parents[2]
    fixture = json.loads((Path(__file__).parent/'results/fringe_164710_capture.json').read_text())
    assert hashlib.sha256(a.raw.read_bytes()).hexdigest() == fixture['dng_sha256']
    norm, meta, _, sensor, gains = dng_inputs(a.raw)
    nr, _, nb = meta['neutral']
    scale, cfa = meta['representation_scale'], meta['cfa']
    native = Native(repo, a.assembled, a.header, a.out/'native')
    probe = DomainProbe(a.out/'native')
    syn = synthetic(native, probe, meta['neutral'], scale)
    # One case per line retains complete reproducible evidence without a huge
    # pretty-printed report. This is still standard JSON.
    cases = syn.pop('cases')
    (a.out/'synthetic.json').write_text(json.dumps(syn, indent=2)[:-2]+',\n  "cases": [\n'+
                                      ',\n'.join('    '+json.dumps(r) for r in cases)+'\n  ]\n}\n')
    colour = Downstream(repo, a.assembled, a.out/'colour')
    colour.configure(a.raw)
    base = native.render(norm, nr, nb, cfa, candidate=False)
    hcam, hstats = TiledDetail(a.out/'native').apply(norm, sensor, base, cfa, nr, nb, meta['black'], meta['white'],
                                                  fixture['detail1H']['rgbProfile'], gains, scale, guard=True)
    variants, rendered = {}, {}
    for mode in ('H', *MODES):
        cam = hcam if mode == 'H' else consume(probe, constraints(probe, norm, sensor, cfa, nr, nb, mode, meta['black'], meta['white']), base, cfa, nr, nb, mode)
        rgb = colour.render(colour.restore(cam, scale), fixture['actual_render_gain'])
        rendered[mode] = rgb
        variants[mode] = dict(pink_pixels=int(pink_mask(rgb).sum()), green_exact_native=bool(np.array_equal(cam[..., 1], base[..., 1])),
                              noise_guard=mode == 'H')
        Image.fromarray(np.rot90(rgb, 3)).save(a.out/(mode+'.jpg'), quality=95, subsampling=2)
        print(mode, variants[mode]['pink_pixels'], flush=True)
    rois = [(1765, 1908), (257, 1345), (1447, 1140)]
    sheet = Image.new('RGB', (1224, 1452), '#16191c')
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
    small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 15)
    draw.text((12, 12), 'Same RAW and exposure — research candidates, no accepted fix', font=font, fill='white')
    draw.text((12, 43), 'Stronger cleanup fails colour tests. Protected cleanup passes this fixture set but leaves most pink.', font=small, fill='#ffc986')
    for col, (mode, label) in enumerate([('H', 'Current DETAIL1H'), ('joint2', 'Stronger cleanup — rejected'),
                                       ('certificate8', 'Protected cleanup — insufficient')]):
        draw.text((col*408+12, 89), label, font=font, fill='white')
        im = np.rot90(rendered[mode], 3)
        for row, (x, y) in enumerate(rois):
            top = 153+row*432
            draw.text((col*408+12, top-25), f'384 px crop at ({x}, {y})', font=small, fill='#c2c8ce')
            sheet.paste(Image.fromarray(im[y:y+384, x:x+384]), (col*408+12, top))
    sheet.save(a.out/'Fringe-reconstruction-research.png')
    report = dict(schema='m9.censored_chroma.same_raw.v1', raw_sha256=fixture['dng_sha256'],
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  actual_render_gain=fixture['actual_render_gain'], H_stats=hstats, variants=variants,
                  synthetic_summary=syn['summary'], synthetic_case_count=syn['case_count'],
                  photographic_acceptance_passed=False, android_implementation_changed=False,
                  scope='H uses the live profile; cleanup probes use D with guard off. Green, colour and exposure fixed. No Android full-pixel parity claim.')
    (a.out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report['synthetic_summary'], indent=2))


if __name__ == '__main__':
    main()
