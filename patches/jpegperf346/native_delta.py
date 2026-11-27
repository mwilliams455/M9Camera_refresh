#!/usr/bin/env python3
"""JPEGPERF346 native delta gate.

Usage: native_delta.py PARENT345_LIB_DIR CANDIDATE_APK OUTPUT_DIR

PARENT345_LIB_DIR holds <abi>/*.so rebuilt from the released 3.45 source at the accepted
build path. Every library in the 3.46 APK must be section-identical to that rebuild except
libm9color.so, the only library whose sources 3.46 changes; its .text must differ.
The exactperf1a provenance gate separately ties both builds back to the accepted 3.13 binaries.
"""
from pathlib import Path
import json
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'exactperf1a'))
from native_provenance import ABIS, compare, exact, sha  # noqa: E402

CHANGED = ('libm9color.so',)


def main():
    parent_dir, candidate_apk, out = (Path(a).resolve() for a in sys.argv[1:4])
    base, head = sys.argv[4:6] if len(sys.argv) == 6 else ('345', '346')
    parent_version, candidate_version = base[0] + '.' + base[1:], head[0] + '.' + head[1:]
    out.mkdir(parents=True, exist_ok=True)
    parent = {f'lib/{abi}/{p.name}': p.read_bytes() for abi in ABIS for p in sorted((parent_dir / abi).glob('*.so'))}
    with zipfile.ZipFile(candidate_apk) as apk:
        candidate = {n: apk.read(n) for n in apk.namelist() if n.startswith('lib/') and n.endswith('.so')}
    problems, rows = [], {}
    if not parent:
        problems.append(f'no {parent_version} parent libraries')
    for name in sorted(parent):
        if name not in candidate:
            problems.append(f'candidate APK missing {name}')
            continue
        result = compare(parent[name], candidate[name])
        changed = Path(name).name in CHANGED
        rows[name] = {'expectedChange': changed, 'exact': exact(result), 'sections': result}
        if changed and result.get('.text', {}).get('exact', True):
            problems.append(f'{name} .text did not change from {parent_version}')
        if not changed and not exact(result):
            problems.append(f'library changed since {parent_version} without a source change: {name}')
    for abi in ABIS:
        for lib in CHANGED:
            if f'lib/{abi}/{lib}' not in parent:
                problems.append(f'{parent_version} parent rebuild missing lib/{abi}/{lib}')
    report = {'status': 'BLOCKED' if problems else 'PASS', 'revision': f'M9JPEGPERF{head}_NATIVE_DELTA',
              f'changedSince{base}': list(CHANGED), 'problems': problems, f'candidateVs{base}SamePath': rows,
              'candidateSha256': {n: sha(candidate[n]) for n in sorted(rows)}}
    (out / f'NATIVE_DELTA_{head}.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'problems': problems,
                      'exact': {n: v['exact'] for n, v in rows.items()}}, indent=2))
    if problems:
        sys.exit(f'{candidate_version} native delta gate blocked: ' + '; '.join(problems))


if __name__ == '__main__':
    main()
