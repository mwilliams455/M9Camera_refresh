#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
GRADLE = ROOT / 'app/build.gradle'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'UPSTREAMAXIS1A {label}: expected exactly 1 anchor, found {n}')
    return text.replace(old, new, 1)


t = CPP.read_text()

helpers = r'''
// UPSTREAMAXIS1A: read-only same-pixel cohort trace. Alternate HSM contexts are
// used only inside SATDOMAIN telemetry and never write rendered pixels.
struct UpstreamAxisPathValue {
    int64_t pre[3]{};
    int64_t sat[3]{};
    double curve[3]{};
    bool branchEven = false;
    bool preHighClip = false;
    bool satBoundary = false;
};

struct UpstreamAxisPathAgg {
    double preGreenDeficit[3]{};
    double satGreenDeficit[3]{};
    double curveGreenDeficit[3]{};
    double preSpread[3]{};
    double satSpread[3]{};
    double curveSpread[3]{};
    uint64_t preMagenta[3]{};
    uint64_t satMagenta[3]{};
    uint64_t curveMagenta[3]{};
    uint64_t branchEven[3]{};
    uint64_t preHighClip[3]{};
    uint64_t satBoundary[3]{};
};

struct UpstreamAxisAgg {
    uint64_t count[3]{};
    UpstreamAxisPathAgg path[3]{};
    uint64_t branchFlipFullVsS0[3]{};
    uint64_t branchFlipFullVsIdentity[3]{};
    uint64_t fullCurveMagentaRescuedByS0[3]{};
    uint64_t fullCurveMagentaRescuedByIdentity[3]{};
    uint64_t hsmS0CurveMagentaIntroducedVsFull[3]{};
    uint64_t identityCurveMagentaIntroducedVsFull[3]{};
};

inline void upstreamAxisEvalPath(const double* m9,
                                 double gain,
                                 const ColorContext& ctx,
                                 UpstreamAxisPathValue* out) {
    const double u[3] = {m9[0] * gain * RAW_MAX,
                         m9[1] * gain * RAW_MAX,
                         m9[2] * gain * RAW_MAX};
    out->preHighClip = (u[0] > RAW_MAX || u[1] > RAW_MAX || u[2] > RAW_MAX);
    for (int ch = 0; ch < 3; ++ch) {
        out->pre[ch] = clipl(static_cast<int64_t>(std::rint(u[ch])), 0, RAW_MAX);
    }
    out->branchEven = out->pre[0] >= out->pre[1];
    const auto& q = out->branchEven ? QE : QO;
    const int64_t a0 = q[0] * out->pre[0] + q[1] * out->pre[1] + q[2] * out->pre[2];
    const int64_t a1 = q[3] * out->pre[0] + q[4] * out->pre[1] + q[5] * out->pre[2];
    const int64_t a2 = q[6] * out->pre[0] + q[7] * out->pre[1] + q[8] * out->pre[2];
    const int64_t shifted[3] = {a0 >> 16, a1 >> 16, a2 >> 16};
    for (int ch = 0; ch < 3; ++ch) {
        if (shifted[ch] < 0 || shifted[ch] > LUT_MAX) out->satBoundary = true;
        out->sat[ch] = clipl(shifted[ch], 0, LUT_MAX);
        out->curve[ch] = static_cast<double>(ctx.curve[static_cast<size_t>(out->sat[ch])]);
    }
}

inline bool upstreamAxisMagenta(double r, double g, double b) {
    return satGreenDeficitNormalized(r, g, b) > 0.01;
}

inline void upstreamAxisAccumulatePath(const UpstreamAxisPathValue& v,
                                       UpstreamAxisPathAgg* a,
                                       int band) {
    const double pr = static_cast<double>(v.pre[0]);
    const double pg = static_cast<double>(v.pre[1]);
    const double pb = static_cast<double>(v.pre[2]);
    const double sr = static_cast<double>(v.sat[0]);
    const double sg = static_cast<double>(v.sat[1]);
    const double sb = static_cast<double>(v.sat[2]);
    a->preGreenDeficit[band] += satGreenDeficitNormalized(pr, pg, pb);
    a->satGreenDeficit[band] += satGreenDeficitNormalized(sr, sg, sb);
    a->curveGreenDeficit[band] += satGreenDeficitNormalized(v.curve[0], v.curve[1], v.curve[2]);
    a->preSpread[band] += satRelativeSpread(pr, pg, pb);
    a->satSpread[band] += satRelativeSpread(sr, sg, sb);
    a->curveSpread[band] += satRelativeSpread(v.curve[0], v.curve[1], v.curve[2]);
    if (upstreamAxisMagenta(pr, pg, pb)) ++a->preMagenta[band];
    if (upstreamAxisMagenta(sr, sg, sb)) ++a->satMagenta[band];
    if (upstreamAxisMagenta(v.curve[0], v.curve[1], v.curve[2])) ++a->curveMagenta[band];
    if (v.branchEven) ++a->branchEven[band];
    if (v.preHighClip) ++a->preHighClip[band];
    if (v.satBoundary) ++a->satBoundary[band];
}

inline void upstreamAxisAuditPixel(const jshort* cam, int c,
                                   const ColorContext& fullCtx,
                                   const ColorContext& hsmS0Ctx,
                                   const ColorContext& identityHsmCtx,
                                   double gain,
                                   UpstreamAxisAgg* agg) {
    double hsm[3]{};
    double m9[3][3]{};
    cameraToM9(cam, c, fullCtx, hsm, m9[0]);
    cameraToM9(cam, c, hsmS0Ctx, hsm, m9[1]);
    cameraToM9(cam, c, identityHsmCtx, hsm, m9[2]);

    UpstreamAxisPathValue pv[3]{};
    for (int path = 0; path < 3; ++path) upstreamAxisEvalPath(m9[path], gain, fullCtx, &pv[path]);
    const double productionSpread = satRelativeSpread(
            static_cast<double>(pv[0].pre[0]),
            static_cast<double>(pv[0].pre[1]),
            static_cast<double>(pv[0].pre[2]));
    constexpr double bands[3] = {0.05, 0.10, 0.20};
    for (int band = 0; band < 3; ++band) {
        if (productionSpread > bands[band]) continue;
        ++agg->count[band];
        for (int path = 0; path < 3; ++path) upstreamAxisAccumulatePath(pv[path], &agg->path[path], band);
        if (pv[0].branchEven != pv[1].branchEven) ++agg->branchFlipFullVsS0[band];
        if (pv[0].branchEven != pv[2].branchEven) ++agg->branchFlipFullVsIdentity[band];
        const bool fullMag = upstreamAxisMagenta(pv[0].curve[0], pv[0].curve[1], pv[0].curve[2]);
        const bool s0Mag = upstreamAxisMagenta(pv[1].curve[0], pv[1].curve[1], pv[1].curve[2]);
        const bool identityMag = upstreamAxisMagenta(pv[2].curve[0], pv[2].curve[1], pv[2].curve[2]);
        if (fullMag && !s0Mag) ++agg->fullCurveMagentaRescuedByS0[band];
        if (fullMag && !identityMag) ++agg->fullCurveMagentaRescuedByIdentity[band];
        if (!fullMag && s0Mag) ++agg->hsmS0CurveMagentaIntroducedVsFull[band];
        if (!fullMag && identityMag) ++agg->identityCurveMagentaIntroducedVsFull[band];
    }
}

inline void upstreamAxisWritePathJson(std::ostringstream& os,
                                      const UpstreamAxisPathAgg& a,
                                      int band,
                                      double den) {
    os << "{\"meanGreenDeficitPreSat\":" << (a.preGreenDeficit[band] / den) << ",";
    os << "\"meanGreenDeficitPostSat3\":" << (a.satGreenDeficit[band] / den) << ",";
    os << "\"meanGreenDeficitPostCurve02\":" << (a.curveGreenDeficit[band] / den) << ",";
    os << "\"meanRelativeSpreadPreSat\":" << (a.preSpread[band] / den) << ",";
    os << "\"meanRelativeSpreadPostSat3\":" << (a.satSpread[band] / den) << ",";
    os << "\"meanRelativeSpreadPostCurve02\":" << (a.curveSpread[band] / den) << ",";
    os << "\"magentaSide1pctFractionPreSat\":" << (a.preMagenta[band] / den) << ",";
    os << "\"magentaSide1pctFractionPostSat3\":" << (a.satMagenta[band] / den) << ",";
    os << "\"magentaSide1pctFractionPostCurve02\":" << (a.curveMagenta[band] / den) << ",";
    os << "\"branchEvenFraction\":" << (a.branchEven[band] / den) << ",";
    os << "\"preSatHighClipFraction\":" << (a.preHighClip[band] / den) << ",";
    os << "\"sat3BoundaryFraction\":" << (a.satBoundary[band] / den) << "}";
}
'''

