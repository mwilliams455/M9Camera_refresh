# M9TG2NEUTRAL1A — preview-only tungsten neutralisation probe

22 September 2026.

## Why this exists

The original TG1 stage is intentionally a gentle warm-light guard, not a full
neutralisation transform. At full weight it compresses only negative Cb
(yellow) by 25% and negative Cr (green) by 16%. Positive Cr — the red/orange
component of many tungsten casts — is untouched.

PAIR1A/PAIR1B preview-timestamp experiments are explicitly out of scope here and
remain rolled back. Photon SurfaceTexture transport is unchanged.

## Candidate math

TG2 keeps the same BT.601 Y authority and therefore does not intentionally alter
luminance. In warm light it operates only on chroma:

- negative Cb/yellow is compressed by 18–58%, strongest for low/moderate chroma;
- positive Cr/red-orange is compressed by up to 42%, but only when negative Cb
  also identifies the warm yellow/orange quadrant;
- negative Cr/green is compressed by 10–22%;
- positive Cb/blue-cyan is untouched;
- correction tapers away as chroma magnitude grows, preserving strongly coloured
  subjects rather than treating genuine yellow/orange/red as neutral surfaces.

The CCT weight remains the existing TG1 4500 K -> 3200 K smoothstep. This probe
does not change exposure, SAT2, curve02, source matrices, sharpness, Noise2,
DETAIL1H, or any saved-JPEG code.

## Promotion boundary

This first candidate is preview-only. The saved JPEG renderer remains byte/hash
frozen. The purpose is to establish whether the proposed two-axis warm residual
math fixes the visible 2400–3000 K viewfinder cast without damaging real subject
colour. If accepted visually, the same BT.601 equations can be ported to the
native 4:2:2 still stage and replayed against the existing photographic corpus.

## Production status — rejected / frozen

Device validation at ~3266–3301 K exposed a failure of the TG2 classification assumption. With the CCT ramp near full strength (~0.98–0.99), low/moderate-chroma genuine warm subject colour—most importantly skin—was treated too much like illuminant contamination and visibly lost colour. This is a conceptual limitation of post-curve BT.601 chroma neutralisation, not a transport or SOURCECAL2A failure.

TG2NEUTRAL1A and TG2STILL1A are therefore **not production candidates** and must not be inherited by successor branches. Keep these files only as research evidence. The production lineage reverts to the original mild TG1 arithmetic plus M9TUNGSTENCONT1A preview continuity. Exposure, SAT2, curve02, DETAIL1H, sharpness/noise and Photon preview transport remain unchanged.

Future tungsten work should start from a scene/illuminant adaptation stage that can distinguish illuminant correction from genuine warm object colour; do not resume by simply increasing or reweighting TG2.
