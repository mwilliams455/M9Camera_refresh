# M9Cam 2.27 CONTRASTMENU1A

Child of accepted 2.26 (`db5538a649cba8d61feb453738053dac8d98a6c1`). Adds Leica M9 contrast beside saturation: Low, Medium low, Standard (default), Medium high, High.

Uses exact 1.216 normal-ISO sRGB curves 00–04, verified against decoded PROCESS_LUTS RAM at offset 3320 and the existing curve02. No generic contrast multiplier, Pull80 policy, HDR or sensor restriction.

The setting is global across lenses and frozen at RAW enqueue with saturation and output selection. Native JPEG receives the selected curve via the existing context API; no native binary changes. Preview loads a five-row texture and selects the curve each draw. The DNG profile uses the actual contrast index stored in that capture's renderer JSON, never current settings. Original-sensor RAW remains untouched.

Standard retains the accepted curve and existing equations. Existing preview brightness/ISP differences are not resolved by this feature. Phone validation is required.

Verification: all 25 contrast/saturation combinations through real GLES, native kernel and DNG profile sampler; Standard full profile regression; inherited source hashes; existing capture parameters, queue, RAW storage and Android regression suites. Queue tests change contrast while jobs are pending.

Build: `.github/workflows/build-m9cam-contrastmenu1a.yml`. Packaging preserves all 23 accepted native libraries, all inherited M9 assets and the existing signing certificate. Only the new 10,240-byte firmware bank is added.
