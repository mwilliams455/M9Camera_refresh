from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
P = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
s = P.read_text()


def one(old: str, new: str, label: str) -> None:
    global s
    n = s.count(old)
    if n != 1:
        raise SystemExit(f'{label}: expected exactly one match, found {n}')
    s = s.replace(old, new, 1)


# TONEBANK1A is based on the current TARGETDIRECT1A / M9SENSORTARGET1A parent.
# The historical TONEAUTH1B runtime fix forced bridge mode 4 because that branch
# still used TARGETINPUTADAPTER1A. Current production intentionally removed that
# historical 15U target-input adapter and renders the recovered M9 sensor target
# directly from the common XYZ D50 scene, so every diagnostic variant must stay
# on exact production bridge mode 0.
required = [
    'int[] bridgeProbeModes = {0, 0, 0};',
    'm9cam.tonebound.v1a.050ev',
    'M9SENSORTARGET1A',
    '_M9_SOURCEFULLNORM1A_GAINLOCK.jpg',
    'SATURATION_BANK == 2 ? 9',
]
for marker in required:
    if marker not in s:
        raise SystemExit('TONEBANK1A TARGETDIRECT prerequisite missing: ' + marker)
if 'int[] bridgeProbeModes = {4, 4, 4};' in s:
    raise SystemExit('TONEBANK1A refuses historical TARGETINPUT mode-4 tone bank')

# Keep the useful runtime-safety part of TONEAUTH1B: diagnostics live in the
# normal primary sidecar rather than direct writes into scoped DCIM storage.
one(
'''                            Path variantJsonPath = Paths.get(
                                    FileManager.sDCIM_CAMERA.getAbsolutePath(),
                                    stem + suffix + ".json");
''',
'''                            // TONEBANK1A/TARGETDIRECTFIX: per-variant diagnostics are
                            // embedded in the normal primary sidecar. Do not write directly
                            // into DCIM/Camera because scoped storage can reject raw Files.write.
''',
'remove direct variant json path')

# Disable unrelated HSM audit work inside the tone-isolation variants. HSM itself
# remains the current identity target stage; this only suppresses diagnostic work.
one(
'''                                        normalizeShadingLumaOutsideMedian1A, shadingLumaTargetOutsideMedianEv1A,
                                        hsmValueStrength, true);''',
'''                                        normalizeShadingLumaOutsideMedian1A, shadingLumaTargetOutsideMedianEv1A,
                                        hsmValueStrength, false);''',
'disable unrelated HSM audits')

old = '''                                variantDiag.put("outputJsonPath", variantJsonPath.toString());'''
n = s.count(old)
if n != 2:
    raise SystemExit(f'output json telemetry: expected 2 matches, found {n}')
s = s.replace(old,
'''                                variantDiag.put("outputJsonPath", JSONObject.NULL);
                                variantDiag.put("outputJsonEmbeddedInPrimarySidecar", true);
                                variantDiag.put("toneBankFullSourceReference", "FULL_LIVE_REMAINING_CAMERA2_MAP_FIXED_PRIMARY_GAIN");''')

one(
'''                            try {
                                Files.write(variantJsonPath,
                                        variantDiag.toString(2).getBytes(StandardCharsets.UTF_8));
                                variantDiag.put("jsonPersisted", true);
                            } catch (Throwable jsonError) {
                                variantDiag.put("jsonPersisted", false);
                                variantDiag.put("jsonError", jsonError.toString());
                            }
''',
'''                            variantDiag.put("jsonPersisted", false);
                            variantDiag.put("jsonPersistencePolicy", "embedded_primary_sidecar_only");
''',
'remove scoped storage direct write')

P.write_text(s)
print('M9 TONEBANK1A TARGETDIRECTFIX applied')
print('A/B/C bridge modes remain exact production TARGETDIRECT mode 0')
print('A=full TC20, B=half TC20 EV authority, C=zero TC20 authority')
print('primary JPEG/capture/TONEBOUND050/SAT2/curve02 unchanged')
print('full-source gain-lock provenance stamped in tone-bank diagnostics')
print('per-variant diagnostics embedded in primary sidecar only')
