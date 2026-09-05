# M9 BESTFIT1A — BRIGHT RGBPIVOT CAP1A

Research-only extension of the reconstructed 0.85-pivot RGB-ratio-preserving operator. Input is the full-12 MP Frozen JPEG95 replay; decoded baseline metrics differ negligibly from the uncompressed pre-JPEG audit.

The tested strength bank is 0 / 0.35 / 0.50 / 0.75 EV. Strength is maximum lower-tone density restraint; effect tapers linearly in EV to zero at normalized Y=0.85.

## Result

On 18:27:56, q95 and centre-q95 remain 236/249 at every pivot strength, while median moves 83 -> 72 -> 67 -> 60. Dark<=64 grows 42.35% -> 47.12% -> 48.94% -> 51.55%. Bright>=224 remains 8.22%.

On 18:20:12, q95/centre-q95 remain 245/255 and bright>=224 remains 10.10% through RGB075. Dark<=64 grows 81.06% -> 81.70% -> 81.94% -> 82.32%. This frame remains an ineligible hard negative; the point is only operator damage if misactivated.

## Conclusion

- RGB pivoting provides a materially safer BRIGHT operator family than uniform negative pre-curve EV on these controls.
- 0.75 EV remains defensible as an **absolute pivot-strength research ceiling** because the upper anchor is preserved, but it is not a default or target treatment.
- Strength still requires BRIGHT-subtype severity plus lower-body safety/rollback.
- Direct confirmed BRIGHT_FAIL DNG replay remains necessary before any live promotion.
