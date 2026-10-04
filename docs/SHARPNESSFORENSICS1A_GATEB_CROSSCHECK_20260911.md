# M9 SHARPNESSFORENSICS1A — Gate B cross-check

Date: 2026-09-11  
Research branch: `research/sharpnessforensics1a`  
Production renderer: **frozen / unchanged**

## Objective

Close the Leica M9 JPEG Sharpness menu-state encoding without transferring a generic sharpening model or promoting a cross-generation analogy to M9-specific fact.

The target question is:

```text
Low          -> ?
Medium low   -> ?
Standard     -> ?
Medium high  -> ?
High         -> ?
```

and, separately:

```text
which byte/selector in the 68-byte M9 process record carries that state?
```

## Canonical M9 1.216 forensic inputs

The preserved 2026-08-27 checkpoint records these canonical assets:

```text
BF547.bin
SHA256 f044097bc9ce0deba129f593321aeb20d30c5c2e7b8c3074e44717e7765c66bd

BF561/bf0.bin
SHA256 61334b081aade232d5900bc43b95b35611502825344f3b30d20713bcb50c8dcb

BF561/bf0.map
SHA256 1efdcd44e8a0739494d9bd1923767b12f04dae5c0b60cb4b02e940aaa28777de
```

The canonical decrypted M9 1.216 updater hash carried by the project is:

```text
4f962bb7799ad9a6745ab36c2a3ba59757bfcbd205f50472ddf1b904a5756d20
```

`tools/m9_sharpness_gateb_probe.py` enforces the canonical BF547/updater hashes by default.

## M9 evidence already proven

The M9 reverse-engineering already establishes:

- `Process_Sharpness` exists in the BF561 imaging architecture.
- `Process_Noise` and `Process_DNGNoise` exist alongside it.
- controller-side stage names include `Sharp` and `Noise`.
- the runtime processing list is composed of approximately 68-byte records.
- `g_CurrentProcessingSetting` is 68 bytes.
- `g_ProcessingList` is 956 bytes, consistent with `4 + 14 * 68`.
- M9 record byte `+10` is `nContrast`.
- M9 record byte `+14` is `nColorSpace`.
- BF561 `Run` is a dispatcher, not proof of photographic execution order.

These facts do not by themselves identify the Sharpness property byte or enum.

## Homologous M-generation evidence

The original M Monochrom 1.022 firmware is a particularly strong structural cross-check because its complete `bf0.map` is an exact byte substring of the M9 `bf0.map`, and it retains the shared spatial-processing architecture including `Process_Sharpness`, `Process_Noise`, `Process_Shading`, `SetStructParameter`, LUT loading, and ISO-dependent resources.

Its process-record trace closes these neighboring fields:

```text
record +9  = nIso
record +10 = nContrast
record +11 = nSaturation
record +12 = nNoise
record +14 = nColorSpace
```

Therefore, in the shared generic Leica record layout, `+13` is the single unresolved byte between `nNoise` and `nColorSpace` and remains the leading candidate for the Sharpness property.

This is strong structural evidence, not M9-specific consumer proof.

## Real Leica BF547 five-state record format

The Monochrom controller trace also proves the actual M-generation menu-record encoding rather than inferring it from UI order.

For the five-state Contrast control, BF547 contains five records at 20-byte stride:

```text
0 -> Low
1 -> Medium low
2 -> Standard
3 -> Medium high
4 -> High
```

The record format begins:

```text
+0x00  u32 pointer to NUL-terminated menu label
+0x04  u32 enum value
+0x08  ... remaining record fields ...
```

For this static BF547 image family, the string pointer is resolved with:

```text
RAM address = BF547 file offset + 0x20000
```

The exact labels include Leica's trailing spaces where present:

```text
"Low "
"Medium low "
"Standard"
"Medium high "
"High "
```

This proves a real Leica M-generation five-state convention with `Standard = 2` for a homologous JPEG property control.

