#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply_gl1q.py <PhotonCamera-root>')
root=Path(sys.argv[1]).resolve()
tone_path=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LiveToneModel1F.java'
shader_path=root/'app/src/main/assets/shaders/preview/main_fs.glsl'
main_path=root/'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java'
for p in (tone_path,shader_path,main_path):
    if not p.exists(): raise SystemExit('GL1Q missing '+str(p))

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'GL1Q {label}: expected 1 anchor, found {n}')
    return text.replace(old,new,1)

tone=tone_path.read_text()
tone=one(tone,'public static final float DEFAULT_SHOULDER = 0.20f;','public static final float DEFAULT_SHOULDER = 0.0f;','default pair strength')
field='''    private static double lastRawGamma1P = DEFAULT_GAMMA;
'''
field_new=field+'''    // M9LIVEGL1Q_PAIRCURVE1A: scene activation for the measured display residual.
    private static double lastSpreadKey1Q;
    private static double lastBrightSupportKey1Q;
    private static double lastBodyKey1Q;
    private static double lastPairCurveStrength1Q;
'''
tone=one(tone,field,field_new,'diagnostic fields')

old='''        // Keep curve02 authoritative; this only controls how hard the vendor OES
        // highlight enters the exact curve.
        double shoulder = DEFAULT_SHOULDER
                + 0.30 * highlightPressure + 0.22 * backlit
                + 0.08 * smoothstep(q95, 205.0, 245.0);
        shoulder = clamp(shoulder, 0.20, 0.75);
'''
new='''        // M9LIVEGL1Q_PAIRCURVE1A
        // GL1P proved the screenshot and still used the same ISO/shutter, while the
        // finished JPEG median landed ~2.76 EV below the pre-GL analyzer and the
        // aligned screenshot/JPEG pair showed a strongly non-linear residual.
        // Activate the measured display-domain pair curve only when the frame has
        // both a broad upper-tail separation and real bright-pixel support.
        final double spreadKey1Q = smoothstep(upperSpread, 85.0, 130.0);
        final double brightSupportKey1Q = Math.max(
                smoothstep(bright224, 0.030, 0.090),
                smoothstep(bright240, 0.012, 0.055));
        final double bodyKey1Q = 1.0 - smoothstep(median, 155.0, 205.0);
        double shoulder = clamp01(spreadKey1Q * brightSupportKey1Q * bodyKey1Q);
'''
tone=one(tone,old,new,'scene activation')

old='''        lastRawGamma1P = gamma;

        if (!seeded) {
'''
new='''        lastRawGamma1P = gamma;
        lastSpreadKey1Q = spreadKey1Q;
        lastBrightSupportKey1Q = brightSupportKey1Q;
        lastBodyKey1Q = bodyKey1Q;
        lastPairCurveStrength1Q = shoulder;

        if (!seeded) {
'''
tone=one(tone,old,new,'diagnostic assignment')

old='''            o.put("smoothedHighlightShoulder", smoothShoulder);
            o.put("gl1mGainFormula", "-0.30 - 2.02 * sceneKey; clamp[-2.40,-0.25]");
'''
new='''            o.put("smoothedHighlightShoulder", smoothShoulder);
            o.put("gl1qPairCurveStrengthRaw", lastPairCurveStrength1Q);
            o.put("gl1qSpreadKey", lastSpreadKey1Q);
            o.put("gl1qBrightSupportKey", lastBrightSupportKey1Q);
            o.put("gl1qBodyKey", lastBodyKey1Q);
            o.put("gl1qPairCurveStrengthSmoothed", smoothShoulder);
            o.put("gl1qTransport", "uM9HighlightShoulder1F_repurposed_as_pair_curve_strength");
            o.put("gl1qCalibration", "20260919_17U_same_exposure_ISO50_1over196_aligned_histogram_transfer");
            o.put("gl1mGainFormula", "-0.30 - 2.02 * sceneKey; clamp[-2.40,-0.25]");
'''
tone=one(tone,old,new,'diagnostic json')
tone_path.write_text(tone)

