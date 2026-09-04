#!/usr/bin/env python3
from __future__ import annotations

"""TC20INTENT1A — offline same-RAW intent-preservation experiment.

This is RESEARCH ONLY. It does not modify the Android app or production renderer.

A0  frozen R3.8-H25/TG1 TC20 reference.
A1  calculate TC20 base/guard from intent-normalized virtual measurements, then
    apply that gain to the physical captured RAW-derived M9 image.
A2  control: intent-normalized median/base request but retain the physical RAW
    tail guard. On guard-limited frames this should remain at/near A0 and proves
    whether the physical hard guard is the blocker.

Intent authority:
    m9ExposureAudit.derived.captureEnergyVsPhotonOnlyEv

For cap C:
    preservedIntentEv = min(max(actualCaptureEnergyVsPhotonOnlyEv, 0), C)

Physical RAW clipping/tail telemetry is NEVER normalized away. The experiment
keeps physical and virtual measurements side by side.

The script consumes one or more directories/ZIPs containing DNG + _M9.json +
_M9_PRIMARY.json records. It uses the exact frozen Android calibration binary
stored in this repository (Cobalt main-camera matrices/HSM + Leica curve02).
"""

import argparse
import csv
import hashlib
import json
import math
import random
import shutil
import struct
import tempfile
import zipfile
from pathlib import Path

import cv2
import numpy as np
import tifffile
from PIL import Image, ImageDraw

VERSION = "TC20INTENT1A-2026-09-04"
CAPS = (0.0, 0.10, 0.20, 0.30)
METER_TARGET = 0.107 * (8192.0 / 10000.0)
METER_CW = 0.75
TC_HEADROOM_TARGET = 0.95
TC_ALPHA = 0.20
TC_TAIL_CURVATURE_THRESHOLD = 0.25
RAW_MAX = 16383
LUT_MAX = 2047
SATURATION_BANK = 3
HSM_H = 0.25
HSM_S = 0.85
HSM_V = 1.00
TG_START_K = 4500.0
TG_FULL_K = 3200.0
TG_NEG_CB_COMPRESSION = 0.25
TG_NEG_CR_COMPRESSION = 0.16

QE = np.array([
    [16754, -7632, -922],
    [-3124, 14774, -3458],
    [-567, -9579, 18330],
], dtype=np.int64)
QO = np.array([
    [18160, -9034, -922],
    [-3422, 15080, -3458],
    [137, -10264, 18330],
], dtype=np.int64)
M9_CM_A = np.array([
    [.8560, -.2034, -.0066],
    [-.4240, 1.3600, .2920],
    [-.0740, .2470, .8980],
], dtype=np.float64)
M9_CM_D65 = np.array([
    [.6260, -.1019, -.0470],
    [-.3730, 1.1450, .1930],
    [-.1409, .2950, .6210],
], dtype=np.float64)
D50_XY = np.array([.34567, .35850], dtype=np.float64)
D65_XY = np.array([.31271, .32902], dtype=np.float64)
BRADFORD = np.array([
    [.8951, .2664, -.1614],
    [-.7502, 1.7135, .0367],
    [.0389, -.0685, 1.0296],
], dtype=np.float64)
BRADFORD_INV = np.linalg.inv(BRADFORD)
XYZ2SRGB = np.array([
    [3.2404542, -1.5371385, -.4985314],
    [-.9692660, 1.8760108, .0415560],
    [.0556434, -.2040259, 1.0572252],
], dtype=np.float64)
PCS_XYZ = np.array([
    D50_XY[0] / D50_XY[1], 1.0,
    (1.0 - D50_XY.sum()) / D50_XY[1],
], dtype=np.float64)
PP_TO_XYZ_RAW = np.array([
    [.7977, .1352, .0313],
    [.2880, .7119, .0001],
    [0.0, 0.0, .8249],
], dtype=np.float64)
PP_TO_XYZ = np.diag(PCS_XYZ / (PP_TO_XYZ_RAW @ np.ones(3))) @ PP_TO_XYZ_RAW
XYZ_TO_PP = np.linalg.inv(PP_TO_XYZ)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def ratios(v):
    v = tuple(v)
    return np.array([v[i] / v[i + 1] for i in range(0, len(v), 2)], dtype=np.float64)


def tag_numeric(tag):
    if int(tag.dtype) in (5, 10):  # TIFF RATIONAL / SRATIONAL
        return ratios(tag.value)
    val = tag.value if isinstance(tag.value, (tuple, list)) else [tag.value]
    return np.asarray(val, dtype=np.float64)


def tag_scalar(tag):
    v = tag_numeric(tag)
    if v.size != 1:
        raise ValueError(f"Expected scalar tag, got {v.size} values for {tag.name}")
    return float(v[0])


def xy_to_xyz(xy):
    x, y = xy
    return np.array([x / y, 1.0, (1.0 - x - y) / y], dtype=np.float64)


