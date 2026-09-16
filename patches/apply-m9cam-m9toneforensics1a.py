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


one(
'''    private static final class Meter {
        double gain, baseGain, legacyGain, p98, guardGain;
        double nativeScratchPrepMs, nativeInputCopyMs, nativeLumaPopulationMs;
''',
'''    private static final class Meter {
        double gain, baseGain, legacyGain, p98, guardGain;
        // M9TONEFORENSICS1A: expose the actual TC20 centre-weighted median used
        // by the frozen gain decision. Read-only telemetry; rendering does not
        // consume these fields.
        double median = Double.NaN;
        int validCount = 0;
        double nativeScratchPrepMs, nativeInputCopyMs, nativeLumaPopulationMs;
''',
"meter fields",
)

one(
'''        int validCount = (int)Math.rint(nativeStats[2]);
        Meter out = new Meter();
        out.nativeScratchPrepMs = nativeStats[3] / 1_000_000.0;
''',
'''        int validCount = (int)Math.rint(nativeStats[2]);
        Meter out = new Meter();
        out.validCount = validCount;
        out.median = validCount > 0 ? nativeStats[0] : Double.NaN;
        out.nativeScratchPrepMs = nativeStats[3] / 1_000_000.0;
''',
"native median capture",
)

one(
'''        int validCount = 0;
        for (double v : y) if (v > 1e-5) validCount++;
        Meter out = new Meter();
        if (validCount == 0) {
''',
'''        int validCount = 0;
        for (double v : y) if (v > 1e-5) validCount++;
        Meter out = new Meter();
        out.validCount = validCount;
        if (validCount == 0) {
''',
"java valid count",
)

one(
'''        out.baseGain = clamp(METER_TARGET / Math.max(median, 1e-6), .5, 16.0);

        // Python's legacy P98 is diagnostic only in R3.5.''',
'''        out.median = median;
        out.baseGain = clamp(METER_TARGET / Math.max(median, 1e-6), .5, 16.0);

        // Python's legacy P98 is diagnostic only in R3.5.''',
"java median capture",
)

one(
'''                meter.guardGain = fixedPrimaryGain;
                meter.p98 = Double.NaN;
                meterResizeElapsedMs = 0L;
''',
'''                meter.guardGain = fixedPrimaryGain;
                meter.p98 = Double.NaN;
                meter.median = Double.NaN;
                meter.validCount = 0;
                meterResizeElapsedMs = 0L;
''',
"fixed meter no median",
)

one(
'''            final double effectiveRenderGain = meterParityRenderBaseGain;

            final JSONObject skinLumaStageAudit1AJson = skinLumaStageAuditEnabled1A
''',
'''            final double effectiveRenderGain = meterParityRenderBaseGain;

            // M9TONEFORENSICS1A: do not alter TC20, exposure, curve02 or pixels.
            // Quantify the current normalization authority and two prospective
            // same-signal alternatives in EV space: half authority and zero authority.
            final JSONObject toneForensics1AJson = toneForensics1A(
                    meter, tail, edgePlacementGainEv, effectiveRenderGain, meterParitySelfMeter);

            final JSONObject skinLumaStageAudit1AJson = skinLumaStageAuditEnabled1A
''',
"tone json creation",
)

one(
'''            d.put("tc20TailValue", tail.tailValue);
                        d.put("satBank", SATURATION_BANK);
            d.put("satDomain1A", skySatDiagnosticEncoded1A);
''',
'''            d.put("tc20TailValue", tail.tailValue);
            d.put("toneForensics1A", toneForensics1AJson);
                        d.put("satBank", SATURATION_BANK);
            d.put("satDomain1A", skySatDiagnosticEncoded1A);
''',
"tone diagnostics attach",
)

