"""Recover/verify the WB arithmetic boundary before native green interpolation."""
from pathlib import Path
import argparse
import ctypes as C
import hashlib
import json
import subprocess
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from m9_sharpnessforensics1a import parse_ldr, read_overlay
from m9_sharpness_export_fulliso_header import FW_SHA, walk


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--firmware', type=Path, required=True)
    ap.add_argument('--objdump', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    fw = a.firmware.read_bytes()
    assert sha(fw) == FW_SHA
    assets = {p: data for p, _, data in walk(fw)}
    ldr = assets['BF561/bf1']
    assert sha(ldr) == '06abf2c4ef5e14beeadc033359d7fe4ae955c8a30b4ef26afa756afcf6d21870'
    temp = a.out / 'temporary.ldr'
    temp.write_bytes(ldr)
    _, blocks = parse_ldr(temp)
    temp.unlink()
    evidence = []
    for name, addr, size in [('Process_WB', 0xff6030d0, 510),
                             ('SetStructParameter', 0xfeb1d098, 292),
                             ('Run_gain_load', 0xff610000, 60),
                             ('Run_WB_call', 0xff6109de, 50)]:
        data = read_overlay(blocks, addr, size)
        binary = a.out / 'temporary.bin'
        binary.write_bytes(data)
        result = subprocess.check_output([str(a.objdump), '-D', '-b', 'binary', '-m', 'bfin',
                                          f'--adjust-vma={addr}', str(binary)], text=True)
        lines = []
        for line in result.splitlines():
            fields = line.split('\t')
            if len(fields) > 2:
                lines.append(fields[0] + ' ' + fields[2].split('/*')[0].rstrip())
        binary.unlink()
        dest = a.out / f'{name}_{addr:08x}.asm.txt'
        dest.write_text('\n'.join(lines) + '\n')
        evidence.append(dict(name=name, address=hex(addr), size=size, code_sha256=sha(data),
                             file=dest.name, text_sha256=sha(dest.read_bytes())))
    source = Path(__file__).with_suffix('.cpp').with_name('wb_boundary.cpp')
    so = a.out / 'wb_boundary.so'
    subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror', '-shared', '-fPIC',
                    str(source), '-o', str(so)], check=True)
    lib = C.CDLL(str(so.resolve()))
    lib.wb_boundary.argtypes = [C.c_void_p, C.c_void_p, C.c_int, C.c_void_p, C.c_int]
    lib.wb_boundary.restype = None
    z = np.repeat(np.arange(16384, dtype=np.uint16)[:, None], 4, axis=1)
    tuples = [(16384, 16384, 16384), (16384, 39200, 25500), (39200, 16384, 25500),
              (32768, 24576, 16384), (8192, 16384, 12000), (16384, 65535, 32768),
              (8192, 12000, 10000)]
    checks = []
    for gains in tuples:
        g = np.array(gains, dtype=np.uint16)
        for pedestal in (0, 64, 256):
            out = np.empty_like(z)
            lib.wb_boundary(z.ctypes.data, out.ctypes.data, len(z), g.ctypes.data, pedestal)
            identity = next((i for i, v in enumerate(gains) if v == 16384), -1)
            oracle = np.empty_like(z)
            for phase, ch in enumerate((0, 1, 1, 2)):
                if identity < 0:
                    oracle[:, phase] = 0
                elif ch == identity:
                    oracle[:, phase] = z[:, phase]
                else:
                    # Independent NumPy signed floor division, all legal inputs.
                    product = (z[:, phase].astype(np.int64) - pedestal) * int(g[ch])
                    assert product.min() >= -2**31 and product.max() < 2**31
                    oracle[:, phase] = np.clip(pedestal + product // 16384, 0, 16383)
            assert np.array_equal(out, oracle)
            checks.append(dict(gains=list(gains), pedestal=pedestal, selected_identity_group=identity,
                               samples_exact=int(z.size), maximum_output=int(out.max())))
    report = dict(schema='m9.wb_boundary.v1', firmware_sha256=sha(fw), ldr_sha256=sha(ldr),
                  disassembler=subprocess.check_output([str(a.objdump), '--version'], text=True).splitlines()[0],
                  evidence=evidence, scalar_source_sha256=sha(source.read_bytes()),
                  probe_sha256=sha(Path(__file__).read_bytes()), samples_exact=sum(r['samples_exact'] for r in checks),
                  checks=checks, clamp_interval=[0, 16383], unity_gain_q14=16384,
                  arithmetic='pedestal + floor((sample - pedestal) * gain_q14 / 16384), then clamp; selected unity phase group is bypassed',
                  gain_source='packet little-endian uint16 at +0x0f,+0x11,+0x13 -> context +0x230,+0x232,+0x234 -> Run local gain array',
                  gain_normalization_producer_recovered=False, phone_scale_mapping_validated=False,
                  blackfin_emulation_proven=False, android_implementation_changed=False,
                  note='Instruction-derived scalar arithmetic checked independently; no hardware/emulator trace or full WB equivalence claim.')
    (a.out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(samples_exact=report['samples_exact'], evidence_functions=len(evidence),
                         gain_normalization_producer_recovered=False), indent=2))


if __name__ == '__main__':
    main()
