# STANDARD_FULLISO1A implementation policy — 2026-09-12

- Leica physical ISO labels: 160,200,250,320,400,500,640,800,1000,1250,1600,2000,2500 -> slots 0..12. Pull 80 reuses slot0 but is reserved for a future explicit user ISO choice.
- Standard selector modes by slot: [4,4,4,4,4,4,3,3,3,3,3,2,2].
- Internal arithmetic: mode4 signed x2, mode3 unchanged, mode2 signed arithmetic >>>1; working coefficients clamp [-2048,+2048].
- Base bank: canonical 13x2050 signed int16 rows derived at CI build time from hash-verified/decrypted Leica M9 1.216 LUTS resource.
- Xiaomi-main bridge: current physical capture SENSOR_SENSITIVITY x2 (established main-module normalization), then nearest Leica ISO in log2(EV), clamped to 160..2500. This bridge is mobile-specific, not claimed as Leica firmware behavior.
- Sharp source: recovered Leica GreenInterpolationWithCo interior q14.
- Noise/support: nNoise=2; Green +3, Noise2 +4, Sharp +2 -> cumulative support margin 9 px.
- RGB seam: SHARPSOURCE1C/RBANCHOR1A unchanged and explicitly labelled as frozen MHC R-G/B-G colour-difference proxy, not bit-exact Leica packed R/B closure.
- Photon sharpness slider integration is deferred until the renderer/lens pipelines are stable; the underlying five Leica UI mode table remains preserved for later mapping.
