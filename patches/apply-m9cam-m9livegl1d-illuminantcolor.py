#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply-m9cam-m9livegl1d-illuminantcolor.py <PhotonCamera-root>")

root = Path(sys.argv[1]).resolve()
main_renderer = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java"
gl_preview = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/GLPreview.java"
camera_fragment = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/CameraFragment.java"
main_fs = root / "app/src/main/assets/shaders/preview/main_fs.glsl"
controller = root / "app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java"
renderer = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java"
gradle = root / "app/build.gradle"

for p in (main_renderer, gl_preview, camera_fragment, main_fs, controller, renderer, gradle):
    if not p.exists():
        raise SystemExit("M9LIVEGL1D missing assembled file: " + str(p))

def one(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"M9LIVEGL1D {label}: expected 1 anchor, found {n}")
    return text.replace(old, new, 1)

mr = main_renderer.read_text()
gp = gl_preview.read_text()
cf = camera_fragment.read_text()
fs = main_fs.read_text()
cc = controller.read_text()
rr = renderer.read_text()

# GL1B exposure and GL1C tone are frozen prerequisites.
for token in ("M9LIVEGL1B_EXPOSUREINTENT", "M9LIVEGL1C_APPEARANCEPARITY",
              "M9_LIVE_GL1C_BLACK_FLOOR", "M9_LIVE_GL1C_SHADOW_POWER",
              "M9_LIVE_GL1C_HIGHLIGHT_SHOULDER"):
    if token not in mr:
        raise SystemExit("M9LIVEGL1D missing MainRenderer prerequisite: " + token)
for token in ("linear *= uM9ExposureScale1B", "tonePlacement1C",
              "M9LIVEGL1C_APPEARANCEPARITY"):
    if token not in fs:
        raise SystemExit("M9LIVEGL1D missing shader prerequisite: " + token)
if "Photon_GL_IsoExpoSelector_intended_pair" not in cc:
    raise SystemExit("M9LIVEGL1D missing frozen still exposure authority")
for token in ("toneBoundLimitEv1A = 0.5", 'captureExposureMutation", false'):
    if token not in rr:
        raise SystemExit("M9LIVEGL1D frozen still renderer prerequisite missing: " + token)

# ---------------------------------------------------------------------------
# MainRenderer
#
# GL1C used only the D65 endpoint.  GL1D adds the recovered A endpoint and
# interpolates between them from the live scene illuminant.  Both matrices are
# transforms from white-balanced linear sRGB(D65 display space) to normalized
# M9 virtual-sensor RGB.  The A endpoint includes Bradford D65->A unadaptation,
# then the recovered M9 A ColorMatrix and per-channel M9 white normalization.
#
# Java arrays are column-major for glUniformMatrix3fv(transpose=false).
# ---------------------------------------------------------------------------
field_anchor = """    private static final float[] M9_LIVE_GL1C_SOURCE_D65 = {
            0.53316906f, 0.09333790f, 0.01986253f,
            0.32894386f, 0.70803917f, 0.28021240f,
            0.13788708f, 0.19862293f, 0.69992507f
    };
"""
field_new = field_anchor + """    // M9LIVEGL1D_ILLUMINANTCOLOR
    private static final float[] M9_LIVE_GL1D_SOURCE_A = {
            0.53755093f, 0.12914680f, 0.05817552f,
            0.38280546f, 0.76276908f, 0.38316200f,
            0.07964361f, 0.10808411f, 0.55866248f
    };
    private volatile float mM9IlluminantWeightA1D = 0.0f;
    private volatile float mM9TungstenWeight1D = 0.0f;
"""
mr = one(mr, field_anchor, field_new, "A-endpoint fields")

uniform_field_anchor = """    private int uM9FalloffPower1C;
"""
uniform_field_new = uniform_field_anchor + """    private int uM9SourceMatrixA1D;
    private int uM9IlluminantWeightA1D;
    private int uM9TungstenWeight1D;
"""
mr = one(mr, uniform_field_anchor, uniform_field_new, "GL1D uniform fields")

uniform_anchor = """        uM9FalloffStrength1C = GLES20.glGetUniformLocation(hProgram, "uM9FalloffStrength1C");
        uM9FalloffPower1C = GLES20.glGetUniformLocation(hProgram, "uM9FalloffPower1C");
        GLES20.glUniform1i(uM9Curve, 1);
"""
uniform_new = """        uM9FalloffStrength1C = GLES20.glGetUniformLocation(hProgram, "uM9FalloffStrength1C");
        uM9FalloffPower1C = GLES20.glGetUniformLocation(hProgram, "uM9FalloffPower1C");
        uM9SourceMatrixA1D = GLES20.glGetUniformLocation(hProgram, "uM9SourceMatrixA1D");
        uM9IlluminantWeightA1D = GLES20.glGetUniformLocation(hProgram, "uM9IlluminantWeightA1D");
        uM9TungstenWeight1D = GLES20.glGetUniformLocation(hProgram, "uM9TungstenWeight1D");
        GLES20.glUniform1i(uM9Curve, 1);
"""
mr = one(mr, uniform_anchor, uniform_new, "GL1D uniform locations")

