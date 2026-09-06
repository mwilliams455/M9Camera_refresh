#!/usr/bin/env python3
"""Regression tests for research-only EDGEPLACEMENTBESTFIT1A selector.

These tests exercise branch semantics and minimal diagnostic-schema extraction.
They do not render pixels and do not change capture, TC20, curve02, color
science, JPEG quality, or DNG output.
"""

from m9edgeplacementbestfit1a_multibranch import evaluate, extract_features


def base_features():
    return {
        "achievedIntentEv": 0.0,
        "previewSceneSpreadEv": 0.0,
        "previewBrightRegionFraction": 0.0,
        "upperLowerShiftEv": 0.0,
        "integralRelativeShiftEv": 0.0,
        "retentionEv": {
            "center": 0.0,
            "lower": 0.0,
            "upper": 0.0,
            "edge": 0.0,
        },
        "broadCollapseCount": 0,
        "renderGridMeanY": 80.0,
        "renderLower12Y": 80.0,
        "renderUpper6Y": 80.0,
        "renderCellMedianP75": 80.0,
        "structuralLowKeyScore": 0.0,
        "tc20Gain": 1.0,
        "finishedGlobalMedianY": 80.0,
        "brightMedianShiftEv": 0.0,
        "brightQ95ShiftEv": 0.0,
        "brightBroadOpeningMinEv": None,
    }


def selected(features):
    return evaluate(features)["selector"]


def branch(result, name):
    return result["branches"][name]["candidate"]


def test_default_hold():
    r = evaluate(base_features())
    assert r["selector"] == "HOLD"
    assert not branch(r, "INTENT_COLLAPSE")
    assert not branch(r, "ZERO_INTENT_COLLAPSE")
    assert not branch(r, "FOREGROUND_COLLAPSE")
    assert not branch(r, "BRIGHT_LOWKEY_BROAD")


def test_dark_intent_branch_preserved():
    f = base_features()
    f.update({
        "achievedIntentEv": 0.20,
        "upperLowerShiftEv": 1.60,
        "renderCellMedianP75": 25.0,
        "integralRelativeShiftEv": 0.10,
    })
    assert selected(f) == "DARK_INTENT"


def test_dark_zero_intent_branch_preserved():
    f = base_features()
    f.update({
        "achievedIntentEv": 0.0,
        "previewSceneSpreadEv": 1.50,
        "previewBrightRegionFraction": 0.30,
        "renderCellMedianP75": 10.0,
        "renderGridMeanY": 20.0,
        "broadCollapseCount": 4,
        "retentionEv": {
            "center": -2.0,
            "lower": -2.0,
            "upper": -2.0,
            "edge": -2.0,
        },
    })
    assert selected(f) == "DARK_ZERO_INTENT"


def test_dark_foreground_branch_preserved():
    f = base_features()
    f.update({
        "achievedIntentEv": 0.30,
        "upperLowerShiftEv": 1.30,
        "renderLower12Y": 15.0,
        "renderUpper6Y": 160.0,
        "renderCellMedianP75": 150.0,
        "retentionEv": {
            "center": -0.50,
            "lower": -1.70,
            "upper": -0.20,
            "edge": -0.40,
        },
    })
    assert selected(f) == "DARK_FOREGROUND"


def test_bright_lowkey_broad_positive():
    # Synthetic representation of the 181559 morphology/response.
    f = base_features()
    f.update({
        "achievedIntentEv": 0.0,
        "structuralLowKeyScore": 0.876096,
        "tc20Gain": 2.0633145986,
        "finishedGlobalMedianY": 82.0,
        "brightMedianShiftEv": 0.313,
        "brightQ95ShiftEv": 0.191,
        "brightBroadOpeningMinEv": 0.191,
    })
    r = evaluate(f)
    assert r["selector"] == "BRIGHT_LOWKEY_BROAD"
    assert branch(r, "BRIGHT_LOWKEY_OPENING")
    assert branch(r, "BRIGHT_BROADOPENING")
    assert branch(r, "BRIGHT_LOWKEY_BROAD")


def test_broad_hold_boundary_does_not_activate_bright():
    # Synthetic representation of 181404: BROAD positive but structural floor OFF.
    f = base_features()
    f.update({
        "achievedIntentEv": 0.0,
        "structuralLowKeyScore": 0.5447914875,
        "tc20Gain": 2.554,
        "finishedGlobalMedianY": 82.0,
        "brightMedianShiftEv": 0.072,
        "brightQ95ShiftEv": 0.030,
        "brightBroadOpeningMinEv": 0.030,
    })
    r = evaluate(f)
    assert r["selector"] == "HOLD"
    assert not branch(r, "BRIGHT_LOWKEY_OPENING")
    assert branch(r, "BRIGHT_BROADOPENING")
    assert not branch(r, "BRIGHT_LOWKEY_BROAD")


