# FOCUSPOINT1A — M9Cam 2.78

Malcolm reports a displaced focus area when tapping near the middle after launching in Monochrom. Recording 52573.mp4 (14.10 s, 1440×3200) shows launch into Monochrom and a clipped focus-ring arc near the top around 6.8–7.2 s. Touch markers and Camera2 region traces are not present; the recording alone cannot prove where the HAL focused.

The source has two coordinate defects: the startup fallback in Swipe subtracts camera-container bounds from holder-local events, whereas the ready M9/Monochrom paths subtract the actual viewfinder screen origin; and the circle assigns frame-local tap coordinates directly to parent-local X/Y. In addition, hiding with GONE invalidates the constrained circle's layout, and setX/setY translations can survive a later constraint layout at the wrong location.

This patch routes normal and fallback focus through one bounded screen-to-viewfinder conversion. The circle remains INVISIBLE when hidden, translates the selected frame point to its parent's coordinates, and restores that anchor after layout. A new tap cancels the previous fade/end action and restores alpha. Hit testing uses the same coordinate conversion. This applies to M9 and Monochrom without device-specific offsets.

Five scoped files change: version, Swipe, TouchFocus, FocusCircleView and a new Android layout regression suite. Camera2 crop mapping and the autofocus protocol are preserved; capture, exposure planners, renderer/native/assets and Spot WB are unchanged. Tracking remains disabled by default and parked. The SL-series tracking goal remains blocked on unresolved firmware decryption.

Source verification confirms the exact scope and reverse restoration of 2.77. Android CI [38139813108](https://github.com/mwilliams455/M9Camera_refresh/actions/runs/38139813108) passed **63 tests**, with zero failures/errors/skips: focus-point layout (4), crop/AF helper (20), tap/shutter handover (36 across both profiles), and overlay layout (3). The empty AF-continuity discovery suite is not counted.

The signed installer passed version/certificate, 16 KiB alignment, required DEX markers, compiled menus and inherited UI checks. All 27 native libraries and 285 assets remain byte-identical to 2.77. APK SHA-256: `7dd99bd89191691e8936cecd1667137b445fd0a5649d9013a5d21a23db12e7bb`. Evidence: [source](SOURCE_VERIFICATION.json), [build](BUILD_VERIFICATION.json), [package](PACKAGED_VERIFICATION.json).

The CI debug artifact retains the inherited output basename `M9Cam_2.77_UISETTINGS1A-debug.apk`; its compiled version is verified as 2.78/27278, and the final installer is `M9Cam_2.78_FOCUSPOINT1A.apk`. Device confirmation needed only for the reported case: reopen in Monochrom and tap the centre, then an off-centre detail. The circle should stay under the selected point on the first tap and after it hides.

[PR #96](https://github.com/mwilliams455/M9Camera_refresh/pull/96) remains a draft; no merge performed.

Phone feedback, 11 October: Malcolm confirmed “This works” after the prescribed startup Monochrom tap check. The reported placement issue is validated; the earlier pending wording and build-time JSON flags above are historical. Broader lifecycle/lens coverage is separate.
