# M9Cam 2.86 UPSTREAMUI1B

This candidate integrates the next selected PhotonCamera UI changes on v2.85:
settings sliders use a 10dp track and 36dp handle; ticks and end markers are hidden
in the settings and zoom sliders; white-theme secondary controls use a darker
neutral container so they remain distinct from the selected control.

The scope is six Android UI resource files plus version metadata. All Java, native,
shader, menu-structure, preference-default and test sources are byte-identical to
2.85. The separate upstream change making blurred viewfinder backgrounds the
default is excluded. Existing user preferences and slider ranges remain intact.
UPSTREAM_SELECTION.json records the three commits and the partial selection.

The user reported the gallery and EXIF improvements in 2.85 work. That is retained
as specific feedback, without treating it as acceptance of all prior capture work.

Source reconstruction and reverse restoration verify the exact seven-file change.
CI runs the existing 146 focused regressions and library release resource verification.
Installer checks verify the actual compiled slider attributes, style dimensions and
white-theme resource mapping, plus identity, SHA-256, CRC, Android v2 signature and
16 KiB APK alignment. All 27 native libraries and 285 assets are preserved from the
verified 2.85 installer. No new tests are added for these resource-only changes.

Device validation for 2.86 remains pending. Install over 2.85, check a settings slider
and the zoom slider, then use the white theme and check that the selected manual
control is visually distinct. Confirm that slider values still change normally.

## Verified installer

CI passed all 146 focused tests with zero failures, errors or skips, and library
release resource verification. The compiled APK contains the expected 10dp/5dp/36dp
slider style, hidden tick/end markers and white-theme colour mapping.

[Download M9Cam-2.86-READY-TO-INSTALL](https://github.com/mwilliams455/M9Camera_refresh/actions/runs/38164466935/artifacts/11712075327).
Extract the ZIP and install `M9Cam_2.86_UPSTREAMUI1B.apk` over 2.85.

Built commit: `92deccf0cf002b7e0280ba36dbaaeb9f531b4564`; run `38164466935`.
The downloaded artifact passed its GitHub digest, CRC, package/version, accepted
Android v2 signature, alignment, compiled UI checks, and byte-identical comparison
of all 27 native libraries and 285 assets against the verified 2.85 installer.
See CI_VERIFICATION.json, PACKAGED_VERIFICATION.json and GITHUB_DELIVERY_VERIFICATION.json.

APK SHA-256: `8440b8a91f014c1dc3b13023e562570990889b3d20c4a58e146b2b8c7a11037a`.

PR #104 is a candidate for phone validation. This is a selective source integration
on the candidate branch; the earlier draft chain is not finalized into main.

## Remaining RAW-size change

Review of upstream `0100edce4b09523086d45864af0c296579695761` confirms the added
vendor raw.size parsing lives inside getAllTargets() under QuadBayer, and only
when the maximum-resolution key is not in use. Quad Bayer defaults to false in
this app. The change therefore has no effect with that option off. It remains
deferred: adoption would need to validate vendor sizes and the resulting camera
session on affected lenses. No RAW-size change is included in this installer.
