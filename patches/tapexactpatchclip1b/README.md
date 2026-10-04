# EXACTPATCHCLIP1B: isolated exact-patch clipping correction

Parent: delivered M9Cam 2.04 TAPMETER1A, repository commit
`3192d73af84dfe56275e24a006e54fc343261ec8`.
Candidate identity: `2.05-m9exactpatch1b-ae1n-perf3i`, code `26725`.

The earlier EXACTPATCHCLIP1A repair archives were listed but their bytes could not
be retrieved in this session. This is an explicitly re-created revision, not a
claim of matching the earlier prepared source hash or re-running its unavailable
private replay. It implements the documented one-predicate correction directly
against the hash-verified delivered 2.04 source and carries its own source hash.

The exact patch already has a direct channel-clipping check. Coarse fields that
intersect that patch also contain pixels outside its visible rectangle. Do not
count those whole cells as subject clipping while the inherited bright-background,
unmet-target and useful-progress deferral is active. Keep direct patch clipping,
global clipping/near-white, broad regional near-white, thresholds and all other
behaviour unchanged. The coarse mask still influences inherited background evidence;
this is not an object mask, a new target policy or a general-purpose spot meter.

Only `M9AutoExposure2D.java` and the version fields in `app/build.gradle` change in
the assembled production tree. The non-tap source prefix and tap helper retain
exact SHA-256 identities. The child receipt enforces the full 1,006-entry source
inventory. Parent verifiers run before the child, not after intentional mutation.

CI executes the inherited four complete-class suites on both baseline and candidate,
plus 59 synthetic guard checks and a 1,152-decision no-tap differential on each.
The negative control expects the original overlap veto. No photograph-derived
fixtures, metadata, pixel arrays, capture stems or scene thresholds are committed.

CI then builds with the inherited Java 17/Android setup, runs inherited APK/signing/
installation/alignment checks, checks the expected same signer and incremented code,
and compares all `assets/`, `lib/` and `res/raw/` entries against the actual delivered
2.04 APK. Source-only success is not proof of a working APK or of photographic quality.

No automatic lock-renewal, HDR, local relighting, colour/curve, sharpening, noise,
DNG, spool, device-specific eligibility, exposure ownership or tracking changes.
No new exposure target or global highlight threshold is selected here.
Phone validation remains required. Retain 2.04 as the comparison baseline.
