# M9 SHARPNESSFORENSICS1A — status 2026-09-11

Research branch: `research/sharpnessforensics1a`
Frozen production base: `fb1db92ef78df70442b9fee879795e584f2170cf`

## Scope

Recover Leica M9 JPEG sharpness/noise behavior from firmware before changing the frozen renderer. No generic sharpening substitute is permitted. The DNG path remains outside the JPEG sharpness control.

## Proven / carried forward

- The M9 exposes five JPEG sharpness positions: Low, Medium low, Standard, Medium high, High.
- BF561 contains `Process_Sharpness`, `Process_Noise`, and `Process_DNGNoise` in the M9 imaging architecture.
- BF561 `Run` is a dispatcher; its case order is not photographic execution order.
- The runtime processing list is built from approximately 68-byte process-setting records.
- In M9 record tracing, byte `+10` is `nContrast` and byte `+14` is `nColorSpace`.
- A controller-side stage-name family includes `Sharp` alongside Shading, WhiteBalance, Noise, interpolation, ColorMatrix and ConvertYCrCb.
- An unresolved M9 ISO-related region contains 13 x 4100-byte blocks. Its consumer is not yet proven.

## New cross-generation evidence

The original M Monochrom 1.022 firmware uses the same M-generation process-setting architecture closely enough to provide a structural cross-check without transferring photographic constants blindly.

Its `SetStructParameter`/diagnostic trace gives:

```text
record +9  = nIso
record +10 = nContrast
record +11 = nSaturation
record +12 = nNoise
record +14 = nColorSpace
```

Therefore byte `+13` is now the leading candidate for the missing sharpness property field, but this is NOT promoted to a result until M9 BF547/BF561 consumer evidence identifies it.

The Monochrom `PROCESS/LUTS` also contains an exact ISO-aligned paired region:

```text
16 ISO slots x 2 x 2050 bytes
= 16 x 4100 bytes
```

and its firmware retains `LoadISODataL1`, `CalculateNoiseParameter`, `Process_Noise`, and `Process_Sharpness`.

This materially strengthens the interpretation of the M9 4100-byte-per-ISO-like region as a paired ISO-dependent spatial/noise/sharpness resource family. It still does NOT prove that either half is a sharpening table.

## Evidence levels

### Proven

- Sharpness is a real five-position JPEG property.
- `Process_Sharpness` exists in the M9 BF561 imaging path.
- `Run` ordering cannot be used as pipeline ordering.
- M9 `+10=nContrast`, `+14=nColorSpace`.
- Homologous M-generation record fields place `nNoise` at `+12`.
- Homologous firmware uses paired 2050-byte ISO-dependent structures.

### Strongly bounded, not proven

```text
record +13 = nSharpness
```

Reason: it is the single missing byte between proven/homologous `nNoise` at +12 and `nColorSpace` at +14 in the generic Leica JPEG-property record. Exact M9 field naming/consumer must still close it.

### Open

- Sharp job ID and real list insertion point.
- Exact Low/Medium low/Standard/Medium high/High enum table for M9 sharpness.
- Whether Standard is enum 2 in the Sharpness property specifically (likely by menu-family convention, but not yet promoted).
- `Process_Sharpness` input domain, kernel/neighborhood, threshold/coring, gain, fixed-point arithmetic, rounding, clipping and borders.
- Exact consumer of the M9 13 x 4100-byte bank.
- Ordering/interaction of Noise and Sharp.
- Whether `Process_DNGNoise` participates in JPEG formation or only DNG-specific handling.

## Research tooling

`tools/m9_sharpnessforensics1a.py` was added on the research branch.

It:

- extracts every mapped implementation of Sharp/Noise and neighboring imaging functions across BF561 map overlays;
- fingerprints function bytes and direct Blackfin CALL/JUMP.L links;
- scans BF547 for process-field/stage-name strings;
- finds five-record Leica `Low -> High` menu table candidates without falsely assigning their property identity;
- fingerprints an isolated 4100-byte bank and groups duplicate blocks;
- explicitly labels `+13=nSharpness` as hypothesis-only.

It embeds no Leica firmware bytes.

### Firmware-direct pass added

`tools/m9_sharpnessforensics1a_firmwarepass.py` now provides a second, firmware-direct pass.

It:

- accepts the decrypted M9 updater/container directly and recursively walks nested PWAD payloads;
- locates BF547 payloads without assuming a hard-coded file offset;
- identifies map candidates only when their fixed-width symbol records actually contain both `Process_Sharpness` and `Process_Noise`;
- identifies possible BF561 LDR payloads structurally, scores map/LDR pairs by whether the LDR really covers mapped imaging symbols, and keeps overlay candidates separate rather than flattening them;
- runs the existing function extractor only on plausible map/LDR pairs;
- scans BF547 for `Sharp`, `Noise`, the JPEG-property field-name family, and pointer xrefs under known M-generation RAM deltas;
- finds exact Low / Medium low / Standard / Medium high / High menu tables and reports their own pointer xrefs, while keeping their property identity explicitly UNASSIGNED;
- records literal breadcrumbs for the 68-byte record stride, 956-byte processing-list size and 14-record capacity;
- never promotes xref proximity alone to proof of `+13=nSharpness` or `Standard=2`.

The firmware-direct pass was syntax-checked before commit. It contains no Leica firmware bytes and modifies no renderer code.

## Historical-boundary check

A fresh search of the preserved M9 project material found no later hidden solution for the Sharp job ID or the BF547 ordered-list builder. The historical investigation genuinely stopped with:

```text
g_CurrentProcessingSetting = 68 bytes
g_ProcessingList           = 956 bytes = 4 + 14*68
```

plus the BF547 stage-name family containing `Noise`, `Sharp`, `ColorMatrix`, `ConvertYCrCb`, etc.

Therefore the job-ID / ordered-list problem remains a real open gate; no older result should be promoted by inference.

## Next decisive run

Preferred direct run against the decrypted M9 updater:

```bash
python tools/m9_sharpnessforensics1a_firmwarepass.py \
  /path/to/m9-1_216.decrypted.upd \
  --out SHARPNESSFORENSICS1A_FIRMWAREPASS
```

The original extractor remains available for already-separated assets:

```bash
python tools/m9_sharpnessforensics1a.py \
  --bf561-dir /path/to/extracted/BF561 \
  --bf547 /path/to/BF547 \
  --iso-bank /path/to/candidate_13x4100.bin \
  --out SHARPNESSFORENSICS1A_OUT
```

Then close in this order:

1. BF547 five-state menu table identity / xrefs -> prove Sharpness enum mapping and `+13`.
2. BF547 68-byte stage builder -> prove Sharp job ID and real process-list placement.
3. BF561 `Process_Sharpness` -> reconstruct arithmetic.
4. `LoadISODataL1` / `CalculateNoiseParameter` xrefs -> identify the 4100-byte bank consumer.
5. Only after those are sufficiently closed, implement offline `SHARPNESSSTD1A` same-RAW A/B.

## Freeze rule

Do not modify the production renderer or APK during the above gates. `SHARPNESSSTD1A` remains offline-only until placement, Standard mapping, and firmware-derived arithmetic are sufficiently proven.
