# MONOPLANWAIT1A — M9Cam 2.76

Malcolm reported intermittent “Exposure preview is not ready. Please try again.” during the 2.75 Monochrom test, alongside eight saved photographs (52390, 52392, 52393, 52395, 52397, 52398, 52399, 52400). The earlier M9 sequence (52374–52382) passed intentional near/far target switching; Malcolm confirmed the chosen targets. App-resume behaviour remains unconfirmed.

## Source finding and correction

The Monochrom path immediately rejected a missing current exposure plan. The 2.74 capture-lifecycle cleanup then treated this pre-submission rejection as a sensor failure and closed/reopened the session. M9 already had a brief wait. Monochrom's selector requires matching physical preview metadata received within 250 ms, so temporary absence is possible. The photographs do not identify which validity condition failed on each refused attempt.

2.76 retains the same ordinary shutter attempt and retries the existing plan selection on its camera handler every 33 ms for at most one second. The original deadline is replaced once; repeated misses do not extend the budget. A valid current plan continues the same shutter without another press. No plan or hardware-AE fallback is invented, no freshness threshold is relaxed, and no exposure allocation or renderer changes.

If the wait expires before any still submission, release the attempt, restore preview focus, report one error and allow another shutter on the same healthy session. Genuine submission/HAL failures and a rejected handler post still use the existing recovery. Queued retries cannot run after pause, session/builder/handler/profile replacement, capture submission, success or retirement. The M9-only preview retry is explicitly excluded from Monochrom's waiting state.

## Reproduce

```sh
python3 patches/monoplanwait1a/assemble.py /absolute/new/PhotonCamera_276
python3 patches/monoplanwait1a/verify_source.py /absolute/PhotonCamera_275 /absolute/PhotonCamera_276
```

Adds 18 Robolectric readiness/lifecycle cases to 181 inherited tests. Tests exercise controller admission/retry/terminal methods with mocked sessions; they do not simulate a full HAL, physical lens or exposure-plan allocator. Source checks establish the production Monochrom capture route reaches this gate before creating/submitting the still. The exposure allocator, plan store and source metadata validity policy are byte-unchanged.

Android and signed-installer verification pending. Device validation of 2.76 remains pending. Draft only; no merge authorized.