def test_strong_lowkey_but_dense_finished_response_stays_hold():
    # Synthetic 181623-style hard negative: morphology high, final body still dense.
    f = base_features()
    f.update({
        "achievedIntentEv": 0.0,
        "structuralLowKeyScore": 0.972,
        "tc20Gain": 1.5415,
        "finishedGlobalMedianY": 14.0,
        "brightMedianShiftEv": -2.10,
        "brightQ95ShiftEv": -0.90,
    })
    r = evaluate(f)
    assert r["selector"] == "HOLD"
    assert not branch(r, "BRIGHT_LOWKEY_OPENING")
    assert not branch(r, "BRIGHT_BROADOPENING")
    assert not branch(r, "BRIGHT_LOWKEY_BROAD")


def test_lowkey_seed_without_broad_response_stays_hold():
    f = base_features()
    f.update({
        "achievedIntentEv": 0.0,
        "structuralLowKeyScore": 0.80,
        "tc20Gain": 2.0,
        "finishedGlobalMedianY": 82.0,
        "brightMedianShiftEv": 0.20,
        "brightQ95ShiftEv": -0.05,
    })
    r = evaluate(f)
    assert branch(r, "BRIGHT_LOWKEY_OPENING")
    assert not branch(r, "BRIGHT_BROADOPENING")
    assert not branch(r, "BRIGHT_LOWKEY_BROAD")
    assert r["selector"] == "HOLD"


def test_missing_intent_cannot_activate_bright():
    f = base_features()
    f.update({
        "achievedIntentEv": None,
        "structuralLowKeyScore": 0.90,
        "tc20Gain": 2.5,
        "finishedGlobalMedianY": 90.0,
        "brightMedianShiftEv": 0.30,
        "brightQ95ShiftEv": 0.20,
    })
    r = evaluate(f)
    assert not branch(r, "BRIGHT_LOWKEY_OPENING")
    assert branch(r, "BRIGHT_BROADOPENING")
    assert not branch(r, "BRIGHT_LOWKEY_BROAD")
    assert r["selector"] == "HOLD"


def test_dark_priority_is_unchanged_if_synthetic_features_overlap_bright():
    f = base_features()
    f.update({
        "achievedIntentEv": 0.20,
        "upperLowerShiftEv": 1.60,
        "renderCellMedianP75": 25.0,
        "integralRelativeShiftEv": 0.10,
        "structuralLowKeyScore": 0.90,
        "tc20Gain": 2.5,
        "finishedGlobalMedianY": 90.0,
        "brightMedianShiftEv": 0.30,
        "brightQ95ShiftEv": 0.20,
    })
    r = evaluate(f)
    assert branch(r, "INTENT_COLLAPSE")
    # Bright LOWKEY is itself OFF because achievedIntentEv=+0.20, but this test
    # also locks the selector priority against future accidental reordering.
    assert r["selector"] == "DARK_INTENT"


def test_bright_schema_extraction_matches_181559_shape():
    # Minimal fixture mirrors the actual diagnostic nesting used by the
    # prospective 18:15:59 bundle, without copying unrelated telemetry.
    capture = {
        "subjectMotion": {
            "previewLuma": {
                "schema": "m9cam.previewluma.v2.spatial1",
                "global": {"median": 66, "q95": 141},
            }
        },
        "m9ExposureAudit": {
            "derived": {"captureEnergyVsPhotonOnlyEv": -3.6e-8}
        },
        "sceneExposureDiagnostic": {
            "structuralLowKeyScore": 0.876096
        },
    }
    primary = {
        "renderer": {
            "tc20": {
                "gain": 2.0633145986,
                "baseMedianGain": 2.0633145986,
                "tc20GuardGain": 3.7034552846,
            },
            "directRenderedLuma": {
                "schema": "m9cam.renderedluma.v1.grid64",
                "global": {"median": 82, "q95": 161},
            },
        }
    }
    f = extract_features(capture, primary)
    assert abs(f["achievedIntentEv"]) < 1e-6
    assert f["structuralLowKeyScore"] == 0.876096
    assert f["tc20Gain"] == 2.0633145986
    assert f["previewGlobalMedianY"] == 66.0
    assert f["previewGlobalQ95Y"] == 141.0
    assert f["finishedGlobalMedianY"] == 82.0
    assert f["finishedGlobalQ95Y"] == 161.0
    assert f["brightMedianShiftEv"] > 0
    assert f["brightQ95ShiftEv"] > 0
    assert evaluate(f)["selector"] == "BRIGHT_LOWKEY_BROAD"


def main():
    tests = [
        value for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]
    for test in tests:
        test()
    print(f"PASS: {len(tests)} BESTFIT1A multibranch regression tests")


if __name__ == "__main__":
    main()
