#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
TTL = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9TtlSidecar1A.java'
WRITER = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java'
RENDERER = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
SPOOL = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java'

checks = []
def ck(name, cond):
    checks.append((name, bool(cond)))

ck('TTL source exists', TTL.exists())
ck('writer exists', WRITER.exists())
ck('renderer exists', RENDERER.exists())
ck('native cpp exists', CPP.exists())
ck('spool exists', SPOOL.exists())

ttl = TTL.read_text() if TTL.exists() else ''
writer = WRITER.read_text() if WRITER.exists() else ''
renderer = RENDERER.read_text() if RENDERER.exists() else ''
spool = SPOOL.read_text() if SPOOL.exists() else ''

ck('TTL schema', 'm9cam.ttl.v1a.reconstructed' in ttl)
ck('TTL suffix', '_M9_TTL1A.json' in ttl)
ck('TTL role', 'm9_ttl1a_reconstructed_meter' in ttl)
ck('diagnostic only', 'out.put("diagnosticOnly", true)' in ttl)
ck('no capture mutation telemetry', 'out.put("captureExposureMutation", false)' in ttl)
ck('no renderer mutation telemetry', 'out.put("rendererMutation", false)' in ttl)
ck('no TC20 mutation telemetry', 'out.put("tc20Mutation", false)' in ttl)
ck('physical M9 TTL unavailable explicit', 'out.put("physicalM9TtlReadingAvailable", false)' in ttl)
ck('proxy provenance explicit', 'reconstructed_virtual_ttl_proxy_not_physical_M9_photodiode' in ttl)
ck('preview proxy source explicit', 'existing_Xiaomi_preview_luma_snapshot' in ttl)
ck('M9 reduced relation recorded', 'Tv = Bv + Sv - 5 - Override' in ttl)
ck('M9 equivalent auto ISO relation recorded', 'Sv = 5 + Tv + Override - Bv' in ttl)
ck('Auto ISO 160 uncertainty explicit', 'believedAutoIsoStartIso' in ttl and 'believed_not_fully_proven_as_complete_live_threshold_policy' in ttl)
ck('lens threshold unresolved explicit', 'lensDependentTvThresholdSolved", false' in ttl)
ck('RAW excluded from TTL decision', 'usedByTtlDecision", false' in ttl)
ck('same-stem RAW audit policy', 'join_same_stem_M9_PRIMARY_after_render' in ttl)
ck('uses existing sidecar spool', 'M9DiagnosticBurstSpool.stage(sidecar, frozen, ROLE)' in ttl)
ck('uses spool schema', 'M9DiagnosticBurstSpool.SCHEMA' in ttl)
ck('writer evaluates virtual BV once into variable', 'JSONObject m9VirtualBv1A = M9VirtualBv1A.evaluate(root);' in writer)
ck('writer preserves virtual BV publication', 'root.put("m9VirtualBv", m9VirtualBv1A);' in writer)
ck('writer stages TTL', 'M9TtlSidecar1A.stage(dngPath, root, m9VirtualBv1A)' in writer)
ck('writer records TTL diagnostic marker', 'root.put("m9Ttl1A"' in writer)
ck('sidecar spool v1 privatebundle1b', 'm9cam.sidecarspool.v1.privatebundle1b' in spool)

# Current frozen photographic baseline must still be present.
ck('tone bound baseline retained', 'm9cam.tonebound.v1a.050ev' in renderer)
ck('true SAT2 bank maps to native mode9', 'SATURATION_BANK == 2 ? 9' in renderer)
ck('SAT2 standard telemetry retained', 'SAT2_STANDARD_M04_M05' in renderer)
ck('curve02 retained', 'curve02 normal-ISO sRGB Standard' in renderer)
ck('exact BT601 retained', 'exact BT601 4:2:2' in renderer)
ck('TG1 retained', 'M9Modern TG1' in renderer)

# Fail if the new TTL class contains obvious active mutation calls or renderer hooks.
for bad in [
    r'CaptureRequest\.Builder',
    r'set\s*\(\s*CaptureRequest\.SENSOR_',
    r'M9R35Renderer\.',
    r'meter\.gain\s*=',
    r'effectiveRenderGain\s*=',
]:
    ck('no TTL active mutation: ' + bad, re.search(bad, ttl) is None)

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(('PASS ' if ok else 'FAIL ') + name)
if failed:
    raise SystemExit('M9TTL1A verify failed: ' + ', '.join(failed))
print('M9TTL1A VERIFY PASS')
print('TTL is sidecar-only; capture exposure and frozen M9 renderer remain untouched')
