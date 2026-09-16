from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
P = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
s = P.read_text()

def one(old, new, label):
    global s
    n=s.count(old)
    if n!=1:
        raise SystemExit(f'{label}: expected 1 match, found {n}')
    s=s.replace(old,new,1)

one(
'''    private static final boolean DEMOSAIC_DIAGNOSTIC_BANK_ENABLED = false;''',
'''    // M9TONEAUTH1A: temporary same-RAW A/B/C tone-authority bank. The primary
    // JPEG is saved before this diagnostic block; enabling this bank therefore
    // cannot alter the normal capture output. It only emits three additional
    // JPEG/JSON controls from the same RAW after primary completion.
    private static final boolean DEMOSAIC_DIAGNOSTIC_BANK_ENABLED = true;''',
'diagnostic bank enable')

old='''                        // BASISHSM1P-SKYSAT1A: same-RAW authentic Leica saturation-family bank.
                        // A meters exactly as frozen 1P/SAT3. B/C/D reuse A's exact effective render gain.
                        // SAT2=04/05 is literal Leica Standard, SAT3=06/07 is current colourful production,
                        // SAT4=08/09 is authentic High Saturation. D keeps the already-proven identity anchor.
                        // No sky classifier, scene guard, exposure change, HSM change, or generic desaturation exists.
                        // DEMOSAICAB1A: same RAW and same NORM030 Bayer; only demosaic changes.
                        // A is MHC production and meters normally. B is OpenCV EA and reuses A's
                        // exact effective render gain. SOURCECAL2A/HSM/TC20 placement/SAT3/curve02/
                        // BT601/TG1 are otherwise identical.
                        String[] suffixes = {
                                "_DEMOSAICNEUTRAL_MHCNB_SAT3",
                                "_DEMOSAICNEUTRAL_MHCPLAIN_SAT3_GAINLOCK",
                                "_DEMOSAICNEUTRAL_EA_SAT3_GAINLOCK"
                        };
                        String[] bridgeProbeNames = {
                                "demosaicneutral_mhcnb_sat3_control",
                                "demosaicneutral_mhcplain_sat3_gainlocked",
                                "demosaicneutral_ea_sat3_gainlocked"
                        };
                        int[] bridgeProbeModes = {50, 55, 54};
                        boolean[] selfMeterFlags = {true, false, false};'''
new='''                        // M9TONEAUTH1A: same-RAW tone-authority A/B/C bank.
                        // Primary output above is untouched. A reruns the current TC20 decision;
                        // B applies half of A's TC20 displacement in EV around unity; C removes
                        // TC20 global exposure authority entirely. All three retain identical
                        // NORM030, frozen MHC, active SOURCECAL2A, TARGETINPUTADAPTER1A,
                        // identity HSM, true SAT2 M04/M05, curve02, BT.601 and TG1.
                        // Mode 0 is essential: encoded 50/51/52 are legacy saturation diagnostics
                        // and would bypass the production SAT2 selector.
                        String[] suffixes = {
                                "_TONEAUTH_A_FULL_TC20",
                                "_TONEAUTH_B_HALF_TC20",
                                "_TONEAUTH_C_ZERO_TC20"
                        };
                        String[] bridgeProbeNames = {
                                "toneauth_a_full_tc20",
                                "toneauth_b_half_tc20_ev",
                                "toneauth_c_zero_tc20"
                        };
                        int[] bridgeProbeModes = {0, 0, 0};
                        boolean[] selfMeterFlags = {true, false, false};'''
one(old,new,'variant bank')

old='''                                double variantFixedGain = fixedPrimaryGain;
                                if (!selfMeter) {
                                    if (!Double.isFinite(skyChromaControlEffectiveRenderGain)
                                            || skyChromaControlEffectiveRenderGain <= 0.0) {
                                        throw new IllegalStateException(
                                                "SKYSAT1A control gain unavailable before locked variant");
                                    }
                                    variantFixedGain = skyChromaControlEffectiveRenderGain;
                                }'''
