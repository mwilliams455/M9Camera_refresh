# 2.79 MONOSAVEPIPE1A

Parent: accepted 2.78 FOCUSPOINT1A, commit c24c08bbc82d5d9153091e3648e524a10b8ced7e. Draft candidate; phone performance is not yet measured.

Monochrom's single render worker waited for JPEG EXIF/publication and up to 60 seconds for linear-DNG publication after its RAW was closed. Its durable DNG publisher also waited for a two-second polling cycle after staging. Both delays occupied render admission unnecessarily. M9 already separates JPEG-only final completion from rendering; its code is unchanged here.

## Changes

- Retain one RAW render worker plus two queued RAW jobs. Close accepted RAW ownership exactly once on success or failure.
- Hand off only paths, frozen scalar settings, immutable diagnostic text and final-save tickets to one completion worker plus two waiting jobs. Saturation completes synchronously on the render worker, applying backpressure without dropping a photograph or enlarging the RAW queue.
- Keep save feedback and Monochrom bracket advancement after requested EXIF/publication results. Pending DNG publication retains the durable private export and existing failure/pending notification.
- Wake the existing DNG publisher after private staging. At most one immediate wake is queued. A stage during an active pump may queue a subsequent pass. Periodic recovery and retry remain; the spool's retry deadlines, disk limits, payload verification and publication protocol are unchanged.
- Under the existing diagnostics switch, record render queue wait, render worker duration, original RAW save time, EXIF/publication wait, completion fallback and total save latency. Disabled diagnostics produce no new timing sidecars.

Photographic rendering, JPEG quality, DNG encoding, exposure, white balance, sharpening, denoising, AF and both native pipelines are unchanged. The performance benefit depends on the phone and output mode; this does not promise an unlimited burst or a particular frame rate.

## Verification

`verify_source.py` pins all 1,357 scoped source files, checks the four changed files and verifies reverse restoration to 2.78. All 1,353 other scoped files are identical.

`verify_queue.py` compiles the actual production Monochrom render/finalizer queues, save selection/status, publication wake and durable spool using deterministic Android/render/storage adapters. It passes 24 scenarios: delayed EXIF, delayed JPEG publication, delayed DNG publication, both bounded saturation paths, rejected ownership, all six output choices, render and I/O failures, missing EXIF, DNG timeout/staging failure, detached callback, disabled diagnostics, frozen settings, 250 sequential completions, coalesced wakes including stages during pumping, rejected executor recovery, retry deadline and retained private payload. These are control-flow/storage tests, not photographic or phone throughput benchmarks.

Android CI run 38141816810 passed: all 24 host scenarios and 28 focused Android regression tests, zero skipped/failures/errors. The empty AfContinuityTest suite contributes zero tests. Signed-package verification passed with the accepted certificate, version 2.79 / code 27279 and 16 KiB ZIP/native alignment. All 27 native libraries and 285 assets are byte-identical to 2.78. Installer SHA-256: `a7483f13c24320185d5a35c1a154db6bd686565e284b7fcdf3d64a8ebd71229d`. See CI_VERIFICATION.json and PACKAGED_VERIFICATION.json. [Draft PR #97](https://github.com/mwilliams455/M9Camera_refresh/pull/97) is not merged. Phone throughput/save completeness validation remains pending.

## Focused phone check

In Monochrom, take 4–6 photos at your usual quick pace with your normal output setting. Check whether the processing warning arrives later or clears sooner, and whether every accepted photo finishes saving. If using JPEG + DNG, confirm each accepted photo has both files. No screen recording is needed. Do not treat a final warning under sustained load as failure: both queues intentionally remain bounded.
