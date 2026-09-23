# Total Auto headroom trial

This patch makes the existing processed-preview highlight budget apply to the
total positive automatic exposure bias, including an inherited scene baseline.
Previously, rejection of extra shadow lift could still leave a positive baseline.

The candidate uses the last consecutive bracket step within the existing new-clip
and broad-brightening budgets. Missing, invalid or stale meter data cannot justify
positive automatic assistance. Negative baselines retain their role. Explicit user
EV still freezes the displayed automatic baseline; manual ISO or shutter still
disables automatic assistance. A quarter-stop rise per fresh sample and immediate
release remain in place.

This is a preview guard, not a RAW channel-headroom guarantee. It can lower image
brightness when a prior positive fallback would have been retained. Device cadence,
transition appearance, and photographic benefit still require phone validation.

`apply.py ASSEMBLED_PHOTON_TREE` checks the exact parent source hash and replaces
only M9AutoExposure2D.java. It refuses an unexpected parent and is idempotent.
`test.py OUTPUT_BUILD_DIR` compiles the actual candidate unchanged and checks 21
synthetic state/selection scenarios. The tiny JSON stubs only discard diagnostic
serialization. Run via a Java runtime containing the compiler module.

No workflow or APK incorporates this patch automatically. No default reconstruction,
SAT bank, tone curve, HSM, TG, JPEG encoding, or existing branch is changed.