def bradford(src_xy, dst_xy):
    s = BRADFORD @ xy_to_xyz(src_xy)
    d = BRADFORD @ xy_to_xyz(dst_xy)
    return BRADFORD_INV @ np.diag(d / s) @ BRADFORD


def cct_from_xy(xy):
    # R3.6 CCTFIX, retained by R3.8.
    x, y = xy
    n = (x - .3320) / (y - .1858)
    t = -449 * n**3 + 3525 * n**2 - 6823.3 * n + 5520.33
    return float(np.clip(t, 2000.0, 12000.0))


def weight_a(cct):
    m = 1e6 / cct
    return float(np.clip(
        (m - 1e6 / 6500.0) / (1e6 / 2850.0 - 1e6 / 6500.0), 0.0, 1.0
    ))


def interp(a, d, wa):
    return wa * a + (1.0 - wa) * d


class FrozenCalibration:
    """Decode payload/app/src/main/assets/m9/m9_r35_calibration.bin."""
    def __init__(self, path: Path):
        b = memoryview(path.read_bytes())
        off = 0
        magic = bytes(b[off:off + 8]); off += 8
        if magic != b"M9R35CAL":
            raise ValueError(f"bad calibration magic: {magic!r}")
        version, hd, sd, vd = struct.unpack_from("<4i", b, off); off += 16
        if version != 1 or (hd, sd, vd) != (90, 30, 1):
            raise ValueError(f"unexpected calibration header v={version}, dims={hd}x{sd}x{vd}")
        self.hd, self.sd, self.vd = hd, sd, vd

        def doubles(n):
            nonlocal off
            a = np.frombuffer(b[off:off + 8 * n], dtype="<f8").astype(np.float64).copy()
            off += 8 * n
            return a

        self.cm_a = doubles(9).reshape(3, 3)
        self.cm_d = doubles(9).reshape(3, 3)
        self.fm_a = doubles(9).reshape(3, 3)
        self.fm_d = doubles(9).reshape(3, 3)
        n_hsm = hd * sd * vd * 3
        self.hsm_a = np.frombuffer(b[off:off + 4 * n_hsm], dtype="<f4").astype(np.float64).copy()
        off += 4 * n_hsm
        self.hsm_d = np.frombuffer(b[off:off + 4 * n_hsm], dtype="<f4").astype(np.float64).copy()
        off += 4 * n_hsm
        self.hsm_a = self.hsm_a.reshape(vd, hd, sd, 3)[0]
        self.hsm_d = self.hsm_d.reshape(vd, hd, sd, 3)[0]
        self.curve02 = np.frombuffer(b[off:off + 2048], dtype=np.uint8).copy(); off += 2048
        if off != len(b):
            raise ValueError(f"unexpected trailing calibration bytes: {len(b) - off}")

    def neutral_to_xy(self, neutral):
        xy = D50_XY.copy()
        for _ in range(30):
            wa = weight_a(cct_from_xy(xy))
            cm = interp(self.cm_a, self.cm_d, wa)
            xyz = np.linalg.solve(cm, neutral)
            xyz /= xyz.sum()
            q = xyz[:2]
            if np.abs(q - xy).sum() < 1e-8:
                return q
            xy = q
        return xy

    @staticmethod
    def _rgb_to_hsv6(rgb):
        r, g, b = np.moveaxis(rgb, -1, 0)
        v = np.maximum(r, np.maximum(g, b))
        mn = np.minimum(r, np.minimum(g, b))
        gap = v - mn
        h = np.zeros_like(v)
        s = np.zeros_like(v)
        m = gap > 1e-12
        mr = m & (r == v)
        mg = m & (~mr) & (g == v)
        mb = m & (~mr) & (~mg)
        h[mr] = (g[mr] - b[mr]) / gap[mr]
        h[mr & (h < 0)] += 6.0
        h[mg] = 2.0 + (b[mg] - r[mg]) / gap[mg]
        h[mb] = 4.0 + (r[mb] - g[mb]) / gap[mb]
        s[m] = gap[m] / np.maximum(v[m], 1e-12)
        return h, s, v

    @staticmethod
    def _hsv6_to_rgb(h, s, v):
        h = np.mod(h, 6.0)
        i = np.floor(h).astype(np.int16)
        f = h - i
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))
        r = np.empty_like(v); g = np.empty_like(v); b = np.empty_like(v)
        vals = [(v, t, p), (q, v, p), (p, v, t),
                (p, q, v), (t, p, v), (v, p, q)]
        for n, (rr, gg, bb) in enumerate(vals):
            m = i == n
            r[m] = rr[m]; g[m] = gg[m]; b[m] = bb[m]
        return np.stack([r, g, b], axis=-1)

    def apply_hsm(self, pp, hsm):
        x = np.clip(pp, 0.0, 1.0)
        h, s, v = self._rgb_to_hsv6(x)
        hp = h * (self.hd / 6.0)
        sp = s * (self.sd - 1)
        h0 = np.floor(hp).astype(np.int16)
        s0 = np.minimum(np.floor(sp).astype(np.int16), self.sd - 2)
        h1 = h0 + 1
        wrap = h0 >= self.hd - 1
        h0 = np.where(wrap, self.hd - 1, h0)
        h1 = np.where(wrap, 0, h1)
        hf = hp - h0
        sf = sp - s0
        e00 = hsm[h0, s0]; e01 = hsm[h1, s0]
        e10 = hsm[h0, s0 + 1]; e11 = hsm[h1, s0 + 1]
        d = ((1.0 - sf)[..., None] * ((1.0 - hf)[..., None] * e00 + hf[..., None] * e01)
             + sf[..., None] * ((1.0 - hf)[..., None] * e10 + hf[..., None] * e11))
        hue = np.mod(h + HSM_H * d[..., 0] * (6.0 / 360.0), 6.0)
        sat = np.minimum(s * (1.0 + HSM_S * (d[..., 1] - 1.0)), 1.0)
        val = np.clip(v * (1.0 + HSM_V * (d[..., 2] - 1.0)), 0.0, 1.0)
        return self._hsv6_to_rgb(hue, sat, val)

    def to_xyz50(self, cam, xy, wa):
        cm = interp(self.cm_a, self.cm_d, wa)
        fm = interp(self.fm_a, self.fm_d, wa)
        cw = cm @ xy_to_xyz(xy)
        cw = cw / np.max(cw)
        cw = np.clip(cw, .001, 1.0)
        pp = np.clip(np.minimum(cam, cw[None, None, :]) @
                     (XYZ_TO_PP @ fm @ np.diag(1.0 / cw)).T, 0.0, 1.0)
        pp = self.apply_hsm(pp, interp(self.hsm_a, self.hsm_d, wa))
        return pp @ PP_TO_XYZ.T


