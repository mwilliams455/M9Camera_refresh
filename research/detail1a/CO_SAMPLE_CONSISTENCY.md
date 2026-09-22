# Co shrink and measured-sample consistency — no-Sharp research

This is the follow-up to the corrected MHC factorial. Each of the eight guide/interpolation/output-green combinations is tested with Co shrink on and off. The existing Co uncertainty signal is fixed. Sharp and Noise2 are absent in all 16 cells. Internal MHC RGB is a separate control.

The 12 random four-CFA/neutral-ratio control cases passed: all eight Co-on cells reproduce the prior experiment byte for byte; direct interpolation obeys the independent measured-anchor equation; matching guide/output with Co off retains measured R/B to at most one camera Q14 unit. The MHC/direct/no-Co control also retains measured green exactly.

The same 1,536 synthetic scenes completed. Every Co-on metric agrees with the prior full report. No alternative passes the zero-false-chroma-regression gate relative to D/cross/Leica-output/Co-on.

Co demonstrably changes measured R/B values. In this synthetic corpus, MHC-guide/direct/MHC-output with Co on alters 805,639 measured red and 860,326 measured blue samples by more than one Q14 unit. With Co off, every measured CFA sample in that control is exact in Q14 for the suite's fixed neutral values. The direct D/Leica-output control preserves measured R/B with Co off but continues to alter measured green through its chosen output-green plane. Cross-phase interpolation changes measured R/B even with Co off.

The Co-off-minus-on comparisons below hold guide, interpolation and final green fixed. Counts show how many cases worsen relative to the same architecture with Co on, not relative to D.

| Architecture | Mean RGB RMS change | False-magenta regressions | False-green regressions |
|---|---:|---:|---:|
| gD_iCross_oLeica | -0.0013659 | 158 | 350 |
| gD_iDirect_oLeica | -0.0012112 | 168 | 456 |
| gD_iCross_oMHC | -0.0018389 | 160 | 343 |
| gD_iDirect_oMHC | -0.0015907 | 168 | 426 |
| gM_iCross_oLeica | +0.0012722 | 230 | 104 |
| gM_iDirect_oLeica | +0.0010593 | 295 | 140 |
| gM_iCross_oMHC | +0.0002899 | 228 | 88 |
| gM_iDirect_oMHC | -0.0008445 | 306 | 140 |

Measurement preservation is not sufficient for colour accuracy. Among the 128 *unclipped* scenes, the MHC/direct/Co-off control still has false colour while retaining the measured values. Of its false-green pixels, 96.52% are at R/B sites where green is interpolated. Of its false-magenta pixels, 46.48% are at green sites where green is measured and R/B must be interpolated. These are location statistics, not proof that a single channel causes every error.

The next architectural investigation should compare coherent edge-aware green and R/B reconstruction while retaining measured samples. Do not treat Co off as a production fix, re-enable Sharp, or infer that preserving R-B alone preserves real colour. No app or colour/tone policy is changed here.

Run after assembling frozen GL2G:

```bash
python research/detail1a/co_sample_probe.py --assembled /path/to/PhotonCamera --prior-report /path/to/true_mhc_factorial/report.json --out /path/to/co_results
```

The prior report is the full 1,536-case output of `true_mhc_factorial.py`; it is required to enforce repeated-control metric parity. The committed summary omits the large per-case arrays. Its phase summary uses the published per-case `phase_errors`, weighting R/G/B sites by 1/4, 1/2, 1/4. Full per-case evidence is retained separately.

Limitations: noiseless synthetic data with four subjects and the prior fixed neutral values; results are white-balanced linear camera RGB, not sRGB. Measurement audits use camera Q14, not RGB16 byte identity. Native source is frozen and hash checked. This synthetic-only publication contains no new photographic results or images.
