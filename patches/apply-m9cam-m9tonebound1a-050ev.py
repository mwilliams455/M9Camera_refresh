from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("PhotonCamera")
P = ROOT / "app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java"
s = P.read_text()


def one(old: str, new: str, label: str) -> None:
    global s
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {n}")
    s = s.replace(old, new, 1)


if 'm9cam.toneforensics.v1a.readonly' not in s:
    raise SystemExit('M9TONEBOUND1A requires M9TONEFORENSICS1A baseline')
if 'SATURATION_BANK == 2 ? 9' not in s:
    raise SystemExit('M9TONEBOUND1A requires true native SAT2 selection')

one(
'''            final double effectiveRenderGain = meterParityRenderBaseGain;

            // M9TONEFORENSICS1A: do not alter TC20, exposure, curve02 or pixels.
            // Quantify the current normalization authority and two prospective
            // same-signal alternatives in EV space: half authority and zero authority.
            final JSONObject toneForensics1AJson = toneForensics1A(
                    meter, tail, edgePlacementGainEv, effectiveRenderGain, meterParitySelfMeter);
''',
'''            // M9TONEBOUND1A: preserve the frozen TC20 decision itself, but bound how much
            // authority that decision may exert on the final render placement. This is a
            // gain-domain clamp around unity, not a new meter and not a capture-EV change.
            // Scale the already-composed effective gain by bounded/original TC20 so any
            // pre-existing edge-placement factor remains exactly preserved.
            final double toneBoundLimitEv1A = 0.5;
            final double toneBoundOriginalTc20Gain1A = meter.gain;
            final double toneBoundOriginalTc20Ev1A = toneLog2Positive1A(toneBoundOriginalTc20Gain1A);
            final boolean toneBoundEligible1A = meterParitySelfMeter
                    && Double.isFinite(toneBoundOriginalTc20Ev1A)
                    && Double.isFinite(toneBoundOriginalTc20Gain1A)
                    && toneBoundOriginalTc20Gain1A > 0.0;
            final double toneBoundAppliedTc20Ev1A = toneBoundEligible1A
                    ? Math.max(-toneBoundLimitEv1A, Math.min(toneBoundLimitEv1A, toneBoundOriginalTc20Ev1A))
                    : toneBoundOriginalTc20Ev1A;
            final double toneBoundAppliedTc20Gain1A = toneBoundEligible1A
                    ? Math.pow(2.0, toneBoundAppliedTc20Ev1A)
                    : toneBoundOriginalTc20Gain1A;
            final boolean toneBoundClampEngaged1A = toneBoundEligible1A
                    && Math.abs(toneBoundAppliedTc20Ev1A - toneBoundOriginalTc20Ev1A) > 1e-9;
            final double toneBoundScale1A = toneBoundEligible1A
                    ? toneBoundAppliedTc20Gain1A / toneBoundOriginalTc20Gain1A
                    : 1.0;
            final double toneBoundUnboundedEffectiveGain1A = meterParityRenderBaseGain;
            final double effectiveRenderGain = toneBoundUnboundedEffectiveGain1A * toneBoundScale1A;

            final JSONObject toneBound1AJson = new JSONObject();
            toneBound1AJson.put("schema", "m9cam.tonebound.v1a.050ev");
            toneBound1AJson.put("policy", "clamp_TC20_EV_about_unity_preserve_composed_edge_factor");
            toneBound1AJson.put("photographicPixelChange", toneBoundEligible1A);
            toneBound1AJson.put("captureExposureMutation", false);
            toneBound1AJson.put("tc20MeterMutation", false);
            toneBound1AJson.put("curve02Mutation", false);
            toneBound1AJson.put("saturationColorMutation", false);
            toneBound1AJson.put("identityHsmRetained", true);
            toneBound1AJson.put("saturationBank", "SAT2_M04_M05");
            toneBound1AJson.put("authorityLimitEv", toneBoundLimitEv1A);
            toneBound1AJson.put("selfMeterEligible", toneBoundEligible1A);
            toneBound1AJson.put("fixedPrimaryPathBypassed", !meterParitySelfMeter);
            toneBound1AJson.put("originalTc20Gain", toneBoundOriginalTc20Gain1A);
            if (Double.isFinite(toneBoundOriginalTc20Ev1A)) {
                toneBound1AJson.put("originalTc20Ev", toneBoundOriginalTc20Ev1A);
                toneBound1AJson.put("appliedTc20Ev", toneBoundAppliedTc20Ev1A);
                toneBound1AJson.put("removedAuthorityEv", toneBoundOriginalTc20Ev1A - toneBoundAppliedTc20Ev1A);
                toneBound1AJson.put("removedAuthorityAbsEv", Math.abs(toneBoundOriginalTc20Ev1A - toneBoundAppliedTc20Ev1A));
            } else {
                toneBound1AJson.put("originalTc20Ev", JSONObject.NULL);
                toneBound1AJson.put("appliedTc20Ev", JSONObject.NULL);
                toneBound1AJson.put("removedAuthorityEv", JSONObject.NULL);
                toneBound1AJson.put("removedAuthorityAbsEv", JSONObject.NULL);
            }
            toneBound1AJson.put("appliedTc20Gain", toneBoundAppliedTc20Gain1A);
            toneBound1AJson.put("clampEngaged", toneBoundClampEngaged1A);
            toneBound1AJson.put("clampDirection", !toneBoundClampEngaged1A ? "none"
                    : toneBoundOriginalTc20Ev1A > toneBoundAppliedTc20Ev1A ? "limit_lift" : "limit_darken");
            toneBound1AJson.put("unboundedEffectiveRenderGain", toneBoundUnboundedEffectiveGain1A);
            toneBound1AJson.put("boundedEffectiveRenderGain", effectiveRenderGain);
            toneBound1AJson.put("effectiveScaleVersusFrozenTc20", toneBoundScale1A);

            // Keep the read-only forensics block, but report the actual bounded render gain.
            // Its currentTc20Gain fields continue to expose the original frozen TC20 decision.
            final JSONObject toneForensics1AJson = toneForensics1A(
                    meter, tail, edgePlacementGainEv, effectiveRenderGain, meterParitySelfMeter);
''',
"bounded effective gain seam",
)

one(
'''            d.put("toneForensics1A", toneForensics1AJson);
                        d.put("satBank", SATURATION_BANK);
''',
'''            d.put("toneForensics1A", toneForensics1AJson);
            d.put("toneBound1A", toneBound1AJson);
                        d.put("satBank", SATURATION_BANK);
''',
"bounded diagnostics attach",
)

P.write_text(s)
print("M9TONEBOUND1A applied")
print("TC20 render authority bounded to +/-0.5 EV for self-metered primary path")
print("capture exposure unchanged")
print("TC20 meter decision unchanged")
print("curve02/SAT2/identity-HSM unchanged")
