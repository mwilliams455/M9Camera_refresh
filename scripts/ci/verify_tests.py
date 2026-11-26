"""Build the app and verify the selected Android regression suites from JUnit XML."""
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
    "FocusTrackingAfTest": 7,
    "FocusTrackingLifecycleTest": 3,
    "FocusPointLayoutTest": 4,
    "TouchFocusTest": 20,
    "TouchFocusHandoverTest": 36,
    "GalleryThumbnailThreadTest": 7,
    "RendererSwitchLifecycleTest": 5,
    "ExifHistogramRequestTest": 6,
    "RawSizeCompatibilityTest": 29,
    "GalleryPauseLifecycleTest": 5,
    "CaptureControllerTest": 3,
    "RawGeometryTest": 22,
    "ColorCorrectionTransformTest": 5,
    "CustomColorGuardTest": 28,
    "NoiseGuardTest": 22,
    "NoiseBoundaryTest": 9,
}
PHONE_CASE = "phoneReportMissingAeModeAndStateUsesMeasuredExposureAndAppliesEvOnce"
# Robolectric discovery can emit empty XML reports for these unselected suites.
EMPTY_FIXTURE_REPORTS = {
    "com.particlesdevs.photoncamera.capture.AfContinuityTest",
    "com.particlesdevs.photoncamera.ui.camera.views.M9LinearManualLifecycleTest",
}


def verify(directory):
    suites = [ET.parse(p).getroot() for p in sorted(directory.glob("TEST-*.xml"))]
    for suite in suites:
        if any(int(suite.attrib[k]) != 0 for k in ["failures", "errors", "skipped"]):
            raise ValueError(f"Failing or skipped tests in {suite.get('name')}")
        if any(c.find(k) is not None for c in suite.findall("testcase")
               for k in ["failure", "error", "skipped"]):
            raise ValueError(f"Failing or skipped testcase in {suite.get('name')}")
    empty = [s for s in suites if s.get("name") in EMPTY_FIXTURE_REPORTS]
    if len({s.get("name") for s in empty}) != len(empty) or any(int(s.attrib["tests"]) != 0 or s.findall("testcase") for s in empty):
        raise ValueError("Unexpected tests in the unselected AF fixture report")
    suites = [s for s in suites if s.get("name") not in EMPTY_FIXTURE_REPORTS]
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
    if not any(c.get("name") == PHONE_CASE for s in suites for c in s.findall("testcase")):
        raise ValueError("Missing regression for the user's mono AE metadata report")
    return {"status": "PASS", "tests": sum(counts.values()), "failures": 0,
            "errors": 0, "skipped": 0, "suites": counts}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    retry_test = "app/src/test/java/com/particlesdevs/photoncamera/ui/camera/AutomaticSubjectAfRetryTest.java"
    if (args.source / retry_test).is_file():
        SUITES["AutomaticSubjectAfRetryTest"] = 1
    if (args.source / "app/src/test/java/com/particlesdevs/photoncamera/ui/camera/views/MultiFaceOverlayTest.java").is_file():
        head_pairs = args.source / "app/src/main/java/com/particlesdevs/photoncamera/control/subject/SceneHeads.java"
        SUITES["MultiFaceOverlayTest"] = 4 if head_pairs.is_file() else 3
    if (args.source / "app/src/test/java/com/particlesdevs/photoncamera/ui/camera/SceneHeadDisplayTest.java").is_file():
        SUITES["SceneHeadDisplayTest"] = 3
    if (args.source / "app/src/test/java/com/particlesdevs/photoncamera/ui/camera/SceneHeadOutputNamesTest.java").is_file():
        SUITES["SceneHeadOutputNamesTest"] = 1
    if (args.source / "app/src/test/java/com/particlesdevs/photoncamera/ui/camera/HeadFrameTimingTest.java").is_file():
        controller = args.source / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/HumanSubjectFocusController.java"
        SUITES["HeadFrameTimingTest"] = 11 if "startPrimaryMotion(" in controller.read_text() else 5
        if "uprightSelection" in controller.read_text():
            SUITES["HeadFrameTimingTest"] = 16
        if (args.source / "app/src/test/java/com/particlesdevs/photoncamera/ui/camera/RepeatedFaceSupportTest.java").is_file():
            SUITES["RepeatedFaceSupportTest"] = 3
    if (args.source / "app/src/test/java/com/particlesdevs/photoncamera/ui/camera/LowerBodyAcquisitionTest.java").is_file():
        SUITES["LowerBodyAcquisitionTest"] = 3
    if (args.source / "app/src/test/java/com/particlesdevs/photoncamera/ui/camera/ObjectWorkTest.java").is_file():
        SUITES["ObjectWorkTest"] = 5
    if (args.source / "app/src/test/java/com/particlesdevs/photoncamera/ui/camera/PetLabelTest.java").is_file():
        SUITES["PetLabelTest"] = 3
    if (args.source / "app/src/test/java/com/particlesdevs/photoncamera/ui/camera/PetSpeciesEvidenceTest.java").is_file():
        SUITES["PetSpeciesEvidenceTest"] = 4
    if (args.source / "app/src/test/java/com/particlesdevs/photoncamera/control/subject/DogFaceCorrectionTest.java").is_file():
        SUITES["DogFaceCorrectionTest"] = 5
    if (args.source / "app/src/test/java/com/particlesdevs/photoncamera/util/TrackingTraceExportTest.java").is_file():
        SUITES["TrackingTraceExportTest"] = 4
        SUITES["TrackingTraceSettingsTest"] = 2
    meter_suite = args.source / "app/src/test/java/com/particlesdevs/photoncamera/m9/preview/M9TrackedSubjectMeterTest.java"
    if meter_suite.is_file():
        SUITES["M9TrackedSubjectMeterTest"] = 9 if "twoIndependentBrightFaceFramesProtectHighlightsOnce" in meter_suite.read_text() else 5
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