shader=shader_path.read_text()
helper_anchor='''vec3 sat2M9(vec3 c) {
'''
curve='''// M9LIVEGL1Q_PAIRCURVE1A
// Monotone display-domain residual measured from the 2026-09-19 17U pair.
// Inputs/outputs are linear-light luminance AFTER GL1O.  RGB is rescaled by the
// luminance ratio, so this stage cannot rotate hue.  The scene classifier controls
// strength separately; ordinary scenes remain near identity.
float m9PairCurve1Q(float y) {
    y = clamp(y, 0.0, 1.0);
    if (y <= 0.0012567) return mix(0.0, 0.0003035, y / 0.0012567);
    if (y <= 0.0058784) return mix(0.0003035, 0.0013435, (y - 0.0012567) / (0.0058784 - 0.0012567));
    if (y <= 0.0204380) return mix(0.0013435, 0.0025576, (y - 0.0058784) / (0.0204380 - 0.0058784));
    if (y <= 0.0503951) return mix(0.0025576, 0.0062605, (y - 0.0204380) / (0.0503951 - 0.0204380));
    if (y <= 0.0802604) return mix(0.0062605, 0.0097955, (y - 0.0503951) / (0.0802604 - 0.0503951));
    if (y <= 0.1430888) return mix(0.0097955, 0.0163085, (y - 0.0802604) / (0.1430888 - 0.0802604));
    if (y <= 0.2605105) return mix(0.0163085, 0.0409161, (y - 0.1430888) / (0.2605105 - 0.1430888));
    if (y <= 0.3543530) return mix(0.0409161, 0.0872869, (y - 0.2605105) / (0.3543530 - 0.2605105));
    if (y <= 0.4817492) return mix(0.0872869, 0.1800684, (y - 0.3543530) / (0.4817492 - 0.3543530));
    if (y <= 0.6246868) return mix(0.1800684, 0.2646380, (y - 0.4817492) / (0.6246868 - 0.4817492));
    if (y <= 0.8987005) return mix(0.2646380, 0.4547111, (y - 0.6246868) / (0.8987005 - 0.6246868));
    if (y <= 0.9665484) return mix(0.4547111, 0.6060910, (y - 0.8987005) / (0.9665484 - 0.8987005));
    return mix(0.6060910, 1.0, (y - 0.9665484) / (1.0 - 0.9665484));
}

'''
shader=one(shader,helper_anchor,curve+helper_anchor,'pair curve helper')
old='''    float y1O = mix(y1N, y1OCurve, toeBlend1O);

    linear *= y1O / y1I;
    return clamp(linearToSrgbM9(linear), vec3(0.0), vec3(1.0));
'''
new='''    float y1O = mix(y1N, y1OCurve, toeBlend1O);

    // M9LIVEGL1Q_PAIRCURVE1A
    // The GL1P pair proved exposure synchronization; remaining error is the
    // non-linear display residual.  Apply the measured monotone curve only in
    // high-spread/high-bright-support scenes.  Preserve chroma by luma ratio.
    float pairStrength1Q = clamp(uM9HighlightShoulder1F, 0.0, 1.0);
    float yPair1Q = m9PairCurve1Q(y1O);
    float y1Q = mix(y1O, yPair1Q, pairStrength1Q);

    linear *= y1Q / y1I;
    return clamp(linearToSrgbM9(linear), vec3(0.0), vec3(1.0));
'''
shader=one(shader,old,new,'active transform')
shader_path.write_text(shader)

main=main_path.read_text()
log_anchor='''        Log.d("M9LiveGL1O", "M9LIVEGL1O_TOELOCK1A pivotLinear=0.071 extraGammaMax=1.60 toe=[0.015,0.055] sceneWeighted=true");
'''
log_new=log_anchor+'''        Log.d("M9LiveGL1Q", "M9LIVEGL1Q_PAIRCURVE1A sameExposurePair=true monotoneLumaKnots=13 chromaPreserving=true");
'''
main=one(main,log_anchor,log_new,'build marker log')
main_path.write_text(main)
print('M9LIVEGL1Q_PAIRCURVE1A applied')