def read_dng(path: Path, long_side=1600):
    with tifffile.TiffFile(path) as tf:
        pg = tf.pages[0]
        tags = pg.tags
        raw = pg.asarray().astype(np.float32)
        bl = tag_numeric(tags["BlackLevel"]).reshape(2, 2)
        wl = tag_scalar(tags["WhiteLevel"])
        norm = np.empty_like(raw, dtype=np.float32)
        for yy in range(2):
            for xx in range(2):
                norm[yy::2, xx::2] = (raw[yy::2, xx::2] - bl[yy, xx]) / (wl - bl[yy, xx])
        norm = np.clip(norm, 0.0, 1.0)
        clipmask = raw >= wl
        unclipped = norm[~clipmask]
        clip_fraction = float(np.mean(clipmask))
        if unclipped.size:
            uq99 = float(np.quantile(unclipped, .99))
            uq995 = float(np.quantile(unclipped, .995))
            uq998 = float(np.quantile(unclipped, .998))
            q = float(np.clip(.999 - TC_ALPHA * clip_fraction, .95, .999))
            adaptive_uq = float(np.quantile(unclipped, q))
        else:
            uq99 = uq995 = uq998 = adaptive_uq = 1.0
            q = .95
        d1 = float(np.log(max(uq995, 1e-9) / max(uq99, 1e-9)))
        d2 = float(np.log(max(uq998, 1e-9) / max(uq995, 1e-9)))
        curvature = float(d2 - .6 * d1)
        isolated = bool(curvature > TC_TAIL_CURVATURE_THRESHOLD)
        tail = float(uq995 if isolated else adaptive_uq)
        rawm = {
            "rawHardClipFraction": clip_fraction,
            "rawUq99": uq99,
            "rawUq99_5": uq995,
            "rawUq99_8": uq998,
            "tc20Q": q,
            "tc20AdaptiveUq": adaptive_uq,
            "tc20TailCurvature": curvature,
            "tc20TailIsolated": isolated,
            "physicalTail": tail,
        }
        cam = cv2.cvtColor((norm * 65535.0 + .5).astype(np.uint16),
                           cv2.COLOR_BayerRG2BGR_EA).astype(np.float32) / 65535.0
        h, w = cam.shape[:2]
        if long_side and max(h, w) > long_side:
            sc = long_side / float(max(h, w))
            cam = cv2.resize(cam, (round(w * sc), round(h * sc)), interpolation=cv2.INTER_AREA)
        neutral = tag_numeric(tags["AsShotNeutral"])
        orientation = int(tags["Orientation"].value) if "Orientation" in tags else 1
        baseline = tag_scalar(tags["BaselineExposure"]) if "BaselineExposure" in tags else 0.0
        iso = int(tags["ISOSpeedRatings"].value) if "ISOSpeedRatings" in tags else 0
    return cam, neutral, orientation, baseline, iso, rawm


def weighted_median_luma(y):
    h, w = y.shape
    yy, xx = np.mgrid[0:h, 0:w]
    ry = (yy - h / 2.0) / (h / 2.0)
    rx = (xx - w / 2.0) / (w / 2.0)
    wg = np.exp(-(ry * ry + rx * rx) / (2.0 * METER_CW * METER_CW)).ravel()
    yf = y.ravel()
    m = yf > 1e-5
    if not m.any():
        return 0.0
    order = np.argsort(yf[m])
    ys = yf[m][order]
    ws = wg[m][order]
    cum = np.cumsum(ws)
    return float(ys[np.searchsorted(cum, cum[-1] * .5)])


