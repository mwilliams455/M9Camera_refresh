# Corrected no-Sharp MHC factorial — research only

The original W probe disabled the Sharp correction but retained SHARPSOURCE1C's replacement of output green. Its supposed MHC guide was consequently the same Leica-derived guide as D in the scored interior. A zero effect from that control cannot clear green guidance.

`true_mhc_factorial.py` bypasses the final green replacement in both frozen GL2G Bayer entry points. It checks full RGB parity against direct calls to the internal neutral-aware MHC functions, preservation of measured CFA samples, thread-count parity and constant-colour preservation. These controls passed all four CFA patterns. The frozen native source SHA-256 remains `23037daba9fe5acbffb68f4bdf1fdce394eb476d7312ef0b57d514678b95a1bc`.

The 2×2×2 experiment independently changes the difference guide (D/MHC), interpolation (cross-phase/direct same-phase) and final output green (Leica/MHC). Sharp is disabled throughout those eight cells. Co shrink and its original D uncertainty are fixed; Noise2 is absent. Genuine internal MHC RGB, the former W native control and D with Sharp are separate references. Synthetic data, scene clipping, rounding and metrics match W. All four repeated W controls match the published W metrics in every one of 1,536 cases.

Results:
- Genuine MHC guidance differs from D in all 1,536 cases.
- At fixed Leica output green, switching cross-phase to direct interpolation increases mean false-green excess by 0.01331037 with D guidance, versus 0.00070648 with MHC guidance. Guidance materially changes the interpolation tradeoff.
- MHC guide + direct interpolation + MHC output green lowers mean scene RGB RMS by 27.94% against D/no-Sharp, but worsens RGB RMS in 356 cases and false-magenta/false-green metrics in 278/621 cases.
- Genuine internal MHC RGB lowers mean scene RGB RMS by 26.47%, but also fails the strict colour gate.
- No alternative passes the zero-false-chroma-regression gate. No candidate is approved for production.

The claim that green is irrelevant is withdrawn. This is a guidance/interpolation/output-green interaction, with remaining reconstruction errors. Average synthetic improvement is insufficient to select an app candidate. Sharp remains disabled in the diagnostic candidates. No app or downstream colour changes.

Run after assembling the frozen GL2G source chain:

```bash
python research/detail1a/true_mhc_factorial.py --assembled /path/to/PhotonCamera --out /path/to/results
```

Optional `--w-report /path/to/W/report.json` additionally enforces exact parity with W's published controls. The committed summary was produced with that check enabled; the full per-case report is retained with the research evidence. `gD/gM` means D or genuine MHC difference guidance; `iCross/iDirect` specifies interpolation; `oLeica/oMHC` specifies final green.

These are noiseless synthetic, white-balanced linear camera RGB tests, with 16 pixels excluded at every edge. They are not sRGB or Android/JPEG parity tests. There are 1,408 clipped and 128 unclipped cases, reported separately. The strict gate is measured relative to D, not a claim that D itself is correct. The source and report here contain no new photographic results or images.
