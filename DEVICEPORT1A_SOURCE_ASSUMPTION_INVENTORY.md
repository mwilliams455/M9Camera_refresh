# DEVICEPORT1A source-assumption inventory

Date: 2026-09-15
Branch: `research/deviceport1a-cfaabstract1a`
Photographic base: `14da08d2ab32d8c295c4a96562ebc6c793486e75` (`SHARPSOURCE1C / RBANCHOR1A`)

This inventory is deliberately descriptive. It does not authorize a photographic change. The portability sequence remains probe -> source-grid proof -> 15U zero-regression -> 17U bring-up.

## Confirmed source assumptions / seams

### 1. Frozen renderer CFA gate

The validated renderer currently rejects `params.cfaPattern != 0`. This is a useful fail-closed safety gate for DEVICEPORT1A and must remain active in the first probe APK.

Owner after generalization: central source descriptor / CFA resolver.

### 2. Active native MHC demosaic is RGGB-specific

`DEMOSAICMHC1A` exposes `demosaicMhcRggb` and classifies native sites using local X/Y parity:

- even/even = R
- odd/odd = B
- green-site R/B interpolation orientation is also selected from local parity

The recovered MHC coefficients are not the portability problem; native-site classification is.

Owner after generalization: `M9CfaResolver` / equivalent compact native CFA descriptor passed to MHC.

### 3. Native black-level normalization is local-phase-sensitive

The native raw normalization path derives a 2x2 plane index from local coordinates:

`plane = ((y & 1) << 1) | (x & 1)`

and indexes the four black values with that plane. Therefore black subtraction is only correct when the black-level pattern and local RAW origin/phase refer to the same grid.

Owner after generalization: same verified source-grid origin/phase model used by CFA classification. Do not fix demosaic while leaving black-plane selection on a contradictory phase model.

### 4. Frozen RAW white/headroom constant

The validated renderer still contains `RAW_MAX = 16383`. DEVICEPORT1A records both Photon dynamic white level and Camera2 `SENSOR_INFO_WHITE_LEVEL`; the probe does not change normalization yet.

Owner after generalization: source descriptor / normalized RAW-domain policy, followed by 15U zero-regression.

### 5. Dormant OpenCV control is RGGB-specific

The dormant forensic/control path retains `Imgproc.COLOR_BayerRG2BGR_EA`. It is not the promoted production MHC path, but must not be mistaken for a generic Bayer control during portability testing.

Owner after generalization: either descriptor-selected OpenCV conversion code for control-only testing or keep it explicitly labelled RGGB-only and unreachable for unsupported patterns.

### 6. RAW geometry versus fixed M9 output geometry

The project intentionally targets a 4096x3072 M9-style output, but source RAW dimensions must be runtime-derived. Any input validation/copy path that conflates source dimensions with the 4096x3072 output contract must be separated.

Owner after generalization: source descriptor for input geometry; M9 renderer/output policy for output geometry.

### 7. Legacy physical-camera gating

Historical native A/B infrastructure contains a Xiaomi-15U-era `MAIN physical ID 2` seam. Physical camera IDs are Android/vendor-assigned identifiers and must not become the portable sensor identity contract.

Owner after generalization: runtime camera discovery + stable internal sensor key derived from characteristics; optional sensor override only when metadata is insufficient.

### 8. Source colour matrices are sensor-specific

Existing SOURCECAL work already treats Camera2/DNG sensor matrices as source calibration. DEVICEPORT1A logs calibration transforms, colour transforms, forward matrices, reference illuminants and capture neutral. The M9 target can remain common; source-to-working calibration cannot be copied blindly from 15U to 17U.

Owner after generalization: source descriptor / source calibration layer.

### 9. Lens shading is sensor+lens specific

DEVICEPORT1A records `SENSOR_INFO_LENS_SHADING_APPLIED`, requested/result map mode, actual capture map availability and map rows/columns. It intentionally does not infer a map size from a nonexistent static key and does not reuse a 15U falloff model.

Owner after generalization: source normalization/shading stage, applied exactly once.

### 10. RAW-grid origin remains unproven in DEVICEPORT1A

The first probe deliberately writes `rawOriginX=0`, `rawOriginY=0`, `rawOriginProven=false`. It does **not** shift CFA phase using the active-array top-left. We need evidence for the coordinate origin of the actual RAW buffer handed to the renderer before applying an origin correction.

Owner after generalization: capture/copy boundary that can prove how Photon rebases (or does not rebase) the RAW buffer.

## Frozen during DEVICEPORT1A

- M9 curve/tone mapping
- TC20 / exposure policy
- H25/HSM
- saturation banks
- Standard/mode-4 sharpness policy
- MHC coefficients
- Leica green arithmetic
- Leica R/B arithmetic
- JPEG quality
- no-HDR policy

## Gate to CFAABSTRACT1B

Do not route MHC through generic CFA handling until:

1. DEVICEPORT1A probe APK compiles and installs.
2. One Xiaomi 17 Ultra main-camera probe sidecar is captured.
3. Reported CFA, RAW geometry, black/white levels and shading state are internally coherent.
4. Local RAW origin/phase is proven or explicitly bounded by a controlled same-RAW test.
5. Existing Xiaomi 15 Ultra RAW resolves to the historical RGGB phase.

Then CFAABSTRACT1B should change **site classification only**, followed by decoded-pixel/stage-hash zero-regression on preserved Xiaomi 15 Ultra RAWs.
