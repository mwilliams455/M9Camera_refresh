# Clipped chroma: colour-preservation counterexamples and WB input boundary

21 September 2026. Follow-up to `DETAIL1H_PHONE_FRINGE.md`.
**No candidate in this investigation meets photographic acceptance. No new APK,
application change, exposure adjustment or noise-strength retune is issued.**

## What the broader tests changed

The first local-bounds probe appeared promising: all 32 clipped-neutral cases
lost the measured pink, and none of the original 320 coloured cases worsened.
Those backgrounds were neutral. Extending the fixtures to genuinely coloured
highlights and stronger clipping exposes substantial errors. Passing the first
384 fixtures was not sufficient for promotion.

`censored_chroma_probe.py` reproduces the selected follow-up probes on 1,536
fixtures: four CFAs, a diagonal step and repeated four-pixel-wide diagonal lines,
four optical blur widths, twelve backgrounds, and four foreground colours.
Backgrounds include blue sky, warm light, cyan, red, blue, magenta and severe
white/magenta clipping. Values are white-balanced linear camera RGB, not sRGB.

The reference and limitations remain explicit: known scene differences after
physical white clipping, added to the same native sharpened green; no sensor
noise, unity lens gains, synthetic float64 normalization, outer 16 pixels
excluded. This is a colour-difference screen, not an independent full-camera,
Leica-hardware or perceptual-quality oracle. All candidates preserve native
green/fixed ISO160 Sharp exactly.

The local bounds use neighbouring uncensored native R/B samples, their raw
colour-minus-interpolated-green differences, and a neutral zero anchor. The
correction never uses a rendered RGB8 hue mask. Nevertheless, the bounds and
abstention rules are heuristics, not recovered M9 processing or proof of the
true colour of every censored/subpixel structure.

| Probe | Operation | Cases with worse R/B reference RMS than D |
| --- | --- | ---: |
| `independent4` | Clamp both signs of each channel difference to local bounds, radius 4 | 909 / 1,536 |
| `joint2` | Reduce positive excess only when both channels exceed their upper bounds, radius 2 | 44 / 1,536 |
| `joint4` | Same joint condition, radius 4 | 34 / 1,536 |
| `certificate8` | Radius-2 joint bounds with a wider genuine-colour abstention rule | 0 / 1,536 |

The last version also uses partially censored evidence correctly: a clipped red
or blue sample can still give a **lower bound** on C-G when its green support
is uncensored. Nearby positive R-G and B-G evidence triggers abstention within
eight pixels. This preserves the difficult magenta cases in this fixture set;
it does not establish preservation for arbitrary colours, noise or finer lines.

The hardest counterexamples include real magenta fine lines against a severely
clipped neutral background, and green subjects against a bright magenta
background. A bright coloured source can clip to white while its blurred edge
still carries real colour. Suppressing that edge simply because it is next to
clipping is incorrect. Broad rectangular bounds can also turn legitimate
coloured highlights towards neutral.

## Same RAW: the remaining tradeoff

All replays retain the 16:47 capture's gain `1.4142135623730951`, shading, source
colour, SAT2 and curve02. H uses the recorded live Camera2 noise profile. Cleanup
probes use D with its noise guard off; no new variance model is implied.

| Replay | Diagnostic pink RGB8 pixels | Change from H |
| --- | ---: | ---: |
| Current H | 174,776 | — |
| `independent4` | 66,153 | −62.1% |
| `joint2` | 67,578 | −61.3% |
| `joint4` | 100,997 | −42.2% |
| `certificate8` | 159,524 | −8.7% |

The diagnostic remains `min(R,B)-G > 15` and mean RGB > 100 before JPEG encoding.
It is useful for this green-foliage scene, not a universal accuracy score or an
objective to minimize on magenta subjects. Original-resolution crops confirm
that stronger cleanup leaves substantially less pink but fails colour tests;
the protected variant still leaves conspicuous fringes. Neither is a suitable
replacement APK. The five-RAW promotion suite is not run for an already
rejected or photographically insufficient candidate.

