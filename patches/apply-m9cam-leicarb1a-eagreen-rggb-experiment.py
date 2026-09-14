#!/usr/bin/env python3
from pathlib import Path
import sys

MARKER = "LEICARB1A_SHARPGREEN_RGGB"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} <PhotonCamera root>", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    cpp_path = root / "app/src/main/cpp/m9color_jni.cpp"
    timing_path = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java"
    if not cpp_path.is_file() or not timing_path.is_file():
        raise RuntimeError("assembled SHARPSOURCE1C baseline missing")

    cpp = cpp_path.read_text()
    timing = timing_path.read_text()
    if MARKER in cpp or MARKER in timing:
        raise RuntimeError("LEICARB1A experiment already present")
    if "SHARPNESS_SHARPSOURCE1C_RBANCHOR1A_ID" not in cpp:
        raise RuntimeError("LEICARB1A requires assembled SHARPSOURCE1C-RBANCHOR1A parent")
    if "m9SharpSourceLeicaGreen14" not in cpp:
        raise RuntimeError("LEICARB1A requires Leica green-source plane")

    # The active SHARPSOURCE1C path already has the exact experiment seam we want:
    # sharpened Leica-derived green is the RGB anchor; MHC R-G/B-G are explicitly
    # temporary proxy differences. Replace those proxy differences only.
    helper_anchor = '''inline uint16_t m9ClosureQ16(uint16_t v){
    return static_cast<uint16_t>((static_cast<uint32_t>(v)*65535u + 8191u)/16383u);
}
'''
    helpers = r'''

// LEICARB1A_SHARPGREEN_RGGB_BEGIN
// Android research experiment at the active SHARPSOURCE1C R/B seam.
//
// Scope/claim:
// - Green source and Standard/mode4 Sharp path remain exactly the assembled parent.
// - R/B proxy differences are replaced by the bit-exact arithmetic semantics closed
//   against ASMRedBlueInterpolation1.
// - The RGGB raw-grid adapter (native R even/even, native B odd/odd) is an Android
//   placement assumption; this is NOT yet a claim of the complete M9 Run/pre-Green path.
// - support_before=8 -> Leica routine increments to support_after=9, exactly matching
//   the existing firmware-proven accumulated 9-pixel valid interior.
inline int16_t m9LeicaRbS16(uint16_t v){ return static_cast<int16_t>(v); }
inline int32_t m9LeicaRbAsr1(int32_t v){
    return v>=0 ? (v/2) : -static_cast<int32_t>((static_cast<uint32_t>(-v)+1u)/2u);
}
inline int16_t m9LeicaRbSat16(int32_t v){
    if(v < -32768) return static_cast<int16_t>(-32768);
    if(v > 32767) return static_cast<int16_t>(32767);
    return static_cast<int16_t>(v);
}
inline int16_t m9LeicaRbWrap16(int32_t v){
    return static_cast<int16_t>(static_cast<uint16_t>(v));
}
inline int16_t m9LeicaRbHAvg(int16_t a,int16_t b){
    return static_cast<int16_t>(m9LeicaRbAsr1(static_cast<int32_t>(m9LeicaRbSat16(static_cast<int32_t>(a)+static_cast<int32_t>(b)))));
}
inline int16_t m9LeicaRbWrapAvg(int16_t a,int16_t b){
    const int16_t s=m9LeicaRbWrap16(static_cast<int32_t>(a)+static_cast<int32_t>(b));
    return static_cast<int16_t>(m9LeicaRbAsr1(static_cast<int32_t>(s)));
}
inline int16_t m9LeicaRbDiagAvg(int16_t a,int16_t b,int16_t c,int16_t d){
    return m9LeicaRbWrapAvg(m9LeicaRbHAvg(a,b),m9LeicaRbHAvg(c,d));
}
inline uint16_t m9LeicaRbFinalAdd(uint16_t green,int16_t diff){
    const int16_t sum=m9LeicaRbWrap16(static_cast<int32_t>(m9LeicaRbS16(green))+static_cast<int32_t>(diff));
    const int32_t v=static_cast<int32_t>(sum);
    if(v<0) return 0;
    if(v>0x3fff) return 0x3fff;
    return static_cast<uint16_t>(v);
}
inline int16_t m9LeicaRbNativeDiff(const jshort* raw,const std::vector<uint16_t>& green14,
                                   int width,int y,int x){
    const size_t q=static_cast<size_t>(y)*static_cast<size_t>(width)+static_cast<size_t>(x);
    const uint16_t raw14=m9ClosureQ14(u16(raw[q]));
    return m9LeicaRbWrap16(static_cast<int32_t>(raw14)-static_cast<int32_t>(green14[q]));
}
inline int16_t m9LeicaRbEstimate(const jshort* raw,const std::vector<uint16_t>& green14,
                                 int width,int y,int x,int parity){
    const int p=parity&1;
    if((y&1)==p && (x&1)==p)
        return m9LeicaRbNativeDiff(raw,green14,width,y,x);
    if((y&1)==p)
        return m9LeicaRbHAvg(
                m9LeicaRbNativeDiff(raw,green14,width,y,x-1),
                m9LeicaRbNativeDiff(raw,green14,width,y,x+1));
    if((x&1)==p)
        return m9LeicaRbWrapAvg(
                m9LeicaRbNativeDiff(raw,green14,width,y-1,x),
                m9LeicaRbNativeDiff(raw,green14,width,y+1,x));
    return m9LeicaRbDiagAvg(
            m9LeicaRbNativeDiff(raw,green14,width,y-1,x-1),
            m9LeicaRbNativeDiff(raw,green14,width,y-1,x+1),
            m9LeicaRbNativeDiff(raw,green14,width,y+1,x-1),
            m9LeicaRbNativeDiff(raw,green14,width,y+1,x+1));
}
// LEICARB1A_SHARPGREEN_RGGB_HELPERS_END
'''
    cpp = replace_once(cpp, helper_anchor, helper_anchor + helpers, "q16 helper insertion")

    old = '''                        // GreenInterpolationWithCo(+3) + Noise mode2(+4) + Sharp(+2)
                        // gives the firmware-proven cumulative support margin of 9 px.
                        if(x>=9 && x<width-9 && y>=9 && y<height-9){
                            // SHARPSOURCE1C-RBANCHOR1A: do not graft a Leica-source Sharp
                            // delta onto a different MHC-green baseline. Anchor reconstructed
                            // RGB to the sharpened Leica green/base exactly, then carry the
                            // frozen neutral-MHC R-G and B-G differences only as temporary
                            // colour-difference proxies until exact BF561 lane semantics close.
                            const int sg=static_cast<int>(closureSharp14[p]);
                            const int mg=static_cast<int>(m9ClosureQ14(base[1]));
                            const int dr=static_cast<int>(m9ClosureQ14(base[0]))-mg;
                            const int db=static_cast<int>(m9ClosureQ14(base[2]))-mg;
                            dst[0]=m9ClosureQ16(m9ClosureClamp14(sg+dr));
                            dst[1]=m9ClosureQ16(static_cast<uint16_t>(sg));
                            dst[2]=m9ClosureQ16(m9ClosureClamp14(sg+db));
                        }else{
                            // Outside Leica's valid accumulated support region, leave the
                            // validated frozen neutral-MHC output byte-for-byte untouched.
                            dst[0]=base[0]; dst[1]=base[1]; dst[2]=base[2];
                        }'''
    new = '''                        // GreenInterpolationWithCo(+3) + Noise mode2(+4) + Sharp(+2)
                        // gives the firmware-proven cumulative support margin of 9 px.
                        if(x>=9 && x<width-9 && y>=9 && y<height-9){
                            // LEICARB1A_SHARPGREEN_RGGB: replace only RBANCHOR1A's temporary
                            // MHC colour-difference proxies. Leica Interp1 support_before=8
                            // increments to 9: plane A parity0 -> RGGB red, plane B parity1 -> blue.
                            // Build native-site R-G/B-G against the pre-Sharp Leica green source,
                            // run the exact recovered directional signed-16 interpolation, then
                            // apply the already-frozen Leica Sharp delta equally as the current
                            // SHARPSOURCE architecture does.
                            const int16_t redDiff=m9LeicaRbEstimate(raw,sharpSourceGreen14,width,y,x,0);
                            const int16_t blueDiff=m9LeicaRbEstimate(raw,sharpSourceGreen14,width,y,x,1);
                            const uint16_t preSharpR=m9LeicaRbFinalAdd(sharpSourceGreen14[p],redDiff);
                            const uint16_t preSharpB=m9LeicaRbFinalAdd(sharpSourceGreen14[p],blueDiff);
                            const int sharpDelta=static_cast<int>(closureSharp14[p])-static_cast<int>(sharpSourceGreen14[p]);
                            const uint16_t r14=m9ClosureClamp14(static_cast<int>(preSharpR)+sharpDelta);
                            const uint16_t g14=closureSharp14[p];
                            const uint16_t b14=m9ClosureClamp14(static_cast<int>(preSharpB)+sharpDelta);
                            dst[0]=m9ClosureQ16(r14);
                            dst[1]=m9ClosureQ16(g14);
                            dst[2]=m9ClosureQ16(b14);
                        }else{
                            // Outside Leica's valid accumulated support region, preserve the
                            // validated frozen neutral-MHC output byte-for-byte.
                            dst[0]=base[0]; dst[1]=base[1]; dst[2]=base[2];
                        }'''
    cpp = replace_once(cpp, old, new, "SHARPSOURCE1C R/B proxy seam")

    old_id = '// SHARPNESS_SHARPSOURCE1C_RBANCHOR1A_ID: menu=Standard slot=0 internalMode=4 scale=2x nNoise=2 supportMargin=9 sharpSource=LeicaGreen14 rgbFoundation=MHCNeutralFrozen rbPolicy=sharpLeicaGreen_plus_frozenMhcRgBg_differences'
    new_id = '// SHARPNESS_SHARPSOURCE1C_RBANCHOR1A_ID: menu=Standard slot=0 internalMode=4 scale=2x nNoise=2 supportMargin=9 sharpSource=LeicaGreen14 rgbFoundation=MHCNeutralFrozen rbPolicy=LEICARB1A_SHARPGREEN_RGGB_exactInterp1Arithmetic_rawGridAdapter'
    cpp = replace_once(cpp, old_id, new_id, "native identity")
    cpp_path.write_text(cpp)

    old_policy = '        root.put("sharpnessRbPolicy", "RBANCHOR1A_sharpLeicaGreen_plus_frozenMHC_color_differences_proxy");\n'
    new_policy = (
        '        root.put("sharpnessRbPolicy", "LEICARB1A_SHARPGREEN_RGGB_exactInterp1Arithmetic_rawGridAdapter");\n'
        '        root.put("leicaRbExperiment", "LEICARB1A_SHARPGREEN_RGGB");\n'
        '        root.put("leicaRbSupportBefore", 8);\n'
        '        root.put("leicaRbSupportAfter", 9);\n'
        '        root.put("leicaRbRedLatticeParity", 0);\n'
        '        root.put("leicaRbBlueLatticeParity", 1);\n'
        '        root.put("leicaRbArithmetic", "Interp1_bit_exact_hSat16_verticalWrap16_diagonal_hThenWrap_finalWrapClamp14");\n'
        '        root.put("leicaRbClaim", "android_raw_grid_adapter_experiment_not_full_M9_Run_preGreen_parity");\n'
    )
    timing = replace_once(timing, old_policy, new_policy, "primary timing R/B policy")
    timing_path.write_text(timing)

    print("LEICARB1A_SHARPGREEN_RGGB applied")
    print(" - active SHARPSOURCE1C sharpened Leica green preserved")
    print(" - MHC R-G/B-G proxy terms replaced only in 9px interior")
    print(" - exact Interp1 signed-16 horizontal/vertical/diagonal/final-add arithmetic")
    print(" - support_before=8 -> support_after=9; RGGB parity0 red / parity1 blue")
    print(" - raw-grid placement remains experimental; full M9 Run/pre-Green parity not claimed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
