# M9Cam 2.96 — dynamic phase-noise tile assignment

The accepted 2.95 phone capture spent 720 ms in the RAW noise filter, inside a
3,670 ms render. Existing 64×512 outer tiles have different costs, especially
near clipped regions. Static worker assignment can leave workers idle.

This candidate changes only that filter's OpenMP loop from `schedule(static)`
to `schedule(dynamic,1)`. Each worker still owns its scratch buffers and writes
disjoint output tiles. The 64×128 dirty subtiles, arithmetic/accumulation order,
noise strength, quarter blend, AMaZE and worker limit are unchanged. The
previously rejected persistent colour-frame scheduler remains disabled.

The other source changes are version 27296 / 2.96-phasenoiseperf1d and diagnostic
labels `M9PHASENOISEPERF1D_DYNAMIC_EXACT` / `dynamic_tiles_chunk1`. Exactly three
scoped source files change; 1,376 are unchanged. Reversing the patch restores
the accepted parent exactly.

## Evidence and limits

- Actual parent/candidate JNI builds: 96 RAW cases, 10,967,408 samples, exact
  against each other and the scalar oracle; 16 complete reconstruction cases
  cover all four CFA layouts and workers 1, 2, 4 and 8 with exact RGB/statistics.
- The inherited scalar, outer/inner seam and 12 MP clustered-highlight checks
  also pass against the candidate.
- Seven alternating 12 MP host benchmark pairs per pattern show median
  filter reductions of 15.7% (smooth/noisy), 11.4% (fine detail), and 10.6%
  (clustered censoring). These are x86 host measurements, not phone speed claims.
- CI must rebuild the unchanged Android parent and compare its executable and
  constant-data sections with the accepted 2.95 `libm9color.so` for both ABIs.
  A mismatch blocks delivery until investigated. The candidate then rebuilds
  in the same source location.
- Packaging changes only the two `libm9color.so` libraries. The other 25 native
  libraries and all 285 assets must match the accepted 2.95 installer. Signature,
  version, compiled UI and 16 KiB alignment checks remain required.
- The current-build workflow runs the existing Android regressions and CodeQL.

No private photographs or photo-derived pixel data are committed. The earlier
exp(0) shortcut was rejected for small/inconsistent gains and is not included.

## Phone gate

After CI and package verification, install the candidate over 2.95. Use normal
M9 photos with unchanged settings; retain a JPEG and matching PRIMARY report.
Check the noise-filter time and overall render time, saving and visual quality.
Keep this PR unmerged until the phone confirms useful performance without a
quality regression. Scene/ISO differences make isolated timings directional;
do not claim an exact speedup from unmatched captures.
