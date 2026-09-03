# SCENEFINGERPRINT1A

Diagnostic-only follow-on to M9NEGATIVE1A.

- Keeps completed-RAW recommendation math unchanged.
- Replaces four-value preview association with a richer preview fingerprint using existing diagnostics.
- Keeps similarity threshold at 1.0 for isolation.
- Adds a 60-second completed-RAW recency gate.
- If no recent sufficiently similar completed RAW exists, feedback is unavailable rather than borrowing an unrelated older frame.
- Does not mutate Camera2 exposure, M9Modern exposure policy, render-meter signed EV, JPEG rendering, H25/TG1/SAT3/BT.601, or DNG samples.