It does **not** by itself prove that the M9 Sharpness property uses the same enum table.

## Evidence matrix

| Claim | Status | Basis |
|---|---|---|
| M9 has five Sharpness positions | Proven | M9 menu/UI behavior and project firmware investigation |
| M9 has `Process_Sharpness` | Proven | BF561 symbol/function trace |
| Leica M-generation five-state menu record uses 20-byte stride | Proven structurally | Monochrom BF547 controller trace |
| Leica M-generation Low..High can encode `0,1,2,3,4` | Proven structurally | Monochrom BF547 Contrast table |
| Leica M-generation Standard can be enum `2` | Proven structurally | Monochrom BF547 Contrast table |
| Shared record has `nNoise` at `+12` | Proven in homologous M-generation implementation | Monochrom `SetStructParameter` / field trace |
| M9 `+13 = nSharpness` | **Very strongly bounded, not proven** | sole gap between homologous `+12=nNoise` and M9/homologous `+14=nColorSpace` |
| M9 Sharpness Standard = `2` | **Very strongly bounded, not proven** | identical five-state Leica UI convention, but M9 property table xref still missing |
| exact M9 Sharpness five-state table offset | Open | requires canonical BF547 scan/xref |
| Sharp job ID | Open | requires stage builder / dispatcher-record correlation |
| Sharp placement in JPEG list | Open | requires BF547 runtime list builder |
| `Process_Sharpness` arithmetic | Open | requires BF561 disassembly/reconstruction |

## Gate-B closure rule

Do not mark Gate B closed merely because the canonical M9 BF547 contains one or more Low→High `0..4` tables.

Gate B closes only when M9-specific evidence ties the Sharpness property to the candidate table/selector. Acceptable closure evidence includes one of the following, preferably more than one:

1. a BF547 Sharpness property handler references the five-state table directly;
2. an M9 diagnostic/property field identified as Sharpness is copied into record byte `+13` and that state reaches the Sharp process record;
3. a switch/table xref maps the Sharp controller stage/property to the same five enum values;
4. the Sharp record builder copies the resolved menu state into the exact parameter consumed by the BF561 Sharp path.

Proximity alone is a clue, not proof.

## New targeted verifier

`tools/m9_sharpness_gateb_probe.py` now performs the decisive controller-side scan.

It:

- accepts either canonical `BF547.bin` or the decrypted updater;
- verifies canonical M9 hashes by default;
- uses the proven `+0x20000` static-RAM mapping first and exclusively for this record family;
- searches exact 20-byte Low→High `0..4` records including trailing spaces;
- reports every candidate table and all direct pointers to its table address;
- scans `Sharp`, `nSharp`, `nSharpness`, `Noise`, `nNoise`, and neighboring process-field names and their pointer xrefs;
- reports nearest Sharp-related/table xref relationships only as clues;
- always leaves Gate B `OPEN` until a semantic M9-specific xref is manually/forensically closed.

Example:

```bash
python tools/m9_sharpness_gateb_probe.py \
  --firmware /path/to/m9-1_216.decrypted.upd \
  --out SHARPNESSFORENSICS1A_GATEB
```

or:

```bash
python tools/m9_sharpness_gateb_probe.py \
  --bf547 /path/to/BF547.bin \
  --out SHARPNESSFORENSICS1A_GATEB
```

## Immediate next action after the canonical run

1. enumerate all exact M9 Low→High `0..4` BF547 tables;
2. inspect their direct table-address xrefs;
3. correlate those xrefs with `Sharp` / property-field consumers;
4. identify the exact M9 table and prove or reject `Standard = 2` for Sharpness;
5. trace the same property into the 68-byte Sharp process record to prove or reject `+13 = nSharpness`;
6. then move to Gate A job ID/list placement and Gate C arithmetic.

Until steps 3–5 close, **do not implement `SHARPNESSSTD1A` and do not modify the production renderer.**
