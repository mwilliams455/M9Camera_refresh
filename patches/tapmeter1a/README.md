# 2.04 TAPMETER1A

Experimental tap-to-focus plus explicit M9 exposure selection on FINISH1N. A tap
measures an actual bounded pixel patch in the existing neutral-reference rendered
32x24 exposure probes, rather than choosing an automatic connected component near
the autofocus rectangle. No new full-frame image copy or shader is introduced.

## Controls

Tap the intended subject in the preview. The yellow rectangle is the rounded,
clipped patch actually sampled. Tap inside that rectangle to return to Auto, or
wait 15 seconds. A new tap elsewhere replaces the selection. Rotation, view
geometry, lens/camera changes and pause clear it. The patch is fixed on the screen;
this first version does not track moving objects.

The label reports the applied Auto EV and whether highlight protection limits the
selection. The metered region guides one global capture exposure, not a local
brightness edit. Current automatic region history is invalidated on selection and
release. The independent no-tap automatic lock-renewal bug is not changed here.

## Measurement and policy

The tap uses view-local coordinates from raw screen coordinates and the displayed
GL viewport. Both the displayed preview and the meter use the same rotated vertex
shader, mirror and source crop, so the tap must not invert sensor rotation again.
The top-to-bottom UI position is converted once to bottom-origin GL probe pixels.
The inverse rectangle is shown to make the exact sampled patch inspectable.

Only measurements submitted after the current selection may control it. Late
results from an old selection cannot replace a newer tap. Camera/mode, freshness
and reference-energy checks remain mandatory. Manual ISO/shutter and user EV retain
priority over the automatic tap-assist branch.

The initial patch readability floor reuses the existing minimum backlight targets:
median 58 and lower quarter 22. Both must be met; the patch cannot pass using a
bright upper tail alone. This is positive subject assistance, not a general-purpose
negative-EV spot meter: an already readable patch requests no extra positive lift.

The global clipping-growth and broad near-white thresholds are unchanged. Actual
patch clipping is checked, and additional regional background-channel tolerance
requires bright-background support and useful progress on the tapped patch. The
weak-background cap remains. Unrelated automatic open-anchor ownership does not
outvote a deliberate tap. No promise is made that subject and window can both be
fully exposed; a limiting indication makes that trade-off visible.

## Frozen photographic path

Native renderer, source calibration, TC20, TONEBOUND050, SAT2, firmware curve02,
TG1, denoise/detail processing, JPEG/DNG paths, preview shaders and spool behaviour
are unchanged. There is no local relighting or multi-frame HDR. Exposure changes
can still alter clipping, noise and motion blur. Phone validation is required.

## Source transport and reproducibility

`payload.00` through `payload.07` contain gzip/base64 JSON for a unified source patch,
per-file before/after SHA-256 manifest and synthetic Java test. The decoded JSON
must match SHA-256
`900134bfe9b12770c75eef0e1d69697336103b0c8f4e0d4cedc2b93f6931720a`
before any source is applied. This transport avoids large contents-API writes;
it is not an executable binary or private-photo fixture.

Decode the readable sources for inspection with:

```
python3 patches/tapmeter1a/apply.py --decode TAPMETER_DECODED
```

The build also exports the readable patch and each changed Java source. Source
inventory verification permits exactly nine Java files plus Android version
identity to change from exact 2.03. Complete-class inherited and tap-specific host
tests run before Android compilation and packaged signing/alignment checks.
