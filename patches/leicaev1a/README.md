# M9Cam 2.33 LEICAEV1A — first Leica exposure-control standardization

Parent: `90483f0066cc21ddc03c380cd7a64d891a4b5638`, M9Cam 2.32 PREVIEWBRIGHTNESS1A. Malcolm reported that 2.32 works on 4 October 2026. He asked whether the Leica exposure standardizations in the separate M Monochrom project were present in M9, then authorized this work: “Let's do it but I strongly suspect it'll be a lot like monochrome.”

The prior description of the M9 controls phase as complete was too broad: the implemented menu roadmap was complete, but Leica exposure-control parity was not. This build completes the EV stage. Auto ISO maximum, slowest shutter, AE-L, timer and bracketing remain subsequent stages, not features of 2.33.

## Source and reference

Leica M9 Instructions, English, printed pages 128, 136–139 and 157, mirrored unmodified at:
https://www.overgaard.dk/pdf/Leica-M9-Instructions-english-as-of-september-9-2009.pdf

The M9's persistent compensation is ±3 EV in thirds. Menu and dial address the same value. The reference implementation is `Monochrom_display_reference` at `1716e806cc66ec999faff4e820c0f6927d92ab3a`, especially `apk/mono1a/monoleicasettings1g`. M9 has existing shooting profiles, so it needs a persistent shared preference rather than copying the Monochrom wheel-only storage literally. This is control standardization, not proof of Leica meter numerical parity or identical phone/CCD sensor response.

## Behavior

- Nineteen values from −3 through +3 EV in exact thirds. Fraction labels distinguish thirds from the old quarter steps.
- The Capture and preview menu, manual EV wheel and shooting profiles use one global persisted value. Selecting a value replaces the previous value; menu and wheel are not added.
- EV survives closing the manual panel, lens changes, and app restart. Long-press EV or select zero to reset it. The explicit reset-all method resets EV as well.
- Existing preference identity and profile schema are retained. Legacy finite offsets within the former ±4 range are rounded to the nearest third and clamped to ±3. For example, −0.68 becomes −⅔. Halfway cases round away from zero. Old profile records are interpreted this way on read; their names, IDs and stored collection are not rewritten merely by opening the screen.
- The default-preference EV is global even when per-lens settings are enabled. The wheel mirrors menu/profile changes on resume and when opening the panel.
- The wheel does not depend on a vendor's Camera2 compensation range or step, including absent/zero metadata.
- The physical M9 plan reads this one value directly. Hardware metering stays at zero compensation and Photon's separate software compensation offset is neutral. The accepted allocator already applies `userEv + autoEv` once to physical ISO/shutter energy.
- Existing manual ISO/shutter authority and device limits remain. With both fixed, EV does not change the physical pair. This is stated in the menu help.
- Diagnostics identify `M9LEICAEV1A`, range, step and the shared authority. They remain controlled by the existing diagnostic switch.

The accepted JPEG/DNG rendering, firmware banks, sharpness, automatic placement, tap metering, physical allocator, capture requests, histogram, clipping warnings and 2.32 preview brightness shader are unchanged. Exposure changes affect the physical capture rather than adding a JPEG-only brightness effect. Device limits can prevent the full requested EV from being reached.

## Verification and packaging

18 selected Android test suites: 133 tests, 132 passed, one pre-existing skip, no failures/errors. Eleven new tests cover exact steps, migration, malformed values, fallback HAL conversion, a real dial model with absent vendor EV metadata, shared storage, profile recall synchronization, explicit reset, panel closing, stale-plan rejection and physical render intent. The existing 13 profile tests now verify legacy normalization while retaining the atomic recall and unrelated-setting protections.

A test-harness collision in Mockito's `RETURNS_SELF` default was resolved by explicitly stubbing the preference editor operations; the profile assertions remain active. An actual panel-close bug was found during implementation: a retained hidden wheel listener could receive a reset. Panel closing now resets the transient control models without resetting the hidden EV wheel.

`verify_source.py` verifies exact patch hashes, 1,184 unchanged source files and 466 unchanged photographic/native/asset files, the neutral metering boundary, the sole EV read path, global scope, and all menu values. All 15 patched files reproduce from the parent byte-for-byte. Packaging preserves all 25 native libraries and every asset from the accepted 2.32 APK, checks the signing certificate, version, 16 KiB alignment and compiled menu.

Phone validation is pending. Automated model tests and compiled resources are not a substitute for an on-device UI/capture check.

## Phone check

1. Keep ISO and shutter on Auto. In Capture and preview → Exposure compensation, select −⅔ EV. Open the manual panel: its EV wheel should also read −⅔.
2. Move the wheel to +⅓. Reopen the settings menu: it should show +⅓, not the sum of the two selections.
3. Close/reopen the manual panel, change lens, and background/reopen the app. EV should persist. Long-press EV to return to zero.
4. From one stable scene, compare preview and saved JPEG at 0, −⅔ and +⅔. They should track the exposure changes while retaining the accepted M9 rendering. Check one profile recall, including an older profile if available.

## Reproduce

`assemble.py <fresh-tree>` chains the exact 2.32 source and applies the hash-checked patch. Build the inherited sharpness native library with `sharpnessmenu1a/build_native.py`, Java 17 and NDK 27.0.12077973. Run the Gradle debug build and selected tests. `verify_source.py <2.32-tree> <candidate-tree> <report.json>` checks isolation. `package.py <candidate-tree> <built-apk> <accepted-2.32-apk> <build-tools-35.0.0> <delivery>` creates the signed final APK. The accepted parent APK SHA256 is `6d6ad64fa3f2f413cf1c7e8fd17d5cf7f77f4fe48fdcdb9fe1e001577517f17b`.

Keep the source and recovery bundle private. The inherited firmware publication restriction remains; no public push is attempted.

## Remaining order

1. Validate this EV stage on the phone.
2. Auto ISO maximum and slowest speed together: reuse the Monochrom physical allocation approach, audit the M9 menu values, include these controls in plan identity, preserve manual overrides, and test energy preservation at sensor limits. M9's normal ISO range is 160–2500; do not copy Monochrom's 320–10000 range blindly. Slowest speed uses a lens-dependent threshold or 1/125, 1/60, 1/30, 1/15, 1/8 seconds. When ISO reaches the cap, allow slower shutter where appropriate.
3. AE-L: freeze the displayed physical ISO/shutter intent across recomposition; reproject each live observation, preserve M9 render intent and clear on camera/session/exposure-control changes. Tap becomes focus-only while locked.
4. Timer: Off / 2 / 12 seconds, including countdown UI and cancellation.
5. Bracketing: separate captures, fixed ISO and shutter offsets, with 3/5/7 frames, supported steps and order, durable output admission before the next frame, error cancellation, and timer once per series. No HDR merge or stacking. Adapt the Monochrom output queue safeguards rather than adding only a menu.
6. Return to any remaining preview colour/framing work; then architectural review of one app containing M9 Colour and M Monochrom with shared camera/UI infrastructure and separate accepted photographic pipelines, exposure policies, DNG handling and per-mode settings.

Cross-lens colour calibration and fringing investigation remain parked. Optional M9 B&W/Vintage work remains behind the merger review.