def tc20_variants(physical_median, physical_tail, baseline_ev, achieved_intent_ev, cap_ev):
    p = min(max(float(achieved_intent_ev), 0.0), float(cap_ev))
    scale_baseline = 2.0 ** float(baseline_ev)
    physical_base = float(np.clip(METER_TARGET / max(physical_median, 1e-6), .5, 16.0) * scale_baseline)
    physical_guard = float(max(1.0, TC_HEADROOM_TARGET / max(physical_tail, 1e-9)))
    a0 = min(physical_base, physical_guard)

    virtual_median = physical_median / (2.0 ** p)
    virtual_tail = physical_tail / (2.0 ** p)
    virtual_base = float(np.clip(METER_TARGET / max(virtual_median, 1e-6), .5, 16.0) * scale_baseline)
    virtual_guard = float(max(1.0, TC_HEADROOM_TARGET / max(virtual_tail, 1e-9)))
    a1 = min(virtual_base, virtual_guard)

    # A2 is deliberately only a blocker/control experiment at this stage.
    # It preserves the virtual median/base request but retains the PHYSICAL tail guard.
    a2 = min(virtual_base, physical_guard)
    return {
        "preservedIntentEv": p,
        "physicalMedian": float(physical_median),
        "physicalTail": float(physical_tail),
        "virtualMedian": float(virtual_median),
        "virtualTail": float(virtual_tail),
        "baseMedianGainPhysical": physical_base,
        "guardGainPhysical": physical_guard,
        "baseMedianGainVirtual": virtual_base,
        "guardGainVirtual": virtual_guard,
        "A0Gain": float(a0),
        "A1Gain": float(a1),
        "A2PhysicalTailGain": float(a2),
    }


def tg_weight(cct):
    x = float(np.clip((TG_START_K - cct) / (TG_START_K - TG_FULL_K), 0.0, 1.0))
    return x * x * (3.0 - 2.0 * x)


def exact_fpga_422_tg1(rgb8, cct):
    h, w, _ = rgb8.shape
    w2 = w - (w & 1)
    r = rgb8[:, :w2, 0].astype(np.int64)
    g = rgb8[:, :w2, 1].astype(np.int64)
    b = rgb8[:, :w2, 2].astype(np.int64)
    y = (4899 * r + 9617 * g + 1868 * b) >> 14
    rs = r[:, 0::2] + r[:, 1::2]
    gs = g[:, 0::2] + g[:, 1::2]
    bs = b[:, 0::2] + b[:, 1::2]
    cb_s = ((((-2765 * rs + 1) >> 1) - ((5427 * gs) >> 1) + ((8192 * bs) >> 1))) >> 14
    cr_s = ((((8192 * rs) >> 1) - ((6860 * gs) >> 1) - ((1332 * bs) >> 1))) >> 14
    cb = ((cb_s + 128) & 0xff).astype(np.float64) - 128.0
    cr = ((cr_s + 128) & 0xff).astype(np.float64) - 128.0
    tw = tg_weight(cct)
    cb_gain = 1.0 - TG_NEG_CB_COMPRESSION * tw
    cr_gain = 1.0 - TG_NEG_CR_COMPRESSION * tw
    cb = np.where(cb < 0, cb * cb_gain, cb)
    cr = np.where(cr < 0, cr * cr_gain, cr)
    cb = np.repeat(cb, 2, axis=1)
    cr = np.repeat(cr, 2, axis=1)
    out = np.stack([
        y + 1.402 * cr,
        y - .344136 * cb - .714136 * cr,
        y + 1.772 * cb,
    ], axis=-1)
    if w2 != w:
        out = np.concatenate([out, rgb8[:, w2:, :].astype(np.float64)], axis=1)
    # Android roundU8 semantics after TG1 reconstruction.
    out = np.clip(out / 255.0, 0.0, 1.0)
    return np.floor(out * 255.0 + .5).astype(np.uint8)


