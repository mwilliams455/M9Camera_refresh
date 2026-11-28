# M9Cam 3.50 AMAZESIMD — arm64 vector AMaZE (test build)

Parent: **3.49-jpegperf** (27349). Candidate: **3.50-amazesimd** (27350). Test build for
on-phone timing and a visual check of purple-fringing scenes.

## Change

AMaZE (librtprocess) has two implementations: a vector path written with SSE2 intrinsics,
and a scalar path. Only x86 builds get the vector path, so the phone has always run the
scalar one. 3.50 adds `m9simd_portable.h`: the exact set of SSE2 helpers AMaZE's vector
path uses, rewritten with GCC/clang vector extensions. They compile to NEON on arm64, with:
- IEEE per-lane arithmetic and no fused multiply-add;
- `_mm_min_ps`/`_mm_max_ps` operand order;
- ordered lane masks and bitwise selects;
- `_mm_set_*` lane order;
- a signed saturating byte add.

On arm64, `amaze.cc` and the vector `median` specialisations now take that path.
armeabi-v7a keeps the scalar path, because ARMv7 NEON flushes denormals. Phase noise,
quarter blend, chroma preparation, noise cancel and colour are unchanged.

`amazeSimdRevision` and `amazeSimdPath` in the render diagnostics show which path ran.
The arm64 path reports `M9AMAZESIMD350_PORTABLE_VECTOR`.

## Output

3.50 on arm64 produces **exactly** what RawTherapee's SSE2 AMaZE produces. It is not
byte-identical to 3.49, because the vector and scalar AMaZE group some arithmetic
differently, so rounding and near-tie edge-direction choices can land differently.

- On a grey synthetic scene with blown highlights, thin dark lines against a blown band and
  hard edges, both paths measure the same:
  - error against the true scene: 179.690 (3.49) vs 179.689 (3.50);
  - false colour near edges: 722.29 vs 722.31;
  - 99.9th-percentile false colour: 4830 vs 4830.
- After an 8-bit sRGB encode, 99.5% of pixels are identical and 0.009% of samples move by
  more than one level.

## Evidence

`host/simd_parity350.py` builds integer-generated frames (identical on every architecture)
with five builds:
- x86 SSE2 (the reference);
- x86 portable;
- arm64 GCC portable;
- arm64 with AMaZE compiled by clang, the compiler the NDK uses;
- arm64 3.49, plus 3.50 with the vector path forced off.

The arm64 builds run under qemu. Results:
- every portable build equals SSE2 bit for bit, for all four CFAs with and without phase
  noise, and at 4096x3072;
- the forced-scalar 3.50 equals 3.49;
- the clang arm64 AMaZE object contains 561 4-lane float instructions and no fused
  multiply-add.

x86 SSE2 output is unchanged from 3.49, so the earlier native parity suites still apply.

On the x86 host the portable path runs AMaZE core in 177 ms vs 364 ms scalar (SSE2: 134 ms).
Phone timing is pending.