draw_anchor = """        GLES20.glUniform1f(uM9FalloffStrength1C, M9_LIVE_GL1C_FALLOFF_STRENGTH);
        GLES20.glUniform1f(uM9FalloffPower1C, M9_LIVE_GL1C_FALLOFF_POWER);
        GLES20.glUniform1i(uM9Curve, 1);
"""
draw_new = """        GLES20.glUniform1f(uM9FalloffStrength1C, M9_LIVE_GL1C_FALLOFF_STRENGTH);
        GLES20.glUniform1f(uM9FalloffPower1C, M9_LIVE_GL1C_FALLOFF_POWER);
        GLES20.glUniformMatrix3fv(uM9SourceMatrixA1D, 1, false, M9_LIVE_GL1D_SOURCE_A, 0);
        GLES20.glUniform1f(uM9IlluminantWeightA1D, mM9IlluminantWeightA1D);
        GLES20.glUniform1f(uM9TungstenWeight1D, mM9TungstenWeight1D);
        GLES20.glUniform1i(uM9Curve, 1);
"""
mr = one(mr, draw_anchor, draw_new, "GL1D uniform uploads")

setter_anchor = """    public void setM9ExposureScale1B(float scale) {
        if (!Float.isFinite(scale) || scale <= 0.0f) scale = 1.0f;
        // Preview transport guard only. Normal exposure controls sit comfortably
        // inside this +/-4 EV window.
        mM9ExposureScale1B = Math.max(0.0625f, Math.min(16.0f, scale));
        mView.requestRender();
    }

"""
setter_new = setter_anchor + """    /**
     * M9LIVEGL1D_ILLUMINANTCOLOR.
     * weightA follows the M9 renderer's reciprocal-temperature A/D65 weighting.
     * tungstenWeight follows the frozen TG1 4500K->3200K smoothstep.
     */
    public void setM9IlluminantState1D(float weightA, float tungstenWeight) {
        if (!Float.isFinite(weightA)) weightA = 0.0f;
        if (!Float.isFinite(tungstenWeight)) tungstenWeight = 0.0f;
        mM9IlluminantWeightA1D = Math.max(0.0f, Math.min(1.0f, weightA));
        mM9TungstenWeight1D = Math.max(0.0f, Math.min(1.0f, tungstenWeight));
        mView.requestRender();
    }

"""
mr = one(mr, setter_anchor, setter_new, "GL1D setter")

log_anchor = """        Log.d("M9LiveGL1C", "M9LIVEGL1C_APPEARANCEPARITY"
                + " source=M9_D65_NORMALIZED"
                + " blackFloor=" + M9_LIVE_GL1C_BLACK_FLOOR
                + " shadowPower=" + M9_LIVE_GL1C_SHADOW_POWER
                + " highlightShoulder=" + M9_LIVE_GL1C_HIGHLIGHT_SHOULDER
                + " falloffStrength=" + M9_LIVE_GL1C_FALLOFF_STRENGTH
                + " GL1B_EXPOSURE_FROZEN");
"""
log_new = log_anchor + """        Log.d("M9LiveGL1D", "M9LIVEGL1D_ILLUMINANTCOLOR"
                + " source=M9_A_D65_DYNAMIC"
                + " lumaPreservingColor=true"
                + " tg1=true"
                + " GL1C_TONE_FROZEN"
                + " GL1B_EXPOSURE_FROZEN");
"""
mr = one(mr, log_anchor, log_new, "GL1D log")
main_renderer.write_text(mr)

# ---------------------------------------------------------------------------
# GLPreview bridge
# ---------------------------------------------------------------------------
gp_anchor = """    public void setM9ExposureScale1B(float scale) {
        if (mRenderer != null) {
            mRenderer.setM9ExposureScale1B(scale);
        }
    }
"""
gp_new = gp_anchor + """
    /** M9LIVEGL1D_ILLUMINANTCOLOR: live M9 A/D65 + TG1 state. */
    public void setM9IlluminantState1D(float weightA, float tungstenWeight) {
        if (mRenderer != null) {
            mRenderer.setM9IlluminantState1D(weightA, tungstenWeight);
        }
    }
"""
gp = one(gp, gp_anchor, gp_new, "GLPreview illuminant bridge")
gl_preview.write_text(gp)

