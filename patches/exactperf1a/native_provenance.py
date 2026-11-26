#!/usr/bin/env python3
"""EXACTPERF1A native provenance gate.

Usage: native_provenance.py PINNED_BASELINE_DIR PARENT_LIB_DIR CANDIDATE_APK OUTPUT_DIR

PINNED_BASELINE_DIR  patches/trackingrecovery1a/baseline (accepted signed 3.13 libraries)
PARENT_LIB_DIR       <abi>/*.so rebuilt from the unchanged 3.42 parent at the same path
CANDIDATE_APK        Gradle APK built from 3.43 at that same path

Hard gates (status BLOCKED otherwise):
  1. The unchanged parent rebuild reproduces the accepted libm9color, libm9dngnoise and
     libdngCreator code/data sections exactly. Delivered candidates therefore differ from
     the shipped libraries only by the 3.43 source changes.
  2. Every other library built from source is section-identical between the parent and
     candidate builds, so the non-debuggable app flag did not alter any native build.
  3. The three changed libraries really changed (.text differs from the parent).
"""
from pathlib import Path
import hashlib
import json
import struct
import sys
import tarfile
import zipfile

ABIS = ("arm64-v8a", "armeabi-v7a")
CHANGED = ("libm9color.so", "libm9dngnoise.so", "libdngCreator.so")
SECTIONS = (".text", ".rodata", ".data.rel.ro", ".data")
sha = lambda data: hashlib.sha256(data).hexdigest()


def sections(blob):
    """Return {name: bytes} for allocated PROGBITS sections of a little-endian ELF."""
    if blob[:4] != b"\x7fELF" or blob[5] != 1:
        raise ValueError("Little-endian ELF required")
    is64 = blob[4] == 2
    if is64:
        shoff, = struct.unpack_from("<Q", blob, 0x28)
        shentsize, shnum, shstrndx = struct.unpack_from("<HHH", blob, 0x3A)
    else:
        shoff, = struct.unpack_from("<I", blob, 0x20)
        shentsize, shnum, shstrndx = struct.unpack_from("<HHH", blob, 0x2E)
    headers = []
    for i in range(shnum):
        base = shoff + i * shentsize
        if is64:
            name, kind, _flags, _addr, offset, size = struct.unpack_from("<IIQQQQ", blob, base)
        else:
            name, kind, _flags, _addr, offset, size = struct.unpack_from("<IIIIII", blob, base)
        headers.append((name, kind, offset, size))
    strtab = headers[shstrndx]
    names = blob[strtab[2]:strtab[2] + strtab[3]]
    out = {}
    for name, kind, offset, size in headers:
        label = names[name:names.index(b"\0", name)].decode()
        if kind == 8:  # SHT_NOBITS
            continue
        out[label] = blob[offset:offset + size]
    return out


def compare(a, b):
    sa, sb = sections(a), sections(b)
    result = {}
    for name in SECTIONS:
        if name not in sa and name not in sb:
            continue
        x, y = sa.get(name), sb.get(name)
        result[name] = {"exact": x == y, "aSha256": sha(x) if x is not None else None,
                        "bSha256": sha(y) if y is not None else None}
    return result


def exact(result):
    return all(entry["exact"] for entry in result.values())


def main():
    pinned_dir, parent_dir, candidate_apk, out = (Path(a).resolve() for a in sys.argv[1:5])
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((pinned_dir / "sha256.json").read_text())
    pinned = {}
    for abi in ABIS:
        with tarfile.open(pinned_dir / f"{abi}.tar.xz", "r:xz") as archive:
            for member in archive:
                payload = archive.extractfile(member).read()
                assert sha(payload) == manifest[member.name], member.name
                pinned[member.name] = payload
    parent = {f"lib/{abi}/{p.name}": p.read_bytes()
              for abi in ABIS for p in sorted((parent_dir / abi).glob("*.so"))}
    with zipfile.ZipFile(candidate_apk) as apk:
        candidate = {n: apk.read(n) for n in apk.namelist() if n.startswith("lib/") and n.endswith(".so")}

    problems = []
    parent_vs_pinned = {}
    for name in sorted(set(parent) & set(pinned)):
        result = compare(parent[name], pinned[name])
        parent_vs_pinned[name] = {"exact": exact(result), "sections": result}
    for abi in ABIS:
        for lib in CHANGED:
            name = f"lib/{abi}/{lib}"
            if name not in parent_vs_pinned:
                problems.append(f"parent rebuild missing {name}")
            elif not parent_vs_pinned[name]["exact"]:
                problems.append(f"parent rebuild does not reproduce accepted {name}")

    candidate_vs_parent = {}
    for name in sorted(set(candidate) & set(parent)):
        result = compare(parent[name], candidate[name])
        changed = Path(name).name in CHANGED
        candidate_vs_parent[name] = {"expectedChange": changed, "exact": exact(result), "sections": result}
        if changed and result.get(".text", {}).get("exact", True):
            problems.append(f"{name} .text did not change")
        if not changed and not exact(result):
            problems.append(f"unchanged library differs between parent and candidate: {name}")
    for abi in ABIS:
        for lib in CHANGED:
            if f"lib/{abi}/{lib}" not in candidate:
                problems.append(f"candidate APK missing lib/{abi}/{lib}")

    report = {
        "status": "BLOCKED" if problems else "PASS",
        "revision": "M9EXACTPERF1A_NATIVE_PROVENANCE",
        "changedLibraries": list(CHANGED),
        "comparedSections": list(SECTIONS),
        "problems": problems,
        "parentRebuildVsAccepted313": parent_vs_pinned,
        "candidateVsParentSamePath": candidate_vs_parent,
        "rebuiltCandidateSha256": {n: sha(candidate[n]) for n in sorted(candidate)
                                   if Path(n).name in CHANGED},
    }
    (out / "NATIVE_PROVENANCE.json").write_text(json.dumps(report, indent=2) + "\n")
    summary = {k: report[k] for k in ("status", "problems", "rebuiltCandidateSha256")}
    summary["parentVsAccepted"] = {n: v["exact"] for n, v in parent_vs_pinned.items()}
    summary["candidateVsParent"] = {n: v["exact"] for n, v in candidate_vs_parent.items()}
    print(json.dumps(summary, indent=2))
    if problems:
        sys.exit("Native provenance gate blocked: " + "; ".join(problems))


if __name__ == "__main__":
    main()
