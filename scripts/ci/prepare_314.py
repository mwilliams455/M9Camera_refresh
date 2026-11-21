"""Reconstruct the accepted 3.14 Android sources outside the packaging checkout."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from prepare_source import fingerprint, inventory, TEST_PATH

REPO = Path(__file__).resolve().parents[2]
PATCHES = REPO / "patches"
MODELS = {
    "efficientdet-lite0.tflite": (
        "focusanimal1a",
        "https://storage.googleapis.com/download.tensorflow.org/models/tflite/task_library/object_detection/android/lite-model_efficientdet_lite0_detection_metadata_1.tflite",
    ),
    "rtm_animal_fp16.tflite": (
        "focusanimaleye1a",
        "https://huggingface.co/litert-community/RTMPose-Animal-AP10K-LiteRT/resolve/main/rtm_animal_fp16.tflite",
    ),
}
STAGES = (
    "focussubject1a", "focusanimal1a", "focusanimal1b", "focusanimal1c",
    "focusanimaleye1a", "focusanimaleye1b", "focuscontrol1a", "aftracking2a",
    "aftracking3a", "aftracking3b", "aftracking4a", "aftracking5a", "autoeye1a",
    "focusoverlay1a", "focusoverlay1b", "trackingdefault1a", "trackingrecovery1a",
)


def run_python(script, *args):
    subprocess.run([sys.executable, script, *args], check=True)


def install_models(source, reports):
    provenance = []
    for name, (stage, url) in MODELS.items():
        target = source / "app/src/main/assets" / name
        subprocess.run(["curl", "--fail", "--location", "--silent", "--show-error",
                        "--retry", "4", "--retry-all-errors", "--connect-timeout", "20",
                        "--max-time", "240", "--output", target, url], check=True)
        expected = (PATCHES / stage / "MODEL_SHA256.txt").read_text().split()[0]
        data = target.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected or data[4:8] != b"TFL3":
            raise ValueError(f"Unexpected model contents: {name}")
        provenance.append({"model": name, "bytes": len(data), "sha256": expected})
    (reports / "MODEL_PROVENANCE.json").write_text(json.dumps(provenance, indent=2) + "\n")


def apply_stages(source, reports):
    for stage in STAGES:
        if stage == "focusanimaleye1a":
            install_models(source, reports)
        script = "apply_live.py" if stage == "focussubject1a" else "apply.py"
        run_python(PATCHES / stage / script, source, "--report", reports / f"{stage}.json")
        if stage == "trackingdefault1a":
            run_python(PATCHES / stage / "host/verify_staged.py", source)


def apply_ci_fixture(source, reports):
    before = inventory(source)
    baseline = fingerprint(before)
    expected = (REPO / "scripts/ci/source-314.sha256").read_text().strip()
    if baseline != expected:
        raise ValueError(f"Unexpected 3.14 production source fingerprint: {baseline}")
    fixture = REPO / "scripts/ci/capture-test-fixture.patch"
    subprocess.run(["git", "apply", str(fixture)], cwd=source, check=True)
    after = inventory(source)
    changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
    if changed != [TEST_PATH]:
        raise ValueError(f"Unexpected CI fixture changes: {changed}")
    report = {"version": "3.14-trackingrecovery1a", "productionScopedSha256": baseline,
              "ciScopedSha256": fingerprint(after), "fixtureChanges": changed}
    (reports / "SOURCE_VERIFICATION.json").write_text(json.dumps(report, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    dest = parser.parse_args().destination.resolve()
    dest.mkdir(parents=True, exist_ok=False)
    if subprocess.run(["git", "-C", dest, "rev-parse", "--show-toplevel"],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        raise ValueError("Reconstruct outside the Git checkout")
    source = dest / "PhotonCamera_314"
    reports = dest / "verification"
    reports.mkdir()
    run_python(PATCHES / "diagindex1a/assemble.py", source)
    apply_stages(source, reports)
    apply_ci_fixture(source, reports)


if __name__ == "__main__":
    main()
