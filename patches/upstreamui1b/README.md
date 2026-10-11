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