new='''                                double variantFixedGain = fixedPrimaryGain;
                                if (!selfMeter) {
                                    if (!Double.isFinite(skyChromaControlTc20BaselineGain)
                                            || skyChromaControlTc20BaselineGain <= 0.0
                                            || !Double.isFinite(skyChromaControlEffectiveRenderGain)
                                            || skyChromaControlEffectiveRenderGain <= 0.0) {
                                        throw new IllegalStateException(
                                                "M9TONEAUTH1A control gain unavailable before locked variant");
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
                                                "M9TONEAUTH1A unexpected fixed-gain variant index " + variantIndex);
                                    }
                                }'''
one(old,new,'authority gain')

old='''                                variantDiag.put("status", "success");
                                variantDiag.put("variant", bridgeProbeName);
                                variantDiag.put("bridgeProbeMode", bridgeProbeMode);'''
new='''                                variantDiag.put("status", "success");
                                variantDiag.put("variant", bridgeProbeName);
                                variantDiag.put("experiment", "M9TONEAUTH1A_sameRAW_ABC");
                                variantDiag.put("toneAuthorityFraction", variantIndex == 0 ? 1.0
                                        : variantIndex == 1 ? 0.5 : 0.0);
                                variantDiag.put("toneAuthorityDomain", "TC20_global_gain_EV_about_unity");
                                variantDiag.put("toneAuthorityControlTc20Gain",
                                        Double.isFinite(skyChromaControlTc20BaselineGain)
                                                ? skyChromaControlTc20BaselineGain : JSONObject.NULL);
                                variantDiag.put("toneAuthorityAppliedEffectiveGain",
                                        variantDiag.optDouble("effectiveRenderGainAfterRepresentationScale",
                                                variantFixedGain));
                                variantDiag.put("toneAuthorityCaptureExposureMutation", false);
                                variantDiag.put("toneAuthorityPrimaryJpegMutation", false);
                                variantDiag.put("toneAuthoritySameRaw", true);
                                variantDiag.put("toneAuthoritySaturationBank", "SAT2_M04_M05");
                                variantDiag.put("bridgeProbeMode", bridgeProbeMode);'''
one(old,new,'variant telemetry')

old='''                        nativeAb1A.put("schema", "m9cam.renderer.satdomain.v1a");
                        nativeAb1A.put("experiment", "BASISHSM1P-DEMOSAICAB1A");'''
new='''                        nativeAb1A.put("schema", "m9cam.renderer.toneauth.v1a.sameRAW");
                        nativeAb1A.put("experiment", "M9TONEAUTH1A_sameRAW_ABC");'''
one(old,new,'bank schema')

old='''                        nativeAb1A.put("productionBehaviorChanged", false);
                        nativeAb1A.put("tc20GainIsolation",
                                "EA_B_locked_to_MHC_A_exact_effective_render_gain");
                        nativeAb1A.put("skinChromaProxyApplied", false);
                        nativeAb1A.put("status", "completed_demosaicab1a");'''
new='''                        nativeAb1A.put("productionBehaviorChanged", false);
                        nativeAb1A.put("captureExposureChanged", false);
                        nativeAb1A.put("primaryJpegChanged", false);
                        nativeAb1A.put("tc20GainIsolation",
                                "A=current_applied_TC20;B=sqrt(A_TC20_gain)_same_edge;C=unity_TC20_same_edge");
                        nativeAb1A.put("toneAuthorityFractions", "1.0,0.5,0.0");
                        nativeAb1A.put("saturationFrozen", "SAT2_M04_M05");
                        nativeAb1A.put("skinChromaProxyApplied", false);
                        nativeAb1A.put("status", "completed_m9toneauth1a_sameRAW_ABC");'''
one(old,new,'bank summary')

P.write_text(s)
print('M9TONEAUTH1A same-RAW A/B/C applied')
print('primary JPEG path unchanged')
print('capture exposure unchanged')
print('A=full TC20, B=half TC20 EV authority, C=zero TC20 authority')
