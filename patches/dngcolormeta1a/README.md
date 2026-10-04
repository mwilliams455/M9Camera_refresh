# DNGCOLORMETA1A

The native single-RAW export still passed through Photon's renderer colour calculation. That path can substitute global sensor-specific matrices and invent an identity ForwardMatrix when optional calibration is absent. Those values can describe a different colour space from the owned RAW.

This release reads the physical CameraCharacteristics and CaptureResult into an owned colour snapshot. DNG export skips renderer colour recalculation and writes only that snapshot. Valid existing matrices and white balance retain the same float-to-rational conversion. Optional missing/invalid forward matrices are omitted; an incomplete dual forward pair falls back to ColorMatrix processing. A missing or unusable second illuminant/ColorMatrix pair exports the first set alone. Missing calibration matrices use the DNG-specified default by omission. Required invalid ColorMatrix1/neutral/illuminant data fail explicitly instead of using another camera's values.

The native change omits CalibrationIlluminant2 when its internal sentinel is zero; DNG does not allow a present second Unknown illuminant. Normal dual-illuminant files retain both values. New sidecar colour diagnostics report the actual selected tags.

The phone's calibration remains authoritative. No Leica sensor coefficients, JPEG tone curve, profile look table, exposure adjustment, RAW processing change or compression change is introduced. JPEG processing code/assets and all native payloads except the DNG writer are retained byte-for-byte from 2.15. This is colour-metadata isolation, not phone-to-M9 sensor characterization. Other existing black/white/shading policy is outside this patch.

Validation includes nine Java policy tests, production colour policy through four synthetic production-native DNG writes with independent TIFF decoding, existing RAW16/noise/diagnostic regression gates, and signed-package checks. Private photos and capture metrics are excluded from this repository.

References: Android CameraCharacteristics sensor calibration/colour/forward matrix contracts; Adobe DNG 1.7.1 specification, CalibrationIlluminant2, CameraCalibration1/2 and ForwardMatrix1/2. The exported feature set remains DNG 1.3.
