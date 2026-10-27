# M9Cam 3.04 FOCUSCONTROL1A — first four Hasselblad-inspired improvements

**Accepted photographic + AF baseline:** phone-tested, signed M9Cam 3.03 FOCUSANIMALEYE1B. Keep all existing M9/Monochrome RAW/DNG/JPEG, M9 colour, white balance, exposure, and all 37 native libs + 301 baseline assets unchanged. Work is an owned Camera2 reimplementation of documented Hasselblad UX behaviours; **not reverse-engineered X2D II autofocus firmware equivalence**.

## 1. Focus Area: Spot / Expand Spot / Custom / Wide

Both M9 and Mono: Settings → Capture → **Focus Area** (Wide default). Independent **Custom width/height** controls choose 5/10/15/20/25/30/40/50% of the sensor crop. Exact existing TrackingGeometry rotation/mirror/crop mapping remains authoritative. Camera2 TrackingFocus now accepts optional sensor AF region dimensions; old three-argument call remains and retains its original region for the Wide default. In Spot and Expand Spot, a 7% AF area starts in the middle of the viewfinder unless the user taps another location; Custom uses chosen dimensions and taps. Expand Spot widens to 19% after Camera2 reports inability to focus across a 650 ms window, then contracts again on reported success. This is a HAL-signal policy approximation of the X2D II workflow, **not original Hasselblad AF mathematics**.

## 2. Multiple subjects: selection and no-steal

Human Eye, Cat/Dog Body/Eye and earlier patch tracking share the Focus Area selector. Automatic acquisition is filtered to candidates overlapping the selected area, while a deliberately tapped face/pet uses the existing sticky subject ID or spatial identity. Non-subject taps can use the explicit Spot/Custom area where AF-C is available. Lens changes and camera-session boundaries invalidate old focus handles and late preview results. Face/animal identity and recognition are inherited from 3.03; no retraining or speculative eye threshold adjustments.

## 3. AF-state feedback separate from detection

Read-only `CaptureController.FocusStateSnapshot` originates from real, accepted preview `TotalCaptureResult.CONTROL_AF_STATE` and is bound to the same session and camera, with sample freshness expiry. An independent viewfinder text badge displays the current focus-area name, the detected subject's label (if any), and **Camera2 HAL state**: scanning, reported focused, reported unfocused, idle or unknown. It never calls a semantic target “optically sharp” just because a detector box moved. The badge is an additional diagnostic, not a shutter lock or exposure change. Expand Spot uses a tracked owner's actual Camera2 region match to avoid consuming AF state from stale/unrelated sessions.

## 4. Per-shot physical RAW calibration/provenance receipt

M9 and Mono **already** possess native Camera2 source calibration and lens-shading audits, source CFA/RAW descriptors, immutable physically bound RAW capture result resolution, and a private-spooled PRIMARY sidecar. Stage 3.04 consolidates these existing audits in the saved `renderer.physicalRawProvenance1A` field of `*_M9_PRIMARY.json` when diagnostics are enabled.

It records physical vs logical camera, selected sensor CFA/black/white levels, frame number, original sensor timestamp where delivered, native vs Photon-effective neutral comparison, original Camera2 characteristics and crop arrays, upstream source calibration/shading presence/error and per-physical-ID consistency. The receipt classifies `CAPTURE_SOURCE_PRESENT`, `INCOMPLETE_SOURCE_EVIDENCE` or `PHYSICAL_ID_MISMATCH`, always retaining `actualCrossLensColorEquivalenceProven=false` and `lensShadingAppliedExactlyOnceProven=false` until matched device evidence supports stronger claims.

**No** camera calibration is transplanted from Hasselblad, no second lens-shading GainMap is applied, and no speculative colour normalisation is performed. Pixel reproduction and colour parity across lenses require real matched lens/illumination captures and are not established by source presence alone.

## Source tests

`FocusControlPolicyTest`: 4 modes, custom dimensions and clipping, spatial subject scope, tap pin, lens epoch, HAL-state freshness/expiry, Expand Spot active/fallback.

`PhysicalSourceEvidence1ATest`: complete evidence, seven missing/incomplete input dimensions, mismatch precedence, never treating absent calibration as proven colour equivalence.

Inherited animal/human eye admission, MediaPipe and SimCC tests, Camera2 focus handover/capture regressions, exact 3.03 signed certificate/assets/native preservation are also required.

## Device acceptance, separate from Android CI

1. With no subjects selected, Wide unchanged from 3.03. Try Spot on a nearby object and focus at centre; tap to move the region. Repeat with Expand Spot on an evenly textured subject and verify it expands when the HAL reports failure, contracts on success.
2. Custom width and height both change the actual AF box; spot near image edges should remain inside the preview. Switch physical lenses and rotation, and test M9 and Mono.
3. With two faces or pets visible, select one, change area mode and move/re-enter frame. The other subject should not silently take ownership. Existing Human Eye, Cat Eye and Dog Eye should remain available.
4. Take matched RAW+JPEG captures with diagnostics on from each usable physical lens in comparable lighting. Compare `PRIMARY.renderer.physicalRawProvenance1A`, `SOURCECAL1A` and `RAWSHADING1A`. Disagreements must be classified before modifying any colour or shading math.
5. Save-shutter reliability, no preview flicker, no double AE/AWB region changes, no exposure/colour change and native renderer untouched.

**Meaning of completion:** point 1/2/3 source implemented and Android-tested; point 4 capture metadata joins implemented and verified. **Real-device, cross-lens colour equivalence and AF optical accuracy remain separate phone acceptance gates.** Keep PR as draft and do not merge until user validation.
