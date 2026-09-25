# M9NOISEPERF1A — exact 8-way NOISECANCEL1B parallelization

Parent: **1.86 / M9NOISECANCEL1B DECOUPLED**.

Phone diagnostics measured NOISECANCEL1B at approximately **679 ms** on a
12 MP ISO-2923 capture, while the filter changed about 3.60 million R/B channel
samples. Its photographic behaviour is accepted for this performance pass.

## Optimization

The 1.86 filter is converted from one scalar row walk to up to **8 disjoint
row-band workers**.

The filter has a one-pixel vertical neighbourhood. To prevent worker B from ever
seeing worker A's already-filtered output, every band's cross-worker neighbour
rows are copied **before any worker is launched**. Each worker then keeps only
rolling row buffers for its own band.

This adds only bounded row-buffer memory; it does **not** make a full 12 MP RGB
copy.

## Frozen math

Unchanged from 1.86:

- Camera2 SENSOR_NOISE_PROFILE authority;
- R-G / B-G carrier;
- green channel exact;
- 0.65 confidence gate;
- 0.90 full-confidence point;
- 0.50 maximum median blend;
- cross-5 neighbourhood;
- edge/chroma-spread rejection;
- black/highlight bypass;
- filter location after AMaZE and before SOURCECAL2A.

The host regression compiles the exact frozen 1.86 scalar source and the new
parallel source and requires byte-for-byte RGB equality over multiple structured
random frames, including worker boundaries and clipped regions.

## Diagnostics

PRIMARY adds:

- `parallelWorkers`;
- `parallelMode=disjoint_row_bands_preloaded_boundaries`;
- `pixelMathRevision=NOISECANCEL1B_FROZEN_EXACT`;
- `parallelParityPolicy=byte_exact_RGB_output_vs_frozen_1_86_scalar`.

Version: **1.87-m9noiseperf1a-parallel8-noisecancel1b-tg1**.
