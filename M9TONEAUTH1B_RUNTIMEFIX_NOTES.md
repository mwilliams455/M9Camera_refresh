# M9TONEAUTH1B runtime fix

Runtime failure in TONEAUTH1A was diagnostic-only.

Root cause:
- A/B/C used `bridgeProbeMode=0`, while the current production primary path uses mode 4 (`TARGETINPUTADAPTER1A` + identity 90x30 HSM).
- Mode 0 creates a 2x2 identity HSM (12 doubles).
- The diagnostic call also enabled the unrelated skin/HSM stage audits; one indexed the 12-entry mode-0 HSM using full-HSM coordinates, producing `ArrayIndexOutOfBoundsException: length=12; index=3246`.
- Variant JSON used raw `Files.write` under DCIM/Camera and hit scoped-storage EACCES. This did not cause the render crash but produced misleading secondary failures.

Fix:
- A/B/C use bridge mode 4, matching primary production.
- SATURATION_BANK=2 still independently selects native saturation mode 9 -> M04/M05.
- Disable unrelated skin/HSM stage audits for TONEAUTH variants.
- Embed variant diagnostics in the normal primary sidecar; do not directly write JSON under DCIM/Camera.
- Primary JPEG path, capture exposure, TC20 primary gain formula, native color C++, curve02 and SAT2 selector remain frozen.
