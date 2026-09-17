#!/usr/bin/env python3
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
"""                        // M9TONEAUTH1A: same-RAW tone-authority A/B/C bank.
                        // Primary output above is untouched. A reruns the current TC20 decision;
                        // B applies half of A's TC20 displacement in EV around unity; C removes
                        // TC20 global exposure authority entirely. All three retain identical
                        // NORM030, frozen MHC, active SOURCECAL2A, TARGETINPUTADAPTER1A,
                        // identity HSM, true SAT2 M04/M05, curve02, BT.601 and TG1.
                        // Mode 0 is essential: encoded 50/51/52 are legacy saturation diagnostics
                        // and would bypass the production SAT2 selector.
                        String[] suffixes = {
                                \"_TONEAUTH_A_FULL_TC20\",
                                \"_TONEAUTH_B_HALF_TC20\",
                                \"_TONEAUTH_C_ZERO_TC20\"
                        };
                        String[] bridgeProbeNames = {
                                \"toneauth_a_full_tc20\",
                                \"toneauth_b_half_tc20_ev\",
                                \"toneauth_c_zero_tc20\"
                        };
                        int[] bridgeProbeModes = {0, 0, 0};
                        boolean[] selfMeterFlags = {true, false, false};""",
"""                        // M9TOEBANK1A: same-RAW global toe-isolation A/B/C bank.
                        // A is the exact current TARGETDIRECT/TONEBOUND050 self-meter control.
                        // B/C reuse A's exact final linear gain and differ only by a bounded
                        // display-domain luma toe below Y=64. No local masks, semantic scene
                        // logic, global EV offset, SAT2, curve02, source calibration or target
                        // calibration changes are permitted in this experiment.
                        String[] suffixes = {
                                \"_M9_TOE1A_A_CONTROL\",
                                \"_M9_TOE1A_B_MILD20\",
                                \"_M9_TOE1A_C_MODERATE40\"
                        };
                        String[] bridgeProbeNames = {
                                \"m9toe1a_a_control\",
                                \"m9toe1a_b_mild20\",
                                \"m9toe1a_c_moderate40\"
                        };
                        int[] bridgeProbeModes = {0, 0, 0};
                        boolean[] selfMeterFlags = {true, false, false};
                        double[] toeStrength1AFlags = {0.0, 0.20, 0.40};""",
"replace TONEAUTH bank with toe bank")

one(
"""                            boolean selfMeter = selfMeterFlags[variantIndex];
                            double hsmValueStrength = hsmValueStrengthFlags[variantIndex];""",
"""                            boolean selfMeter = selfMeterFlags[variantIndex];
                            double toeStrength1A = toeStrength1AFlags[variantIndex];
                            double hsmValueStrength = hsmValueStrengthFlags[variantIndex];""",
"toe strength variable")

one(
"""                                double variantFixedGain = fixedPrimaryGain;
                                if (!selfMeter) {
                                    if (!Double.isFinite(skyChromaControlTc20BaselineGain)
                                            || skyChromaControlTc20BaselineGain <= 0.0
                                            || !Double.isFinite(skyChromaControlEffectiveRenderGain)
                                            || skyChromaControlEffectiveRenderGain <= 0.0) {
                                        throw new IllegalStateException(
                                                \"M9TONEAUTH1A control gain unavailable before locked variant\");
                                    }
                                    final double edgeFactor = Math.pow(2.0, primaryEdgeEv);
                                    if (variantIndex == 1) {
                                        // Half TC20 authority in EV: log2(gain) * 0.5.
                                        variantFixedGain = Math.sqrt(skyChromaControlTc20BaselineGain)
                                                * edgeFactor;
                                    } else if (variantIndex == 2) {
                                        // Zero TC20 exposure authority; preserve any already-selected
                                        // edge-placement term independently for isolation.
                                        variantFixedGain = edgeFactor;
                                    } else {
                                        throw new IllegalStateException(
                                                \"M9TONEAUTH1A unexpected fixed-gain variant index \" + variantIndex);
                                    }
                                }""",
"""                                double variantFixedGain = fixedPrimaryGain;
                                if (!selfMeter) {
                                    if (!Double.isFinite(skyChromaControlEffectiveRenderGain)
                                            || skyChromaControlEffectiveRenderGain <= 0.0) {
                                        throw new IllegalStateException(
                                                \"M9TOEBANK1A control effective gain unavailable before locked variant\");
                                    }
                                    // Exact control final-linear-gain lock. TONEBOUND050 and any
                                    // already-selected edge factor are therefore identical across A/B/C.
                                    variantFixedGain = skyChromaControlEffectiveRenderGain;
                                }""",
"exact final gain lock")

one(
"""                                } else {
                                    variantDiag.put(\"primaryBrightPivotReplication\", false);
                                }

                                JSONObject skinLumaFinishedAudit =""",
"""                                } else {
                                    variantDiag.put(\"primaryBrightPivotReplication\", false);
                                }

                                JSONObject toe1A = applyM9Toe1A(variantBitmap, toeStrength1A);
                                variantDiag.put(\"m9Toe1A\", toe1A);

                                JSONObject skinLumaFinishedAudit =""",
"toe application")

