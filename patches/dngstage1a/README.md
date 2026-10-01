# M9Cam 2.13 DNGSTAGE1A

Adds the ordinary recovered Leica M9 DNG rendering exposure default,
BaselineExposure -1/2 as SRATIONAL, only to the M9 still DNG path.
The reader applies this default; RAW samples, shutter/ISO metadata, sensor
calibration, shading opcodes and JPEG processing remain unchanged.
This is an experimental interpretation choice for phone RAW. It is not
M9 sensor equivalence or the complete M9 colour/noise/shading pipeline.
Phone ISO80 does not establish the M9 pulled-ISO80 mode: the firmware's
-1.5 EV special case is deliberately not mapped to phone ISO numbers.

DNG DateTime uses the same frozen capture-name date/time as JPEG EXIF,
validated as a real calendar date. Unknown names retain writer-time fallback.
General Photon save paths retain their previous defaults.

Assemble with `python3 patches/dngstage1a/assemble.py PhotonCamera`.
The manifest pins the parent and all changed/new source files. Native tests
check signed exposure values, invalid inputs, alignment and RAW preservation.
Java tests cover capture-date parsing, invalid dates, DST ambiguity and policy.
The build preserves all PERF2S native libraries except libdngCreator and all
M9 assets. Handset and actual Lightroom/Camera Raw validation remain required.
No private photo-derived inputs/results are published in this branch.

Firmware evidence: Leica M9 1.216 BF547 file offsets 0x93284 (producer),
0x175fc..0x1760e (capture binding), 0x4787c (IFD0 writer); ordinary -500/1000,
pulled ISO80 -1500/1000. Both supplied genuine firmware-1.002 ISO160 files
corroborate -500/1000. DNG tag 50730, signed rational.