# ---------------------------------------------------------------------------
# CameraFragment
#
# Use the same live neutral already used by the Photon HUD.  The existing HUD
# has a robust fallback to captureController.mPreviewTemp; mirror that here.
# The CCT estimate is intentionally only an illuminant selector.  It never
# changes still capture, exposure, WB or RAW metadata.
# ---------------------------------------------------------------------------
cf_anchor = """                        captureController.updateM9LiveGlIntendedExposure1B(
                                intended1B.iso, intended1B.exposure);
                    }
                }
            } catch (Throwable t) {
                Log.w(TAG, "M9LIVEGL1B exposure intent update failed: " + t);
            }
        }
"""
cf_new = """                        captureController.updateM9LiveGlIntendedExposure1B(
                                intended1B.iso, intended1B.exposure);
                    }
                }

                // M9LIVEGL1D_ILLUMINANTCOLOR
                // GL1C fixed the preview target at D65.  The still renderer does not:
                // it interpolates the recovered Leica M9 A/D65 target by scene light.
                // Use the same live neutral already displayed by Photon's WB HUD.
                android.util.Rational[] neutral1D =
                        result.get(CaptureResult.SENSOR_NEUTRAL_COLOR_POINT);
                if ((neutral1D == null || neutral1D.length < 3)
                        && captureController.mPreviewTemp != null
                        && captureController.mPreviewTemp.length >= 3) {
                    neutral1D = captureController.mPreviewTemp;
                }
                if (neutral1D != null && neutral1D.length >= 3) {
                    double neutralR1D = neutral1D[0].doubleValue();
                    double neutralB1D = neutral1D[2].doubleValue();
                    if (neutralR1D > 1.0e-6 && neutralB1D > 1.0e-6) {
                        // Same live CCT estimator already used by calculateWhitebalanceString().
                        double ratio1D = neutralB1D / neutralR1D;
                        double cct1D = 3000.0 * Math.pow(ratio1D, 0.75);
                        cct1D = Math.max(2000.0, Math.min(10000.0, cct1D));

                        double invT1D = 1000000.0 / cct1D;
                        double invD651D = 1000000.0 / 6500.0;
                        double invA1D = 1000000.0 / 2850.0;
                        double weightA1D = (invT1D - invD651D) / (invA1D - invD651D);
                        weightA1D = Math.max(0.0, Math.min(1.0, weightA1D));

                        double tgX1D = (4500.0 - cct1D) / (4500.0 - 3200.0);
                        tgX1D = Math.max(0.0, Math.min(1.0, tgX1D));
                        double tgWeight1D = tgX1D * tgX1D * (3.0 - 2.0 * tgX1D);

                        textureView.setM9IlluminantState1D(
                                (float) weightA1D, (float) tgWeight1D);
                    }
                }
            } catch (Throwable t) {
                Log.w(TAG, "M9LIVEGL1D live preview state update failed: " + t);
            }
        }
"""
cf = one(cf, cf_anchor, cf_new, "CameraFragment live illuminant state")
camera_fragment.write_text(cf)

# ---------------------------------------------------------------------------
# Shader
#
# Important correction from GL1C:
#   Photon OES is already display-rendered.  We therefore do NOT allow the
#   target matrix to change luminance.  We apply the recovered M9 A/D65 delta
#   only as a chromatic remapping, then rescale to preserve input Rec.709 luma.
# This keeps the exposure/shadow/highlight behaviour the user validated while
# moving hue/chroma toward the still renderer.
#
# After exact curve02, apply the same M9Modern TG1 signed BT.601 chroma-axis
# compression used by the still renderer.  TG1 preserves BT.601 Y exactly.
# ---------------------------------------------------------------------------
fs = main_fs.read_text()
uniform_anchor_fs = """uniform mat3 uM9SourceMatrix1C;
"""
uniform_new_fs = uniform_anchor_fs + """// M9LIVEGL1D_ILLUMINANTCOLOR
uniform mat3 uM9SourceMatrixA1D;
uniform float uM9IlluminantWeightA1D;
uniform float uM9TungstenWeight1D;
"""
fs = one(fs, uniform_anchor_fs, uniform_new_fs, "shader GL1D uniforms")