one(
"""                                variantDiag.put(\"experiment\", \"M9TONEAUTH1A_sameRAW_ABC\");
                                variantDiag.put(\"toneAuthorityFraction\", variantIndex == 0 ? 1.0
                                        : variantIndex == 1 ? 0.5 : 0.0);
                                variantDiag.put(\"toneAuthorityDomain\", \"TC20_global_gain_EV_about_unity\");
                                variantDiag.put(\"toneAuthorityControlTc20Gain\",
                                        Double.isFinite(skyChromaControlTc20BaselineGain)
                                                ? skyChromaControlTc20BaselineGain : JSONObject.NULL);
                                variantDiag.put(\"toneAuthorityAppliedEffectiveGain\",
                                        variantDiag.optDouble(\"effectiveRenderGainAfterRepresentationScale\",
                                                variantFixedGain));
                                variantDiag.put(\"toneAuthorityCaptureExposureMutation\", false);
                                variantDiag.put(\"toneAuthorityPrimaryJpegMutation\", false);
                                variantDiag.put(\"toneAuthoritySameRaw\", true);
                                variantDiag.put(\"toneAuthoritySaturationBank\", \"SAT2_M04_M05\");""",
"""                                variantDiag.put(\"experiment\", \"M9TOEBANK1A_sameRAW_control_mild_moderate\");
                                variantDiag.put(\"toeStrength1A\", toeStrength1A);
                                variantDiag.put(\"toeDomain1A\", \"finished_sRGB_global_BT601_luma_after_curve02_before_JPEG\");
                                variantDiag.put(\"toeBlackAnchorY1A\", 0);
                                variantDiag.put(\"toeCutoffY1A\", 64);
                                variantDiag.put(\"toeLocalMasking1A\", false);
                                variantDiag.put(\"toeSemanticSceneLogic1A\", false);
                                variantDiag.put(\"toeGlobalEvOffset1A\", 0.0);
                                variantDiag.put(\"toneAuthorityControlTc20Gain\",
                                        Double.isFinite(skyChromaControlTc20BaselineGain)
                                                ? skyChromaControlTc20BaselineGain : JSONObject.NULL);
                                variantDiag.put(\"toneAuthorityAppliedEffectiveGain\",
                                        variantDiag.optDouble(\"effectiveRenderGainAfterRepresentationScale\",
                                                variantFixedGain));
                                variantDiag.put(\"toneAuthorityCaptureExposureMutation\", false);
                                variantDiag.put(\"toneAuthorityPrimaryJpegMutation\", false);
                                variantDiag.put(\"toneAuthoritySameRaw\", true);
                                variantDiag.put(\"toneAuthoritySaturationBank\", \"SAT2_M04_M05\");""",
"toe telemetry")

one(
"""                        nativeAb1A.put(\"schema\", \"m9cam.renderer.toneauth.v1a.sameRAW\");
                        nativeAb1A.put(\"experiment\", \"M9TONEAUTH1A_sameRAW_ABC\");""",
"""                        nativeAb1A.put(\"schema\", \"m9cam.renderer.toebank.v1a.sameRAW\");
                        nativeAb1A.put(\"experiment\", \"M9TOEBANK1A_sameRAW_control_mild_moderate\");""",
"bank schema")

one(
"""                        nativeAb1A.put(\"tc20GainIsolation\",
                                \"A=current_applied_TC20;B=sqrt(A_TC20_gain)_same_edge;C=unity_TC20_same_edge\");
                        nativeAb1A.put(\"toneAuthorityFractions\", \"1.0,0.5,0.0\");
                        nativeAb1A.put(\"saturationFrozen\", \"SAT2_M04_M05\");
                        nativeAb1A.put(\"skinChromaProxyApplied\", false);
                        nativeAb1A.put(\"status\", \"completed_m9toneauth1a_sameRAW_ABC\");""",
"""                        nativeAb1A.put(\"tc20GainIsolation\",
                                \"A=self_meter_control;B_C=exact_A_final_linear_gain_lock\");
                        nativeAb1A.put(\"toeStrengths\", \"0.00,0.20,0.40\");
                        nativeAb1A.put(\"toeDomain\", \"finished_sRGB_global_BT601_luma_after_curve02_before_JPEG\");
                        nativeAb1A.put(\"toeBlackAnchorY\", 0);
                        nativeAb1A.put(\"toeCutoffY\", 64);
                        nativeAb1A.put(\"toneAuthorityFractions\", \"same_final_linear_gain_all_variants\");
                        nativeAb1A.put(\"saturationFrozen\", \"SAT2_M04_M05\");
                        nativeAb1A.put(\"skinChromaProxyApplied\", false);
                        nativeAb1A.put(\"status\", \"completed_m9toebank1a_sameRAW_ABC\");""",
"bank summary")

