# M9AUTOEXPOSUREFINISH1L — OPENANCHORBAL1A

The first 1.99 phone capture proved BGQUAL1A and HIGHLIGHTRET1A were working, but
also exposed an older soft-anchor interaction.

## Phone evidence

The 08:50:35 frame had:

- coherent current body, severity 1
- body median about 13, q25 about 4.7
- BGQUAL1A cap: +1.0 EV
- HIGHLIGHTRET1A cap: +2.0 EV
- protected textured open anchor: 3 fields
- old open-anchor cap: +0.25 EV

So the final exposure stopped at +0.25 EV even though both of the newer safety
systems would have allowed materially more exposure. The result preserved the wall
well, but left the person and bedding too dark.

## 1L rule

The existing +0.25 EV protected-anchor rule is retained for ordinary ambiguous
dark material.

A new middle tier allows **+0.75 EV** only when all of these are true:

- a coherent body is valid
- confidence >= 0.35
- severity >= 0.85
- body median <= 18
- body q25 <= 8
- BGQUAL1A absolute-background evidence score <= 0.15

The +0.75 EV cap is then still intersected with BGQUAL1A and HIGHLIGHTRET1A.
Therefore it cannot bypass either the weak-background +1 EV ceiling or the global
single-exposure highlight-retention ceiling.

Strong bright-background anchored scenes keep the previously validated +0.50 EV
severe-anchor branch. Ordinary anchors stay at +0.25 EV.

No HDR, local tone mapping, multi-frame merge, or post-render highlight recovery
is introduced.
