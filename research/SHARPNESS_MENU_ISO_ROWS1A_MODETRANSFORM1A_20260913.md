# M9 Sharpness MENUISO1A / MODETRANSFORM1A

Date: 2026-09-13

Research branch: `research/sharpness-menu-iso-rows1a`

## Scope

This note records firmware-derived Leica M9 1.216 Sharp menu behavior. It does **not** promote or alter the frozen production renderer. Normal project saturation remains SAT3 M06/M07. RBANCHOR1A remains the temporary RGB reconstruction until the packed Leica R-G/B-G reconstruction is closed.

## Canonical source

Canonical decrypted firmware SHA256:
`4f962bb7799ad9a6745ab36c2a3ba59757bfcbd205f50472ddf1b904a5756d20`

Sharp menu mode table source:
`LUTS/PROCESS/LUTS`, offset `0x5f8`.

Manual Leica ISO labels / base-LUT slots:

`160, 200, 250, 320, 400, 500, 640, 800, 1000, 1250, 1600, 2000, 2500`

Slots are 0..12 in that order. Pull ISO80 retains its separate firmware flag and shares slot0 behavior; exact operational ISO-threshold selection remains a separate research question.

## Five Leica Sharp selector rows

Selector enum and exact 13-slot internal-mode rows:

- Off (selector 0): `[1,1,1,1,1,1,1,1,1,1,1,1,1]`
- Low (selector 1): `[3,3,3,3,3,3,2,2,2,2,2,1,1]`
- Standard (selector 2): `[4,4,4,4,4,4,3,3,3,3,3,2,2]`
- Medium high (selector 3): `[7,7,7,7,7,7,6,6,6,6,6,3,4]`
- High (selector 4): `[5,5,5,5,5,5,4,4,4,4,4,4,5]`

This supersedes the older research shorthand that treated each menu position as one global coefficient multiplier. A menu position is ISO-dependent.

## Exact internal mode transforms

`LoadAndModifySharpnessData` accepts internal modes 1..7. It copies the selected 2050-entry base LUT into the working LUT, transforms each signed 16-bit coefficient, then clamps each result to `[-2048,+2048]`.

Exact transforms:

1. `coeff >> 2` using signed arithmetic right shift.
2. `coeff >> 1` using signed arithmetic right shift.
3. `coeff` unchanged before clamp.
4. `coeff << 1` (2x) before clamp.
5. `coeff << 2` (4x) before clamp.
6. `3 * (coeff >> 1)` before clamp.
7. `3 * coeff` before clamp.

Mode 6 is the important finite-precision case. It is **not** interchangeable with floating `1.5 * coeff` or `(3*coeff)>>1` for odd coefficients. Firmware halves first using signed arithmetic shift, then multiplies by three. Fingerprints include:

- `+3 -> +3`
- `-3 -> -6`
- `+5 -> +6`
- `-5 -> -9`

## Consequences for the current Android implementation

1. `STANDARD_FULLISO1A` remains correct: Standard slots 0..5 use mode4/2x, slots 6..10 mode3/1x, slots 11..12 mode2/0.5x.
2. Low, Medium high and High must not be implemented as generic Android strength multipliers. They must select the firmware row by Leica ISO slot and apply the exact internal transform.
3. Off is not a bypass. The firmware row is mode1 at every ISO, so Leica `Off` still applies the recovered Sharp kernel with quarter-strength working coefficients.
4. Modes 5/6/7 are now sufficiently closed for offline/reference implementation; no interpolation or float approximation is required.
5. No APK menu/pixel-path change is promoted by this research note. A canonical-firmware CI cross-check must pass first.

## Remaining sharpness fidelity gaps

- Exact Leica operational ISO-to-slot threshold/selection semantics. The current Xiaomi main-module bridge (`CaptureResult ISO x2 -> nearest Leica label in log2`) remains a mobile adaptation, not Leica threshold truth.
- Exact packed/two-phase R-G/B-G reconstruction after Sharp. Firmware tracing has already closed that post-Sharp green at `frame+0x3c` is the authoritative base consumed by `ASMRedBlueInterpolation1`; RBANCHOR1A remains temporary until the packed difference lanes, filtering and complementary passes are reproduced offline.
- UI wiring and device validation for the four non-Standard menu positions after the RGB/threshold decisions above.

## Next gate

Proceed with an offline scalar RBCLOSURE reference from the recovered Blackfin producer/consumer chain. Preserve the validated Standard/SAT3 production path unchanged while that work is falsified against synthetic invariants and representative Xiaomi DNGs.
