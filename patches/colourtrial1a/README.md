# Auto exposure — highlight protection

Highlight protection belongs to automatic exposure selection. Its role is to
limit additional positive Auto exposure when the preview predicts excessive
clipping or broad brightening. This is separate from colour reconstruction
and from any attempt to infer values after the sensor has clipped.

The working colour/detail configuration is documented in
[`research/colourtrial1b`](../../research/colourtrial1b/README.md). It retains
bounded noise and chroma corrections alongside this Auto policy; stronger
highlight reconstruction is not part of that configuration.

## Total positive Auto bias

This patch makes the existing processed-preview highlight budget apply to the
total positive automatic exposure bias, including an inherited scene baseline.
Previously, rejection of extra shadow lift could still leave a positive baseline.

The candidate uses the last consecutive bracket step within the existing new-clip
and broad-brightening budgets. Missing, invalid or stale meter data cannot justify
positive automatic assistance. Negative baselines retain their role. Explicit user
EV still freezes the displayed automatic baseline; manual ISO or shutter still
disables automatic assistance. A quarter-stop rise per fresh sample and immediate
release remain in place.

The guard uses processed-preview measurements. It does not establish physical
RAW channel headroom, recover clipped colour, or remove all interpolation
fringe. It caps positive Auto assistance rather than imposing a fixed negative
EV on every scene. It can lower image brightness when a prior positive fallback
would have been retained. Device cadence, transition appearance, and photographic
benefit still require phone validation.

## Implementation status

`apply.py ASSEMBLED_PHOTON_TREE` checks the exact parent source hash and replaces
only M9AutoExposure2D.java. It refuses an unexpected parent and is idempotent.
`test.py OUTPUT_BUILD_DIR` compiles the actual candidate unchanged and checks 21
synthetic state/selection scenarios. The tiny JSON stubs only discard diagnostic
serialization. Run via a Java runtime containing the compiler module.

No workflow or APK incorporates this patch automatically. No default reconstruction,
SAT bank, tone curve, HSM, TG, JPEG encoding, or existing branch is changed.
