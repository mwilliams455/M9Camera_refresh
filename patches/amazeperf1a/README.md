# M9AMAZEPERF1A — exact parallel AMaZE peripheral stages

Parent: **1.88 / M9PREPPERF1A PARALLEL8 + M9NOISEPERF1A PARALLEL8**.

The 1.88 phone capture reduced total rendering to about **4.55 s**, with the
native reconstruction block still taking about **2.26 s**. Before changing the
AMaZE algorithm itself, this pass removes serial work around it and exposes the
internal timing split.

## Frozen AMaZE

The librtprocess AMaZE implementation, tile size, worker count and dynamic
`chunkSize=2` scheduling are unchanged.

The selected quarter-strength Camera2-profile RAW noise proposal is also
unchanged.

## Parallelized peripheral work

Four independent per-pixel stages now use the existing 8-worker budget:

- Camera2 noise-variance / censor-mask transport;
- quarter-blend and exact changed/max/censored statistics;
- normalized Bayer-to-float AMaZE input preparation;
- final AMaZE float RGB to uint16 camera-RGB quantization.

The original scalar `trial_variance` and `trial_reconstruct` entry points are
retained unchanged in the native library as parity oracles. Production JNI uses
new performance entry points.

## Diagnostics

The PRIMARY `colourTrial1C` block adds:

- `amazeRawCopyMs`
- `amazeVarianceMs`
- `amazePhaseNoiseMs`
- `amazeQuarterBlendMs`
- `amazeFloatInputMs`
- `amazeCoreMs`
- `amazeOutputQuantizeMs`
- `amazeBorderMs`
- `amazePerfWorkers`

This lets the phone tell us whether AMaZE itself or its surrounding preparation
still dominates.

## Quality gate

Host tests require exact equality between the frozen 1.88 scalar/peripheral
functions and the optimized functions for:

- Camera2 variance values;
- censor masks;
- all four Bayer CFA patterns;
- final 16-bit RGB output;
- raw-noise changed/max/censored statistics.

No photographic parameter is changed.

Version: **1.89-m9amazeperf1a-parallelperiphery-prepperf1a-tg1**.
