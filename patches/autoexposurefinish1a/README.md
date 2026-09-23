# AUTOEXPOSUREFINISH1A — bounded backlit-subject placement

This child patch applies only after the released COLOURTRIAL1E assembly. It does
not change reconstruction, source/target colour, HSM, SAT2, curve02, BT.601 4:2:2,
TG1, TC20, JPEG/DNG writing, resolution, or the accepted diagnostic/stability work.

## Problem isolated

The existing rendered Auto helper has a whole-frame shadow gate: weighted median
below 40 and global dark fraction at least 55%. In backlit scenes, a bright window
or sky can dilute the global dark fraction even when the subject occupying the
centre remains too dark. Legacy M10-R-style multi-field feedback can still provide
a positive baseline, but the rendered helper itself has no subject/body fallback.

The handoff also identified an ownership mismatch: the legacy feedback call receives
the Auto eligibility flag (including tripod/manual state), while
`M9AutoExposure2D.decide()` did not.

## Candidate behavior

The 32x24 neutral-reference GPU meter keeps every existing statistic and adds:

- central-half median;
- central-half dark fraction;
- bright fraction outside the central half.

A separate backlight path requires all three kinds of evidence: the centre must be
dark, the surround must be genuinely bright, and the simulated positive bracket
must remain inside the existing +1.5 percentage-point clipping and +4 percentage-
point broad-brightening budgets.

The rendered backlight contribution is capped at **+0.5 EV total**, not added on
top of the existing baseline. It still rises by at most +0.25 EV per fresh sample,
cannot ratchet on a reused sample, and releases immediately when the safe target
falls. This is a global exposure placement only: no local lift, HDR, tone-mapping
substitute, or post-capture highlight reconstruction is introduced.

Ordinary whole-frame shadow assistance is unchanged. Positive inherited MFM bias
remains subject to the same rendered headroom limit. Missing/stale evidence still
cannot justify positive automatic assistance. Manual ISO/shutter retains authority,
and explicit user EV continues to hold the already displayed Auto baseline.

The Auto eligibility flag is now passed into the rendered helper. When user EV is
zero and no manual ISO/shutter is active, an ineligible state such as tripod cannot
start rendered scene placement.

## Host evidence

`test.py` compiles the exact candidate and checks 33 state/policy assertions,
including the original 21 COLOURTRIAL1A behaviors plus:

- a backlight fixture that deliberately fails the old global shadow gate;
- staged +0.25 -> +0.5 EV backlit-subject assistance;
- no repeated-sample ratchet;
- no assist without a bright surround;
- no assist when the centre is already healthy;
- existing highlight-budget veto of the backlight path;
- eligibility/tripod ownership;
- exact central/outer meter geometry.

These are synthetic policy proofs, not photographic acceptance. The phone gate is
a fixed-framing backlit subject/window scene, ordinary daylight, and a dim interior,
with a bright↔dark transition and user-EV handover. Preserve original JPEG/DNG and
joined diagnostics for representative captures.

## Known limit

The bracket remains processed-preview RGB evidence. It does not prove physical RAW
per-channel headroom. AUTOEXPOSUREFINISH1A therefore does not add an absolute RAW
clipping predictor or a new negative-search policy. Those remain separate follow-on
work after this backlight behavior is validated on-device.
