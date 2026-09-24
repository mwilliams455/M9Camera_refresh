# AUTOEXPOSUREFINISH1E — rendered 4x6 multi-field body readability

Child of the stable 1.77 M9-character-guard build.

The phone examples showed that centre-rectangle metering is not a sufficiently
general proxy for subject placement. A bright window can share the centre with a
dark subject, while an off-centre subject can be missed entirely.

1E keeps the same neutral-reference 32x24 rendered bracket and changes only how
the backlight/body branch interprets those pixels.

## 4x6 rendered field map

Each bracket is summarized into 4 rows x 6 columns (24 fields), using:
- median rendered luma;
- lower-quartile rendered luma;
- 90th-percentile rendered luma;
- near-white fraction;
- channel-clipping fraction.

The 24-region topology is deliberately borrowed from the earlier M10-R
multi-field research because it is a useful scene-geometry architecture. The
signal and decision math here are our M9 rendered-domain measurements; this is
not claimed to be Leica M10-R or M9 numerical metering parity.

## Coherent dark-body selection

At neutral reference, 1E searches for a connected dark component rather than
assuming the centre is the subject.

Safeguards:
- near-black featureless floor/shadow fields are excluded;
- one isolated outer-edge dark field is rejected;
- a two-field edge strip with no inner support is rejected;
- a component covering most of the frame is treated as whole-scene/low-key
  structure rather than a backlit subject;
- an already-high-key frame is not brightened simply because one dark patch
  remains.

The winning component mask is then held across every +0.25-EV rendered bracket,
so Auto measures the same body while exposure changes.

## Readability, not normalization

The selected body receives a relative target, not a universal brightness target.

Depending on baseline starvation, body median is asked to improve by roughly
16-22 rendered codes, clamped to a dense 44-60 range. Body Q25 rises by roughly
8-12 codes, clamped to 14-26. Q90 can satisfy the detail/readability side when
legitimate dark material keeps Q25 low.

This is intentionally much darker than conventional middle-grey exposure.

## M9 character ceiling

Background window/sky clipping remains expendable when the coherent body is
still starved. The body itself gets stronger protection:
- stop when the dark component becomes too open (median >=72 and Q25 >=36);
- once readable, bound new bright/clipped pixels inside the body mask;
- suppress further lift in an already-high-key frame;
- retain a 30% full-frame clipping ceiling and finite background-loss budget.

## Temporal behavior

The 1.77 classification hysteresis and two-fresh-sample confirmation for ordinary
downward target changes remain unchanged. Real highlight-safety release remains
immediate.

## Frozen

- whole-dark / accepted-night scene-key policy;
- ordinary-scene strict highlight behavior;
- user EV and manual ISO/shutter ownership;
- JPEG/DNG/native renderer and colour;
- WYSIWYG preview shader and neutral-reference TC20;
- shutter draw-lock;
- 1.75 streaming diagnostic-spool stability repair.

The goal is general: preserve M9-like density while allowing a meaningful dark
subject/body to come through, regardless of whether it is centred.
