# Recovery provenance

This bundle reconstructs the deleted **M9 bootstrap Git repository** through the current v0.7ZQ / PERF3I test candidate.

## Byte-exact retained material

The entire cumulative v0.7ZQ/PERF3I overlay at repository root (`payload/`, `patches/apply-m9cam-v0.7-r35-parity.py`, verifier, reference tests and validation summaries) is copied byte-for-byte from the package that was being tested immediately before the Git repository was deleted.

The current v0.7 payload also contains the exact current `M9SubjectMotionAnalyzer.java`; the foundation bootstrap uses that same retained source and the cumulative v0.7 overlay copies it again.

## Source-recovered foundational material

`M9ModernExposurePolicy.java` v0.6 structure and motion-to-shutter map were recovered from the retained original source. The accepted v0.6.1 handoff freezes only:

- `MOTION_ACTIVATE = 0.52`
- `PERSISTENCE_PEAK_SCALE = 0.96`
- `PERSISTENCE_MAX_BOOST = 0.08`
- `ANALOG_HEADROOM_FRACTION = 0.95`
- the existing v0.6 motion-to-shutter mapping unchanged.

`apply-m9cam-recovered-v0.6.1.py` therefore deterministically applies those accepted changes to the recovered v0.6 controller.

`M9CaptureMetadataWriter.java` is recovered from the retained v0.5.3 source contract and adds the v0.6 `m9ModernExposureDecision` field required by subsequent versions.

## Reconstructed compatibility glue

The original deleted Git repository itself and its Git history were not recoverable byte-for-byte. The recovery foundation patch and `M9ExposureDiagnostics.java` are reconstructed compatibility glue from the retained source/handoffs and current JSON contract. They exist to recreate the pre-v0.7 seams that the exact cumulative PERF3I overlay expects. They do **not** define the frozen photographic renderer.

The final v0.7 renderer/native payload and photographic constants are the retained exact files.

## Upstream Photon commit

Historical Actions cloned `PhotonCamera` branch `dev` without pinning a commit and printed `rev-parse HEAD`; the deleted repository did not retain that SHA as a source file. This recovery workflow therefore mirrors that behavior and records the commit used for each new build in `PHOTON_UPSTREAM_COMMIT.txt`. If Photon `dev` drifts enough to break patch anchors, use the last compatible SHA from an old GitHub Actions log if available and pin it in the workflow.
