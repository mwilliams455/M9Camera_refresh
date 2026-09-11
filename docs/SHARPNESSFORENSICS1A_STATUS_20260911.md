# M9 SHARPNESSFORENSICS1A — status 2026-09-11

Research branch: `research/sharpnessforensics1a`  
Frozen production base: `fb1db92ef78df70442b9fee879795e584f2170cf`

## Scope

Recover Leica M9 JPEG sharpness/noise behavior from firmware before changing the frozen renderer. No generic sharpening substitute is permitted. The DNG path remains outside the JPEG sharpness control.

## Firmware-derived correction — M9 Sharpening menu now proven

The earlier handoff described the M9 Sharpness positions as:

```text
Low
Medium low
Standard
Medium high
High
```

That was not firmware-correct for the Sharpening control itself.

A canonical M9 1.216 BF547 trace now identifies the actual 32-byte controller descriptor:

```text
label         = "Sharpening"
descriptor    = BF547 file 0xC2A54 / runtime 0xE2A54
control ID    = 0x1005
type          = 6
options ptr   = 0xE5E10
```

Following `0xE5E10` directly decodes five 20-byte Leica menu records:

```text
enum 0 -> Off
enum 1 -> Low
enum 2 -> Standard
enum 3 -> Medium high
enum 4 -> High
```

Exact record starts:

```text
0xC5E10  Off          0
0xC5E24  Low          1
0xC5E38  Standard     2
0xC5E4C  Medium high  3
0xC5E60  High         4
```

Therefore:

```text
M9 Sharpening Standard = enum 2
```

is now **PROVEN from the M9 firmware itself**.

The similarly shaped five-state table at runtime `0xE60D8` belongs to the separate controller descriptor:

```text
label       = "Contrast"
control ID  = 0x1006
options ptr = 0xE60D8
```

and that Contrast table is:

```text
Low          0
Medium low   1
Standard     2
Medium high  3
High         4
```

This explains the old ambiguity: `Medium low` is present in the Contrast table, but not in the canonical M9 Sharpening table.

## Canonical firmware reconstruction now reproducible in CI

The historical decrypted assets no longer need to be manually re-uploaded.

Public M9 1.216 and M Monochrom 1.022 ciphertexts use the same 1021-byte repeating XOR stream and contain a byte-identical BODY at different offsets. Their BODY offset difference modulo 1021 is 69, with:

```text
gcd(69, 1021) = 1
```

so the pair determines the full XOR stream up to one byte. Requiring the decrypted M9 header to be `PWAD` resolves the remaining byte uniquely.

`tools/recover_m9_key_from_shared_body.py` reproduces the historical key and is guarded by the preserved hashes:

```text
M9 raw SHA256       c3d30d7124abe6a3674cf2095719c178454b8773b1454cb70cf54ae468024da4
MM raw SHA256       53330385edfbfb9beeffa06645bffa2789e27dda614869107698919464f80ad8
key SHA256          595c49ebabdaafcde7cc6cbd6aa7a37092d7c2ad4ca47d0d8bc57a04a5bed3a1
M9 decrypted SHA256 4f962bb7799ad9a6745ab36c2a3ba59757bfcbd205f50472ddf1b904a5756d20
BF547 SHA256        f044097bc9ce0deba129f593321aeb20d30c5c2e7b8c3074e44717e7765c66bd
```

The canonical reconstruction and Gate-B controller traces have run successfully in GitHub Actions. Firmware/key bytes are deleted from the runner; only derived JSON/text evidence is retained.

## Proven / carried forward

- M9 Sharpening is a real five-state JPEG property.
- Exact M9 Sharpening menu is `Off=0, Low=1, Standard=2, Medium high=3, High=4`.
- Sharpening controller ID is `0x1005` and its selector table is runtime `0xE5E10`.
- Contrast is a separate control ID `0x1006` with `Low=0, Medium low=1, Standard=2, Medium high=3, High=4`.
- BF561 contains `Process_Sharpness`, `Process_Noise`, and `Process_DNGNoise` in the M9 imaging architecture.
- BF561 `Run` is a dispatcher; its case order is not photographic execution order.
- The runtime processing list is built from approximately 68-byte process-setting records.
- `g_CurrentProcessingSetting` is 68 bytes.
- `g_ProcessingList` is 956 bytes, consistent with `4 + 14*68`.
- In M9 record tracing, byte `+10` is `nContrast` and byte `+14` is `nColorSpace`.
- A controller-side stage-name family includes `Sharp` alongside Shading, WhiteBalance, Noise, interpolation, ColorMatrix and ConvertYCrCb.
- An unresolved M9 ISO-related region contains 13 x 4100-byte blocks. Its consumer is not yet proven.

