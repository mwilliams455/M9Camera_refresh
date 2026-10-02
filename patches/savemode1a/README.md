# M9Cam 2.24 — save selector

Use the existing Photon Save selector: 0 JPEG, 1 RAW+JPEG, 2 RAW (DNG).
Selection and the optional comparison RAW switch are frozen at RAW enqueue.
JPEG-only never invokes a DNG writer, even if the comparison switch is on.
RAW-only executes the unchanged photographic calculation needed for the embedded
Leica profile and exposure feedback, but skips JPEG creation, compression, EXIF,
and publication. Profile embedding depends on renderer success, not JPEG output.
RAW+JPEG retains the accepted rendering and output paths. The optional unfiltered
RAW is available in either RAW mode; diagnostic export remains independently controlled.
No files already saved are deleted. No native or photographic-math change.

Host tests exercise the production queue with controlled platform/render/I/O adapters;
Android compilation and regression tests follow, then all native binaries and M9 assets
are checked against delivered 2.23. Phone validation remains required.
