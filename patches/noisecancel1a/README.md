# M9NOISECANCEL1A — quiet-chroma cancellation

Parent: **1.82 / FINISH1I FASTACQUIRE1B SAFE075**.

The current DETAIL1H stage already uses the live Camera2 noise profile to apply a
bounded noise guard in the reconstructed R/B-minus-green carrier. Phone and host
forensics showed that the earlier global `strength=2` experiment is not a safe
default: although it reduces flat neutral noise further, it can worsen fine
colour structure.

NOISECANCEL1A therefore does **not** double the assumed sensor noise and does not
add generic luminance denoising.

## Policy

The existing DETAIL1H strength=1 classifier remains authoritative. Its local
`trust * weight` confidence still decides whether a residual looks like noise
or image detail.

Only when that existing confidence is already above **0.65** is the correction
allowed to move slightly farther toward the same mode1 smoothing target. The
additional blend rises smoothly and can consume at most 50% of the remaining
distance to the target. It never crosses the target.

Consequences:

- green/luma samples are unchanged;
- Leica texture/sharpness foundation is unchanged;
- low-confidence edges and fine structure are byte-identical to the 1.82 guard;
- clipped/censored neighbourhood protection is unchanged;
- no device-name or guessed ISO multiplier is introduced;
- Camera2 `SENSOR_NOISE_PROFILE` remains the noise authority;
- exposure, TC20, tone, saturation, tungsten and JPEG/DNG paths are frozen.

The intent is stronger **chroma-noise cancellation in quiet regions** without
turning the renderer into a smooth computational-camera look.

## Validation gate

The host regression compiles both the exact 1.82 guard and the candidate guard.
It requires:

1. the same smoothing target;
2. changed pixels only where the baseline confidence exceeds 0.65;
3. every changed carrier sample to move toward, but never across, that target;
4. high-frequency detail below the gate to remain byte-identical to 1.82;
5. censored neighbourhoods to remain exact bypass.

Version: **1.83-m9noisecancel1a-quietchroma-tg1**.