t = replace_once(t,
                 '\nstd::string auditSatDomainJson(const ColorContext& ctx,',
                 helpers + '\nstd::string auditSatDomainJson(const ColorContext& ctx,',
                 'helper insertion')

t = replace_once(t,
'''    SatDomainFamilyAgg fam[3]{};\n    std::array<SatDomainSample, 6> sat3Samples{};''',
'''    SatDomainFamilyAgg fam[3]{};\n    UpstreamAxisAgg upstreamAxis{};\n    // Exact production HSM evaluator is reused. Replacing every interpolated d1 with 1\n    // makes the HSM saturation multiplier exactly unity while preserving H25 and V100.\n    ColorContext hsmS0Ctx = ctx;\n    for (size_t i = 1; i < hsmS0Ctx.hsm.size(); i += 3) hsmS0Ctx.hsm[i] = 1.0;\n    // Constant [hueDelta=0, satScale=1, valueScale=1] triples make applyHsm() identity.\n    ColorContext identityHsmCtx = ctx;\n    for (size_t i = 0; i + 2 < identityHsmCtx.hsm.size(); i += 3) {\n        identityHsmCtx.hsm[i] = 0.0;\n        identityHsmCtx.hsm[i + 1] = 1.0;\n        identityHsmCtx.hsm[i + 2] = 1.0;\n    }\n    std::array<SatDomainSample, 6> sat3Samples{};''',
                 'audit contexts')

