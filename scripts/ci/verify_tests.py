"""Run or check the existing 183-test regression gate plus 22 RAW geometry tests."""
import argparse
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

SUITES = {
    "MonoReadinessDialogTest": 4,
    "MonoExposureReadinessTest": 27,
    "MonoReadinessExportTest": 3,
    "MonoPrimaryEvidenceTest": 7,
    "MonoDiagnosticPreferenceTest": 5,
    "StillCaptureLifecycleTest": 44,
    "MonoPlanObservationTest": 32,
    "ProfileCaptureTest": 6,
    "GalleryThumbnailThreadTest": 7,
    "RendererSwitchLifecycleTest": 5,
    "ExifHistogramRequestTest": 6,
    "RawSizeCompatibilityTest": 29,
    "GalleryPauseLifecycleTest": 5,
    "CaptureControllerTest": 3,
    "RawGeometryTest": 22,
}
PHONE_CASE = "phoneReportMissingAeModeAndStateUsesMeasuredExposureAndAppliesEvOnce"
# Gradle/Robolectric discovery emits an empty report for this unselected AF suite.
# It is not an additional selected suite and contributes no tests to the gate.
EMPTY_FIXTURE_REPORT = "com.particlesdevs.photoncamera.capture.AfContinuityTest"


def verify(directory):
    suites = [ET.parse(p).getroot() for p in sorted(directory.glob("TEST-*.xml"))]
    for suite in suites:
        if any(int(suite.attrib[k]) != 0 for k in ["failures", "errors", "skipped"]):
            raise ValueError(f"Failing or skipped tests in {suite.get('name')}")
        if any(c.find(k) is not None for c in suite.findall("testcase")
               for k in ["failure", "error", "skipped"]):
            raise ValueError(f"Failing or skipped testcase in {suite.get('name')}")
    empty = [s for s in suites if s.get("name") == EMPTY_FIXTURE_REPORT]
    if len(empty) > 1 or any(int(s.attrib["tests"]) != 0 or s.findall("testcase") for s in empty):
        raise ValueError("Unexpected tests in the unselected AF fixture report")
    suites = [s for s in suites if s.get("name") != EMPTY_FIXTURE_REPORT]
    by_name = {s.get("name", "").rsplit(".", 1)[-1]: s for s in suites}
    if set(by_name) != set(SUITES) or len(suites) != len(SUITES):
        raise ValueError(f"Expected all {len(SUITES)} suites exactly once; found {sorted(by_name)}")
    counts = {}
    for name, expected in SUITES.items():
        suite = by_name[name]
        cases = suite.findall("testcase")
        count = int(suite.attrib["tests"])
        if count != len(cases) or count != expected:
            raise ValueError(f"Unexpected test count in {name}: {count}")
        counts[name] = count
    if sum(counts.values()) < 205:
        raise ValueError("The 183 existing regressions and 22 geometry tests must all run")
    if not any(c.get("name") == PHONE_CASE for s in suites for c in s.findall("testcase")):
        raise ValueError("Missing regression for the user's mono AE metadata report")
    return {"status": "PASS", "tests": sum(counts.values()), "failures": 0,
            "errors": 0, "skipped": 0, "suites": counts}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    results = args.source / "app/build/test-results/testDebugUnitTest"
    if args.run:
        command = ["bash", "gradlew", ":app:assembleDebug", ":app:testDebugUnitTest"]
        for name in SUITES:
            command.extend(["--tests", "*" + name])
        # Disable incremental/build-cache reuse so CodeQL observes actual compilation.
        command.extend(["--no-daemon", "--max-workers=2", "--no-build-cache", "--rerun-tasks"])
        subprocess.run(command, cwd=args.source, check=True)
    report = verify(results)
    (args.source.parent / "TEST_VERIFICATION.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
