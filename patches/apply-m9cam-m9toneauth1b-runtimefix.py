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


one(
'''                        // Mode 0 is essential: encoded 50/51/52 are legacy saturation diagnostics
                        // and would bypass the production SAT2 selector.
''',
'''                        // M9TONEAUTH1B runtime fix: use the exact production bridge mode.
                        // Primary rendering enters mode 4 for TARGETINPUTADAPTER1A + identity HSM;
                        // SATURATION_BANK=2 independently selects native mode 9 -> SAT2 M04/M05.
''',
'correct mode comment')

one(
'''                        int[] bridgeProbeModes = {0, 0, 0};''',
'''                        int[] bridgeProbeModes = {4, 4, 4};''',
'production bridge mode')

one(
'''                            Path variantJsonPath = Paths.get(
                                    FileManager.sDCIM_CAMERA.getAbsolutePath(),
                                    stem + suffix + ".json");
''',
'''                            // Per-variant diagnostics are embedded in the normal primary sidecar.
                            // Do not write directly into DCIM/Camera: scoped storage can reject that
                            // raw Files.write path even when ImageSaver can publish the JPEG.
''',
'remove direct diagnostic json path')

one(
'''                                        normalizeShadingLumaOutsideMedian1A, shadingLumaTargetOutsideMedianEv1A,
                                        hsmValueStrength, true);''',
'''                                        normalizeShadingLumaOutsideMedian1A, shadingLumaTargetOutsideMedianEv1A,
                                        hsmValueStrength, false);''',
'disable unrelated HSM audits')

# There are two outputJsonPath writes: success and isolated-failure telemetry.
old = '''                                variantDiag.put("outputJsonPath", variantJsonPath.toString());'''
n = s.count(old)
if n != 2:
    raise SystemExit(f'output json telemetry: expected 2 matches, found {n}')
s = s.replace(old,
'''                                variantDiag.put("outputJsonPath", JSONObject.NULL);
                                variantDiag.put("outputJsonEmbeddedInPrimarySidecar", true);''')

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
print('M9TONEAUTH1B runtime fix applied')
print('A/B/C now use exact production bridge mode 4')
print('unrelated skin/HSM audits disabled')
print('per-variant diagnostics embedded in primary sidecar only')
