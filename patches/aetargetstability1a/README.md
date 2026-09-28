# M9AETARGETSTABILITY1A — persistent photographic target

Parent: verified 2.07 AESTABILITY1A.
Candidate: 2.08-m9aetargetstability1a-aestability1a-aecadence1a, code 26728.

2.07 made applied exposure movement smoother, but the phone recording showed that the
photographic target itself could still move between nearby EV values while the scene
and tap intent felt unchanged. This overlay adds a target-persistence stage before the
existing 2.07 applied-EV ramp.

The raw target still comes from the unchanged FINISH1N/tap calculations. A 0.25 EV target
change needs three fresh agreeing samples; a 0.50/0.75 EV change needs two. A >=1.0 EV
scene transition is accepted immediately, while the existing AESTABILITY1A ramp still
limits ordinary sensor movement. A newly tighter hard highlight/headroom safety target
also bypasses persistence immediately.

The accepted target is reset on a new tap selection, camera/mode ownership change, manual
exposure ownership, or a fully expired meter. Brief invalid-meter intervals continue to
use the 2.07 bounded transient hold.

Diagnostics now distinguish:
- aeTargetRawEv: current photographic calculation
- aeTargetAcceptedEv: persistent target accepted by temporal evidence
- aeTargetPendingEv / confirmations: candidate target awaiting persistence
- appliedTotalAutoEv plus AESTABILITY1A fields: exposure actually being applied

No scene brightness target, clipping threshold, tap search range, night-Auto placement,
subject tracker, renderer, tone curve, saturation, sharpness, noise, JPEG/DNG path or
125 ms probe cadence changes here. This build intentionally does not solve the separate
automatic-region renewal defect or turn the fixed tap patch into object tracking.

Phone acceptance is perceived consistency: same scene/intent should not wander among
nearby exposure targets, while real scene transitions should remain responsive.
