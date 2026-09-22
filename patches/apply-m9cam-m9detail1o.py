#!/usr/bin/env python3
"""Apply M9DETAIL1O COMMON50 strictly on top of exact DETAIL1H."""
from pathlib import Path
import hashlib,json,shutil,sys
root=Path(sys.argv[1]).resolve()
here=Path(__file__).resolve().parent
repo=here.parent
h=json.loads((here/'m9cam-m9detail1h-manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

before={
 'app/src/main/cpp/m9detail1h.cpp':h['added']['app/src/main/cpp/m9detail1h.cpp']['sha256'],
 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9Detail1H.java':h['added']['app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9Detail1H.java']['sha256'],
 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java':h['changed']['app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java']['after'],
}
for rel,want in before.items():
    p=root/rel
    if not p.exists() or sha(p)!=want: raise SystemExit('DETAIL1O baseline mismatch: '+rel)

payloads={
 'app/src/main/cpp/m9detail1h.cpp':repo/'patches/m9detail1o/m9detail1h.cpp',
 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9Detail1H.java':repo/'patches/m9detail1o/M9Detail1H.java',
}
for rel,src in payloads.items():
    shutil.copyfile(src,root/rel)

p=root/'app/build.gradle';s=p.read_text()
old="versionName '1.61-m9detail1h-tg1pair1a'"
new="versionName '1.61-m9detail1o-common50'"
if s.count(old)!=1: raise SystemExit('DETAIL1O version anchor mismatch')
p.write_text(s.replace(old,new))

p=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java';s=p.read_text()
repl={
 'd.put("detail1H", detail1HJson);':'d.put("detail1H", detail1HJson);\n                d.put("detail1O", detail1HJson);',
 '"DETAIL1H_corrected_RB_guarded_noise_candidate"':'"DETAIL1O_common50_RB_guarded_noise_candidate"',
 '"DETAIL1H_SAT2_NATIVE_GUARD"':'"DETAIL1O_COMMON50_SAT2_NATIVE_GUARD"',
 '"DETAIL1D_RB_DETAIL1F_guard_green_Sharp_fixed"':'"DETAIL1O_common50_RB_DETAIL1F_guard_green_Sharp_fixed"',
}
for a,b in repl.items():
    if s.count(a)!=1: raise SystemExit('DETAIL1O renderer anchor mismatch: '+a)
    s=s.replace(a,b)
p.write_text(s)

# Semantic + payload identity verification. Output hashes are recorded for CI evidence.
checks={
 'cpp_payload_exact':sha(root/'app/src/main/cpp/m9detail1h.cpp')==sha(payloads['app/src/main/cpp/m9detail1h.cpp']),
 'java_payload_exact':sha(root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9Detail1H.java')==sha(payloads['app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9Detail1H.java']),
 'short_version':"1.61-m9detail1o-common50" in (root/'app/build.gradle').read_text(),
 'tungsten_successor_preserved':(root/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewSourceContinuity1A.java').exists() and "M9TUNGSTENCONT1A" in (root/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewSourceContinuity1A.java').read_text(),
 'renderer_detail1o': 'd.put("detail1O", detail1HJson);' in p.read_text(),
}
if not all(checks.values()): raise SystemExit('DETAIL1O verification failed: '+repr(checks))
print('M9DETAIL1O COMMON50 APPLIED')
for rel in [*payloads,'app/build.gradle','app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java']:
    print(rel,sha(root/rel))
