# M9 SHARPNESSFORENSICS1A — ISO-indexed Sharp LUT pass 2

Date: 2026-09-11
Research branch: `research/sharpnessforensics1a`
Frozen production base: `fb1db92ef78df70442b9fee879795e584f2170cf`

## Scope

Record the canonical M9 1.216 firmware evidence that links the Sharpness preparation path to the firmware ISO slot and decodes the seven internal LUT modification modes. No production renderer/APK change is authorized by this note.

## Evidence source

Canonical GNU Blackfin workflow run: `34642959042`
Artifact: `M9-SHARPNESS-GNU-BLACKFIN-FORENSICS`
Artifact ID: `10280842980`

The run completed firmware reconstruction, coherent BF561 overlay extraction, deep helper extraction, reverse callgraph generation, GNU Blackfin disassembly, BF547 controller windows, and artifact publication successfully.

## 1. M9 ISO slot is written to processing structure +0x78

The clean M9 `SetStructParameter` implementation at `0xfeb167e0` reads source byte `+9` and writes the derived ISO slot to destination `+0x78`.

The mapping includes a special case for source value 1 and otherwise normalizes low enum values before subtracting 4. This is consistent with the existing M-generation evidence that source byte `+9` is the ISO selector and with the M9 physical ISO table having 13 slots.

The exact camera-enum-to-physical-ISO mapping remains separately documented; the important result here is:

```text
processing_structure + 0x78 = firmware ISO LUT slot
```

## 2. Run passes that exact ISO slot to LoadAndModifySharpnessData

The clean M9 `Run` implementation does:

```text
R0 = processing_structure + 0x658
R1 = [processing_structure + 0x78]
CALL LoadAndModifySharpnessData
```

Therefore `LoadAndModifySharpnessData` receives:

```text
R0 = Sharp-data descriptor/work structure
R1 = M9 ISO LUT slot
```

This link is direct M9 firmware evidence.

## 3. LoadAndModifySharpnessData selects one signed-16-bit LUT row by ISO

For the clean helper at `0xfeb11f10`:

```text
count = [sharp + 0x18]
source_bank = [sharp + 0x0C]
working_lut = [sharp + 0x10]
```

Before modifying the LUT it computes the source address from the incoming ISO slot:

```text
source = source_bank + 2 * count * iso_slot
bytes  = 2 * count
DMAmemcpy(working_lut, source, bytes)
```

Thus the M9 Sharp working LUT is selected from an **ISO-indexed bank of signed 16-bit rows**.

This is now PROVEN.

## 4. Seven internal LUT-strength modification modes

After copying the ISO-selected row, the helper reads a mode at `sharp + 0x00`. Valid modes are 1..7. Every path applies a transform to each signed 16-bit LUT value and bounds the result to:

```text
-2048 <= value <= +2048
```

Canonical arithmetic observed:

```text
mode 1: value >>> 2                  ~ x0.25
mode 2: value >>> 1                  ~ x0.5
mode 3: no scale, clamp only          x1.0
mode 4: arithmetic shift by +1       ~ x2.0
mode 5: arithmetic shift by +2       ~ x4.0
mode 6: (value >>> 1) * 3            ~ x1.5
mode 7: value * 3                     x3.0
```

Signed fixed-point / saturation details must be reproduced exactly before a bit-faithful renderer implementation; the approximate multipliers above describe the mathematical intent of the decoded operations.

## 5. Important architectural implication

The M9 Sharpness path is now structurally:

```text
firmware ISO enum
  -> ISO LUT slot
  -> select one signed-16-bit Sharp LUT row
  -> apply one of seven bounded internal strength transforms
  -> Process_Sharpness
  -> ASMUMGauss3LUT Gaussian/residual/LUT kernel
```

This is substantially more specific than a generic unsharp-mask model.

The five-position user menu and seven internal modes must NOT be assumed to map 1:1. The proven UI is:

```text
Off=0
Low=1
Standard=2
Medium high=3
High=4
```

`Off` may disable the Sharp process entirely, while the four non-off positions may select a subset of the seven internal strength modes. That mapping remains to be proven from the `Set` / controller-builder path.

## 6. Relationship to the unresolved 13 x 4100-byte M9 bank

Existing LUTS forensics established an unresolved contiguous region of:

```text
13 x 4100 bytes
= 13 x 2050 signed int16 values
= 53,300 bytes
```

`LoadAndModifySharpnessData` now proves the Sharp source bank is indexed as:

```text
row_bytes = 2 * count
row        = iso_slot
```

Therefore, if the Sharp descriptor proves:

```text
count = 2050
```

the unresolved 13 x 4100-byte region becomes an exact dimensional match for the Sharp ISO bank.

That final `count=2050` link is NOT yet promoted in this note; it is the next proof target.

## 7. Reverse callgraph result for LoadISODataL1

The canonical reverse-callgraph artifact identifies mapped `Set` as the direct caller of the clean `LoadISODataL1` implementations:

```text
Set 0xfeb16904 -> LoadISODataL1 0xfeb16f10
Set 0xfeb1d1bc -> LoadISODataL1 0xfeb1d7c8
```

Neither clean `Process_Sharpness` nor clean `LoadAndModifySharpnessData` directly calls `LoadISODataL1`.

This indicates ISO data are prepared earlier by `Set`, while `Run` later uses the prepared ISO slot at `+0x78` to select the Sharp LUT row.

## 8. Next decisive work

1. Disassemble mapped `Set` and determine the Sharp descriptor initialization, especially `sharp+0x18` LUT count and `sharp+0x00` modification mode.
2. Prove whether Sharp LUT `count = 2050`, closing or rejecting the 13x4100 bank identity.
3. Trace the proven Sharpening UI control `0x1005` to the internal seven-mode selector and determine the Standard=2 internal mode.
4. Continue exact `ASMUMGauss3LUT` arithmetic/border reconstruction.
5. Only then build offline `SHARPNESSSTD1A` same-RAW A/B.

## Freeze rule

Production remains frozen. No generic sharpening filter and no speculative Standard implementation are allowed.
