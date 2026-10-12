# v2.88 numeric conversion review

Reviewed 2026-10-12 against main `44807fb8e3b0cc18bd9ba698a86f0bef547297f4`.
This is a review only: no application, renderer, version, or APK changes.

The full CodeQL scan contains 16 `java/implicit-cast-in-compound-assignment`
warnings across six files. They represent six code groups, including four
test-helper duplicates and two warnings in an unreferenced node. The warnings
do not establish 16 defects or a current M9/Monochrom capture regression.

The useful follow-up is validation at the affected input boundaries. Two
custom-colour interpolation defects are reproduced below; RAW geometry and
noise settings also have conditional validation gaps. Making casts explicit
alone would preserve these problems.

## Warning inventory

Paths below are relative to `PhotonCamera_288/app/src/main/java/com/particlesdevs/photoncamera/`.
Line numbers refer to the exact reconstructed source, not compressed patches.

| Source and lines | Count | Conversion and reachability | Assessment |
| --- | ---: | --- | --- |
| `capture/CaptureController.java`, 6863-6866, 6871-6874 | 8 | Double multiplication narrowed to integer rectangle coordinates. Four production assignments in `mul`; four in `@TestOnly mulForTest`. Production callers are confined to QuadBayer size selection at 1266-1275. | Integer pixel coordinates require rounding. Existing truncation is not itself evidence of a bug. Validate metadata and scaled bounds first; see conditional hardening below. |
| `processing/opengl/postpipeline/PostPipeline.java`, 249-250 | 2 | Double `Math.pow` multiplier narrowed back to float noise coefficients. Called by the inherited Photon render/gain-map paths. | Appropriate float storage for downstream GL uniforms. Normal UI strength is -6 to +4, giving multipliers 1/64 to 16. Invalid persisted settings/model values are a separate risk. |
| `processing/opengl/postpipeline/SmartNR.java`, 31-32 | 2 | Double setting multiplied into float denoising levels. | No constructor call, class lookup, or pipeline registration found in current source. Do not change an unused node as an urgent capture fix. |
| `processing/render/ColorCorrectionCube.java`, 45-46 | 2 | Double epsilon added to float white-point components. Only interpolation caller is `Initial.java:203`, gated on custom `CUBES` mode. | Narrowing itself is small float rounding. Confirmed adjacent defects: undefined interpolation for equal reference ratios and mutation of the caller's white point. |
| `processing/render/ColorCorrectionTransform.java`, 38 | 1 | Double reciprocal/product narrowed to float interpolation weight. Called from `Initial:214`, `ModernInitial:92`, `HeadroomRender:127`, each gated on `MATRIXES`. | Float result is expected. Confirmed missing validation of the interpolation denominator; changing casts does not fix it. |
| `ui/camera/views/viewfinder/SurfaceViewOverViewfinder.java`, 253 | 1 | Float font spacing narrowed to integer y coordinate. Full-debug AF text only; text size is 25. | Cosmetic fractional line-spacing loss. No credible overflow at screen/text dimensions and no photographic pixel impact. Optional `float y` cleanup. |

## Confirmed findings

**P2 — Reject degenerate custom colour interpolation.**

`ColorCorrectionTransform.combineMatrix`, lines 35-40, divides by the difference
between the two reference white-point ratios. Distinct input vectors can still
have the same ratio: `(1,1,1)` and `(2,2,2)` both produce 2. The real `FillCCT`
parser accepts this configuration, and the real interpolation method produces
9/9 non-finite coefficients. A zero blue component in the incoming white point
also produces 9/9 non-finite coefficients with otherwise valid reference points.

`ColorCorrectionCube.Combine`, lines 47-50, has the same equal-ratio problem:
27/27 coefficients become non-finite. Its epsilon changes the incoming white
point, not the difference between the reference ratios, so it cannot protect
that denominator. The existing cube unit fixture even uses identical reference
points, but tests parsing rather than interpolation.

These coefficients are passed to shader uniforms without a finite check. That
establishes invalid render inputs; a black/incorrect image is a plausible
consequence, not a device-reproduced result of this review. It does not prove
an Android process crash. Reachability requires a custom `MATRIXES`/`CUBES`
configuration loaded from `DCIM/PhotonCamera/customCCT.txt` (`Parameters:587,
650-655`) and the relevant inherited Photon rendering route.

Recommended fix: validate finite coefficients, white-point ratios and usable
denominators before accepting an interpolated custom transform. Preserve the
computed default matrix as a fallback and keep the arithmetic for valid inputs
unchanged. Decide explicitly how ill-conditioned, nearly equal reference
ratios should be handled; merely checking exact equality is incomplete.

**P3 — Stop cube interpolation from mutating the caller's white point.**

`ColorCorrectionCube.Combine`, lines 45-46, writes into the actual
`Parameters.whitePoint` array supplied by `Initial:203`. With a finite input
`[0.1, 0.2, 0.3]`, one call changes it to `[0.10000001, 0.2, 0.3]`. Repeating
the call 100 times changes the first output coefficient from `1.6666666` to
`1.666665`. This demonstrates state-dependent computation, not a claimed
visible defect in a normal single render. `Initial` also reuses its bind method
in its optional tiled comparison path.

