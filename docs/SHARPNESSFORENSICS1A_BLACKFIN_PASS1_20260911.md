# M9 SHARPNESSFORENSICS1A — canonical Blackfin pass 1

Date: 2026-09-11
Research branch: `research/sharpnessforensics1a`
Frozen production base: `fb1db92ef78df70442b9fee879795e584f2170cf`

## Scope

Record the first conclusions supported directly by the successful canonical M9 1.216 GNU Blackfin disassembly artifact. No production renderer/APK changes are authorized by this note.

## Evidence source

Successful workflow run: `34641244526`
Artifact: `M9-SHARPNESS-GNU-BLACKFIN-FORENSICS`
Artifact ID: `10280360830`

The run reconstructs the canonical decrypted M9, verifies the preserved hashes, extracts a coherent BF561 overlay, and disassembles mapped functions with GNU Blackfin binutils.

## 1. Sharp routing in BF561 Run

In both clean mirrored `Run` implementations, the processing mask is loaded into `R7`. The routing logic contains:

```text
BITTST(R7, 6) -> Process_Noise block
BITTST(R7, 7) -> Process_Sharpness block
```

The bit-7 branch lands at the block that directly calls mapped `Process_Sharpness`:

```text
0xffa10c28 -> CALL 0xffa03d90 Process_Sharpness
0xff610908 -> CALL 0xff610dc0 Process_Sharpness
```

Therefore:

```text
M9 BF561 Sharp process-mask bit = 7    PROVEN
M9 BF561 Noise process-mask bit = 6    PROVEN
```

This is a process-enable/routing bit. It is not yet the BF547 ordered-list insertion index, and the post-call return value must not be relabeled as a job ID.

## 2. Process_Sharpness is a wrapper around ASMUMGauss3LUT

The clean mapped `Process_Sharpness` implementations are:

```text
0xffa03d90 size 112
0xff610dc0 size 112
```

Each directly calls a mapped lower-level function:

```text
0xffa03dea -> 0xffa018b0 ASMUMGauss3LUT
0xff610e1a -> 0xff601af0 ASMUMGauss3LUT
```

The wrapper:

- obtains a signed 16-bit value from a table pointer;
- derives a signed table index from a structure field using halving/rounding arithmetic;
- requires a count/mode-like field to be in the inclusive range 1..7;
- derives a pointer into a signed 16-bit table;
- passes bounds/table state into `ASMUMGauss3LUT`;
- advances a caller-owned state/pointer by 2 after the kernel call.

Exact semantic names for those fields are still open.

## 3. ASMUMGauss3LUT architecture

The canonical M9 body at `0xffa018b0` is consistent with its mapped name and establishes a firmware-specific Gaussian/residual/LUT sharpness architecture.

Observed operations include:

1. construction of line/stride state for 16-bit image data;
2. two Gaussian-style filtering passes using packed fixed-point arithmetic;
3. calculation of a packed residual between source data and the filtered result;
4. residual limiting with packed MIN/MAX bounds;
5. conversion of each signed residual component into an index into a signed 16-bit LUT;
6. loading a correction value from that LUT;
7. adding the correction back to the original source sample;
8. final output limiting with packed MIN/MAX;
9. signed 16-bit output writes.

This proves the M9 JPEG sharpness path is not accurately represented by a generic Android-style `amount/radius/threshold` unsharp mask. Fidelity requires reproducing the firmware Gaussian/residual/LUT behavior and the correct LUT preparation.

## 4. Run calls LoadAndModifySharpnessData before image processing

The clean `Run` overlay directly calls mapped:

```text
0xffa10fac -> 0xfeb11f10 LoadAndModifySharpnessDa...
0xff610c8c -> 0xfeb18d48 LoadAndModifySharpnessDa...
```

This is now the highest-value parameter-preparation target because `Process_Sharpness` consumes LUT/bound state rather than a simple scalar sharpness amount.

A deeper GNU forensic pass has been added to extract and disassemble `ASMUMGauss3LUT` and `LoadAndModifySharpnessDa...` explicitly.

## 5. M9 LoadISODataL1 differs from M Monochrom

The two clean M9 `LoadISODataL1` implementations show:

```text
P5 = [P1++]          # ISO-slot-like index; P1 advances by 4
P0 = P1 + 0x64
P0 = P0 + (P5 << 2)
R0 = [P0]
```

Relative to the original descriptor base, the per-ISO entry lookup therefore begins at approximately:

```text
descriptor + 0x68 + 4*slot
```

The independently decoded M Monochrom 1.022 helper uses:

```text
descriptor + 0x5C + 4*slot
```

Therefore the M9 helper is not byte-identical to the Monochrom helper and its descriptor layout is evolved/different. Cross-generation symbol-map identity does not license transfer of helper offsets or photographic constants.

## 6. SetStructParameter changes the +13 hypothesis

In the two clean M9 `SetStructParameter` implementations, bytes `+13` and `+14` are read as an adjacent byte pair and combined into one 16-bit word:

```text
lo = B[src + 0x13]
hi = B[src + 0x14]
W[dst + 0x234] = lo | (hi << 8)
```

The same code similarly packs:

```text
+0x0F/+0x10 -> W[dst + 0x230]
+0x11/+0x12 -> W[dst + 0x232]
+0x13/+0x14 -> W[dst + 0x234]
```

`Run` reads all three destination words on entry, but in the clean `Run` disassembly the local copies of `0x230`, `0x232`, and `0x234` are not subsequently referenced.

Consequences:

- `+13 = nSharpness` remains **unproven**.
- The old cross-generation gap argument is no longer sufficient by itself.
- This specific BF561 setter treats +13/+14 as one 16-bit packed value, so the controller/list-builder trace must determine the true source-record semantics.
- This does not by itself disprove that one byte encodes sharpness in a different controller-side structure; it means the structures/traces must not be conflated.

## 7. Current evidence levels

### Proven

- M9 Sharpening menu: Off=0, Low=1, Standard=2, Medium high=3, High=4.
- Sharpening controller ID = `0x1005`.
- BF561 Sharp process-mask bit = `7`.
- BF561 Noise process-mask bit = `6`.
- Clean `Run` directly calls clean `Process_Sharpness`.
- Clean `Process_Sharpness` directly calls mapped `ASMUMGauss3LUT`.
- `ASMUMGauss3LUT` implements a Gaussian/residual/signed-LUT correction path with fixed-point limiting.
- `Run` calls `LoadAndModifySharpnessDa...` during preparation.
- M9 `LoadISODataL1` uses a descriptor layout different from M Monochrom.
- The clean M9 `SetStructParameter` packs source +13/+14 into one 16-bit destination word at +0x234.

### Still open

- Controller/list-builder destination of Sharpening control `0x1005` and whether it proves/rejects `+13=nSharpness` in the historical 68-byte process record.
- Exact BF547 ordered-list insertion position for Sharp.
- Exact semantics of every `Process_Sharpness` / `ASMUMGauss3LUT` argument.
- Exact `LoadAndModifySharpnessDa...` arithmetic and source tables.
- Exact consumer of the M9 13 x 4100-byte ISO bank.
- Whether and how ISO/noise state modifies the Sharp LUT.
- Border behavior and every rounding/clipping detail needed for a bit-faithful offline implementation.

## Freeze rule

Do not implement or promote `SHARPNESSSTD1A` yet. Production remains frozen. The next decisive evidence is the full `LoadAndModifySharpnessDa...` disassembly plus the controller/list-builder trace from `0x1005` into the 68-byte process record.
