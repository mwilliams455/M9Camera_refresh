# M9Cam 2.43 UIOVERLAY1E — torch, Night and WB placement

User request: remove the upper-left M9 Colour heading because the lower-right renderer selector already identifies M9; add upper-left torch and Night toggles; move white balance from Shooting controls to the manual row immediately before settings. Explore alternative Photo/Motion selector layouts before choosing one.

## Implemented in this APK

The top bar starts with torch and Night icons. The old render heading is removed; a compact status field shows Night/other capture mode and the active timer only when relevant. The lower-right renderer selector is retained. Torch delegates to the existing FlashButton action and is disabled when the active lens lacks flash. Both new actions obey the existing startup, capture, timer, bracket, recording and final-save guards.

Night switches to the existing CameraMode.NIGHT. Switching it off restores the last Photo or Motion mode, remembered in the private m9_overlay_ui / last_primary_mode UI preference. An absent/invalid remembered value falls back to Photo; video/RAW Video/Unlimited cannot become the return target. Selecting Photo or Motion directly exits Night. Existing mode ordinals, camera mode implementations and photographic processing are unchanged. Night is not a modifier combined with Motion; only one Photon capture mode is active at once.

The manual row is ISO / Shutter / EV / Focus / WB / settings. WB mirrors the original Photon label and delegates to its existing click/long-click and flat-ruler callbacks. WB and torch are removed from Shooting controls. Night is removed from Other capture modes because its direct toggle is now visible; Unlimited remains there. All videos remain hidden. The gear still opens app settings directly.

The current separate Photo and Motion buttons remain in this APK. Three in-conversation mockups compare a joined switch above the shutter, a text strip below it, and a compact mode menu. No mockup choice has been accepted or implemented yet.

## Verification

Android build passed. Eight suites / 54 tests passed without failures, errors or skips. Two added policy tests cover Night round trips to Photo/Motion and safe fallback from invalid/non-primary modes. The Android API 35 view-lifecycle regression tests from 2.41 pass. Source verification: eight changed/added files, 1,226 identical parent files, patch round trip passed. All 25 native library entries and every asset match the accepted 2.38 photographic APK. Signature, version 27243 and 16 KiB alignment verified. Phone UX/torch/Night/WB checks remain pending.

## Recovery

assemble.py chains uioverlay1d into a fresh source destination. verify_source.py takes 2.42 source, 2.43 source and report path. The runner/init script record local Java 17 and SDK/cache paths. package.py takes source, built APK, accepted 2.38 APK, build tools 35.0.0 and delivery directory. The recovery bundle requires base commit db5538a649cba8d61feb453738053dac8d98a6c1 (2.26); use its latest tip. No public push.

APK SHA-256: 0eaf3b7c3664c939f38739017cb33782834d874e3f7416f8f0ad4719f4168125