Recommended fix: perform any necessary input adjustment on local values and
leave shared white-point metadata untouched. Test repeated calls and input
immutability alongside the denominator fix. Do not broadly remove epsilon
behavior without checking valid-output compatibility.

## Conditional hardening, not observed device failures

**QuadBayer rectangle scaling.** `CaptureController:1270` divides target height
by `activeArraySize.bottom` after checking only that the two rectangles are
non-null. The production helper silently converts NaN to zero and very large
positive doubles to `Integer.MAX_VALUE`. Using the actual helper with a
zero-bottom input and target height 6000 gives `right=2147483647, bottom=0`.
Ordinary 4000x3000 to 8000x6000 scaling passes.

This malformed-metadata probe does not show that the user's camera supplies
such a rectangle. Valid Android sensor metadata should not have a zero active
height. The v2.87 `raw.size` compatibility checks validate candidate dimensions
and buffer addressability, not the source rectangles or scaled coordinate
range. Its session fallback only covers newly discovered vendor candidates.
Therefore it is not a general guarantee for every QuadBayer geometry update.

Recommended fix: check source rectangle validity, a positive finite scale and
all scaled coordinates before publishing either rectangle. Preserve originals
and reject an invalid candidate through the applicable fallback/error path.
Retain existing truncation for validated, representable values initially.
Changing `.bottom` to `.height()` is a separate coordinate-system change and
needs evidence from devices with non-zero active-array origins.

**Noise settings and model coefficients.** `Settings:81` reads a float setting
into the double `noiseRstr`; `SettingsManager:373-376` directly uses
`Float.parseFloat`. The UI range is -6 to +4 (`preferences.xml:527-537`), but
the storage read does not enforce that range or reject NaN. UI numeric clamp
comparisons also do not reject NaN. Normal slider values are not a demonstrated
failure trigger.

Using the actual `computeNoise` method with representative finite coefficients
gives finite results at -6, 0 and +4. A stored NaN propagates to both outputs;
a stored strength of 140 overflows `noiseS` to infinity. The later
`Math.max(value, Float.MIN_NORMAL)` is a lower clamp, not a finite/range check.
Invalid/custom model coefficients can also reach this method; some conversion
already occurs through `Double.floatValue()` before the warned statements.

Recommended fix: validate persisted noise strength at its read boundary and
check model/output finiteness before sending coefficients to GL. Use an
established/default model or a controlled failure for invalid models; do not
silently substitute enormous clamped coefficients. Preserve valid settings.

## Scope and implementation recommendation

`DefaultSaver:52-124` routes primary M9 and Monochrom captures to their dedicated
render queues and returns before the legacy `HdrxProcessor` path. The custom
colour interpolation and `PostPipeline.computeNoise` warnings therefore do not
identify a defect in those primary JPEG renderers. QuadBayer geometry selection
and the debug overlay are shared camera code and should be assessed separately.

For this fork, prioritize shared RAW-geometry validation, then the conditional
custom-transform and noise-setting guards. The unused SmartNR node and debug
text layout are low-priority cleanup. No evidence from this review requires
rolling back v2.88 or changing M9/Monochrom photographic math.

When documenting intentional conversions, an explicit cast around the entire
original expression can preserve behavior. Changing `1.0` to `1.0f`, or casting
an operand earlier, can change it: a probe found `1.6260316` versus `1.6260318`
for the same reciprocal/multiply inputs. Avoid broad float-literal rewrites
merely to make CodeQL green. Any targeted fix should have input-boundary tests
and a valid-input parity check; RAW changes also need device/session testing.

## Reproduction and evidence

- Full-source CodeQL artifact: run `38215095093`, artifact `11732187272`,
  `ci-reports/codeql/java.sarif`.
- All six warning-bearing local files were byte-compared with the corresponding
  archived `ci-source/PhotonCamera_288` files and matched.
- No Android integration build or device test was run for this review.
- OpenJDK 17.0.20 ran 14 checks against unchanged production colour classes and
  verbatim extracted `computeNoise`/`mul` methods. Small dependency stubs replace
  logging and data containers only. These reproduce existing behavior; they
  do not certify desired behavior or simulate Camera2/OpenGL.

Run from this repository with an already reconstructed v2.88 source tree:

```sh
python3 scripts/review/numeric_probe.py /path/to/PhotonCamera_288
```

The runner prints SHA-256 hashes of its four source inputs, compiles in a
temporary directory and deletes temporary output automatically. Expected
results are recorded in `NUMERIC_CONVERSION_PROBE_20261012.txt` next to this
report. Review-only code lives under `scripts/review` and is not part of the
Android app or CI gate.

Language semantics checked against the primary Java 17 specification:
[compound assignments, JLS 15.26.2](https://docs.oracle.com/javase/specs/jls/se17/html/jls-15.html#jls-15.26.2)
and [narrowing conversions, JLS 5.1.3](https://docs.oracle.com/javase/specs/jls/se17/html/jls-5.html#jls-5.1.3).
