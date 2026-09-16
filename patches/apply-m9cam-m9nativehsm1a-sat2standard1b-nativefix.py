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
'''    // SAT3: firmware ColorMatrix M06/M07 piecewise pair, selected by R >= G.
    private static final long[] QE = {
            16754, -7632, -922,
            -3124, 14774, -3458,
            -567, -9579, 18330
    };
    private static final long[] QO = {
            18160, -9034, -922,
            -3422, 15080, -3458,
            137, -10264, 18330
    };''',
'''    // SAT2 / Leica M9 Standard sRGB: firmware ColorMatrix M04/M05 piecewise pair, selected by R >= G.
    private static final long[] QE = {
            13659, -4457, -1004,
            -2244, 13469, -3033,
            -199, -6014, 14398
    };
    private static final long[] QO = {
            14811, -5604, -1004,
            -2455, 13688, -3033,
            393, -6588, 14398
    };''',
"Java SAT matrix pair",
)

one(
'''            if (skyDiagnosticEncodedAny1A) bridgeProbeMode = 3;

            if (bridgeProbeMode == 1) {''',
'''            if (skyDiagnosticEncodedAny1A) bridgeProbeMode = 3;

            // SAT2STANDARD1B NATIVEFIX: the native scalar renderer already contains
            // firmware SAT2/SAT3/SAT4 banks. Mode 9 selects SAT2 M04/M05.
            // SAT2STANDARD1A changed Java telemetry while ordinary production still
            // passed native mode 0 (SAT3). Keep explicit diagnostic modes untouched,
            // but bind ordinary production rendering to the selected firmware bank.
            final int nativeSaturationMode1A = skyDiagnosticEncodedAny1A
                    ? skyChromaMode1A
                    : (SATURATION_BANK == 2 ? 9 : (SATURATION_BANK == 4 ? 10 : 0));

            if (bridgeProbeMode == 1) {''',
"native saturation mode insertion",
)

one(
'''                    PP_TO_XYZ, XYZ2SRGB, firmwareCurve02, ctx.hueDivisions, ctx.satDivisions,
                    skyChromaMode1A);''',
'''                    PP_TO_XYZ, XYZ2SRGB, firmwareCurve02, ctx.hueDivisions, ctx.satDivisions,
                    nativeSaturationMode1A);''',
"native createContext saturation mode",
)

one(
'''            d.put("skyChromaMode1A", skyChromaMode1A);
            d.put("skyChromaModeName1A", skyChromaModeName1A(skyChromaMode1A));''',
'''            d.put("skyChromaMode1A", skyChromaMode1A);
            d.put("skyChromaModeName1A", skyChromaModeName1A(skyChromaMode1A));
            d.put("nativeSaturationMode1A", nativeSaturationMode1A);
            d.put("nativeSaturationModeName1A", skyChromaModeName1A(nativeSaturationMode1A));
            d.put("nativeSaturationBankActuallySelected", SATURATION_BANK);
            d.put("nativeSaturationMatrixPairActuallySelected",
                    nativeSaturationMode1A == 9 ? "M04_M05"
                            : nativeSaturationMode1A == 10 ? "M08_M09" : "M06_M07");''',
"native saturation runtime telemetry",
)

# Correct frozen-production labels inherited from the SAT3 baseline. Diagnostic
# mode names themselves remain available and unchanged.
s = s.replace("MHC_NEUTRAL_SAT3_PRODUCTION", "MHC_NEUTRAL_SAT2_PRODUCTION")
s = s.replace(
    "WB_shading_SOURCECAL2A_basis_H25_TC20_gain_SAT3_curve02_BT601_TG1",
    "WB_shading_SOURCECAL2A_basis_identityHSM_TC20_gain_SAT2_curve02_BT601_TG1",
)
s = s.replace(
    "demosaic_only_WB_shading_SOURCECAL_HSM_TC20_SAT3_curve02_BT601_TG1_frozen",
    "demosaic_only_WB_shading_SOURCECAL_identityHSM_TC20_SAT2_curve02_BT601_TG1_frozen",
)

P.write_text(s)
print("SAT2STANDARD1B NATIVEFIX applied")
print("production native saturation mode: 9")
print("firmware pair: M04/M05")
print("tone/exposure untouched")
