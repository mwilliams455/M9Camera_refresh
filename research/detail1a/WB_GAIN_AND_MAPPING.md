# WB gain producer and coherent signal-domain replay

21 September 2026. **The controller's gain normalization is recovered. The
physical-white phone adaptation is rejected; no new APK or application change.**
This follows `CENSORED_CHROMA_AND_WB.md` and keeps its negative results intact.
Auto exposure remains unresolved and deferred.

## What is now established

Canonical BF547 is a raw image with runtime address = file offset + 0x20000,
SHA-256 `f044097bc9ce0deba129f593321aeb20d30c5c2e7b8c3074e44717e7765c66bd`.
The fresh extraction is from the same hash-verified M9 1.216 firmware as the
BF561 WB evidence. The new excerpts are in `evidence_wb_producer/`.

1. `0xa98d4` averages four measured triples and forms green-relative reciprocal
   R/B gains using integer division. It checks measurement ranges and writes
   status at packet+0x1d. This is the measured-WB branch, not the automatic
   estimator.
2. `0xab588` obtains R/B gains from the selected estimate/calibration inputs.
   At `0xab714` it bounds those preliminary gains above, and if either is below
   Q14 unity, multiplies all three by `floor(2^28 / min(Rgain, Bgain))` in Q14.
   Otherwise the multiplier and green gain are 0x4000. The resulting gains
   have a lower bound of 0x4000 before being narrowed to packet halfwords.
3. Dispatch at `0xaba68` selects the measured, preset, temperature or automatic
   path. The automatic path calls `0xab7bc`, which reaches `0xab588` at
   `0xaba2c`. The common tail at `0xabb36` snaps packet values **0x3fff and
   0x4001 to 0x4000**. This explains the BF561 routine's exact-unity contract.
4. In the capture setup, `0xb01fa` copies packet gains into capture-record
   fields +0xac/+0xb4/+0xbc, relative to the object at capture+0x360.
   `0x39f74` copies those fields back to the processing packet at
   capture+0x12c, offsets +0x0f/+0x11/+0x13, and hands it to `0x6d0a0`.
   The previously recovered BF561 `SetStructParameter` consumes those same
   three offsets into context+0x230/+0x232/+0x234, then `Run` passes them to WB.
   This is a static field/call trace, not a live interprocessor packet capture.

`wb_gain_contract.cpp` models the bounded normalizer tail and common snap;
`wb_gain_contract.py` independently checks **381,799 gain pairs/triples** with
NumPy integer arithmetic. In the **326,853** cases without signed-product
overflow or zero packet gains, every result has an exact unity member and all
gains are at least unity. It also retains the awkward out-of-range behaviour:
the observed cap at 65536 followed by uint16 narrowing produces zero in 54,943
tested cases; three further cases are excluded for overflowing products.
Those are not valid phone fallbacks. The phone probe rejects unsupported
ratios/products instead of transplanting them. No firmware execution, complete
automatic-WB estimator or universal sensor-gain range is claimed.

`LUTS/WBPARAM` was located and hashed (20,008 bytes, SHA-256
`8f2075372d16c021b12a898195ccc9623c19c13715ee0309c8e8be76f7ad6911`).
Its full format is not decoded or substituted into the phone's colour pipeline.

### Pedestal attribution correction

The earlier note called the WB pedestal `frame+0x7c`. That was incorrect:
`Run` reloads P5 from FP-0x40 at `0xff61022c`, so the WB call reads
**context+0x7c**. Its sample pointer still comes from **frame+0x34** via P0.
Frame+0x7c is a separate geometric field. `Init` zeroes context+0x78 through
+0x1db, covering the pedestal, but a complete audit of subsequent writes is
not claimed. The phone's zero pedestal is an explicit adaptation of its
already black-subtracted input, not a recovered M9 black-calibration value.

## Coherent phone test

The failing RAW has neutral `[0.41796875, 1, 0.6435546875]`. Using the recovered
Q14 normalization rule gives the phone probe gains **[39199, 16384, 25458]**.
The ideal unquantized gain ratios already have green as their minimum; the
normalizer adds no common gain. This closes the ambiguity for this capture,
without claiming that an M9 estimator would produce these smartphone gains.

`wb_mapping_replay.py` runs two explicitly named domains:

- **Stored-buffer control:** quantize NORM030 directly to 14 bits, apply WB
  with floor and clamp, then run native green, fixed ISO160 Sharp, Co=2 carrier
  and R/B reconstruction. Undo the quantized WB for the existing colour code.
- **Physical-white probe:** first restore NORM030's representation scale
  (1.6105431518598052), defining black-subtracted physical white as 16383.
  Run the same WB and reconstruction, then undo WB and representation scale
  before returning to the existing downstream pipeline.

Both clamp the input to the legal 14-bit interval. They apply the WB limit
before green and R/B consistently, unlike the earlier producer-only cap.
The green/Sharp algorithm and ISO bank remain unchanged, but their **input
domain changes**: green samples are therefore not required or claimed to
match H. The physical probe changes 11,686,417 green output samples; the
stored control changes 94,703, mostly from quantization and highlight limits.
Neither reuses H's noise variance model across this nonlinear change; their
noise guard is off. H retains its recorded live profile as the control.

This is a phone-domain experiment. The M9's sensor black/white calibration and
shading-to-WB headroom contract are still not recovered. A common numeric
14-bit cap alone does not prove that mapping physical phone white to it is
the original M9 signal mapping.

## Same photograph and falsification

All replays keep the exact RAW, source colour, SAT2, curve02 and recorded
render gain 1.4142135623730951. No new metering or exposure adjustment.

| Replay | Diagnostic pink pixels | Change from H |
| --- | ---: | ---: |
| Current H | 174,776 | — |
| Stored-buffer WB | 147,320 | −15.7% |
| Physical-white WB | 54,096 | −69.0% |

The diagnostic remains pre-JPEG `min(R,B)-G > 15` and RGB sum >300. It is a
foliage-specific aid, not a hue mask used in processing or an accuracy score
on real magenta subjects. Original-resolution crops show substantial remaining
fringes even in the stronger probe.

The same 1,536 fixtures include all four CFAs, two edge/line geometries, four
blur widths, twelve neutral/coloured/clipped backgrounds and four subjects.
The **original fixed-green R/B oracle is retained**. Since this experiment
changes the green input domain, a second reference compares the full output to
the known, optically blurred scene after physical per-channel white clipping.
This reference does not model desired native sharpening, but it exposes colour
loss without depending on the old green output. Both references and every case
are retained, using the same strict 1e-12 comparison tolerance.

| Probe / metric | Cases worse than D | Largest RMS increase |
| --- | ---: | ---: |
| Stored / original fixed-green R/B | 274 | 0.00002245 |
| Stored / known-scene RGB | 313 | 0.00001850 |
| Physical / original fixed-green R/B | 826 | 0.09919630 |
| Physical / known-scene RGB | 838 | 0.09394100 |

Stored-domain regressions are tiny but recorded, and its photographic cleanup
is insufficient. Physical-domain failures are substantial. For example, RGGB
magenta fine lines against severely clipped white, with blur sigma 0.5, rise
from known-scene RGB RMS **0.02684822 to 0.12078922**. Against a bright magenta
background, one fine-line R/B case rises from **0.00019787 to 0.15060075**.
Thus the physical-white cap is rejected even when WB, green and R/B are moved
together. It is not rescued by changing the oracle or checking foliage alone.

## Consequence for the next correction

The gain-normalization gap is now closed for this experiment. Do not spend
another pass on arbitrary gain normalization or promote the physical-white
cap as a fix. The unresolved requirement is reconstructing clipped edges while
preserving genuine colour and the chosen sharpness behaviour. A successful
replacement must improve those specific counterexamples as well as the RAW.
No five-RAW promotion, phone build or performance tuning is justified for these
already insufficient/rejected candidates. The current app and draft PR status
are unchanged; this commit adds research evidence only.

```bash
python3 research/detail1a/wb_gain_contract.py \
  --firmware /absolute/path/m9-1_216.decrypted.upd \
  --objdump /absolute/path/bfin-capable-objdump \
  --out /absolute/path/wb_gain_contract
python3 research/detail1a/wb_mapping_replay.py \
  --raw /absolute/path/IMG_20260921_164710_1790005630040_00.dng \
  --assembled /absolute/path/to/frozen/PhotonCamera \
  --header /absolute/path/m9_sharp_fulliso_bank.h \
  --out /absolute/path/wb_mapping
```
