# Recent GL2G -> DETAIL1H regression: causal isolation

22 September 2026. The user's recurrence report was on 21 September after the
DETAIL1H APK. This investigation centres that transition. The separate
12 September Sharp integration history is not the primary boundary here.

## Finding

The added R/B replacement is the demonstrated recent regression boundary.
Its replacement of MHC colour differences with the D carrier is the dominant
harmful change in the tested synthetic suite. The earlier Co shrink within D
can add to it. Scaling the green offset into camera R/B units improves the
average result and must not be blamed for the entire D regression.

The private same-RAW replay corroborates that distinction. H's guard-off
output is byte-exact to full-frame D. The three historical host JPEGs remain
byte-exact. New private photographic measurements are retained separately.
No phone correction or alternative renderer has been promoted.

## Exactly what changed

Let `M_R, M_G, M_B` be Q14 internal MHC samples, `S` the existing GL2G green
after its green/Sharp integration, `delta=S-M_G`, `n` the camera neutral for
R or B, and `C` D's interpolated green-normalized colour difference. Ignore
rounding and clamping only in these explanatory equations:

```
GL2G:                  M_channel + delta
MHC, scaled offset:    M_channel + n * delta
Carrier, old offset:   n * (M_G + C) + delta
DETAIL1D:              n * (M_G + C) + n * delta
```

The middle rows are counterfactual diagnostics. They separate the changed
colour estimate from the changed offset scaling. Native green/Sharp and the
outer ten-pixel border are identical throughout. Quantization, signed rounding
and clamping are executed in the actual diagnostic outputs. Both historical
endpoints are independently byte-exact to the existing implementations in all
1,536 cases; prior endpoint metrics also reproduce within 1e-14.

## Known-scene results

Four CFAs, 1,536 cases, one channel-neutral triplet, fixed existing Sharp row.
Scene construction and error definitions are inherited from
`true_mhc_factorial.py`; these are scene-truth comparisons, not photographic
colour-threshold classifications.

| Output | Mean scene RGB RMS | Cases worse than GL2G | Mean false-magenta excess fraction | Mean false-green excess fraction |
|---|---:|---:|---:|---:|
| GL2G native | 0.050424 | — | 0.145762 | 0.038769 |
| MHC, scaled offset | 0.041255 | 92 | 0.130139 | 0.033155 |
| Carrier, old offset | 0.060251 | 1,412 | 0.175934 | 0.043190 |
| DETAIL1D | 0.050453 | 829 | 0.173189 | 0.035846 |
| DETAIL1D, Co off | 0.048899 | 784 | 0.160843 | 0.034751 |

Replacing MHC chroma with carrier chroma worsens scene RGB in 1,412 cases
under the old offset rule and 1,404 under the scaled offset rule. Therefore
the conclusion does not depend on choosing just one offset convention.
Co worsens scene RGB in 966 cases compared with D Co-off, but is not universally
harmful. None of these counterfactuals is accepted as a correction.

## Carrier mechanism and limits

`rb_domain_stages` subtracts a cardinal green estimate at each R/B site,
optionally shrinks the signed difference toward zero, then diagonally averages
it onto the opposite Bayer phase. `rb_domain_consume` interpolates that carrier
back to output pixels and adds the unchanged native green. It replaces native
R/B even at directly measured R/B sites.

An impulse check on all four CFAs shows the spatial effect. With Co excluded,
the original-phase difference samples contribute through this normalized
kernel at an R/B anchor (sample spacing is two image pixels):

```
1/16  2/16  1/16
2/16  4/16  2/16
1/16  2/16  1/16
```

The anchor's own difference has weight 1/4, with 3/4 from neighbours. This is
an exact operator measurement in the divisible integer impulse case, not a
claim that this kernel alone explains every output error or that a particular
firmware instruction was mistranslated. The guide, Co, interpolation, native
green response and clipping interact.

The attribution script expresses the exact D-minus-GL2G camera-Q14 difference
as four signed terms: Co-off carrier replacing MHC, Co shrink, offset scaling,
and rounding/clipping. After normalization these sum to the change in common
R/B-versus-G chroma. The budget is not an allocation of final RGB8 error
percentages: downstream colour and clipping are nonlinear.

## Negative control: uncomplicated neutral edges can improve

`detail_boundary_neutral.py` adds 64 unclipped achromatic controls. In 32 of
them all neutral gains equal one, making both offset conventions byte-identical.
In these controls D reduces chroma RMS in every case and introduces no measured
false-magenta excess above the existing 0.02 threshold. Unequal-neutral controls
also improve chroma RMS in every case. Native green and Sharp remain unchanged.

This does not contradict the broader regression. It shows why flat colours
and uncomplicated neutral-edge tests could pass while the reconstruction still
fails more difficult coloured/clipped structures. Do not describe the carrier
as uniformly magenta-biased in every scene, or Co as always harmful.

## Root-cause scope and corrective direction

The phone patch executes `M9Detail1H.apply` after the native demosaic completes.
Its guard-off and guard-fallback paths still run D. Therefore the direct
rollback control for this recurrence is to bypass that entire overwrite and
retain native GL2G RGB, preserving current downstream colour and unrelated
app work. That would remove the added D/H regression, not prove all historical
fringes solved. ISO-row changes and new hue-suppression heuristics are not
required to explain this recent regression.

The original DETAIL1D validation emphasized repair of the worse C probe and
simple neutral/constant-colour invariants. Those were insufficient promotion
criteria against the actual GL2G photographic baseline. The new evidence
identifies the regression-producing replacement and its dominant contribution;
exact Leica firmware fidelity and a broadly colour-safe replacement remain
unresolved.

## Reproduce

```bash
python research/detail1a/detail_boundary_probe.py \
  --assembled /path/to/frozen/PhotonCamera \
  --prior-report /path/to/iso_sharp_regression/report.json \
  --out /path/to/detail_boundary
python research/detail1a/detail_boundary_neutral.py \
  --assembled /path/to/frozen/PhotonCamera \
  --out /path/to/detail_boundary_neutral
```

Aggregate reports retain all source hashes, endpoint identities, conditional
effects and the neutral control example. Full case reports and private photo
evidence are preserved separately. The phone app and TG2 are unchanged.
