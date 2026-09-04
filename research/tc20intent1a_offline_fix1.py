#!/usr/bin/env python3
"""TC20INTENT1A FIX1 entry point.

Keeps the validated TC20INTENT1A renderer/equations untouched and widens only
preview safety-metadata discovery so current/older M9 sidecar schemas classify
the saturated-preview safety cohort correctly.
"""

import tc20intent1a_offline as core


def preview_safety_from_m9(obj):
    candidates = []

    # Current diagnostic architecture: capture-linked scene exposure inputs carry
    # the exact global preview tail metrics we need for the q95==255 safety cohort.
    try:
        candidates.append(obj["m9SceneExposureDiagnostic"]["inputs"])
    except Exception:
        pass

    # Live feedback snapshot variants used by prior builds.
    try:
        candidates.append(obj["m9ExposureFeedback"]["classifierAtDecision"]["inputs"])
    except Exception:
        pass
    try:
        candidates.append(obj["m9BacklightDiagnostic"]["inputs"])
    except Exception:
        pass

    # MFM2A will publish these directly; MFM1 usually will not, but retain support.
    try:
        candidates.append(obj["m9M10rMfmTest"])
    except Exception:
        pass

    # Raw preview-luma snapshots have appeared under both names across the project.
    for root_name in ("subjectMotion", "m9SubjectMotion"):
        try:
            candidates.append(obj[root_name]["previewLuma"]["global"])
        except Exception:
            pass

    for c in candidates:
        if not isinstance(c, dict):
            continue
        q95 = c.get("globalQ95")
        if q95 is None:
            q95 = c.get("previewGlobalQ95Y")
        if q95 is None:
            q95 = c.get("q95")
        b240 = c.get("brightFractionGE240")
        if b240 is None:
            b240 = c.get("previewBrightFractionGE240")
        if q95 is not None or b240 is not None:
            return (
                float(q95) if q95 is not None else None,
                float(b240) if b240 is not None else None,
            )
    return None, None


core.preview_safety_from_m9 = preview_safety_from_m9
core.VERSION = core.VERSION + "-FIX1-PREVIEWSAFETY"


if __name__ == "__main__":
    core.main()