Original sensor hard-clipped samples by CFA colour are R=46,926, G=186,885 and
B=74,340. This is not exclusively a green-only clipping case. Assuming a common
missing-green error while excluding every mixed-channel-clipping neighbourhood
was too conservative to improve this photograph meaningfully.

Evidence: `results/censored_chroma_synthetic.json` retains every fixture's RMS;
`results/censored_chroma_replay.json` records the selected same-RAW probes.
Private image pixels remain outside git.

## New native WB evidence

The selected firmware path's **enabled WB stage clamps processed samples to
14 bits before green interpolation**. This closes an arithmetic evidence gap
left open in `DETAIL1D.md`; it does not establish the phone's correct equivalent
gain normalization or input scale.

Fresh extraction from the hash-verified M9 1.216 firmware reproduces the earlier
local binary bytes. The executable source is `Process_WB` at `0xff6030d0`,
510 bytes, SHA-256
`f8c920cd0bdd38797b3599bd070aa8f528ff9932426b66622061e1c3c48e5143`.
The instruction-derived arithmetic for a processed sample is:

```
y = clamp(pedestal + floor((x - pedestal) * gain_q14 / 16384), 0, 16383)
```

The routine checks the three gain groups for **exact Q14 unity, 0x4000**, in
order. The selected unity group is bypassed; the other groups are multiplied,
arithmetic-shifted by 14 (no half-unit rounding addition), pedestal-restored and
clamped with explicit MAX/MIN instructions. The groups correspond to spatial
phases 00, 01/10 and 11. If none is exactly unity, the final branch clears the
region. That unusual branch is evidence of an input contract, not an Android
fallback policy to copy without the missing producer context.

The gain provenance is now traced one step upstream:

- `SetStructParameter` at `0xfeb1d098` reads little-endian uint16 values from
  packet offsets `+0x0f`, `+0x11`, `+0x13` into context offsets `+0x230`,
  `+0x232`, `+0x234`.
- `Run` at `0xff610000` loads those values into its local three-gain array.
- Its conditional bit-3 dispatch passes that array and `frame+0x34` to
  `Process_WB`, then returns to the dispatch preceding bit-4
  `GreenInterpolationWithCo`. The existing `Run_WB_before_green` evidence
  establishes that execution order.
- The pedestal argument is loaded as a signed halfword from the frame at
  `+0x7c`. Its photometric definition and phone mapping remain unverified.

`wb_boundary.cpp` is a scoped scalar arithmetic model. The independent Python
oracle checks all 16,384 legal input levels in all four spatial phases, seven
gain triples and three pedestals: **1,376,256 output samples agree exactly**.
The checked products fit signed 32-bit. This proves agreement of two arithmetic
implementations derived from the instructions, not Blackfin hardware execution,
full region traversal, complete WB recovery or Android parity.

## Where the correction must go next

The mobile D probe intentionally retains wider neutralized R/B headroom; that
is distinct from this recovered pre-interpolation WB clamp. The known native
behaviour makes its upstream signal contract the next concrete investigation:
the producer of the packet gains, how it guarantees an exact unity group, and
the relationship between its black/white levels and the app's NORM030
representation scale. A bare 14-bit clamp in the app's scaled buffer would
choose a different physical white, so the disassembly does not authorize that
shortcut or overturn the failed early-white-limit colour checks.

Recover and validate that mapping, then replay the coherent WB/green/RB path
against both this RAW and the coloured-highlight counterexamples. Keep the
current output as the control; do not promote another local fringe mask from a
single improved foliage crop. Auto exposure remains unresolved and deferred.

```bash
python3 research/detail1a/censored_chroma_probe.py \
  --raw /absolute/path/IMG_20260921_164710_1790005630040_00.dng \
  --assembled /absolute/path/to/frozen/PhotonCamera \
  --header /absolute/path/m9_sharp_fulliso_bank.h \
  --out /absolute/path/censored_chroma

python3 research/detail1a/wb_boundary_probe.py \
  --firmware /absolute/path/m9-1_216.decrypted.upd \
  --objdump /absolute/path/bfin-capable-objdump \
  --out /absolute/path/wb_boundary
```