def render_stage(m9, gain, curve, cct):
    scaled = m9 * float(gain) * RAW_MAX
    pre_any_hi = float(np.mean(np.any(scaled > RAW_MAX, axis=-1)))
    pre_all_hi = float(np.mean(np.all(scaled > RAW_MAX, axis=-1)))
    pre_any_lo = float(np.mean(np.any(scaled < 0.0, axis=-1)))
    x = np.clip(np.rint(scaled), 0, RAW_MAX).astype(np.int64)
    flat = x.reshape(-1, 3)
    mask = flat[:, 0] >= flat[:, 1]
    acc = np.empty_like(flat)
    acc[mask] = flat[mask] @ QE.T
    acc[~mask] = flat[~mask] @ QO.T
    raw_idx = acc >> 16
    matrix_high = float(np.mean(np.any(raw_idx > LUT_MAX, axis=1)))
    matrix_low = float(np.mean(np.any(raw_idx < 0, axis=1)))
    idx = np.clip(raw_idx, 0, LUT_MAX).astype(np.int32)
    rgb8_pre_bt = curve[idx].reshape(x.shape).astype(np.uint8)
    rgb8_clip_fraction = float(np.mean((rgb8_pre_bt == 0) | (rgb8_pre_bt == 255)))
    out8 = exact_fpga_422_tg1(rgb8_pre_bt, cct)
    return out8, {
        "preMatrixAnyChannelHighClipFraction": pre_any_hi,
        "preMatrixAllChannelHighClipFraction": pre_all_hi,
        "preMatrixAnyChannelBelowZeroFraction": pre_any_lo,
        "matrixIndexHighClipFraction": matrix_high,
        "matrixIndexLowClipFraction": matrix_low,
        "rgb8PreBt601EdgeClipFraction": rgb8_clip_fraction,
        "branchEvenOccurrence": float(mask.mean()),
    }


def exact_y8(rgb8):
    a = rgb8.astype(np.int64)
    return ((4899 * a[..., 0] + 9617 * a[..., 1] + 1868 * a[..., 2]) >> 14).astype(np.uint8)


def output_stats(rgb8):
    y = exact_y8(rgb8)
    h, w = y.shape
    cy0, cy1 = h // 4, h - h // 4
    cx0, cx1 = w // 4, w - w // 4
    my0, my1 = h // 3, h - h // 3
    mx0, mx1 = w // 3, w - w // 3
    mx = rgb8.max(axis=-1)
    return {
        "renderGlobalMedianY8": float(np.median(y)),
        "renderCenter50MedianY8": float(np.median(y[cy0:cy1, cx0:cx1])),
        "renderMiddleCenterMedianY8": float(np.median(y[my0:my1, mx0:mx1])),
        "renderQ95Y8": float(np.quantile(y, .95)),
        "renderQ99Y8": float(np.quantile(y, .99)),
        "renderNearWhiteFraction": float(np.mean(mx >= 250)),
        "renderAnyChannelFullClipFraction": float(np.mean(np.any(rgb8 == 255, axis=-1))),
        "renderAllChannelWhiteFraction": float(np.mean(np.all(rgb8 == 255, axis=-1))),
        "renderDeepBlackFractionY16": float(np.mean(y <= 16)),
    }


def orient_image(im: Image.Image, orientation: int):
    if orientation == 3:
        return im.rotate(180, expand=True)
    if orientation == 6:
        return im.rotate(-90, expand=True)
    if orientation == 8:
        return im.rotate(90, expand=True)
    return im


def read_json(path):
    try:
        return json.loads(path.read_text(errors="replace"))
    except Exception:
        return None


def achieved_intent_from_m9(obj):
    try:
        return float(obj["m9ExposureAudit"]["derived"]["captureEnergyVsPhotonOnlyEv"])
    except Exception:
        return None


def preview_safety_from_m9(obj):
    # Prefer the capture-decision snapshot if present; then current preview-luma global.
    candidates = []
    try:
        candidates.append(obj["m9ExposureFeedback"]["classifierAtDecision"]["inputs"])
    except Exception:
        pass
    try:
        candidates.append(obj["m9M10rMfmTest"])
    except Exception:
        pass
    try:
        candidates.append(obj["subjectMotion"]["previewLuma"]["global"])
    except Exception:
        pass
    for c in candidates:
        q95 = c.get("globalQ95", c.get("q95"))
        b240 = c.get("brightFractionGE240")
        if q95 is not None or b240 is not None:
            return (float(q95) if q95 is not None else None,
                    float(b240) if b240 is not None else None)
    return None, None


def renderer_from_primary(obj):
    if not isinstance(obj, dict):
        return None
    r = obj.get("renderer")
    return r if isinstance(r, dict) else None


def stem_of_dng(p: Path):
    return p.stem


def find_sidecar(files, stem, suffix):
    exact = [p for p in files if p.name == stem + suffix]
    if exact:
        return exact[0]
    # Some bundles preserve sidecars in nested diagnostic directories.
    cand = [p for p in files if p.name.startswith(stem) and p.name.endswith(suffix)]
    return cand[0] if cand else None


def unpack_inputs(inputs, work: Path):
    work.mkdir(parents=True, exist_ok=True)
    for idx, src in enumerate(inputs):
        src = Path(src)
        if src.is_dir():
            dst = work / f"dir_{idx}"
            shutil.copytree(src, dst, dirs_exist_ok=True)
        elif src.suffix.lower() == ".zip":
            dst = work / f"zip_{idx}"
            dst.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(src) as z:
                z.extractall(dst)
        else:
            raise ValueError(f"unsupported input: {src}")
    # Recover one level of nested ZIP bundles without repeated recursive extraction.
    nested = list(work.rglob("*.zip"))
    for i, zpath in enumerate(nested):
        dst = zpath.parent / (zpath.stem + f"__nested_{i}")
        try:
            dst.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zpath) as z:
                z.extractall(dst)
        except zipfile.BadZipFile:
            pass
    return work


