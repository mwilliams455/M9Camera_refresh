"""Require rebuilt parent executable/data sections to match the accepted APK."""
from pathlib import Path
import hashlib
import io
import json
import sys
import zipfile
from elftools.elf.elffile import ELFFile

control, native_dir, output = (Path(x).resolve() for x in sys.argv[1:])
output.mkdir(parents=True, exist_ok=True)
sha = lambda data: hashlib.sha256(data).hexdigest()
assert sha(control.read_bytes()) == 'e305c046a425ab79e89727045c53e414b5578873d333cbfe91dc5be33ac5c45c'
results = []
with zipfile.ZipFile(control) as archive:
    for abi in ['arm64-v8a','armeabi-v7a']:
        old = ELFFile(io.BytesIO(archive.read('lib/'+abi+'/libm9color.so')))
        new = ELFFile(io.BytesIO((native_dir/abi/'libm9color.so').read_bytes()))
        sections = {}
        for name in ['.text','.rodata','.data.rel.ro']:
            a,b = old.get_section_by_name(name),new.get_section_by_name(name)
            assert a is not None and b is not None
            sections[name] = {'acceptedSha256':sha(a.data()),'rebuiltSha256':sha(b.data()),
                              'exact':a.data()==b.data()}
        results.append({'abi':abi,'sections':sections})
report = {'status':'PASS' if all(s['exact'] for r in results for s in r['sections'].values()) else 'BLOCKED',
          'libraries':results,'comparison':'Accepted 2.95 versus freshly rebuilt unchanged parent'}
(output/'NATIVE_BASELINE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
assert report['status']=='PASS', 'Parent rebuild differs: inspect provenance before delivering new native code'
