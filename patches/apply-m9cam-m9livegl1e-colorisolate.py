#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply-m9cam-m9livegl1e-colorisolate.py <PhotonCamera-root>")

root = Path(sys.argv[1]).resolve()
main_renderer = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java"
main_fs = root / "app/src/main/assets/shaders/preview/main_fs.glsl"
controller = root / "app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java"
renderer = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java"
gradle = root / "app/build.gradle"

for p in (main_renderer, main_fs, controller, renderer, gradle):
    if not p.exists():
        raise SystemExit("M9LIVEGL1E missing assembled file: " + str(p))

def one(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"M9LIVEGL1E {label}: expected 1 anchor, found {n}")
    return text.replace(old, new, 1)

mr = main_renderer.read_text()
fs = main_fs.read_text()
cc = controller.read_text()
rr = renderer.read_text()

# Frozen prerequisites: exposure intent, GL1C tone, and GL1D colour candidate
# must all be present so this is a controlled bypass rather than a new path.
for token in (
    "M9LIVEGL1B_EXPOSUREINTENT",
    "M9LIVEGL1C_APPEARANCEPARITY",
    "M9LIVEGL1D_ILLUMINANTCOLOR",
    "M9_LIVE_GL1C_BLACK_FLOOR",
    "M9_LIVE_GL1C_SHADOW_POWER",
    "M9_LIVE_GL1C_HIGHLIGHT_SHOULDER",
):
    if token not in mr:
        raise SystemExit("M9LIVEGL1E missing MainRenderer prerequisite: " + token)

for token in (
    "sourceToM9Target1D",
    "tonePlacement1C",
    "sat2M9",
    "curve02M9",
    "tungstenGuard1D",
    "linear *= uM9ExposureScale1B",
):
    if token not in fs:
        raise SystemExit("M9LIVEGL1E missing shader prerequisite: " + token)

if "Photon_GL_IsoExpoSelector_intended_pair" not in cc:
    raise SystemExit("M9LIVEGL1E missing frozen still exposure authority")
for token in ("toneBoundLimitEv1A = 0.5", 'captureExposureMutation", false'):
    if token not in rr:
        raise SystemExit("M9LIVEGL1E frozen still renderer prerequisite missing: " + token)

# ---------------------------------------------------------------------------
# CONTROL EXPERIMENT:
#
# Photon SurfaceTexture/OES is already a display-rendered colour image.
# GL1C/GL1D then treated that image as though it were sensor/scene RGB and
# applied M9 target matrices + firmware SAT2 (+ TG1 in GL1D). Device video
# showed exposure/tone becoming useful while chroma collapsed badly.
#
# GL1E keeps the exact successful exposure/tone stages but bypasses *all*
# sensor-domain Leica colour operations in the live preview:
#
#   Photon sRGB
#     -> inverse sRGB
#     -> GL1B exposure intent
#     -> GL1C tone placement
#     -> GL1C falloff hook (currently identity)
#     -> GL1A display gain
#     -> exact curve02
#     -> screen
#
# The helper functions/uniform plumbing remain in the assembled source solely
# so this branch is a minimal controlled diff. They are deliberately not called.
# Still JPEG/DNG rendering is completely untouched.
# ---------------------------------------------------------------------------
old_transform = """vec3 m9DisplayTransform(vec3 photonSrgb, vec2 uv) {
    if (!uM9Enabled) return photonSrgb;
    vec3 linear = srgbToLinearM9(clamp(photonSrgb, vec3(0.0), vec3(1.0)));

    // M9LIVEGL1D_ILLUMINANTCOLOR: colour-only recovered target mapping.
    linear = sourceToM9Target1D(linear);

    // M9LIVEGL1B_EXPOSUREINTENT stays authoritative and unchanged.
    linear *= uM9ExposureScale1B;

    // GL1C tone placement stays unchanged.
    linear = tonePlacement1C(linear);
    linear *= falloffGain1C(uv);

    vec3 sat2 = clamp(sat2M9(linear) * uM9DisplayGain, vec3(0.0), vec3(1.0));
    vec3 curved = vec3(curve02M9(sat2.r), curve02M9(sat2.g), curve02M9(sat2.b));
    return tungstenGuard1D(curved);
}
"""
new_transform = """vec3 m9DisplayTransform(vec3 photonSrgb, vec2 uv) {
    if (!uM9Enabled) return photonSrgb;
    vec3 linear = srgbToLinearM9(clamp(photonSrgb, vec3(0.0), vec3(1.0)));

    // M9LIVEGL1E_COLORISOLATE
    // Photon OES is already display-colour rendered.  Do not reinterpret it as
    // M9 sensor/scene RGB.  GL1D A/D65 matrix, firmware SAT2 and TG1 are
    // intentionally bypassed in this control build.
    //
    // M9LIVEGL1B_EXPOSUREINTENT stays authoritative and unchanged.
    linear *= uM9ExposureScale1B;

    // GL1C black/shadow/highlight placement stays authoritative and unchanged.
    linear = tonePlacement1C(linear);
    linear *= falloffGain1C(uv);

    // Retain the existing display gain + exact curve02 so this experiment
    // isolates colour-domain operations rather than changing tone again.
    vec3 toned1E = clamp(linear * uM9DisplayGain, vec3(0.0), vec3(1.0));
    return vec3(curve02M9(toned1E.r),
                curve02M9(toned1E.g),
                curve02M9(toned1E.b));
}
"""
fs = one(fs, old_transform, new_transform, "colour isolate transform")
main_fs.write_text(fs)

log_anchor = """        Log.d("M9LiveGL1D", "M9LIVEGL1D_ILLUMINANTCOLOR"
                + " source=M9_A_D65_DYNAMIC"
                + " lumaPreservingColor=true"
                + " tg1=true"
                + " GL1C_TONE_FROZEN"
                + " GL1B_EXPOSURE_FROZEN");
"""
log_new = log_anchor + """        Log.d("M9LiveGL1E", "M9LIVEGL1E_COLORISOLATE"
                + " oesColor=Photon_display_rendered"
                + " m9TargetMatrix=false"
                + " sat2=false"
                + " tg1=false"
                + " curve02=true"
                + " GL1C_TONE_FROZEN"
                + " GL1B_EXPOSURE_FROZEN");
"""
mr = one(mr, log_anchor, log_new, "GL1E log")
main_renderer.write_text(mr)

# Build identity only.
g = gradle.read_text()
lines = g.splitlines()
changed = False
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith("versionName "):
        if "m9livegl1e" not in stripped.lower():
            prefix = line[:len(line) - len(line.lstrip())]
            value = stripped[len("versionName "):].strip()
            quote = '"' if value.startswith('"') else "'"
            if not (value.startswith(quote) and value.endswith(quote)):
                raise SystemExit("M9LIVEGL1E unsupported versionName syntax: " + line)
            base = value[1:-1]
            lines[i] = prefix + "versionName " + quote + base + "-m9livegl1e-colorisolate" + quote
            changed = True
        break
else:
    raise SystemExit("M9LIVEGL1E versionName missing")
if changed:
    gradle.write_text("\n".join(lines) + ("\n" if g.endswith("\n") else ""))

print("M9LIVEGL1E_COLORISOLATE applied")
print(" - Photon OES colour retained as display-domain source")
print(" - M9 A/D65 target matrix BYPASSED in live preview")
print(" - firmware SAT2 BYPASSED in live preview")
print(" - TG1 BYPASSED in live preview")
print(" - GL1B exposure authority frozen")
print(" - GL1C black/shadow/highlight placement frozen")
print(" - display gain + exact curve02 retained")
print(" - still M9 photographic renderer untouched")
