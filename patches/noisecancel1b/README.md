# M9NOISECANCEL1B — decoupled AMaZE quiet-chroma cancellation

Parent: **1.85 / PRIMARYEXPORT1B FRESHFIRST + NOISECANCEL1A assets**.

Phone validation finally produced a current PRIMARY and showed that
`detail1HApplied=false` on the accepted COLOURTRIAL1C AMaZE production path.
Therefore NOISECANCEL1A's guard existed in the APK but was not on the active
render path.

NOISECANCEL1B fixes that architectural coupling without re-enabling DETAIL or
sharpness.

## Active stage

The new filter runs:

```
accepted AMaZE camera RGB
        ↓
NOISECANCEL1B quiet chroma
        ↓
SOURCECAL2A / M9 target transform
        ↓
TC20 → SAT2 → curve02 → BT.601/TG1
```

It works only on **R−G and B−G** residuals. The green channel is copied exactly
and never written by the filter.

## Noise authority

Camera2 `SENSOR_NOISE_PROFILE` remains authoritative. Local lens-shading gain
is used to transport the expected sensor variance into the current camera-RGB
code domain. No ISO lookup table, device-name branch, or guessed multiplier is
introduced.

The filter uses a five-sample cross median only when both:

- green/luma structure is quiet relative to expected sensor noise; and
- local chroma spread/residual is compatible with noise rather than a real
  colour edge.

Confidence must exceed **0.65**, ramps to full at **0.90**, and can move a
channel at most **50%** of the distance toward the local chroma median.
Near-black and near-saturated pixels are bypassed.

## Explicit non-goals

- DETAIL1H remains off.
- Sharpness is not reintroduced.
- Green/luminance denoising is not added.
- The existing AMaZE RAW 0.25 noise stage remains unchanged.
- Auto exposure, TC20, SAT2, curve02, TG1, DNG and preview are unchanged.
- PRIMARYEXPORT1B fresh-first diagnostics remain unchanged.

Version: **1.86-m9noisecancel1b-decoupled-primaryexport1b-tg1**.
