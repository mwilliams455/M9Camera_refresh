# M9AESTABILITY1A — smooth exposure application

Parent: verified 2.06 AECADENCE1A.
Candidate: 2.07-m9aestability1a-aecadence1a-exactpatch1b-ae1n-perf3i, code 26727.

This build retains the 125 ms settling cadence and all existing scene/tap target calculations.
It changes only how a fresh target is temporally applied.

Ordinary movement is limited to 0.25 EV per fresh sample when far from target and 0.125 EV
near target. Small direction reversals require two agreeing fresh samples. A >=1 EV reversal
can respond immediately but still moves at the bounded ordinary step. Genuine highlight/headroom
safety reductions remain immediate.

A valid exposure is held for up to 375 ms across a transient invalid/stale meter interval, rather
than snapping to zero between probes. This is a short evidence-refresh grace period, not exposure
lock.

Diagnostics separate aeRawTargetEv, aeStableTargetEv and applied exposure. AESTABILITY1A does not
change night-scene targets, tap search range, signed tap behavior, automatic region renewal,
autofocus, renderer, JPEG/DNG quality, HDR, local tone mapping, or shutter/ISO allocation.

The 0.50/0.75 EV legacy fast-acquire eligibility calculations remain available for diagnostics,
but AESTABILITY1A no longer applies those as single-sample exposure jumps. At 125 ms, a 0.25 EV
far-step still permits about 2 EV/s of ordinary acquisition.

Phone validation must check perceived smoothness, response speed, oscillation and actual capture
consistency. Hard safety transitions may still be visibly abrupt by design.
