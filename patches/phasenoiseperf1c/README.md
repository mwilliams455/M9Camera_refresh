# M9 PHASENOISEPERF1C — ADAPTIVE128 EXACT

Parent: **1.92 M9PREPPERF1B PERSISTENT8 EXACT**.

Phone validation of PHASENOISEPERF1B showed strong clean-scene gains but
scene-dependent runtime. The 64x512 clean fast path falls back for an entire
outer tile when any clipped/invalid sample is present in that tile's required
halo. Localized bright windows/highlights can therefore force much more exact
fallback work than their pixel area implies.

PHASENOISEPERF1C keeps the proven 64x512 path unchanged for clean outer tiles.
Only an outer tile that cannot use the clean path is subdivided into 64x128
target regions. Each 128-wide region independently chooses the same exact clean
or fallback arithmetic.

Frozen:
- 24-candidate dy/dx accumulation order;
- nine-term py/px patch accumulation order;
- symmetric 12-direction weight identity;
- variance, censor, count>=7 and exp() arithmetic;
- llround() output;
- raw noise strength / quarter blend;
- AMaZE, PREPPERF1B, NOISECANCEL, exposure, TC20, SAT2, curve02 and TG1.

No private photograph or photo-derived pixel data is committed. Clustered
highlight tests are synthetic.

Hard gates:
- byte-exact versus scalar and PHASENOISEPERF1B;
- 1/2/4/8 workers;
- outer 512 and subtile 128 seam stress;
- 4096x3072 exact clustered-censor parity;
- end-to-end all-four-CFA reconstruction parity.

Version: **1.93-m9phasenoiseperf1c-adaptive128-prepperf1b-tg1**.
