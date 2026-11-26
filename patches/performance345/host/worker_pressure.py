"""Exercise the production RAW16 entry point with scratch space for zero to four workers."""
from pathlib import Path
import re
import subprocess
import sys

source, objects = (Path(v).resolve() for v in sys.argv[1:])
here = Path(__file__).resolve().parent
binary = objects / 'memory_probe'
native = source / 'app/src/main/cpp/m9dngnoise'
objs = [objects / ('native_parity_' + lib + '.o') for lib in
        ('parent_adapter', 'parent_shaded', 'cand_adapter', 'cand_shaded')]
subprocess.run(['g++','-O2','-std=c++17','-pthread','-I',str(native),str(here/'memory_probe.cpp'),
                *map(str,objs),'-o',str(binary)],check=True)
def run(label, limit):
    line = subprocess.check_output([binary,label,str(limit)],text=True).strip()
    print(line)
    return re.search(r'status=(-?\d+) scratch double arrays peak=(\d+).*changed=(\d+) digest=(\w+)',line).groups()
status, peak, changed, digest = run('parent',5)
assert status=='0' and peak=='5' and int(changed)>0
for workers in (1,2,3,4,8):
    status, peak, count, actual = run('candidate',workers*5)
    assert status=='0' and (count,actual)==(changed,digest) and int(peak)<=5*min(workers,4)
assert run('candidate',0)[0]=='-5'