## Cross-generation record evidence

The original M Monochrom 1.022 firmware uses the same M-generation process-setting architecture closely enough to provide a structural cross-check without transferring photographic constants blindly.

Its `SetStructParameter`/diagnostic trace gives:

```text
record +9  = nIso
record +10 = nContrast
record +11 = nSaturation
record +12 = nNoise
record +14 = nColorSpace
```

Therefore byte `+13` remains the leading candidate for the missing sharpness property field.

Important distinction:

```text
Sharpening Standard = 2       PROVEN on M9
record +13 = nSharpness       NOT YET PROVEN on M9
```

The Monochrom `PROCESS/LUTS` also contains an ISO-aligned paired region:

```text
16 ISO slots x 2 x 2050 bytes
= 16 x 4100 bytes
```

and retains `LoadISODataL1`, `CalculateNoiseParameter`, `Process_Noise`, and `Process_Sharpness`.

This materially strengthens the interpretation of the M9 4100-byte-per-ISO-like region as a paired ISO-dependent spatial/noise/sharpness resource family. It still does NOT prove that either half is a sharpening table.

## Evidence levels

### Proven

- M9 Sharpening menu identity and exact enum mapping.
- M9 Sharpening `Standard = 2`.
- M9 Sharpening controller ID `0x1005`.
- `Process_Sharpness` exists in the M9 BF561 imaging path.
- `Run` ordering cannot be used as pipeline ordering.
- M9 `+10=nContrast`, `+14=nColorSpace`.
- Homologous M-generation record fields place `nNoise` at `+12`.
- Homologous firmware uses paired 2050-byte ISO-dependent structures.

### Strongly bounded, not proven

```text
record +13 = nSharpness
```

Reason: it is the single missing byte between homologous `nNoise` at +12 and M9/homologous `nColorSpace` at +14 in the generic Leica JPEG-property record. The remaining task is to trace the proven M9 Sharpening selector state into the process record / BF561 consumer.

### Open

- Exact M9 process-record field receiving Sharpening enum (`+13` is the leading candidate).
- Sharp job ID and real process-list insertion point.
- `Process_Sharpness` input domain, kernel/neighborhood, threshold/coring, gain, fixed-point arithmetic, rounding, clipping and borders.
- Exact consumer of the M9 13 x 4100-byte bank.
- Ordering/interaction of Noise and Sharp.
- Whether `Process_DNGNoise` participates in JPEG formation or only DNG-specific handling.

## Current tooling

- `tools/m9_sharpnessforensics1a.py` — extracted BF561/BF547 evidence pass.
- `tools/m9_sharpnessforensics1a_firmwarepass.py` — firmware-direct PWAD / overlay-aware pass.
- `tools/m9_sharpness_gateb_probe.py` — strict canonical BF547 five-state table/xref probe.
- `tools/m9_sharpness_gateb_context.py` — controller descriptor/context decode.
- `tools/m9_sharpness_gateb_follow_menu.py` — follows the M9 Sharpening descriptor to its own options table.
- `tools/recover_m9_key_from_shared_body.py` — reproducible canonical firmware reconstruction.
- `.github/workflows/m9-sharpness-gateb-forensics.yml` — canonical Gate-B evidence workflow.
- `.github/workflows/m9-sharpness-blackfin-forensics.yml` — direct Blackfin disassembly/reconstruction workflow under active development.

## Next decisive work

Close the remaining gates in this order:

1. Trace M9 Sharpening enum from control `0x1005` into the 68-byte processing record and prove or reject `+13=nSharpness`.
2. Recover Sharp job ID and real BF547 ordered-list placement.
3. Disassemble/reconstruct BF561 `Process_Sharpness` arithmetic.
4. Trace `LoadISODataL1` / `CalculateNoiseParameter` / `Process_Noise` to identify the 4100-byte bank consumer and Sharp/Noise interaction.
5. Only after placement and arithmetic are sufficiently closed, implement offline `SHARPNESSSTD1A` same-RAW A/B with Standard enum 2.

## Freeze rule

Do not modify the production renderer or APK during the above gates. `SHARPNESSSTD1A` remains offline-only until placement, firmware-derived arithmetic, and the noise/ISO relationship are sufficiently proven.