def blind_order(stem, variants, seed):
    h = int(hashlib.sha256((str(seed) + "|" + stem).encode()).hexdigest()[:16], 16)
    rng = random.Random(h)
    vv = list(variants)
    rng.shuffle(vv)
    return vv


def make_blind_sheet(items, path, cols=2, cell_w=520, cell_h=430, title_h=34):
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cell_w * cols, (cell_h + title_h) * rows), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (label, p) in enumerate(items):
        im = Image.open(p).convert("RGB")
        im.thumbnail((cell_w - 10, cell_h - 8), Image.Resampling.LANCZOS)
        x = (i % cols) * cell_w
        y = (i // cols) * (cell_h + title_h)
        draw.text((x + 8, y + 8), label, fill="black")
        sheet.paste(im, (x + (cell_w - im.width) // 2, y + title_h))
    sheet.save(path, quality=95, subsampling=0)


def build_scene_linear(cal: FrozenCalibration, cam, neutral):
    xy = cal.neutral_to_xy(neutral)
    cct = cct_from_xy(xy)
    wa = weight_a(cct)
    xyz50 = cal.to_xyz50(cam, xy, wa)
    xyz_scene = xyz50 @ bradford(D50_XY, xy).T
    m9cm = interp(M9_CM_A, M9_CM_D65, wa)
    mcam = xyz_scene @ m9cm.T
    mwhite = m9cm @ xy_to_xyz(xy)
    m9 = np.maximum(mcam / np.maximum(mwhite[None, None, :], 1e-8), 0.0)
    xyz65 = xyz50 @ bradford(D50_XY, D65_XY).T
    prox = xyz65 @ XYZ2SRGB.T
    ylin = np.maximum(.2126 * prox[..., 0] + .7152 * prox[..., 1] + .0722 * prox[..., 2], 0.0)
    return m9, ylin, cct, wa


def self_test():
    med = 0.02
    tail = 0.88
    achieved = 0.27
    r0 = tc20_variants(med, tail, 0.0, achieved, 0.0)
    if abs(r0["A1Gain"] - r0["A0Gain"]) > 1e-12:
        raise SystemExit("SELFTEST fail: zero-preservation A1 != A0")
    r2 = tc20_variants(med, tail, 0.0, achieved, 0.20)
    expected = min(r2["A0Gain"] * (2.0 ** r2["preservedIntentEv"]), 16.0)
    if r2["guardGainPhysical"] <= r2["baseMedianGainPhysical"]:
        # This synthetic scene should be guard-limited.
        if abs(math.log2(r2["A1Gain"] / r2["A0Gain"]) - r2["preservedIntentEv"]) > 1e-10:
            raise SystemExit("SELFTEST fail: guard-limited A1 does not preserve requested intent")
        if abs(r2["A2PhysicalTailGain"] - r2["A0Gain"]) > 1e-12:
            raise SystemExit("SELFTEST fail: physical-tail A2 control should remain A0 when guard-limited")
    if not math.isfinite(expected):
        raise SystemExit("SELFTEST fail: non-finite expected gain")
    print("PASS TC20INTENT1A self-test")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("inputs", nargs="*", type=Path, help="directories or ZIP archives")
    ap.add_argument("--calibration-bin", type=Path,
                    default=Path("payload/app/src/main/assets/m9/m9_r35_calibration.bin"))
    ap.add_argument("--outdir", type=Path, default=Path("TC20INTENT1A_OUT"))
    ap.add_argument("--long-side", type=int, default=1600)
    ap.add_argument("--blind-seed", type=int, default=9152009)
    ap.add_argument("--positive-threshold", type=float, default=0.01)
    ap.add_argument("--android-parity-tolerance-ev", type=float, default=0.025)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        if not args.inputs:
            return
    if not args.inputs:
        ap.error("provide at least one input directory/ZIP, or --self-test")

    out = args.outdir
    if out.exists():
        shutil.rmtree(out)
    (out / "renders").mkdir(parents=True)
    (out / "blind").mkdir(parents=True)
    (out / "metadata").mkdir(parents=True)
    extraction = out / "_extracted"
    unpack_inputs(args.inputs, extraction)

    cal = FrozenCalibration(args.calibration_bin)
    files = [p for p in extraction.rglob("*") if p.is_file()]
    dngs = sorted([p for p in files if p.suffix.lower() == ".dng"])
    if not dngs:
        raise SystemExit("No DNGs found in supplied inputs")

    rows = []
    blind_key = {}
    missing_m9 = []
    android_parity_failures = []
    processed = 0

    for di, dng in enumerate(dngs, 1):
        stem = stem_of_dng(dng)
        m9_path = find_sidecar(files, stem, "_M9.json")
        primary_path = find_sidecar(files, stem, "_M9_PRIMARY.json")
        m9_obj = read_json(m9_path) if m9_path else None
        primary_obj = read_json(primary_path) if primary_path else None
        intent = achieved_intent_from_m9(m9_obj) if m9_obj else None
        if intent is None:
            missing_m9.append(stem)
            intent = 0.0
        q95, bright240 = preview_safety_from_m9(m9_obj) if m9_obj else (None, None)

        cam, neutral, orientation, baseline, iso, rawm = read_dng(dng, args.long_side)
        m9, ylin, cct, wa = build_scene_linear(cal, cam, neutral)
        physical_median = weighted_median_luma(ylin)
        physical_tail = rawm["physicalTail"]

        # A0 is computed once. All variants apply gain to the exact same m9 array.
        base_v0 = tc20_variants(physical_median, physical_tail, baseline, intent, 0.0)
        a0_gain = base_v0["A0Gain"]

        renderer = renderer_from_primary(primary_obj)
        android_gain = float(renderer["gain"]) if renderer and renderer.get("gain") is not None else None
        android_base = float(renderer["baseMedianGain"]) if renderer and renderer.get("baseMedianGain") is not None else None
        android_guard = float(renderer["tc20GuardGain"]) if renderer and renderer.get("tc20GuardGain") is not None else None
        android_delta_ev = None
        if android_gain and android_gain > 0 and a0_gain > 0:
            android_delta_ev = math.log2(a0_gain / android_gain)
            if abs(android_delta_ev) > args.android_parity_tolerance_ev:
                android_parity_failures.append({
                    "file": stem, "offlineA0Gain": a0_gain,
                    "androidGain": android_gain, "deltaEv": android_delta_ev,
                })

        variant_images = {}
        for cap in CAPS:
            vv = tc20_variants(physical_median, physical_tail, baseline, intent, cap)
            for family, gain_key in (("A0", "A0Gain"), ("A1", "A1Gain"), ("A2", "A2PhysicalTailGain")):
                # A0 is identical for every cap; only render it at cap==0.
                if family == "A0" and cap != 0.0:
                    continue
                # A2 is primarily telemetry/control; do not write redundant JPEGs.
                write_image = family in ("A0", "A1")
                gain = vv[gain_key]
                rgb8, stage = render_stage(m9, gain, cal.curve02, cct)
                stats = output_stats(rgb8)
                label = "A0" if family == "A0" else f"{family}_C{int(round(cap*100)):02d}"
                image_path = None
                if write_image:
                    image_path = out / "renders" / label
                    image_path.mkdir(parents=True, exist_ok=True)
                    image_path = image_path / f"{stem}_{label}.jpg"
                    pil = orient_image(Image.fromarray(rgb8, mode="RGB"), orientation)
                    pil.save(image_path, quality=95, subsampling=0)
                    variant_images[label] = image_path

                row = {
                    "file": stem,
                    "variant": label,
                    "family": family,
                    "testCapEv": cap,
                    "actualCaptureEnergyVsPhotonOnlyEv": intent,
                    **vv,
                    "candidateGain": gain,
                    "actualGainDeltaVsA0Ev": math.log2(max(gain, 1e-12) / max(a0_gain, 1e-12)),
                    "physicalTailTimesGain": physical_tail * gain,
                    "rawHardClipFraction": rawm["rawHardClipFraction"],
                    "rawUq99": rawm["rawUq99"],
                    "rawUq99_5": rawm["rawUq99_5"],
                    "rawUq99_8": rawm["rawUq99_8"],
                    "tc20Q": rawm["tc20Q"],
                    "tc20TailCurvature": rawm["tc20TailCurvature"],
                    "tc20TailIsolated": rawm["tc20TailIsolated"],
                    "previewGlobalQ95": q95,
                    "previewBrightFractionGE240": bright240,
                    "saturatedPreviewSafetyCohort": bool(q95 is not None and q95 >= 255.0),
                    "iso": iso,
                    "baselineExposureEv": baseline,
                    "cct": cct,
                    "AWeight": wa,
                    "androidFrozenGain": android_gain,
                    "androidFrozenBaseMedianGain": android_base,
                    "androidFrozenGuardGain": android_guard,
                    "offlineA0VsAndroidGainDeltaEv": android_delta_ev,
                    **stage,
                    **stats,
                }
                rows.append(row)

        # Blind only frames with real positive achieved assistance; A0 + A1 C10/C20/C30.
        if intent > args.positive_threshold:
            variants = ["A0", "A1_C10", "A1_C20", "A1_C30"]
            variants = [v for v in variants if v in variant_images]
            shuffled = blind_order(stem, variants, args.blind_seed)
            letters = [chr(ord("A") + i) for i in range(len(shuffled))]
            items = []
            key = {}
            for letter, variant in zip(letters, shuffled):
                items.append((letter, variant_images[variant]))
                key[letter] = variant
            sheet = out / "blind" / f"{stem}_BLIND.jpg"
            make_blind_sheet(items, sheet)
            blind_key[stem] = {
                "actualCaptureEnergyVsPhotonOnlyEv": intent,
                "previewGlobalQ95": q95,
                "saturatedPreviewSafetyCohort": bool(q95 is not None and q95 >= 255.0),
                "key": key,
            }

        processed += 1
        print(f"[{di}/{len(dngs)}] {stem}: intent={intent:+.3f} A0={a0_gain:.4f} "
              f"guard={base_v0['guardGainPhysical']:.4f} q95={q95}", flush=True)

    # Remove copied corpus after results so output package remains small.
    shutil.rmtree(extraction, ignore_errors=True)

    csv_path = out / "metadata" / "tc20intent1a_metrics.csv"
    if rows:
        fields = []
        for row in rows:
            for k in row:
                if k not in fields:
                    fields.append(k)
        with csv_path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader(); w.writerows(rows)

    (out / "metadata" / "blind_key.json").write_text(json.dumps(blind_key, indent=2))

    # Summary by A1 cap, excluding saturated-preview safety cohort from the ordinary means.
    summary_variants = {}
    for label in ("A0", "A1_C10", "A1_C20", "A1_C30", "A2_C10", "A2_C20", "A2_C30"):
        rr = [r for r in rows if r["variant"] == label and r["actualCaptureEnergyVsPhotonOnlyEv"] > args.positive_threshold]
        ordinary = [r for r in rr if not r["saturatedPreviewSafetyCohort"]]
        safety = [r for r in rr if r["saturatedPreviewSafetyCohort"]]
        def agg(x):
            if not x:
                return {"count": 0}
            keys = [
                "actualGainDeltaVsA0Ev", "renderGlobalMedianY8", "renderCenter50MedianY8",
                "renderMiddleCenterMedianY8", "renderNearWhiteFraction",
                "renderAnyChannelFullClipFraction", "renderAllChannelWhiteFraction",
                "renderDeepBlackFractionY16", "preMatrixAnyChannelHighClipFraction",
                "matrixIndexHighClipFraction",
            ]
            o = {"count": len(x)}
            for k in keys:
                o["mean_" + k] = float(np.mean([float(r[k]) for r in x]))
                o["max_" + k] = float(np.max([float(r[k]) for r in x]))
            return o
        summary_variants[label] = {
            "ordinaryPositiveCohort": agg(ordinary),
            "saturatedPreviewSafetyCohort": agg(safety),
        }

    manifest = {
        "schema": "m9cam.tc20intent.offline.v1a",
        "version": VERSION,
        "researchOnly": True,
        "productionImplementation": False,
        "rendererReference": "R3.8-H25/TG1 frozen colour/tone architecture",
        "calibrationBin": str(args.calibration_bin),
        "intentAuthority": "m9ExposureAudit.derived.captureEnergyVsPhotonOnlyEv",
        "preservedIntentRule": "min(max(actualCaptureEnergyVsPhotonOnlyEv,0),testCapEv)",
        "capsEv": list(CAPS),
        "A0": "frozen physical median + physical TC20 tail",
        "A1": "intent-normalized virtual median + virtual tail; gain applied to unchanged physical RAW-derived M9 image",
        "A2": "intent-normalized virtual median but physical TC20 tail guard retained; blocker/control only",
        "A2DelayedClip": "NOT IMPLEMENTED in 1A; only investigate after A1 preferred strength is identified",
        "physicalSafetyNeverNormalized": True,
        "saturatedPreviewCohortRule": "previewGlobalQ95==255 is separated from ordinary strength selection",
        "blind": "A0/A1-0.10/A1-0.20/A1-0.30 randomized per positive-intent frame; key stored separately",
        "metricDefinitions": {
            "renderCenter50MedianY8": "central 50% width x 50% height, exact Q14 Leica BT601 Y on final RGB",
            "renderMiddleCenterMedianY8": "central third width x central third height",
            "renderDeepBlackFractionY16": "fraction final exact-Q14 Y <=16",
            "preMatrixAnyChannelHighClipFraction": "fraction m9*gain channels exceeding RAW_MAX before current physical clamp",
            "matrixIndexHighClipFraction": "fraction pixels where any QE/QO matrix index exceeds LUT_MAX before LUT clamp",
        },
        "inputDngCount": len(dngs),
        "processedCount": processed,
        "missingM9IntentSidecars": missing_m9,
        "androidParityToleranceEv": args.android_parity_tolerance_ev,
        "androidParityFailureCount": len(android_parity_failures),
        "androidParityFailures": android_parity_failures,
        "summary": summary_variants,
    }
    (out / "metadata" / "manifest.json").write_text(json.dumps(manifest, indent=2))

    print("\nTC20INTENT1A complete")
    print(" processed:", processed)
    print(" positive blind sheets:", len(blind_key))
    print(" saturated-preview positive cohort:", sum(1 for v in blind_key.values() if v["saturatedPreviewSafetyCohort"]))
    print(" Android A0 parity failures:", len(android_parity_failures))
    print(" output:", out)


if __name__ == "__main__":
    main()
