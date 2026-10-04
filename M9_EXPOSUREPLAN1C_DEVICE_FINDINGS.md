# EXPOSUREPLAN1C — negative EV lost at minimum ISO

20 September 2026. Parent GL1W: `bb356bb6b427b3fa1159b5b264dde260db6ffe05`, draft PR30.

The supplied GL1W bracket exposes a reproducible allocation bug. Selecting -1 EV near minimum ISO sent almost the neutral exposure to both preview and capture. EXPOSUREPLAN1C corrects this calculation before the existing ISO/shutter allocator; it does not retune Auto or the photographic renderer.

## Device evidence and photo matching

The three supplied JPEGs match the three PRIMARY outputs by their brightness statistics. The reduced JPEGs contain no EXIF; correspondence is based on the near-identical mean/median and ordering, not recovered original filenames.

| Uploaded photo | Capture time | User EV | Actual ISO / exposure ns | Plan scale relative to that capture's neutral reference | JPEG mean / median |
| --- | --- | ---: | --- | ---: | --- |
| 39670.jpg | 11:53:01 | 0 | 50 / 491227 | 1.000000 | 54.165 / 40.588 |
| 39672.jpg | 11:53:07 | +1 | 50 / 1098332 | 1.989999 | 95.008 / 87.872 |
| 39675.jpg | 11:53:12 | -1 | 50 / 603405 | 0.989995 | 60.939 / 47.918 |

The reference changes as framing/AE changes: 491227ns, 551926ns, 609503ns at ISO50. Therefore compare each plan to its own reference; the third capture is actually about +0.297EV above the first in absolute sensor exposure despite selecting -1 EV.

All three requested/actual ISO and exposure values match exactly. Auto EV is 0 with neutral-deadband reason in all three. `intentApplied` is true, and the still renderer retains the plan's achieved exposure ratio. The failure is upstream of both GL and the still request, not a sensor refusing the request or TC20 cancelling a correct -1 EV.

The device reports manufacturer Xiaomi, model `25010PN30G`, main focal length8.72mm, aperturef1.63. This differs from the preceding 11:21 data's 8.71mm/f1.67. Keep this model identity explicit; do not label this a 17 Ultra parity validation without confirmation.

Source bundle: `M9_DIAGNOSTICS_BURST_1789901598586_16(1).json`, 16 entries, includes all three capture/PRIMARY records and live-pair records for the later two shots. Individual first-capture diagnostics duplicate corresponding bundle content; later SOURCECAL/RAWSHADING/PRIMARY are recovered from the supplied bundle.

## GL1W diagnostic result

All three PRIMARY files contain `M9LIVEGL1W_ATOMICSTATE1A` with available/recent/enabled GL draw state, matching camera/mode and user EV. Draw ages are 11.407ms, 6.959ms, 2.363ms. The GL exposure uniforms are 1.0, 1.989999, 0.989995: the preview received the same wrong -1 EV factor as the saved still.

Each OES texture is about33.269ms newer than the state result (one source frame). The draw's exposure pair differs from the capture plan by at most approximately0.006EV in this set. Plan-ID inequality alone is therefore not evidence of a wrong user intent. This small observed difference cannot explain a missing full stop. The texture/result synchronization limitation remains explicit and is not changed in 1C.

There is no new screen recording/actual viewfinder pixel capture in this set. These records verify submitted GL state, not displayed-pixel parity or compositor presentation. The live colour path remains processed OES chroma plus luma transformation, distinct from the RAW M9 colour/curve path.

All three JPEGs and DNGs saved, queues accepted. Render times 2877ms,2239ms,2213ms. TC20 applied gains1.414214,1.414214,1.389730; no new performance or rendering-quality change is introduced.

## Exact failure mechanism

The real EV dial produces -0.9999999701976785EV from float Camera2 step1/3. Its inverse factor is1.9999999586852102. At sensor ISO50, normalized ISO is100. The legacy `ExpoCompensateLower` does reversible arithmetic on integer fields:

1. Divide normalized ISO100 by the inverse factor -> integer50, below minimum.
2. Try restoring ISO by multiplication -> integer99, not100.
3. Try the shorter shutter609503 / factor ->304751ns.
4. The restored ISO99 is still below minimum, so the bounds check rejects the pair and undoes the shutter change ->609501ns.
5. The shutter-priority allocator preserves this now-wrong energy and returns physical ISO50 /603405ns, ratio0.9899951271773888.

The host regression compiling the actual production allocator and actual dial callback reproduced **603405ns and0.9899951271773888 exactly before the fix**. Earlier tests began at sensor ISO100 with minimum50, so they did not exercise this fallback at base ISO. Exact integer-stop constants also fail to represent the dial's actual float conversion.

## Bounded source correction

For an M9 exposure plan, multiply the intermediate duration by2^(userEV+autoEV), rounded to nanoseconds, before the existing shutter-priority allocator distributes exposure energy. ISO is unchanged in this intermediate representation. This eliminates the lossy integer ISO attempt/rollback. The intermediate duration is not submitted to hardware. Existing mode caps, physical ISO/time bounds, exposure-balance controls and manual overrides remain in force.

The legacy non-plan allocation path retains its existing helper. Neutral EV0/Auto0 is unchanged. Auto's chosen offset is unchanged; its execution now uses the same corrected scaling. Plan revision is `M9EXPOSUREPLAN1C`; APK version appends `m9exposureplan1c` after the GL1W suffix.

Only three assembled files change: IsoExpoSelector.java, the plan revision constant, and app version. Exact hashes preserve GL1W transport/diagnostics, shader, tone model, MFM/modern policy, capture route, TC20/still renderer, native colour/calibration, SAT2/curve02 and manual dial.

## Validation

The same device inputs now produce:

| User EV | Old plan scale | Corrected plan scale | Corrected ISO / exposure ns |
| --- | ---: | ---: | --- |
| 0 | 1.000000 | 1.000000 | 50 /491227 |
| +1 | 1.989999 | 2.000000 | 50 /1103852 |
| -1 | 0.989995 | 0.50000082 | 50 /304752 |

These are production-code host replays with explicit synthetic bounds, not new device captures. The supplied sidecars do not enumerate the camera's exposure-time range. On a device where a true limit prevents the requested EV, the existing bounds still apply.

2561 focused assertions exercise actual dial/allocator behavior: minimum ISO50/64/100/160, above-base ISO, Camera2 steps1/3 and1/6, fractional and integer EV in Photo/Motion, monotonic brackets, manual-pair preservation, minimum-shutter clamping and high-end limits. Device fixtures use strict nanosecond-scale checks. Sweeps above mode shutter caps allow the existing0.025EV tolerance for physical integer-ISO quantization. A true minimum-shutter limit returns the closest feasible exposure rather than silently reverting to neutral.

The 479 inherited exposure/route and43 atomic-preview assertions pass locally; the dedicated workflow also runs84 unchanged spatial assertions. Clean parent-file patch replay and photographic freeze pass. Full Android build/artifact validation is tracked in the draft PR.

## Remaining device gate

Retake a fixed-framing0/+1/-1 bracket with the new APK and PRIMARY diagnostics. The important check is negative EV: plan, submitted GL scale and actual sensor exposure should all decrease by the requested amount unless a recorded physical limit intervenes. All previous Auto-placement and full preview/JPEG tone/colour questions remain separate and open. Do not merge on host replay alone.
