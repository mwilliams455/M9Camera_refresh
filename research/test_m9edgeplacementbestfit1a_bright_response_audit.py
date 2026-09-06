#!/usr/bin/env python3
"""Regression tests for BRIGHT response audit v2.

The fixtures are intentionally minimal and target schema/semantic mistakes that
could create false BRIGHT activation. No photographic path is exercised.
"""

import json
import tempfile
from pathlib import Path

from m9edgeplacementbestfit1a_bright_response_audit import audit_file


def bundle(*, score, intent_marker=True, intent=0.0, gain=2.0, base=2.0, guard=3.0,
           pmed=66, pq95=141, fmed=82, fq95=161, extra_primary=None):
    capture = {
        "subjectMotion": {
            "previewLuma": {
                "schema": "m9cam.previewluma.v2.spatial1",
                "global": {"median": pmed, "q95": pq95},
            }
        },
        "sceneExposureDiagnostic": {"structuralLowKeyScore": score},
    }
    if intent_marker:
        capture["m9ExposureAudit"] = {
            "derived": {
                "captureEnergyVsPhotonOnlyEv": intent,
                "captureEnergyVsPreviewEv": intent,
            }
        }

    primary = {
        "renderer": {
            "tc20": {
                "gain": gain,
                "baseMedianGain": base,
                "tc20GuardGain": guard,
            },
            "directRenderedLuma": {
                "schema": "m9cam.renderedluma.v1.grid64",
                "global": {"median": fmed, "q95": fq95},
            },
        }
    }
    if extra_primary:
        primary["extra"] = extra_primary

    return {
        "schema": "m9cam.diagnosticbundle.v1.sidecar1b",
        "entries": [
            {
                "role": "capture_metadata",
                "publicFilename": "IMG_TEST_00_M9.json",
                "payload": capture,
            },
            {
                "role": "primary_timing",
                "publicFilename": "IMG_TEST_00_M9_PRIMARY.json",
                "payload": primary,
            },
        ],
    }


def run_fixture(obj):
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "M9_DIAGNOSTICS_BURST_TEST.json"
        path.write_text(json.dumps(obj), encoding="utf-8")
        return audit_file(path)


def test_181559_shape_is_lowkey_broad():
    r = run_fixture(bundle(
        score=0.876096,
        intent=-3.5887095894817645e-8,
        gain=2.0633145986,
        base=2.0633145986,
        guard=3.7034552846,
        pmed=66,
        pq95=141,
        fmed=82,
        fq95=161,
    ))
    assert r["tc20Gain"] == 2.0633145986
    assert r["tc20Binding"] == "median"
    assert abs(r["achievedIntentEv"]) < 1e-6
    assert r["broadOpening"] is True
    assert r["lowkeySeed"] is True
    assert r["lowkeyBroad"] is True


def test_applied_gain_not_base_gain_controls_lowkey_floor():
    # Mirrors the important 181423-type distinction: a large baseMedianGain
    # must NOT pass the LOWKEY gain floor when the actually applied TC20 gain
    # is below 1.50 because the guard/clamp restrained it.
    r = run_fixture(bundle(
        score=0.808704,
        intent=0.0,
        gain=1.4461111111,
        base=5.7030028276,
        guard=1.4461111111,
        pmed=69,
        pq95=171,
        fmed=82,
        fq95=180,
    ))
    assert r["baseMedianGain"] > 5.0
    assert r["tc20Gain"] < 1.50
    assert r["tc20Binding"] == "guard"
    assert r["broadOpening"] is True
    assert r["lowkeySeed"] is False
    assert r["lowkeyBroad"] is False


def test_missing_intent_remains_unknown_not_zero():
    r = run_fixture(bundle(
        score=0.90,
        intent_marker=False,
        gain=2.2,
        base=2.2,
        guard=3.0,
    ))
    assert r["achievedIntentEv"] is None
    assert r["lowkeyCoreNoIntent"] is True
    assert r["lowkeySeed"] is None
    assert r["lowkeyBroad"] is None


def test_capture_energy_photon_only_path_is_authoritative():
    obj = bundle(
        score=0.90,
        intent=0.05,
        gain=2.2,
        base=2.2,
        guard=3.0,
    )
    capture = obj["entries"][0]["payload"]
    # Add a conflicting compatibility-style field. The real exposure-audit
    # path must win instead of an arbitrary recursive key search.
    capture["legacyResearch"] = {"achievedIntentEv": 0.75}
    r = run_fixture(obj)
    assert abs(r["achievedIntentEv"] - 0.05) < 1e-12
    assert r["lowkeySeed"] is True


def test_conflicting_tc20_triplets_are_ambiguous():
    obj = bundle(
        score=0.90,
        intent=0.0,
        gain=2.2,
        base=2.2,
        guard=3.0,
        extra_primary={
            "gain": 1.1,
            "baseMedianGain": 4.0,
            "tc20GuardGain": 1.1,
        },
    )
    r = run_fixture(obj)
    assert r["tc20Gain"] is None
    assert r["lowkeyCoreNoIntent"] is False
    assert r["lowkeySeed"] is False
    assert r["lowkeyBroad"] is False


def main():
    tests = [
        value for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]
    for test in tests:
        test()
    print(f"PASS: {len(tests)} BRIGHT response audit regression tests")


if __name__ == "__main__":
    main()
