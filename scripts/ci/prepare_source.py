"""Reconstruct the pinned 2.88 source and apply the test-only upstream CI fix."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CHAIN = [
    "focustrack1a", "afcontinuity1a", "aflifecycle1a", "aftaphandover1a",
    "monoplanwait1a", "uisettings1a", "focuspoint1a", "monosavepipe1a",
    "monoplanwait1b", "monodiagexport1c", "monodiagview1d", "monoaeref1a",
    "monoaeref1b", "upstreamui1a", "upstreamui1b", "rawsize1a", "gallerypause1a",
]
TEST_PATH = "app/src/test/java/com/particlesdevs/photoncamera/capture/CaptureControllerTest.java"


def inventory(root):
    files = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for d in ["app/src", "circularbarlib/src"]
             for p in (root / d).rglob("*") if p.is_file()}
    for name in ["app/build.gradle", "circularbarlib/build.gradle"]:
        files[name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
    return files


def fingerprint(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def prepare(destination, verified_source=None):
    if destination.exists():
        raise ValueError("Use a fresh destination")
    destination.mkdir(parents=True)
    if verified_source:
        source = destination / "PhotonCamera_288"
        shutil.copytree(verified_source, source,
                        ignore=shutil.ignore_patterns(".git", ".gradle", ".cxx", "build"))
    else:
        previous = None
        for version, bundle in enumerate(CHAIN, 272):
            source = destination / f"PhotonCamera_{version}"
            folder = REPO / "patches" / bundle
            command = [sys.executable, str(folder / "assemble.py"), str(source)]
            if previous:
                command += ["--parent", str(previous)]
            subprocess.run(command, check=True)
            if previous:
                subprocess.run([sys.executable, str(folder / "verify_source.py"),
                                str(previous), str(source)], check=True)
                shutil.rmtree(previous)
            previous = source

    before = inventory(source)
    baseline = json.loads((REPO / "patches/gallerypause1a/manifest.json").read_text())
    if fingerprint(before) != baseline["candidateScopedSha256"]:
        raise ValueError("Source is not the verified 2.88 baseline")
    subprocess.run(["git", "apply", "--check", str(HERE / "capture-test-fixture.patch")],
                   cwd=source, check=True)
    subprocess.run(["git", "apply", str(HERE / "capture-test-fixture.patch")], cwd=source, check=True)
    after = inventory(source)
    changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
    if changed != [TEST_PATH]:
        raise ValueError(f"CI overlay changed unexpected files: {changed}")
    report = {"status": "PASS", "appVersion": "2.88-gallerypause1a",
              "baselineScopedSha256": fingerprint(before), "ciScopedSha256": fingerprint(after),
              "changedFiles": changed, "productionSourceUnchanged": True}
    (destination / "SOURCE_VERIFICATION.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--verified-source", type=Path,
                        help="Reuse a local 2.88 tree; its fingerprint is checked before applying the fixture")
    args = parser.parse_args()
    prepare(args.destination.resolve(), args.verified_source)