source_old = """vec3 sourceToM9Target1C(vec3 linearSrgb) {
    // D65 white-balanced display input -> normalized Leica M9 virtual sensor.
    // Neutral axis is preserved exactly by the row-normalized matrix.
    return max(uM9SourceMatrix1C * linearSrgb, vec3(0.0));
}
"""
source_new = """vec3 sourceToM9Target1D(vec3 linearSrgb) {
    // Recovered Leica M9 target endpoints.  Interpolate using the live scene
    // illuminant rather than forcing every preview through the D65 endpoint.
    vec3 d65 = max(uM9SourceMatrix1C * linearSrgb, vec3(0.0));
    vec3 a = max(uM9SourceMatrixA1D * linearSrgb, vec3(0.0));
    vec3 target = mix(d65, a, clamp(uM9IlluminantWeightA1D, 0.0, 1.0));

    // Photon OES is display-rendered, not RAW sensor RGB.  Preserve luminance so
    // this stage changes colour only and cannot undo the GL1C exposure/tone win.
    const vec3 Y709 = vec3(0.2126, 0.7152, 0.0722);
    float yin = dot(max(linearSrgb, vec3(0.0)), Y709);
    float yout = dot(target, Y709);
    if (yin > 1.0e-7 && yout > 1.0e-7) {
        target *= yin / yout;
    }
    return max(target, vec3(0.0));
}
"""
fs = one(fs, source_old, source_new, "luma-preserving illuminant target")

falloff_anchor = """float falloffGain1C(vec2 uv) {
"""
tg_helper = r'''vec3 tungstenGuard1D(vec3 rgb) {
    // M9Modern TG1, expressed directly on normalized full-range BT.601 axes.
    // Y is preserved; only negative Cb (yellow) and negative Cr (green) are
    // gently compressed under warm light.
    float y = dot(rgb, vec3(0.299000, 0.587000, 0.114000));
    float cb = dot(rgb, vec3(-0.168736, -0.331264, 0.500000));
    float cr = dot(rgb, vec3(0.500000, -0.418688, -0.081312));

    float w = clamp(uM9TungstenWeight1D, 0.0, 1.0);
    if (cb < 0.0) cb *= (1.0 - 0.25 * w);
    if (cr < 0.0) cr *= (1.0 - 0.16 * w);

    vec3 outv;
    outv.r = y + 1.402000 * cr;
    outv.g = y - 0.344136 * cb - 0.714136 * cr;
    outv.b = y + 1.772000 * cb;
    return clamp(outv, vec3(0.0), vec3(1.0));
}

''' + falloff_anchor
fs = one(fs, falloff_anchor, tg_helper, "TG1 helper")

transform_old = """    // M9LIVEGL1C_APPEARANCEPARITY: enter the same recovered M9 target family
    // before the existing exposure intent, SAT2 and exact curve02 stages.
    linear = sourceToM9Target1C(linear);

    // M9LIVEGL1B_EXPOSUREINTENT stays authoritative and unchanged.
    linear *= uM9ExposureScale1B;

    linear = tonePlacement1C(linear);
    linear *= falloffGain1C(uv);

    vec3 sat2 = clamp(sat2M9(linear) * uM9DisplayGain, vec3(0.0), vec3(1.0));
    return vec3(curve02M9(sat2.r), curve02M9(sat2.g), curve02M9(sat2.b));
"""
transform_new = """    // M9LIVEGL1D_ILLUMINANTCOLOR: colour-only recovered target mapping.
    linear = sourceToM9Target1D(linear);

    // M9LIVEGL1B_EXPOSUREINTENT stays authoritative and unchanged.
    linear *= uM9ExposureScale1B;

    // GL1C tone placement stays unchanged.
    linear = tonePlacement1C(linear);
    linear *= falloffGain1C(uv);

    vec3 sat2 = clamp(sat2M9(linear) * uM9DisplayGain, vec3(0.0), vec3(1.0));
    vec3 curved = vec3(curve02M9(sat2.r), curve02M9(sat2.g), curve02M9(sat2.b));
    return tungstenGuard1D(curved);
"""
fs = one(fs, transform_old, transform_new, "GL1D transform")
main_fs.write_text(fs)

# Build identity only.
g = gradle.read_text()
lines = g.splitlines()
changed = False
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith("versionName "):
        if "m9livegl1d" not in stripped.lower():
            prefix = line[:len(line) - len(line.lstrip())]
            value = stripped[len("versionName "):].strip()
            quote = '"' if value.startswith('"') else "'"
            if not (value.startswith(quote) and value.endswith(quote)):
                raise SystemExit("M9LIVEGL1D unsupported versionName syntax: " + line)
            base = value[1:-1]
            lines[i] = prefix + "versionName " + quote + base + "-m9livegl1d-illuminantcolor" + quote
            changed = True
        break
else:
    raise SystemExit("M9LIVEGL1D versionName missing")
if changed:
    gradle.write_text("\n".join(lines) + ("\n" if g.endswith("\n") else ""))

print("M9LIVEGL1D_ILLUMINANTCOLOR applied")
print(" - GL1B exposure authority frozen")
print(" - GL1C black/shadow/highlight placement frozen")
print(" - D65-only target replaced by live A/D65 interpolated M9 colour mapping")
print(" - target colour mapping preserves preview luminance")
print(" - M9Modern TG1 warm-light BT601 chroma guard added")
print(" - still M9 photographic renderer untouched")
