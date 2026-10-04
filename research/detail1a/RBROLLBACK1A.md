# RBROLLBACK1A — restore native GL2G RGB, retain TG2

22 September 2026. Phone validation candidate requested after the GL2G ->
DETAIL1H recurrence was isolated. Base is the current DETAIL research branch
with the TG2STILL1A app assembly, not an older whole-application checkout.

The patch bypasses the complete `M9Detail1H.apply` call after native demosaic.
It preserves the existing native RGB buffer. It does not merely switch off
the H guard, whose fallback would still execute D reconstruction.

Version: `1.61-m9rbrollback1a-tg2still1a`.

Only `M9R35Renderer.java` and `app/build.gradle` change in the assembled app.
The exact reverse renderer transformation must reproduce the TG2STILL1A
parent hash. The source receipt checks every app/circularbar source and asset:
965 other files remain byte-identical. The native GL2G spatial functions,
existing green/ISO160 Sharp, TG2 preview/still code, tone/colour assets,
exposure allocation and capture transport remain frozen.

Capture diagnostics retain the existing `detail1H` location with:

```
id: M9RBROLLBACK1A
reconstructionApplied: false
guardRequested: false
guardApplied: false
nativeRgbPreserved: true
reason: DETAIL1D_H_overwrite_bypassed
fallback: GL2G_native_RGB
```

The main demosaic control is `RBROLLBACK1A_GL2G_native_RGB`; tungsten identity
remains `TG2NEUTRAL1A_STILL`. The retained D/H implementation is inactive on
the render path and stays available for historical research.

## Parent replay repair

The legacy GL1U assembly can omit the original three-line no-HDR allocator
guard. `apply-m9cam-m9exposureplan1a.py` now recognizes only that exact source
hash and restores the guard before its unchanged manifest checks. The result
must match the already required `6eb84e...` parent hash exactly. Unknown inputs
still fail. This repairs reproducibility of the frozen parent; it does not
change the accepted exposure policy in the resulting app.

## Build and validation

The dedicated `build-m9cam-m9rbrollback1a.yml` workflow replays the full parent
source chain, runs its exposure/preview/TG2/native checks, applies the bypass,
verifies source scope, builds Android, and checks package identity, signature,
alignment and embedded render markers. The new candidate is not merged into
the ongoing app branch automatically.

Offline research establishes the earlier native RGB control and the recent
regression boundary. On-device photographic acceptance remains open. The
rollback removes the D/H addition; it does not promise elimination of every
older residual fringe.

## Phone check

Install over the current app. Capture foliage or fine branches against bright
sky, then one ordinary daylight scene. Keep DNG + JPEG and the matching
M9_PRIMARY diagnostics. Compare fringe reduction and fine detail. If the app
refuses the update, retain the current installation and report the message.
