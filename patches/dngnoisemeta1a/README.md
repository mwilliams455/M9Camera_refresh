# M9Cam 2.14 DNGNOISEMETA1A

Native M9 RAW export previously wrote NoiseModeler.computeModel, which divides
coefficients by frameCount * 0.9 and may substitute generic/device tuning.
Those values describe a processing model rather than this single saved mosaic.

The M9-only path now reads the owned physical capture's SENSOR_NOISE_PROFILE
and its physical CFA. It emits RGB pairs for DNG CFAPlaneColor order, selecting
the complete higher-S green pair (first CFA position on ties), like Android's
DngCreator. Non-finite coefficients, S <= 0, O < 0, missing four-pair calibration
or unsupported CFA omit this optional tag. It does not invent a noise model.
Dynamic metadata loading skips the processing NoiseModeler for native M9 RAW;
generic Photon paths continue using it. The existing per-frame boundary trace
records the source pairs, selected RGB values and omission status.

This is a calibration-metadata fix, not a new Leica noise filter or M9 colour
profile. Native RAW, levels, matrices, WB, gain maps, exposure default and JPEG
rendering behaviour remain unchanged. All native libraries and M9 assets in
the delivered APK are frozen to the accepted 2.13 APK.

Assemble with `python3 patches/dngnoisemeta1a/assemble.py PhotonCamera`.
JVM tests cover all four Bayer layouts, unequal greens, tie policy, missing and
invalid coefficients and per-capture isolation. Host serializer tests check
exact DOUBLE[6], omission, RAW identity and the existing signed-EV/alignment gates.
Phone validation remains required; the saved DNG tag must equal the new sidecar
`photonBoundary2Q.dngNoiseProfile.exportedRgbPairs` when present.

References:
- Android CaptureResult.SENSOR_NOISE_PROFILE: coefficients are in CFA channel order.
  https://developer.android.com/reference/android/hardware/camera2/CaptureResult#SENSOR_NOISE_PROFILE
- Android DngCreator, generateNoiseProfile: complete higher-S pair selection.
  https://android.googlesource.com/platform/frameworks/base/+/HEAD/core/jni/android_hardware_camera2_DngCreator.cpp
- Adobe DNG 1.7.1, NoiseProfile tag 51041: DOUBLE, RGB plane order, positive S,
  nonnegative O; optional for unprocessed RAW calibration.

Only source and synthetic tests are included in the repository.
