# M9 DNGRAWPAIR1A — same-exposure diagnostic build 2.19

Adds an additional `_RAW_UNFILTERED.dng` to each successful M9 physical single-RAW
capture. The normal JPEG, filtered DNG and embedded M9 App1B profile retain their
accepted 2.18 algorithms. No extra exposure, stacking or HDR is used.

The control uses the original owned RAW16 buffer with no numeric expansion or
noise filtering. Original black/white levels are frozen before DNG filtering and
set on a separate writer; physical colour calibration, white balance, gain-map
opcodes, orientation and exposure metadata follow the normal physical writer.
The control omits the M9 look and NoiseProfile. External comparisons must disable
the normal DNG's look and extra editor NR, and account for its numeric encoding
scale. The control does not remove processing already present in Camera2 output.

The control is written after the normal base DNG succeeds, on the existing bounded
DNG worker/fallback path, before frame release. A protected direct view avoids a
second Java RAW copy. The native writer still needs one temporary DNG allocation.
Each 4096 x 3072 control costs approximately 25.2 MB and extra write time.

Same-directory `M9_PAIR_PENDING_*.dng` staging uses the accepted Android media
extension. Completion uses a no-replace move; handled failures remove only their
own staging file and preserve the normal capture. Abrupt process death can leave
an uncommitted staging DNG. There is no background deletion sweep.

The control is media-scanned without updating the normal capture thumbnail.
`renderer.photonBoundary2Q.dngRawPair1A` records success/path, source-buffer hashes,
original levels, scale/filter state of the normal DNG, timestamp, size and timing.
After upload, decode the control and compare its raster hash against the source
hash; the phone does not claim to have independently decoded its saved DNG.

Build from an empty destination:
`python3 patches/dngrawpair1a/assemble.py PhotonCamera`

The dedicated workflow runs the pair storage/ownership tests, inherited profile,
storage, native serializer/colour gates and Android unit tests. Packaging checks
all source hashes and preserves all 23 native libraries and six M9 assets from
accepted 2.16, as 2.18 did. Public tests contain synthetic input only.

This is a diagnostic build. It does not claim a fringing fix or completed handset
validation. Upload the matching normal DNG, `_RAW_UNFILTERED.dng`, JPEG and PRIMARY
JSON from one exposure for analysis.
