# M9 production architecture contract

Revision: COBALTROLEPURGE1A / NATIVEFIRMWARE1A

This contract records the production architecture agreed for the M9 project and is intended to prevent future diagnostic experiments from being promoted accidentally into the shipping renderer.

## 1. Sensor-specific source layer

The source layer may vary by physical camera module. Its job is only to turn that module's RAW data into the common scene-referred handoff.

Allowed sensor-specific inputs are:

- physical Camera2 camera identity;
- RAW dimensions and Bayer CFA/phase;
- black and white levels;
- live LensShadingMap / source shading metadata;
- physical Camera2/DNG CalibrationTransform, ColorMatrix, ForwardMatrix and neutral metadata;
- sensor-specific RAW normalization required to reach the common scene representation.

Current production source calibration is SOURCECAL2A_CMFIX using the active physical Camera2/DNG dual-illuminant metadata.

## 2. Common scene boundary

After SOURCECAL2A the renderer must no longer depend on Xiaomi lens identity, focal length, camera ID, or a Xiaomi-profile look table. The output of source normalization is the boundary between device characterization and Leica rendering.

## 3. Shared M9 target layer

The M9 target renderer is lens-independent and is shared by main, ultrawide, telephoto and future supported sensors after they reach the common scene boundary.

The current retained shared target stages are the M9 bridge, TC20, SAT3 M06/M07, firmware curve02, exact BT.601 4:2:2 arithmetic and TG1, with the existing frozen sharpening/tone infrastructure unless a separate M9-forensics change explicitly replaces one of those stages.

A source sensor may change its characterization. It must not change the M9 target look.

## 4. Cobalt prohibition in production

Production must not consume:

- Cobalt Xiaomi ColorMatrix;
- Cobalt Xiaomi ForwardMatrix;
- Cobalt Xiaomi ProfileHueSatMap / HSM;
- the historical linear basis derived from the Cobalt source profile;
- any per-lens Cobalt nonlinear look as Leica target behavior.

Cobalt assets may remain only as dormant forensic/offline comparison material. They must not be instantiated by the production mode.

The production HSM at the source-to-target boundary is identity unless and until an M9-derived nonlinear color operation is independently reconstructed from Leica evidence.

## 5. Target-only firmware asset

Production curve02 is extracted byte-for-byte into `m9/m9_curve02_firmware.bin` and loaded through `M9TargetFirmwareCalibration`. Production mode must not instantiate `M9R35Calibration`, whose historical mixed payload also contains Cobalt source-profile tables.

## 6. Production mode invariant

`renderNativeSourceProduction1P` must call the native prospective core with `bridgeProbeMode = 0`.

Modes 1/2/3 and encoded diagnostic modes are forensic experiments only and must never become the production call without an explicit architecture decision.

## 7. Portability invariant

The same target renderer must be usable after source normalization for every supported physical Bayer sensor. Portability work may add CFA/phase, black-level, shading, metadata or source-transform handling. It may not add a lens-specific M9 HSM/look.

## 8. CI enforcement

The COBALTROLEPURGE1A verifier checks the production mode, identity-HSM path, per-sensor SOURCECAL2A boundary, target-only curve asset, CFA support and retained shared M9 stages. CI also hashes the native photographic core and multi-camera plumbing before/after the architecture patch so this correction cannot silently change demosaic, CFA authority, DNG authority, native color arithmetic or queue behavior.
