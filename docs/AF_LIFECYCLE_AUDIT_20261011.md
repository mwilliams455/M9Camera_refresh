# Autofocus lifecycle audit — 11 October 2026

## Result

The source audit found six actionable lifecycle defects/gaps. The first fixes should preserve AF mode/region/manual distance in Monochrom still requests and remove the legacy trigger sequence from ordinary preview recovery. Several problems predate the experimental tracker; parking tracking does not remove them.

This is a source/control-flow audit, not a claim that these defects caused the supplied photographs' softness, exposure pumping or the screen-recorder/shutter failure. No runtime app code or APK changed in the original audit pass; subsequent corrections are tracked below.

## Correction progress — 2.73 AFCONTINUITY1A

AF-01 and AF-02 are addressed in source in [draft PR #91](https://github.com/mwilliams455/M9Camera_refresh/pull/91). Both still routes now use shared focus preparation; recovery preserves focus mode and submits only a capability-gated continuous-AF CANCEL before IDLE repeats. AUTO/MACRO and manual infinity remain intact. Initialization/manual-panel exit restore preferences explicitly. One-shot cleanup clears its original builder even if the camera closes during submission.

There are 30 new parameterized controller/request-boundary cases across M9 and Monochrom. Source reconstruction, both production call sites and reverse restoration pass. Android CI passed all 101 tests (30 new focus cases and 71 inherited cases), with zero failures/errors/skips. The signed installer passed version/certificate, 16 KiB alignment, compiled-menu and native/assets preservation checks. Phone lens behaviour remains unvalidated. These tests isolate the existing profile exposure configuration and are not full capture/HAL simulations.

Evidence: [build verification](../patches/afcontinuity1a/BUILD_VERIFICATION.json), [packaging verification](../patches/afcontinuity1a/PACKAGED_VERIFICATION.json), [source verification](../patches/afcontinuity1a/SOURCE_VERIFICATION.json).

AF-03/AF-04 are addressed by the subsequent 2.74 candidate below. AF-05/AF-06 are addressed by the subsequent 2.75 candidate below. The historical audit and four pinned host reproductions below describe 2.72 and are intentionally unchanged. Tracking remains parked and default off; SL firmware decryption remains blocked.

## Correction progress — 2.74 AFLIFECYCLE1A

AF-03 ordinary still cleanup and AF-04 shared callback/session ownership are implemented in [draft PR #92](https://github.com/mwilliams455/M9Camera_refresh/pull/92). A single attempt owns AF preparation, submission and RAW handoff. Failure/abort/closure and no-result deadlines retire the attempt once, release its input, stop further capture admission and reopen through existing recovery. Long-shutter budgets include requested exposure/frame duration. Dedicated capture-session configuration has its own deadline.

Preview and still results are checked before state mutation. Configuration callbacks, queued shutters and delayed RAW/recovery work carry the owning device, open token and session generation. Failed/retired work cannot recover autofocus onto a replacement camera. Ordinary capture success releases ownership after RAW handoff to the existing saving route. No native renderer, exposure/WB policy or tracking algorithm changed.

The new tests cover submission faults, duplicate/late completion, no AF/results, missing/late RAW, capture overlap, stale preview results, replacement sessions, input release and long exposures. They exercise controller lifecycle methods with mocked sessions/savers and a Robolectric clock, parameterized for both profiles. Exact source checks establish both production capture routes and dedicated-session submission reach those methods. These are not full HAL, RAW pipeline or physical lens simulations.

Android CI passed all **145 tests** (44 new lifecycle cases and 101 inherited cases), with zero failures/errors/skips. The signed 2.74 installer passed version/certificate, 16 KiB alignment, both compiled-menu and native/assets preservation checks. Successful 2.74 phone checks are recorded below; wider lens/lifecycle coverage is not established. Evidence: [build](../patches/aflifecycle1a/BUILD_VERIFICATION.json), [package](../patches/aflifecycle1a/PACKAGED_VERIFICATION.json), [source](../patches/aflifecycle1a/SOURCE_VERIFICATION.json). Tap/shutter handover and TouchFocus disposal (AF-05), and passive-settle eligibility (AF-06), are tracked in 2.75 below; this change does not claim to fix them or prove the cause of earlier image softness/exposure symptoms.

## Phone feedback — 2.74, 11 October

Malcolm reported capture was quick enough and clarified that 52317/52318 were taken using tap-to-focus followed by capture in M9 and Monochrom. He then supplied 52339/52338/52336 and explicitly stated focus was still settling when the shutter was pressed. All five captures completed; the displayed samples show reasonably defined scene edges. Count these as successful checks of those attempts. Do not list those same tap/shutter or settling tests as still awaiting user execution. They do not establish every asynchronous ordering, lens or lifecycle transition.

## Correction progress — 2.75 AFTAPHANDOVER1A

AF-05/AF-06 corrections are implemented in [draft PR #93](https://github.com/mwilliams455/M9Camera_refresh/pull/93). A tap captures its preview/session owner and submits request mutations on the camera handler. Shutter admission retires tap continuations before focus preparation while retaining AF mode and selected region. Tap admission is blocked during the capture, and a pre-shutter queued tap cannot revive after capture completion. Session/manual replacement and view pause/destruction retire callbacks; timeout removal targets its original handler. Manual focus writes use the same camera handler and retain valid infinity. The existing tap-meter clear on initialization/reset is preserved.

Passive settling now requires current-tap eligibility for both scan observation and completion. Absolute timeout retires the attempt without treating elapsed time as an observed focus acknowledgment. Tests exercise actual TouchFocus state transitions and controller admission/request methods with mocked sessions, request-result tags and a Robolectric clock. This is not a full HAL or physical-lens simulation.

Android CI passed all **181 tests** (36 new handover cases plus 145 inherited cases), with zero failures/errors/skips. The signed 2.75 installer passed version/certificate, 16 KiB alignment, both compiled-menu and byte preservation checks for all 27 native libraries and 285 assets. Evidence: [build](../patches/aftaphandover1a/BUILD_VERIFICATION.json), [package](../patches/aftaphandover1a/PACKAGED_VERIFICATION.json), [source](../patches/aftaphandover1a/SOURCE_VERIFICATION.json). Subsequent 2.75 M9 target-switching feedback and the Monochrom exposure-readiness failure are recorded below; the successful 2.74 feedback remains valid for that build. Photographic rendering, exposure/WB policy and the parked tracker are unchanged. SL-series tracking remains blocked by unresolved firmware decryption.

## Phone feedback — 2.75, 11 October

Malcolm supplied M9 images 52374/52375/52376/52377/52380/52381/52382 and confirmed deliberately switching focus targets between the foreground bottle, background and animals. The sharp planes follow those selected distances; the last cat image resolves eye/whisker detail. Count this M9 focus-switching/capture check as passed.

The subsequent Monochrom images 52390/52392/52393/52395/52397/52398/52399/52400 show completed captures, with a moving subject. Malcolm reported several refused shutters with “Exposure preview is not ready. Please try again.” Do not mark Monochrom capture reliability as passed. App-resume behaviour remains unconfirmed. These JPEGs do not contain a trace of the refused attempts and cannot establish why their exposure plans were unavailable.

## Follow-up — 2.76 MONOPLANWAIT1A

Source inspection found Monochrom immediately rejected a missing current exposure plan and invoked full session recovery before any still submission. This is a concrete readiness-handling gap, separate from successful focus-switching evidence. [MONOPLANWAIT1A](../patches/monoplanwait1a/README.md) gives the existing plan selector a bounded one-second retry on the same shutter owner. If it remains unavailable, release the unsubmitted attempt without restarting the healthy camera session. Preserve all exposure-plan validity checks; genuine sensor/submission failures still recover through the existing path. Adds 18 readiness/lifecycle cases. Android and installer verification pending; physical-device validation remains pending.

## Source and verification

- Repository head audited: `80f50936cb6ff6dd10f90b0987aba4f4d3ee84b0`, draft tracking PR #90.
- Tested Android source revision: `83a421a4b47533135628b8d69c9f92338dea2ac6`; the later head adds verification records only.
- Reconstructed the complete pinned 2.72 source chain with `patches/focustrack1a/assemble.py`. Its parent and candidate fingerprint checks passed. Candidate scoped SHA-256: `e6b83b94984a6690182c80031e6621f2fe6e6a7627ffb94e0aa67c462512d323`.
- Four bounded Java control-flow cases reproduced from hash-verified production methods/branches: legacy recovery leaks CANCEL into repeating requests; Monochrom changes continuous-picture AF to AUTO; Monochrom changes manual AF_OFF to AUTO; a stale result advances the tap passive phase.
- Reproduction: `python research/aflifecycle1a/probe.py /absolute/path/to/reconstructed/PhotonCamera_272`. Results: [PROBE_RESULTS.json](../research/aflifecycle1a/PROBE_RESULTS.json).
- The probe uses request-recording and clock stubs, and treats `ParamController.setupPreview()` as a no-op. It is not a full Android test, concurrency test, HAL simulation or device focus measurement.
- Previous Android CI passed 71 tests. Those results remain historical; this audit did not rerun Android CI or count the four host cases as Android tests.

All source locations below refer to that reconstructed source under `app/src/main/java/com/particlesdevs/photoncamera/`, not the sparse recovery repository's payload directory.

## Findings, ordered for correction

### AF-01 — P1: Monochrom still capture changes the selected focus policy

`capture/CaptureController.java`, `captureStillPictureMono()`, lines 6878–6883 and 6904–6908.

For ordinary PHOTO/NIGHT/MOTION capture, the Monochrom branch replaces a continuous-picture or manual preview mode with `AF_MODE_AUTO` and puts `AF_TRIGGER_CANCEL` on the still request. It does not use `M9FocusContinuity2B.prepareStill()`, which the M9 branch calls at lines 5000–5005. The later Monochrom exposure and dark-frame helpers do not restore the AF keys.

The Monochrom AF region copy is conditional on `mTouchFocus.isTouchFocus`; tracking deliberately clears that flag when it takes ownership. The tracking region therefore lacks the unconditional copy that M9's `prepareStill()` provides. There is also no equivalent preservation of manual focus distance, including valid infinity (0 diopters).

Confirmed request-policy mismatch: a preview lock/region/manual setting cannot be assumed to survive the Monochrom still request. Actual lens movement and image sharpness are device checks. The host probe reproduces the mode/trigger change for continuous-picture and manual modes.

Correction: apply the shared still-focus preparation to both render profiles without changing their exposure, rendering or RAW processing. Verify continuous-picture mode, AF region and manual distance at actual session submission.

### AF-02 — P1: legacy recovery leaks CANCEL into repeating preview

`capture/CaptureController.java`, `unlockFocus()` lines 4116–4153; `reset3Aparams()` lines 5432–5442; `rebuildPreviewBuilder()` lines 1517–1549.

The legacy sequence sends CANCEL, resets 3A (including a repeating submission while CANCEL remains set), sends START, sends CANCEL again, then rebuilds preview without restoring IDLE. The extracted-method probe records one-shots `[CANCEL, START, CANCEL]`, repeating submissions `[CANCEL, CANCEL]`, and a final builder trigger of CANCEL in the ordinary no-manual-override case. Later parameter rebuilds can inherit it.

Reachable callers include initial non-video session configuration (line 3181), Monochrom capture completion (line 7116), Monochrom missing-plan recovery (line 6779) and manual-panel exit (`manual/ParamController.java`, line 310). Thus M9's successful-capture minimal recovery does not cover the entire shared lifecycle.

Correction: replace these ordinary still-preview recovery uses with a capability-aware shared recovery function. Send a discrete CANCEL only where needed to release continuous AF; always restore IDLE, including submission failure. Preserve AUTO/MACRO lock and AF_OFF/manual distance as appropriate. Keep exposure/white-balance restoration explicit and separate.

### AF-03 — P1: unsuccessful capture lacks a general terminal cleanup path

`capture/CaptureController.java`: M9 callback lines 5165–5182 and catch lines 5306–5312; Monochrom submission lines 7147–7169.

Both still routes set `burst=true` before submitting. M9's submission-exception and sequence-aborted cleanup runs only for an active bracket. Monochrom catches a `CameraAccessException` only to log it, and its still callback has no failure/abort overrides. A non-bracket submission exception or aborted sequence can therefore leave capture state/AF ownership unreleased when the normal completion callback will not run. An individual failed frame followed by normal sequence completion is a different case and may recover normally.

The tracker rejects updates while `burst` is true and can defer restoration repeatedly until preview resumes; it cannot repair missing capture cleanup.

Correction: a single idempotent terminal handler for success, submission failure, sequence abort and session closure, scoped to the owning capture/session. Clear the applicable capture state, resolve output admission/status and recover AF only on the still-current camera. Do not recover an old capture onto a newly opened lens.

### AF-04 — P2: preview results are not gated by current session before mutation

`capture/CaptureController.java`, shared `mCaptureCallback`, lines 777–862.

Progressed/completed callbacks call the shared capture state machine and feed the current `TouchFocus` without first rejecting an old session. Completed results overwrite `mFocus`, preview request/result and other metadata before any general ownership check. The `session==mCaptureSession` check protects only the Monochrom observation helper, not the rest of this callback.

Android documents that a closed capture session may still finish in-progress requests. Device-open tokens and the tracker's own handle identity checks do not guard this shared callback. This establishes an accepted stale-callback path; its timing on the test phone has not been reproduced.

Correction: gate callbacks with a session generation before mutating shared state. Apply the same ownership check to delayed post-capture recovery. Keep any old session's required resource/accounting cleanup separate from current preview mutation.

### AF-05 — P2: tap focus and shutter focus have no explicit handover

`control/TouchFocus.java`, `startFocusSequence()` lines 514–604 and `sendAfStartLocked()` lines 612–627; `capture/CaptureController.java`, `takePicture()` / `lockFocus()` lines 4017–4042 and 2612–2640.

Ordinary tap focus checks `burst`, but not `STATE_PREVIEW`, capture ownership, or a captured builder/session identity. Shutter lock sets `STATE_WAITING_LOCK` before `burst` becomes true and does not retire the pending tap sequence. Consequently a tap during the lock/precapture window, or a continuation from an earlier tap, can submit its own AF changes during shutter acquisition. Tap submissions originate on the UI thread while result continuations use the camera handler; their sequence lock is not shared by shutter/recovery code.

The new tracker already refuses updates outside `STATE_PREVIEW` and retires tap watchers on takeover. The inherited tap/shutter boundary does not have an equivalent contract.

Correction: serialize AF request ownership on the camera handler. At shutter acceptance, retire pending tap continuations while retaining the intended region; ignore or explicitly queue new tap commands until preview is restored. Add retire/dispose hooks for pause, replacement and teardown instead of relying on timeout or a UI circle reset to end ownership.

### AF-06 — P2: a stale settled result can end the current passive scan phase

`control/TouchFocus.java`, `onCaptureResult()`, lines 702–709.

The passive phase requires `regionLive` when observing PASSIVE_SCAN, but does not require it when evaluating whether that scan has settled. After a current-tap scan is observed, an ineligible old result reporting PASSIVE_FOCUSED can call `sendAfStartLocked()` immediately—even before dwell or the shared deadline. The host probe reproduces this transition using the exact branch and helper.

Correction: require current sequence/session eligibility for state-driven completion as well as scan observation. Keep the absolute timeout independent and explicitly distinguish deadline completion from observed settling. Existing `TouchFocusTest` cases test `StateWatcher` and the pure passive helper, not this enclosing branch.

## Lifecycle coverage and existing protections

| Transition | Evidence / remaining issue |
|---|---|
| Open / preview configuration | Open/session configuration uses tokens, but ordinary photo initialization calls legacy recovery (AF-02). |
| Tap / retap | Per-tap generation and tags reject many old acknowledgements; passive completion has AF-06 and shutter handover has AF-05. |
| Tracking movement / retap / loss | Camera-handler updates, one initial CANCEL, IDLE repeating, handle identity and UI epoch checks are present. Loss requires retap. |
| Capture success | M9 preserves selected still AF and uses minimal continuous release; Monochrom diverges (AF-01/02). |
| Capture failure / abort | No general session-owned finalization for ordinary stills (AF-03). |
| Pause / resume / view destruction | Tracker stops/closes and defers bitmap disposal until callbacks finish. Touch focus lacks an explicit disposal hook; shared result gating needs AF-04. |
| Lens / zoom / profile / mode change | Tracker rejects changed builder, session, camera, crop, zoom, geometry and environment. Shared old results and delayed recovery still require AF-04. |
| Manual focus / return to Auto | Manual preview sets AF_OFF/distance; Monochrom still overwrites it (AF-01). Manual-panel exit also reaches legacy recovery (AF-02). |
| Fixed-focus / unsupported lens | Tracking capability checks exist and shared shutter lock has a can-trigger gate. Legacy initialization/reset still sends unconditional trigger sequences; include in AF-02 coverage. |

## Implementation and validation order

1. **AF continuity parity:** correct AF-01/02 in both profiles; retain Continuous Picture AF, manual focus including infinity, and AF regions. Verify recovery leaves trigger IDLE and does not perturb AE/AWB through focus-only operations.
2. **Ownership and stale work:** address AF-04/05/06 with one session/operation ownership contract. Regress retap, tap-then-shutter, pause/resume, old-session results, lens switch and manual takeover.
3. **Terminal cleanup:** address AF-03 with fault injection for submission exception, abort, missing results and replacement during recovery. AF-lock timeout currently advances only when results arrive (`waitingLockProcess` / `hitTimeoutLocked`); include a no-results deadline test and bounded cleanup in this work.
4. **Android + phone validation:** add real submission-boundary tests for both capture routes, not just helper methods. On phone, validate near/far focus before and after repeated captures, manual infinity, lens/zoom changes and pause/resume. Test M9 and Monochrom separately. Screen recording is not required to press the shutter.

Current source tests do not establish HAL focus accuracy, absence of hunting, or saved-image sharpness. The earlier 71-test pass includes tracking ownership and lifecycle tests but not a complete Monochrom still/recovery lifecycle.

SL-series firmware-derived tracking remains a **blocked future goal**, as recorded in [PROJECT_GOALS.md](PROJECT_GOALS.md). It is independent of these corrections.

## Platform references

- [Camera2 AF request controls](https://developer.android.com/reference/android/hardware/camera2/CaptureRequest#CONTROL_AF_TRIGGER): IDLE is the normal trigger value; START/CANCEL are commands.
- [Capture session close behaviour](https://developer.android.com/reference/android/hardware/camera2/CameraCaptureSession#close()): in-progress requests can complete after session close.
