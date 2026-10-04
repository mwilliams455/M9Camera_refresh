#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-cfaabstract1b-ultrawide1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
native_java_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java'
native_cpp_path = root / 'app/src/main/cpp/m9color_jni.cpp'
renderer = renderer_path.read_text()
native_java = native_java_path.read_text()
native_cpp = native_cpp_path.read_text()


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'CFAABSTRACT1B {label}: expected one anchor, found {count}')
    return text.replace(old, new, 1)


def extract_braced(text, marker):
    start = text.find(marker)
    if start < 0:
        raise SystemExit('CFAABSTRACT1B missing frozen anchor: ' + marker)
    brace = text.find('{', start)
    if brace < 0:
        raise SystemExit('CFAABSTRACT1B missing opening brace: ' + marker)
    depth = 0
    for i in range(brace, len(text)):
        c = text[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise SystemExit('CFAABSTRACT1B unterminated block: ' + marker)


# Freeze the exact validated RGGB implementations before adding the new route.
legacy_mhc = extract_braced(native_cpp,
        'Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_demosaicMhcRggb(')
legacy_gain = extract_braced(renderer,
        'private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(\n')
legacy_gain_luma = extract_braced(renderer,
        'private static NativeProspectiveShadingStats applyNativeProspectiveGainMapLumaDecomp1A(\n')

# Outer fail-closed gate: permit only conventional Bayer values 0..3.
renderer = replace_once(renderer,
'''            // Frozen main-camera R3.5 reference is RGGB.  Fail loudly rather than
            // silently applying the wrong Bayer interpretation to another lens.
            if (params.cfaPattern != 0) {
                throw new IllegalStateException("R3.5 v0.7 main-camera parity build expects RGGB CFA=0, got " + params.cfaPattern);
            }
''',
'''            // CFAABSTRACT1B: accept only the four conventional Bayer layouts.
            // CFA=0 remains on the exact validated legacy RGGB implementation.
            final int sourceCfaPattern = params.cfaPattern & 0xff;
            if (!M9CfaResolver.isSupported(sourceCfaPattern)) {
                throw new IllegalStateException("CFAABSTRACT1B unsupported Bayer CFA=" + sourceCfaPattern);
            }
''', 'source CFA gate')

# Thread the captured CFA value into every native-source render, including exact rerenders.
renderer = replace_once(renderer,
'''                    encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation, 0.0,
                    characteristics, diagnosticCaptureResult1A);
''',
'''                    encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation, 0.0,
                    characteristics, diagnosticCaptureResult1A, sourceCfaPattern);
''', 'primary production call')
renderer = replace_once(renderer,
'''                                cameraRotation, candidateEv,
                                characteristics, diagnosticCaptureResult1A);
''',
'''                                cameraRotation, candidateEv,
                                characteristics, diagnosticCaptureResult1A, sourceCfaPattern);
''', 'edge rerender call')
renderer = replace_once(renderer,
'''                                        cameraRotation, selfMeter ? primaryEdgeEv : 0.0,
                                        characteristics, physicalResult,
                                        variantFixedGain, applyShading, bridgeProbeMode, selfMeter,
''',
'''                                        cameraRotation, selfMeter ? primaryEdgeEv : 0.0,
                                        characteristics, physicalResult, sourceCfaPattern,
                                        variantFixedGain, applyShading, bridgeProbeMode, selfMeter,
''', 'diagnostic prospective call')
renderer = replace_once(renderer,
'''                                         double edgePlacementGainEv,
                                         CameraCharacteristics nativeCharacteristics,
                                         CaptureResult nativeCaptureResult) throws Exception {
''',
'''                                         double edgePlacementGainEv,
                                         CameraCharacteristics nativeCharacteristics,
                                         CaptureResult nativeCaptureResult,
                                         int sourceCfaPattern) throws Exception {
''', 'production signature')
renderer = replace_once(renderer,
'''                cameraRotation, edgePlacementGainEv,
                nativeCharacteristics, nativeCaptureResult,
                1.0,
''',
'''                cameraRotation, edgePlacementGainEv,
                nativeCharacteristics, nativeCaptureResult, sourceCfaPattern,
                1.0,
''', 'production to core')
renderer = replace_once(renderer,
'''                                         double edgePlacementGainEv,
                                         CameraCharacteristics nativeCharacteristics,
                                         CaptureResult nativeCaptureResult,
                                         double fixedPrimaryGain,
''',
'''                                         double edgePlacementGainEv,
                                         CameraCharacteristics nativeCharacteristics,
                                         CaptureResult nativeCaptureResult,
                                         int sourceCfaPattern,
                                         double fixedPrimaryGain,
''', 'core signature')
renderer = replace_once(renderer,
'''        final boolean demosaicNeutralEa1A = bridgeProbeMode == 54;
        final boolean demosaicPlainMhc1A = bridgeProbeMode == 55;
''',
'''        final boolean demosaicNeutralEa1A = bridgeProbeMode == 54;
        final boolean demosaicPlainMhc1A = bridgeProbeMode == 55;
        // DEVICEPORT1A deliberately did not infer RAW origin from active-array metadata.
        // Current Xiaomi 15 Ultra full-frame RAW validation is origin0; keep this explicit.
        final int sourceRawOriginX = 0;
        final int sourceRawOriginY = 0;
''', 'explicit origin0 seam')

# Source-domain lens shading.  RGGB/origin0 takes the untouched legacy function.
renderer = replace_once(renderer,
'''        NativeProspectiveShadingStats nativeShading = applyNativeShading
                ? (applyShadingLumaDecomp1A
                        ? applyNativeProspectiveGainMapLumaDecomp1A(
                                norm16, width, height, nativeLiveGainMap, effectiveShadingLumaAuthorityAlpha)
                        : applyNativeProspectiveGainMap(norm16, width, height, nativeLiveGainMap))
                : NativeProspectiveShadingStats.none();
''',
'''        NativeProspectiveShadingStats nativeShading = applyNativeShading
                ? (applyShadingLumaDecomp1A
                        ? (sourceCfaPattern == 0 && sourceRawOriginX == 0 && sourceRawOriginY == 0
                                ? applyNativeProspectiveGainMapLumaDecomp1A(
                                        norm16, width, height, nativeLiveGainMap, effectiveShadingLumaAuthorityAlpha)
                                : applyNativeProspectiveGainMapLumaDecomp1ABayer(
                                        norm16, width, height, nativeLiveGainMap, effectiveShadingLumaAuthorityAlpha,
                                        sourceCfaPattern, sourceRawOriginX, sourceRawOriginY))
                        : (sourceCfaPattern == 0 && sourceRawOriginX == 0 && sourceRawOriginY == 0
                                ? applyNativeProspectiveGainMap(norm16, width, height, nativeLiveGainMap)
                                : applyNativeProspectiveGainMapBayer(
                                        norm16, width, height, nativeLiveGainMap,
                                        sourceCfaPattern, sourceRawOriginX, sourceRawOriginY)))
                : NativeProspectiveShadingStats.none();
''', 'shading dispatch')

# Demosaic dispatch.  The production RGGB path remains literally the old JNI method.
renderer = replace_once(renderer,
'''            if (demosaicNeutralEa1A) {
                rawMat.put(0, 0, norm16);
                Imgproc.cvtColor(rawMat, cam16, Imgproc.COLOR_BayerRG2BGR_EA);
                rawMat.release();
            } else {
                long mhcNativeNs = M9NativeColorCore.demosaicMhcRggb(
                        norm16,width,height,mhcRgbBuffer,NATIVE_COLOR_WORKERS,
                        neutralF[0],neutralF[1],neutralF[2],!demosaicPlainMhc1A,mhcStats);
                if(mhcNativeNs<0) throw new IllegalStateException("DEMOSAICMHCNEUTRAL1A native failure: "+mhcNativeNs);
            }
''',
'''            if (demosaicNeutralEa1A) {
                if (sourceCfaPattern != 0 || sourceRawOriginX != 0 || sourceRawOriginY != 0) {
                    throw new IllegalStateException(
                            "CFAABSTRACT1B OpenCV diagnostic control remains RGGB/origin0 only");
                }
                rawMat.put(0, 0, norm16);
                Imgproc.cvtColor(rawMat, cam16, Imgproc.COLOR_BayerRG2BGR_EA);
                rawMat.release();
            } else {
                final long mhcNativeNs;
                if (sourceCfaPattern == 0 && sourceRawOriginX == 0 && sourceRawOriginY == 0) {
                    // Exact validated 15U-main path.
                    mhcNativeNs = M9NativeColorCore.demosaicMhcRggb(
                            norm16,width,height,mhcRgbBuffer,NATIVE_COLOR_WORKERS,
                            neutralF[0],neutralF[1],neutralF[2],!demosaicPlainMhc1A,mhcStats);
                } else {
                    mhcNativeNs = M9NativeColorCore.demosaicMhcBayer(
                            norm16,width,height,sourceCfaPattern,sourceRawOriginX,sourceRawOriginY,
                            mhcRgbBuffer,NATIVE_COLOR_WORKERS,
                            neutralF[0],neutralF[1],neutralF[2],!demosaicPlainMhc1A,mhcStats);
                }
                if(mhcNativeNs<0) throw new IllegalStateException("DEMOSAICMHCNEUTRAL1A native failure: "+mhcNativeNs);
            }
''', 'demosaic dispatch')

# Generic LensShadingMap variants.  Android channel order is semantic:
# [R, G-even-sensor-row, G-odd-sensor-row, B].
gain_insert = r'''    // CFAABSTRACT1B: same LensShadingMap arithmetic as the frozen RGGB helper,
    // with only Bayer sample -> Camera2 semantic channel lookup generalized.
    private static int gainMapPlaneForBayer(int x, int y, int cfaPattern, int originX, int originY) {
        return M9CfaResolver.lensShadingChannelAt(x, y, cfaPattern, originX, originY);
    }

    private static NativeProspectiveShadingStats applyNativeProspectiveGainMapLumaDecomp1ABayer(
            short[] norm16, int width, int height, LensShadingMap map, double alpha,
            int cfaPattern, int originX, int originY) {
        if (map == null) throw new IllegalStateException("CFAABSTRACT1B shading render requires physical LensShadingMap");
        if (!M9CfaResolver.isSupported(cfaPattern)) throw new IllegalArgumentException("CFAABSTRACT1B unsupported CFA=" + cfaPattern);
        if (!Double.isFinite(alpha) || alpha < 0.0 || alpha > 1.0) throw new IllegalArgumentException("SHADINGLUMADECOMP1A alpha out of range: " + alpha);
        final int mapW=map.getColumnCount(), mapH=map.getRowCount(), cells=mapW*mapH; float[] src=new float[map.getGainFactorCount()]; map.copyGainFactors(src,0);
        if(mapW<1||mapH<1||src.length!=cells*4) throw new IllegalStateException("SHADINGLUMADECOMP1A invalid map dimensions");
        double[] gains=new double[src.length]; double minGain=Double.POSITIVE_INFINITY,maxGain=Double.NEGATIVE_INFINITY;
        for(int cell=0;cell<cells;cell++) { int base=cell*4; double ls=0.0; for(int p=0;p<4;p++){double g=src[base+p]; if(!Double.isFinite(g)||g<=0.0)throw new IllegalStateException("SHADINGLUMADECOMP1A invalid gain"); ls+=Math.log(g);} double gc=Math.exp(0.25*ls), ca=Math.exp(alpha*Math.log(gc)); for(int p=0;p<4;p++){double g=(src[base+p]/gc)*ca; gains[base+p]=g; minGain=Math.min(minGain,g); maxGain=Math.max(maxGain,g);} }
        final double representationScale=maxGain; if(!Double.isFinite(representationScale)||representationScale<=0.0)throw new IllegalStateException("SHADINGLUMADECOMP1A invalid representation scale");
        final double xScale=width>1?(mapW-1.0)/(width-1.0):0.0, yScale=height>1?(mapH-1.0)/(height-1.0):0.0; long corrected=0,aboveNominal=0,postClip=0;
        for(int y=0;y<height;y++){double gy=y*yScale;int y0=(int)Math.floor(gy),y1=Math.min(mapH-1,y0+1);double fy=gy-y0;int row=y*width;for(int x=0;x<width;x++){double gx=x*xScale;int x0=(int)Math.floor(gx),x1=Math.min(mapW-1,x0+1);double fx=gx-x0;int plane=gainMapPlaneForBayer(x,y,cfaPattern,originX,originY);int i00=((y0*mapW+x0)*4)+plane,i01=((y0*mapW+x1)*4)+plane,i10=((y1*mapW+x0)*4)+plane,i11=((y1*mapW+x1)*4)+plane;double g0=gains[i00]+fx*(gains[i01]-gains[i00]),g1=gains[i10]+fx*(gains[i11]-gains[i10]),gain=g0+fy*(g1-g0);int index=row+x;double normalized=(norm16[index]&0xffff)/65535.0,correctedLinear=normalized*gain;if(correctedLinear>1.0)aboveNominal++;double represented=correctedLinear/representationScale;if(represented<-1e-12||represented>1.0+1e-12)postClip++;represented=Math.max(0.0,Math.min(1.0,represented));int q=(int)Math.floor(represented*65535.0+0.5);norm16[index]=(short)(q&0xffff);corrected++;}}
        if(postClip!=0)throw new IllegalStateException("SHADINGLUMADECOMP1A representation scaling clipped: "+postClip);
        return new NativeProspectiveShadingStats(true,mapW,mapH,minGain,maxGain,corrected,representationScale,aboveNominal,postClip);
    }

    private static NativeProspectiveShadingStats applyNativeProspectiveGainMapBayer(
            short[] norm16, int width, int height, LensShadingMap map,
            int cfaPattern, int originX, int originY) {
        if (map == null) throw new IllegalStateException("CFAABSTRACT1B source+shading requires live physical LensShadingMap");
        if (!M9CfaResolver.isSupported(cfaPattern)) throw new IllegalArgumentException("CFAABSTRACT1B unsupported CFA=" + cfaPattern);
        final int mapW=map.getColumnCount(), mapH=map.getRowCount(); float[] gains=new float[map.getGainFactorCount()]; map.copyGainFactors(gains,0);
        if(mapW<1||mapH<1||gains.length!=mapW*mapH*4)throw new IllegalStateException("CFAABSTRACT1B invalid LensShadingMap dimensions");
        double minGain=Double.POSITIVE_INFINITY,maxGain=Double.NEGATIVE_INFINITY;
        for(float g:gains){if(!Float.isFinite(g)||g<=0.0f)throw new IllegalStateException("CFAABSTRACT1B invalid LensShadingMap factor");minGain=Math.min(minGain,g);maxGain=Math.max(maxGain,g);}
        if(!Double.isFinite(maxGain)||maxGain<=0.0)throw new IllegalStateException("CFAABSTRACT1B invalid LensShadingMap max gain");
        final double representationScale=maxGain, xScale=width>1?(mapW-1.0)/(width-1.0):0.0, yScale=height>1?(mapH-1.0)/(height-1.0):0.0; long corrected=0,aboveNominal=0,postScaleClip=0;
        for(int y=0;y<height;y++){double gy=y*yScale;int y0=(int)Math.floor(gy),y1=Math.min(mapH-1,y0+1);double fy=gy-y0;int row=y*width;for(int x=0;x<width;x++){double gx=x*xScale;int x0=(int)Math.floor(gx),x1=Math.min(mapW-1,x0+1);double fx=gx-x0;int plane=gainMapPlaneForBayer(x,y,cfaPattern,originX,originY);int i00=((y0*mapW+x0)*4)+plane,i01=((y0*mapW+x1)*4)+plane,i10=((y1*mapW+x0)*4)+plane,i11=((y1*mapW+x1)*4)+plane;double g0=gains[i00]+fx*(gains[i01]-gains[i00]),g1=gains[i10]+fx*(gains[i11]-gains[i10]),gain=g0+fy*(g1-g0);int index=row+x;double normalized=(norm16[index]&0xffff)/65535.0,correctedLinear=normalized*gain;if(correctedLinear>1.0)aboveNominal++;double represented=correctedLinear/representationScale;if(represented<-1e-12||represented>1.0+1e-12)postScaleClip++;represented=Math.max(0.0,Math.min(1.0,represented));int q=(int)Math.floor(represented*65535.0+0.5);norm16[index]=(short)(q&0xffff);corrected++;}}
        if(postScaleClip!=0)throw new IllegalStateException("CFAABSTRACT1B representation scaling lost linear headroom: clipCount="+postScaleClip);
        return new NativeProspectiveShadingStats(true,mapW,mapH,minGain,maxGain,corrected,representationScale,aboveNominal,postScaleClip);
    }

'''
stat_anchor = '    private static final class NativeProspectiveShadingStats {\n'
if renderer.count(stat_anchor) != 1:
    raise SystemExit('CFAABSTRACT1B shading insertion anchor missing/ambiguous')
renderer = renderer.replace(stat_anchor, gain_insert + stat_anchor, 1)

# Java JNI declaration: legacy method stays unchanged, generic method is additive.
old_decl = '''    static native long demosaicMhcRggb(short[] raw,
                                       int width,
                                       int height,
                                       java.nio.ByteBuffer outRgb16,
                                       int workers,
                                       float neutralR, float neutralG, float neutralB,
                                       boolean neutralAware,
                                       long[] stats);
'''
new_decl = old_decl + '''
    /** CFAABSTRACT1B: conventional Bayer adapter for non-RGGB source sensors. */
    static native long demosaicMhcBayer(short[] raw,
                                        int width,
                                        int height,
                                        int cfaPattern,
                                        int originX,
                                        int originY,
                                        java.nio.ByteBuffer outRgb16,
                                        int workers,
                                        float neutralR, float neutralG, float neutralB,
                                        boolean neutralAware,
                                        long[] stats);
'''
native_java = replace_once(native_java, old_decl, new_decl, 'native Java declaration')

# Native source adapter.  All four Bayer layouts are RGGB phase variants.
cpp_helpers = r'''
// CFAABSTRACT1B: conventional Bayer source adapter.  All four Camera2 Bayer
// patterns are RGGB with a 2x2 phase: RGGB=(0,0), GRBG=(1,0), GBRG=(0,1), BGGR=(1,1).
// The validated legacy RGGB/origin0 functions remain untouched and are still used for CFA=0.
inline int m9PhaseParity(int v){ int r=v%2; return r<0?r+2:r; }
inline bool m9PhaseEvenX(int x,int phaseX){ return m9PhaseParity(x+phaseX)==0; }
inline bool m9PhaseEvenY(int y,int phaseY){ return m9PhaseParity(y+phaseY)==0; }
inline double mhcNAtBayerPhase(const jshort* raw,int w,int h,int y,int x,double ir,double ib,
                               int phaseX,int phaseY){
    y=mhcClampCoord(y,h); x=mhcClampCoord(x,w);
    const bool ey=m9PhaseEvenY(y,phaseY), ex=m9PhaseEvenX(x,phaseX);
    const double k=(ey&&ex)?ir:((!ey&&!ex)?ib:1.0);
    return static_cast<double>(u16(raw[y*w+x]))*k;
}
inline void mhcPixelBayerPhase(const jshort* raw,int w,int h,int y,int x,uint16_t* rgb,
                               int phaseX,int phaseY){
    const int64_t C=mhcAt(raw,w,h,y,x),N=mhcAt(raw,w,h,y-1,x),S=mhcAt(raw,w,h,y+1,x),W=mhcAt(raw,w,h,y,x-1),E=mhcAt(raw,w,h,y,x+1);
    const int64_t NN=mhcAt(raw,w,h,y-2,x),SS=mhcAt(raw,w,h,y+2,x),WW=mhcAt(raw,w,h,y,x-2),EE=mhcAt(raw,w,h,y,x+2);
    const int64_t NW=mhcAt(raw,w,h,y-1,x-1),NE=mhcAt(raw,w,h,y-1,x+1),SW=mhcAt(raw,w,h,y+1,x-1),SE=mhcAt(raw,w,h,y+1,x+1);
    const int64_t g8=4*C+2*(N+S+W+E)-(NN+SS+WW+EE);
    const int64_t o16=12*C+4*(NW+NE+SW+SE)-3*(NN+SS+WW+EE);
    const int64_t h16=10*C+8*(W+E)+(NN+SS)-2*(NW+NE+SW+SE)-2*(WW+EE);
    const int64_t v16=10*C+8*(N+S)+(WW+EE)-2*(NW+NE+SW+SE)-2*(NN+SS);
    const bool ey=m9PhaseEvenY(y,phaseY), ex=m9PhaseEvenX(x,phaseX);
    if(ey&&ex){rgb[0]=static_cast<uint16_t>(C);rgb[1]=mhcSat16From8ths(g8);rgb[2]=mhcSat16From16ths(o16);}
    else if(!ey&&!ex){rgb[0]=mhcSat16From16ths(o16);rgb[1]=mhcSat16From8ths(g8);rgb[2]=static_cast<uint16_t>(C);}
    else if(ey){rgb[0]=mhcSat16From16ths(h16);rgb[1]=static_cast<uint16_t>(C);rgb[2]=mhcSat16From16ths(v16);}
    else{rgb[0]=mhcSat16From16ths(v16);rgb[1]=static_cast<uint16_t>(C);rgb[2]=mhcSat16From16ths(h16);}
}
inline uint16_t mhcNeutralGreenBayerPhase(const jshort* raw,int w,int h,int y,int x,double ir,double ib,
                                          int phaseX,int phaseY){
    const bool ey=m9PhaseEvenY(y,phaseY), ex=m9PhaseEvenX(x,phaseX);
    if(ey!=ex)return u16(raw[y*w+x]);
    const double C=mhcNAtBayerPhase(raw,w,h,y,x,ir,ib,phaseX,phaseY),N=mhcNAtBayerPhase(raw,w,h,y-1,x,ir,ib,phaseX,phaseY),S=mhcNAtBayerPhase(raw,w,h,y+1,x,ir,ib,phaseX,phaseY),W=mhcNAtBayerPhase(raw,w,h,y,x-1,ir,ib,phaseX,phaseY),E=mhcNAtBayerPhase(raw,w,h,y,x+1,ir,ib,phaseX,phaseY);
    const double NN=mhcNAtBayerPhase(raw,w,h,y-2,x,ir,ib,phaseX,phaseY),SS=mhcNAtBayerPhase(raw,w,h,y+2,x,ir,ib,phaseX,phaseY),WW=mhcNAtBayerPhase(raw,w,h,y,x-2,ir,ib,phaseX,phaseY),EE=mhcNAtBayerPhase(raw,w,h,y,x+2,ir,ib,phaseX,phaseY);
    return mhcND((4*C+2*(N+S+W+E)-(NN+SS+WW+EE))/8.0);
}
inline void mhcPixelNeutralRbCompleteBayerPhase(const jshort* raw,int w,int h,int y,int x,uint16_t green,uint16_t* rgb,
                                                double nr,double nb,double ir,double ib,int phaseX,int phaseY){
    const double C=mhcNAtBayerPhase(raw,w,h,y,x,ir,ib,phaseX,phaseY),N=mhcNAtBayerPhase(raw,w,h,y-1,x,ir,ib,phaseX,phaseY),S=mhcNAtBayerPhase(raw,w,h,y+1,x,ir,ib,phaseX,phaseY),W=mhcNAtBayerPhase(raw,w,h,y,x-1,ir,ib,phaseX,phaseY),E=mhcNAtBayerPhase(raw,w,h,y,x+1,ir,ib,phaseX,phaseY);
    const double NN=mhcNAtBayerPhase(raw,w,h,y-2,x,ir,ib,phaseX,phaseY),SS=mhcNAtBayerPhase(raw,w,h,y+2,x,ir,ib,phaseX,phaseY),WW=mhcNAtBayerPhase(raw,w,h,y,x-2,ir,ib,phaseX,phaseY),EE=mhcNAtBayerPhase(raw,w,h,y,x+2,ir,ib,phaseX,phaseY);
    const double NW=mhcNAtBayerPhase(raw,w,h,y-1,x-1,ir,ib,phaseX,phaseY),NE=mhcNAtBayerPhase(raw,w,h,y-1,x+1,ir,ib,phaseX,phaseY),SW=mhcNAtBayerPhase(raw,w,h,y+1,x-1,ir,ib,phaseX,phaseY),SE=mhcNAtBayerPhase(raw,w,h,y+1,x+1,ir,ib,phaseX,phaseY);
    const double o=(12*C+4*(NW+NE+SW+SE)-3*(NN+SS+WW+EE))/16.0;
    const double hh=(10*C+8*(W+E)+(NN+SS)-2*(NW+NE+SW+SE)-2*(WW+EE))/16.0;
    const double vv=(10*C+8*(N+S)+(WW+EE)-2*(NW+NE+SW+SE)-2*(NN+SS))/16.0;
    const bool ey=m9PhaseEvenY(y,phaseY), ex=m9PhaseEvenX(x,phaseX); const uint16_t sm=u16(raw[y*w+x]);
    if(ey&&ex){rgb[0]=sm;rgb[1]=green;rgb[2]=mhcND(o*nb);}
    else if(!ey&&!ex){rgb[0]=mhcND(o*nr);rgb[1]=green;rgb[2]=sm;}
    else if(ey){rgb[0]=mhcND(hh*nr);rgb[1]=sm;rgb[2]=mhcND(vv*nb);}
    else{rgb[0]=mhcND(vv*nr);rgb[1]=sm;rgb[2]=mhcND(hh*nb);}
}
inline void m9SharpSourceLeicaGreen14BayerPhase(const jshort* raw,int w,int h,std::vector<uint16_t>& dst,
                                                int phaseX,int phaseY){
    const size_t n=static_cast<size_t>(w)*static_cast<size_t>(h); dst.resize(n);
    for(int y=0;y<h;++y)for(int x=0;x<w;++x){
        const size_t p=static_cast<size_t>(y)*static_cast<size_t>(w)+static_cast<size_t>(x);
        const bool ey=m9PhaseEvenY(y,phaseY), ex=m9PhaseEvenX(x,phaseX); int g;
        if(ey==ex){
            g=(static_cast<int>(m9SharpSourceRaw14At(raw,w,h,y-1,x))+static_cast<int>(m9SharpSourceRaw14At(raw,w,h,y+1,x))+static_cast<int>(m9SharpSourceRaw14At(raw,w,h,y,x-1))+static_cast<int>(m9SharpSourceRaw14At(raw,w,h,y,x+1)))/4;
        }else{
            g=(4*static_cast<int>(m9SharpSourceRaw14At(raw,w,h,y,x))+static_cast<int>(m9SharpSourceRaw14At(raw,w,h,y-1,x-1))+static_cast<int>(m9SharpSourceRaw14At(raw,w,h,y-1,x+1))+static_cast<int>(m9SharpSourceRaw14At(raw,w,h,y+1,x-1))+static_cast<int>(m9SharpSourceRaw14At(raw,w,h,y+1,x+1)))/8;
        }
        dst[p]=static_cast<uint16_t>(g<0?0:(g>16383?16383:g));
    }
}

'''
legacy_jni_anchor = '''extern "C" JNIEXPORT jlong JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_demosaicMhcRggb(
'''
if native_cpp.count(legacy_jni_anchor) != 1:
    raise SystemExit('CFAABSTRACT1B legacy JNI anchor missing/ambiguous')
native_cpp = native_cpp.replace(legacy_jni_anchor, cpp_helpers + legacy_jni_anchor, 1)

cpp_jni = r'''extern "C" JNIEXPORT jlong JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_demosaicMhcBayer(
        JNIEnv* env, jclass,
        jshortArray rawArray,
        jint width,
        jint height,
        jint cfaPattern,
        jint originX,
        jint originY,
        jobject outBuffer,
        jint workers,
        jfloat neutralR, jfloat neutralG, jfloat neutralB,
        jboolean neutralAware,
        jlongArray statsArray) {
    if (!rawArray || !outBuffer || width <= 0 || height <= 0) return -1;
    if (cfaPattern < 0 || cfaPattern > 3) return -8;
    const int basePhaseX=(cfaPattern==1||cfaPattern==3)?1:0;
    const int basePhaseY=(cfaPattern==2||cfaPattern==3)?1:0;
    const int phaseX=m9PhaseParity(basePhaseX+originX);
    const int phaseY=m9PhaseParity(basePhaseY+originY);
    if (neutralAware && (!std::isfinite(neutralR)||!std::isfinite(neutralG)||!std::isfinite(neutralB)||neutralR<=0||neutralG<=0||neutralB<=0)) return -6;
    const double nr=neutralAware?static_cast<double>(neutralR)/static_cast<double>(neutralG):1.0;
    const double nb=neutralAware?static_cast<double>(neutralB)/static_cast<double>(neutralG):1.0;
    if(!std::isfinite(nr)||!std::isfinite(nb)||nr<=0.0||nb<=0.0)return -7;
    const double invR=1.0/nr,invB=1.0/nb;
    const int64_t pixels64=static_cast<int64_t>(width)*static_cast<int64_t>(height);
    if(pixels64<=0||pixels64>0x7fffffffLL)return -2;
    const jsize pixels=static_cast<jsize>(pixels64);
    if(env->GetArrayLength(rawArray)<pixels)return -3;
    void* outRaw=env->GetDirectBufferAddress(outBuffer);
    const jlong outCapacity=env->GetDirectBufferCapacity(outBuffer);
    const int64_t requiredBytes=pixels64*3LL*static_cast<int64_t>(sizeof(uint16_t));
    if(!outRaw||outCapacity<requiredBytes)return -4;
    jboolean isCopy=JNI_FALSE;
    jshort* raw=static_cast<jshort*>(env->GetPrimitiveArrayCritical(rawArray,&isCopy));
    if(!raw)return -5;
    auto* out=static_cast<uint16_t*>(outRaw);
    const auto started=std::chrono::steady_clock::now();
    const int workerCount=std::max(1,std::min(static_cast<int>(workers),static_cast<int>(height)));
    std::vector<std::thread> threads; threads.reserve(static_cast<size_t>(workerCount));
    if(neutralAware){
        std::vector<uint16_t> greenPlane(static_cast<size_t>(pixels64));
        for(int worker=0;worker<workerCount;++worker){
            const int y0=(height*worker)/workerCount,y1=(height*(worker+1))/workerCount;
            threads.emplace_back([=,&greenPlane](){for(int y=y0;y<y1;++y)for(int x=0;x<width;++x){
                greenPlane[static_cast<size_t>(y)*static_cast<size_t>(width)+static_cast<size_t>(x)]=mhcNeutralGreenBayerPhase(raw,width,height,y,x,invR,invB,phaseX,phaseY);
            }});
        }
        for(auto& thread:threads)thread.join();
        std::vector<uint16_t> sharpSourceGreen14; m9SharpSourceLeicaGreen14BayerPhase(raw,width,height,sharpSourceGreen14,phaseX,phaseY);
        std::vector<uint16_t> closureSharp14; m9ClosureSharpIso160Standard(sharpSourceGreen14,closureSharp14,width,height);
        threads.clear();
        for(int worker=0;worker<workerCount;++worker){
            const int y0=(height*worker)/workerCount,y1=(height*(worker+1))/workerCount;
            threads.emplace_back([=,&greenPlane,&sharpSourceGreen14,&closureSharp14](){for(int y=y0;y<y1;++y)for(int x=0;x<width;++x){
                const size_t p=static_cast<size_t>(y)*static_cast<size_t>(width)+static_cast<size_t>(x); uint16_t* dst=out+p*3u; uint16_t base[3];
                mhcPixelNeutralRbCompleteBayerPhase(raw,width,height,y,x,greenPlane[p],base,nr,nb,invR,invB,phaseX,phaseY);
                if(x>=9&&x<width-9&&y>=9&&y<height-9){
                    const int sg=static_cast<int>(closureSharp14[p]),mg=static_cast<int>(m9ClosureQ14(base[1]));
                    const int dr=static_cast<int>(m9ClosureQ14(base[0]))-mg,db=static_cast<int>(m9ClosureQ14(base[2]))-mg;
                    dst[0]=m9ClosureQ16(m9ClosureClamp14(sg+dr));dst[1]=m9ClosureQ16(static_cast<uint16_t>(sg));dst[2]=m9ClosureQ16(m9ClosureClamp14(sg+db));
                }else{dst[0]=base[0];dst[1]=base[1];dst[2]=base[2];}
            }});
        }
        for(auto& thread:threads)thread.join();
    }else{
        for(int worker=0;worker<workerCount;++worker){
            const int y0=(height*worker)/workerCount,y1=(height*(worker+1))/workerCount;
            threads.emplace_back([=](){for(int y=y0;y<y1;++y)for(int x=0;x<width;++x){
                uint16_t* dst=out+(static_cast<size_t>(y)*static_cast<size_t>(width)+static_cast<size_t>(x))*3u;
                mhcPixelBayerPhase(raw,width,height,y,x,dst,phaseX,phaseY);
            }});
        }
        for(auto& thread:threads)thread.join();
    }
    const auto ended=std::chrono::steady_clock::now(); env->ReleasePrimitiveArrayCritical(rawArray,raw,JNI_ABORT);
    const jlong elapsedNs=static_cast<jlong>(std::chrono::duration_cast<std::chrono::nanoseconds>(ended-started).count());
    if(statsArray&&env->GetArrayLength(statsArray)>=2){const jlong stats[2]={elapsedNs,static_cast<jlong>(workerCount)};env->SetLongArrayRegion(statsArray,0,2,stats);}
    return elapsedNs;
}

'''
normalize_anchor = '''extern "C" JNIEXPORT jlong JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_normalizeRawDirect(
'''
if native_cpp.count(normalize_anchor) != 1:
    raise SystemExit('CFAABSTRACT1B normalize JNI anchor missing/ambiguous')
native_cpp = native_cpp.replace(normalize_anchor, cpp_jni + normalize_anchor, 1)

# Refuse the patch if any validated RGGB arithmetic block changed.
if extract_braced(native_cpp,
        'Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_demosaicMhcRggb(') != legacy_mhc:
    raise SystemExit('CFAABSTRACT1B changed frozen demosaicMhcRggb body')
if extract_braced(renderer,
        'private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(\n') != legacy_gain:
    raise SystemExit('CFAABSTRACT1B changed frozen RGGB GainMap body')
if extract_braced(renderer,
        'private static NativeProspectiveShadingStats applyNativeProspectiveGainMapLumaDecomp1A(\n') != legacy_gain_luma:
    raise SystemExit('CFAABSTRACT1B changed frozen RGGB decomposed GainMap body')

renderer_path.write_text(renderer)
native_java_path.write_text(native_java)
native_cpp_path.write_text(native_cpp)
print('CFAABSTRACT1B/ULTRAWIDE1A applied')
print(' - CFA0/origin0 retains exact legacy RGGB MHC and GainMap implementations')
print(' - CFA1/2/3 use isolated 2x2-phase MHC/Leica-green source adapter')
print(' - Camera2 LensShadingMap routing is semantic [R, Geven, Godd, B]')
print(' - RAW origin remains explicitly 0 until DEVICEPORT evidence proves otherwise')
