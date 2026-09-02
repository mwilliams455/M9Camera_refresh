#!/usr/bin/env python3
"""Reference implementation of the v0.7K LUMA2.2 diagnostic scorer.

Usage:
  python3 luma2_2_backlight_scorer_reference.py IMG_..._M9.json [...]

The scorer uses Photon preview exposure energy and LUMA1 preview statistics
only. It does not use RAW/image data and never applies exposure feedback.
"""
import json, math, sys

DARK64_LOW = 0.20
DARK64_HIGH = 0.35
BRIGHT192_LOW = 0.04
BRIGHT192_HIGH = 0.10
SEPARATION_LOW = 60.0
SEPARATION_HIGH = 110.0
ENERGY_FULL_SCORE = 1.00
ENERGY_ZERO_SCORE = 2.50
ABSOLUTE_BRIGHT_CONFIDENCE_FLOOR = 0.62

CENTER_PROTECTION_START_Y = 16.0
CENTER_PROTECTION_FULL_Y = 28.0

CATA_ENERGY_FULL_SCORE = 0.03
CATA_ENERGY_ZERO_SCORE = 0.12
CATA_MEDIAN_FULL_DARK_Y = 32.0
CATA_MEDIAN_ZERO_DARK_Y = 64.0
CATA_Q95_FULL_DARK_Y = 64.0
CATA_Q95_ZERO_DARK_Y = 96.0
CATA_Q99_FULL_DARK_Y = 80.0
CATA_Q99_ZERO_DARK_Y = 112.0

APPLY_SCORE = 0.50
EV_RAMP_LOW = 0.35
EV_RAMP_HIGH = 0.85
MAX_RECOMMENDED_EV = 0.75

def clamp01(v):
    return max(0.0, min(1.0, v))

def smoothstep(v, lo, hi):
    t = clamp01((v-lo)/(hi-lo)) if hi > lo else (1.0 if v >= hi else 0.0)
    return t*t*(3.0-2.0*t)

def cbrt(v):
    return v ** (1.0/3.0) if v > 0.0 else 0.0

def score(j):
    e = j["photonExposureDecision"]["preview"]["exposureEnergyIsoSeconds"]
    l = j["subjectMotion"]["previewLuma"]
    g = l["global"]
    c = l.get("center50", {})

    d = g["darkFractionLE64"]
    b = g["brightFractionGE192"]
    median = g["median"]
    q95 = g["q95"]
    q99 = g["q99"]
    sep = g.get("q95MinusMedian", q95-median)
    center_delta = c.get("medianMinusGlobalMedian")

    dark = smoothstep(d, DARK64_LOW, DARK64_HIGH)
    bright = smoothstep(b, BRIGHT192_LOW, BRIGHT192_HIGH)
    separation = smoothstep(sep, SEPARATION_LOW, SEPARATION_HIGH)
    relative_structure = cbrt(max(0.0, dark*separation))
    bright_multiplier = (ABSOLUTE_BRIGHT_CONFIDENCE_FLOOR
                         + (1.0-ABSOLUTE_BRIGHT_CONFIDENCE_FLOOR)*bright)
    structure = clamp01(relative_structure*bright_multiplier)
    energy = 1.0 - smoothstep(e, ENERGY_FULL_SCORE, ENERGY_ZERO_SCORE)
    raw_relative = clamp01(structure*energy)

    center_protection = (smoothstep(center_delta, CENTER_PROTECTION_START_Y,
                                    CENTER_PROTECTION_FULL_Y)
                         if center_delta is not None and math.isfinite(center_delta)
                         else 0.0)
    center_multiplier = 1.0-center_protection
    protected_relative = clamp01(raw_relative*center_multiplier)

    cata_energy = 1.0-smoothstep(e, CATA_ENERGY_FULL_SCORE, CATA_ENERGY_ZERO_SCORE)
    cata_median = 1.0-smoothstep(median, CATA_MEDIAN_FULL_DARK_Y, CATA_MEDIAN_ZERO_DARK_Y)
    cata_q95 = 1.0-smoothstep(q95, CATA_Q95_FULL_DARK_Y, CATA_Q95_ZERO_DARK_Y)
    cata_q99 = 1.0-smoothstep(q99, CATA_Q99_FULL_DARK_Y, CATA_Q99_ZERO_DARK_Y)
    collapse = cbrt(max(0.0, cata_median*cata_q95*cata_q99))
    catastrophic = clamp01(cata_energy*collapse)

    total = max(protected_relative, catastrophic)
    rec = MAX_RECOMMENDED_EV*smoothstep(total, EV_RAMP_LOW, EV_RAMP_HIGH)
    would = total >= APPLY_SCORE

    catastrophic_dominant = catastrophic > protected_relative
    center_suppressed = (center_protection > 0.0 and raw_relative >= APPLY_SCORE
                         and protected_relative < APPLY_SCORE)
    if catastrophic_dominant and would:
        reason = "catastrophic_ae_starvation_candidate"
    elif center_suppressed:
        reason = "center_body_protected_high_contrast_control"
    elif relative_structure <= 0.0 and catastrophic <= 0.0:
        reason = "no_relative_backlight_structure_or_preview_collapse"
    elif energy <= 0.0 and catastrophic <= 0.0:
        reason = "backlight_structure_but_ae_energy_not_starved"
    elif not would:
        reason = "weak_ae_starvation_candidate"
    elif bright <= 0.0:
        reason = "relative_backlight_starvation_candidate_low_absolute_bright"
    else:
        reason = "backlight_starvation_candidate"

    return {
        "energy": e,
        "median": median,
        "q95": q95,
        "q99": q99,
        "dark64": d,
        "bright192": b,
        "q95MinusMedian": sep,
        "centerMedianMinusGlobalMedian": center_delta,
        "darkBodyScore": dark,
        "brightPopulationScore": bright,
        "bodyHighlightSeparationScore": separation,
        "relativeBodyHighlightStructureScore": relative_structure,
        "absoluteBrightConfidenceMultiplier": bright_multiplier,
        "backlightStructureScore": structure,
        "energyStarvationScore": energy,
        "rawRelativeBacklightStarvationScore": raw_relative,
        "centerBodyProtectionScore": center_protection,
        "centerBodyProtectionMultiplier": center_multiplier,
        "protectedRelativeBacklightStarvationScore": protected_relative,
        "catastrophicEnergyStarvationScore": cata_energy,
        "catastrophicMedianDarkScore": cata_median,
        "catastrophicQ95DarkScore": cata_q95,
        "catastrophicQ99DarkScore": cata_q99,
        "catastrophicPreviewCollapseScore": collapse,
        "catastrophicAeStarvationScore": catastrophic,
        "backlightStarvationScore": total,
        "wouldApply": would,
        "recommendedExposureCorrectionEv": rec,
        "appliedExposureCorrectionEv": 0.0,
        "reason": reason,
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    for path in sys.argv[1:]:
        with open(path, "r", encoding="utf-8") as f:
            result = score(json.load(f))
        print(path)
        print(json.dumps(result, indent=2, sort_keys=True))