method_anchor = "    private static JSONObject skinLumaFinishedBitmapAudit1A(Bitmap bitmap) throws Exception {"
if s.count(method_anchor) != 1:
    raise SystemExit("M9TOEBANK1A helper insertion anchor missing or ambiguous")

helper = """    // M9TOEBANK1A: bounded global toe probe. This is intentionally a finished-output
    // diagnostic so it cannot alter TC20, SAT2, curve02, source calibration, target calibration
    // or capture exposure. It preserves exact black at Y=0 and is exactly identity at
    // and above Y=64. RGB is scaled by one common factor derived from exact BT.601-Q14 luma,
    // so there is no per-channel hue rotation. Scale is clipped before any channel would clip.
    private static JSONObject applyM9Toe1A(Bitmap bitmap, double strength) throws Exception {
        JSONObject j = new JSONObject();
        j.put(\"schema\", \"m9cam.toe.v1a.global_bt601_bounded\");
        j.put(\"strength\", strength);
        j.put(\"blackAnchorY\", 0);
        j.put(\"cutoffY\", 64);
        j.put(\"localMasking\", false);
        j.put(\"semanticSceneLogic\", false);
        j.put(\"globalEvOffset\", 0.0);
        j.put(\"curve02Mutation\", false);
        j.put(\"sat2Mutation\", false);
        j.put(\"targetCalibrationMutation\", false);
        j.put(\"sourceCalibrationMutation\", false);
        if (bitmap == null || bitmap.isRecycled()) {
            j.put(\"applied\", false);
            j.put(\"reason\", \"bitmap_unavailable\");
            return j;
        }
        if (!(strength > 0.0)) {
            j.put(\"applied\", false);
            j.put(\"reason\", \"control_identity\");
            j.put(\"changedPixels\", 0);
            return j;
        }

        final int width = bitmap.getWidth();
        final int height = bitmap.getHeight();
        final int blackY = 0;
        final int cutoffY = 64;
        final int rowsPerChunk = 64;
        final int[] px = new int[Math.max(1, width * Math.min(rowsPerChunk, height))];
        long eligible = 0L;
        long changed = 0L;
        long channelScaleLimited = 0L;
        double maxDeltaY = 0.0;
        double sumDeltaY = 0.0;

        for (int y0 = 0; y0 < height; y0 += rowsPerChunk) {
            int rows = Math.min(rowsPerChunk, height - y0);
            int count = width * rows;
            bitmap.getPixels(px, 0, width, 0, y0, width, rows);
            for (int i = 0; i < count; i++) {
                int argb = px[i];
                int a = (argb >>> 24) & 0xff;
                int r = (argb >>> 16) & 0xff;
                int g = (argb >>> 8) & 0xff;
                int b = argb & 0xff;
                int yy = (4899 * r + 9617 * g + 1868 * b) >>> 14;
                if (yy <= blackY || yy >= cutoffY) continue;
                eligible++;

                double d = yy - blackY;
                double t = d / (double)(cutoffY - blackY);
                double targetY = blackY + d * (1.0 + strength * (1.0 - t));
                double scale = targetY / Math.max(1.0, yy);
                double maxScale = Double.POSITIVE_INFINITY;
                if (r > 0) maxScale = Math.min(maxScale, 255.0 / r);
                if (g > 0) maxScale = Math.min(maxScale, 255.0 / g);
                if (b > 0) maxScale = Math.min(maxScale, 255.0 / b);
                if (scale > maxScale) {
                    scale = maxScale;
                    channelScaleLimited++;
                }
                int rr = Math.max(0, Math.min(255, (int)Math.round(r * scale)));
                int gg = Math.max(0, Math.min(255, (int)Math.round(g * scale)));
                int bb = Math.max(0, Math.min(255, (int)Math.round(b * scale)));
                if (rr != r || gg != g || bb != b) {
                    px[i] = (a << 24) | (rr << 16) | (gg << 8) | bb;
                    int outY = (4899 * rr + 9617 * gg + 1868 * bb) >>> 14;
                    double delta = outY - yy;
                    if (delta > maxDeltaY) maxDeltaY = delta;
                    sumDeltaY += delta;
                    changed++;
                }
            }
            bitmap.setPixels(px, 0, width, 0, y0, width, rows);
        }

        j.put(\"applied\", true);
        j.put(\"eligiblePixels\", eligible);
        j.put(\"changedPixels\", changed);
        j.put(\"channelScaleLimitedPixels\", channelScaleLimited);
        j.put(\"maxDeltaY\", maxDeltaY);
        j.put(\"meanDeltaYChanged\", changed > 0 ? sumDeltaY / changed : 0.0);
        j.put(\"highTonesY64PlusExactIdentity\", true);
        j.put(\"blackY0ExactIdentity\", true);
        return j;
    }

"""
s = s.replace(method_anchor, helper + method_anchor, 1)

P.write_text(s)
print("M9TOEBANK1A applied")
print("A=current bounded TC20 control; B/C exact A final-gain lock")
print("toe strengths 0.00 / 0.20 / 0.40; Y=0 and Y>=64 exact identity")
print("global BT601-luma toe only; no local masking, scene semantics or global EV")