t = replace_once(t,
'''        cameraToM9(cam, c, ctx, hsm, m9);\n        const double u[3] = {m9[0] * gain * RAW_MAX, m9[1] * gain * RAW_MAX, m9[2] * gain * RAW_MAX};''',
'''        cameraToM9(cam, c, ctx, hsm, m9);\n        upstreamAxisAuditPixel(cam, c, ctx, hsmS0Ctx, identityHsmCtx, gain, &upstreamAxis);\n        const double u[3] = {m9[0] * gain * RAW_MAX, m9[1] * gain * RAW_MAX, m9[2] * gain * RAW_MAX};''',
                 'pixel accumulation')

t = replace_once(t,
'''        os << "]},";\n        os << "\\\"spatial3x3\\\":{\\\"pixelCount\\\":[";''',
'''        os << "]},";\n        os << "\\\"upstreamAxisAudit\\\":{\\\"schema\\\":\\\"m9cam.upstreamaxis1a.v1\\\",";\n        os << "\\\"readOnly\\\":true,\\\"renderedPixelsModified\\\":false,";\n        os << "\\\"selection\\\":\\\"production_preSAT_relative_RGB_spread\\\",";\n        os << "\\\"sameHistoricalBasisAllPaths\\\":true,\\\"sameM9BridgeAllPaths\\\":true,";\n        os << "\\\"sameFrozenGainAllPaths\\\":true,\\\"sameSAT3_M06_M07_AllPaths\\\":true,\\\"sameCurve02AllPaths\\\":true,";\n        os << "\\\"hsmS0Construction\\\":\\\"production_HSM_table_with_every_saturation_multiplier_d1_forced_to_1_preserves_H25_V100\\\",";\n        os << "\\\"identityHsmConstruction\\\":\\\"production_HSM_table_replaced_by_constant_0_1_1_triples\\\",";\n        os << "\\\"paths\\\":[\\\"FULL_H25_S85_V100\\\",\\\"HSM_S0_H25_V100\\\",\\\"IDENTITY_HSM\\\"],\\\"bands\\\":[";\n        constexpr double upstreamBands[3] = {0.05, 0.10, 0.20};\n        for (int ub = 0; ub < 3; ++ub) {\n            if (ub) os << ",";\n            const double ud = upstreamAxis.count[ub] ? static_cast<double>(upstreamAxis.count[ub]) : 1.0;\n            os << "{\\\"maxProductionPreSatRelativeSpread\\\":" << upstreamBands[ub] << ",\\\"pixelCount\\\":" << upstreamAxis.count[ub] << ",";\n            os << "\\\"full\\\":"; upstreamAxisWritePathJson(os, upstreamAxis.path[0], ub, ud); os << ",";\n            os << "\\\"hsmS0\\\":"; upstreamAxisWritePathJson(os, upstreamAxis.path[1], ub, ud); os << ",";\n            os << "\\\"identityHsm\\\":"; upstreamAxisWritePathJson(os, upstreamAxis.path[2], ub, ud); os << ",";\n            os << "\\\"branchFlipFullVsHsmS0Fraction\\\":" << (upstreamAxis.branchFlipFullVsS0[ub] / ud) << ",";\n            os << "\\\"branchFlipFullVsIdentityHsmFraction\\\":" << (upstreamAxis.branchFlipFullVsIdentity[ub] / ud) << ",";\n            os << "\\\"fullCurveMagentaRescuedByHsmS0Fraction\\\":" << (upstreamAxis.fullCurveMagentaRescuedByS0[ub] / ud) << ",";\n            os << "\\\"fullCurveMagentaRescuedByIdentityHsmFraction\\\":" << (upstreamAxis.fullCurveMagentaRescuedByIdentity[ub] / ud) << ",";\n            os << "\\\"hsmS0CurveMagentaIntroducedVsFullFraction\\\":" << (upstreamAxis.hsmS0CurveMagentaIntroducedVsFull[ub] / ud) << ",";\n            os << "\\\"identityCurveMagentaIntroducedVsFullFraction\\\":" << (upstreamAxis.identityCurveMagentaIntroducedVsFull[ub] / ud) << "}";\n        }\n        os << "]},";\n        os << "\\\"spatial3x3\\\":{\\\"pixelCount\\\":[";''',
                 'upstream JSON')

t = replace_once(t,
                 'os << "\\\"schema\\\":\\\"m9cam.curvedomain1b.neutralaxis1a.v1\\\",";',
                 'os << "\\\"schema\\\":\\\"m9cam.curvedomain1c.upstreamaxis1a.v1\\\",";',
                 'schema')

CPP.write_text(t)

g = GRADLE.read_text()
g = replace_once(g,
                 '-curvedomain1b-neutralaxis1a-nativewpclip1a',
                 '-curvedomain1c-upstreamaxis1a-nativewpclip1a',
                 'version')
GRADLE.write_text(g)

print('UPSTREAMAXIS1A read-only diagnostic applied')
print(' - production pixels unchanged; alternate paths exist only inside telemetry')
print(' - exact production applyHsm() reused for FULL / HSM-S0 / identity-HSM')
print(' - same historical basis, M9 bridge, gain, M06/M07 and curve02 across paths')
