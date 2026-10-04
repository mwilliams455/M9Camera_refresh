# M9Cam 2.10 UPSTREAM2R FIX1

The upstream arrival packer can run when Photon's saved burst preference exceeds
one, even though M9 takes a single RAW. It replaces the owned RAW16 buffer with
a packed bitstream. M9's renderer and physical-CFA DNG writer consume RAW16
directly, bypassing Photon's normal unpack stage. This makes JPEG rendering
fail and can make the native DNG writer read beyond the packed allocation.

FIX1 guards the shared `ImageFrame.packBurstAtArrival` entry point by the M9
processing route. Both ordinary and ZSL arrival callers retain RAW16, regardless
of the burst preference. Photon-only processing keeps upstream packing.

Before native M9 DNG writing, a second check rejects packed, floating-point,
undersized, or invalid-dimension input. The PRIMARY diagnostic records the FIX1
revision, arrival packing policy, packed-bit flag, and buffer capacity.

The Photon base remains `4ee108e169496f429c0afa0cc33e57bb6b2ec724`.
All 111 frozen M9 source/assets and both delivered M9 native colour libraries
remain identical to the 2.08 control. No colour, tone, exposure or demosaic
algorithm is changed. Digital cropping remains disabled; physical lenses remain.

## Reproduce

Use the same JDK 17 and Android toolchain described in `../upstream2r/README.md`.
From the wrapper root:

```sh
python3 patches/upstream2r_fix1/assemble.py PhotonCamera
cd PhotonCamera
chmod +x gradlew
./gradlew :app:assembleDebug :app:testDebugUnitTest --tests '*ZoomControllerTest' --tests '*M9Upstream2RZoomTest' --tests '*M9Upstream2RRawPackingTest'
cd ..
python3 patches/upstream2r_fix1/package.py PhotonCamera CONTROL.apk "$ANDROID_HOME/build-tools/35.0.0" DELIVERY
```

The new wrapper applies a small checked delta to the preserved UPSTREAM2R
overlay and verifies the complete resulting source manifest. Keep the 2.08 or
accepted 2.07 control APK for packaging. Version code is 27210, package and
certificate are unchanged, and the output is `M9Cam_2.10_UPSTREAM2R_FIX1.apk`.

Regression tests exercise the real shared packing method and RAW16 validation,
including full 4096x3072 data, 10/12/14/16-bit sensor counts, buffer identity,
pixel hashes, cursor preservation, packing/fp16 flags, short buffers and integer
overflow. `M9_RAW16_FIXTURE` can point to an optional private 4096x3072 RAW16
fixture; this extra test is skipped when it is not provided. No photographs or
photo-derived data are stored in this repository.

Build and host checks do not confirm phone JPEG output or a fringing improvement.
First phone test: main physical camera at 1x, Auto WB and 4:3. Check JPEG and DNG
save, then collect the full JPEG, DNG and PRIMARY JSON for the fringe comparison.