one(
'''    private static final class Meter {
''',
'''    private static double toneLog2Positive1A(double value) {
        return Double.isFinite(value) && value > 0.0
                ? Math.log(value) / Math.log(2.0)
                : Double.NaN;
    }

    private static double toneSpanEv1A(double high, double low) {
        return Double.isFinite(high) && Double.isFinite(low) && high > 0.0 && low > 0.0
                ? toneLog2Positive1A(high / low)
                : Double.NaN;
    }

    private static JSONObject toneForensics1A(Meter meter, RawTail tail,
                                                double edgePlacementGainEv,
                                                double actualEffectiveRenderGain,
                                                boolean selfMeter) throws Exception {
        JSONObject j = new JSONObject();
        j.put("schema", "m9cam.toneforensics.v1a.readonly");
        j.put("diagnosticOnly", true);
        j.put("photographicPixelChange", false);
        j.put("captureExposureMutation", false);
        j.put("tc20Mutation", false);
        j.put("curve02Mutation", false);
        j.put("saturationColorMutation", false);
        j.put("purpose", "measure_TC20_normalization_authority_before_M9_tone_policy_change");
        j.put("selfMeter", selfMeter);
        j.put("validLumaCount", meter.validCount);
        if (Double.isFinite(meter.median)) {
            j.put("tc20WeightedMedian", meter.median);
            j.put("meterTarget", METER_TARGET);
            j.put("medianToTargetRatio", meter.median / Math.max(METER_TARGET, 1e-12));
            j.put("medianRequestedGainUnclamped", METER_TARGET / Math.max(meter.median, 1e-6));
        } else {
            j.put("tc20WeightedMedian", JSONObject.NULL);
            j.put("meterTarget", METER_TARGET);
            j.put("medianToTargetRatio", JSONObject.NULL);
            j.put("medianRequestedGainUnclamped", JSONObject.NULL);
        }

        final double currentGain = meter.gain;
        final double currentGainEv = toneLog2Positive1A(currentGain);
        final double halfGain = Math.sqrt(Math.max(currentGain, 0.0));
        final double zeroGain = 1.0;
        final double edgeFactor = Math.pow(2.0, edgePlacementGainEv);
        final double eps = 1e-9;
        final String limiter;
        if (!selfMeter) {
            limiter = "fixed_primary_gain_not_tc20";
        } else if (meter.baseGain <= 0.5 + eps) {
            limiter = "median_target_lower_clamp";
        } else if (meter.baseGain >= 16.0 - eps && meter.gain >= meter.guardGain - eps) {
            limiter = "median_target_upper_clamp";
        } else if (meter.guardGain < meter.baseGain - eps) {
            limiter = "raw_tail_headroom_guard";
        } else {
            limiter = "median_target";
        }

        j.put("limitingDecision", limiter);
        j.put("baseMedianGain", meter.baseGain);
        j.put("baseMedianGainEv", toneLog2Positive1A(meter.baseGain));
        j.put("rawTailGuardGain", meter.guardGain);
        j.put("rawTailGuardGainEv", toneLog2Positive1A(meter.guardGain));
        j.put("currentTc20Gain", currentGain);
        j.put("currentTc20GainEv", currentGainEv);
        j.put("currentDirection", currentGain > 1.0 + eps ? "lift" : currentGain < 1.0 - eps ? "darken" : "hold");
        if (Double.isFinite(currentGainEv)) {
            j.put("normalizationDistanceFromUnityEv", Math.abs(currentGainEv));
        } else {
            j.put("normalizationDistanceFromUnityEv", JSONObject.NULL);
        }
        j.put("edgePlacementGainEv", edgePlacementGainEv);
        j.put("actualEffectiveRenderGain", actualEffectiveRenderGain);
        j.put("actualEffectiveRenderGainEv", toneLog2Positive1A(actualEffectiveRenderGain));

        JSONObject raw = new JSONObject();
        raw.put("hardClipFraction", tail.clipFraction);
        raw.put("q25", tail.uq25);
        raw.put("q50", tail.uq50);
        raw.put("q99", tail.uq99);
        raw.put("q99_5", tail.uq995);
        raw.put("q99_8", tail.uq998);
        raw.put("tailValue", tail.tailValue);
        raw.put("q99_8_over_q50_ev", toneSpanEv1A(tail.uq998, tail.uq50));
        raw.put("q99_5_over_q50_ev", toneSpanEv1A(tail.uq995, tail.uq50));
        raw.put("q99_over_q50_ev", toneSpanEv1A(tail.uq99, tail.uq50));
        j.put("rawPlacement", raw);

        JSONObject authority = new JSONObject();
        authority.put("interpretation", "prospective_only_same_signal_gain_authority_no_pixel_change");
        authority.put("fullGain", currentGain);
        authority.put("fullGainEv", currentGainEv);
        authority.put("halfGain", halfGain);
        if (Double.isFinite(currentGainEv)) {
            authority.put("halfGainEv", 0.5 * currentGainEv);
        } else {
            authority.put("halfGainEv", JSONObject.NULL);
        }
        authority.put("zeroGain", zeroGain);
        authority.put("zeroGainEv", 0.0);
        authority.put("fullEffectiveGainWithEdge", currentGain * edgeFactor);
        authority.put("halfEffectiveGainWithEdge", halfGain * edgeFactor);
        authority.put("zeroEffectiveGainWithEdge", zeroGain * edgeFactor);
        authority.put("rawQ99_8AfterFullGainProxy", tail.uq998 * currentGain);
        authority.put("rawQ99_8AfterHalfGainProxy", tail.uq998 * halfGain);
        authority.put("rawQ99_8AfterZeroGainProxy", tail.uq998);
        authority.put("proxyDomainWarning", "raw_linear_proxy_only_downstream_M9_matrix_curve_can_clip_differently");
        j.put("normalizationAuthorityProbe", authority);
        return j;
    }

    private static final class Meter {
''',
"tone helper",
)

P.write_text(s)
print("M9TONEFORENSICS1A applied")
print("photographic pixels unchanged")
print("TC20 gain unchanged")
print("curve02 unchanged")
