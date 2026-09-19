#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv)!=2:
    raise SystemExit("usage: verify-m9cam-m9livegl1q-paircurve1a.py <PhotonCamera-root>")
root=Path(sys.argv[1]).resolve()
tone=root/"app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LiveToneModel1F.java"
shader=root/"app/src/main/assets/shaders/preview/main_fs.glsl"
main=root/"app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java"
for p in (tone,shader,main):
    if not p.exists(): raise SystemExit("GL1Q missing "+str(p))
t=tone.read_text(); s=shader.read_text(); m=main.read_text()
checks=[
("build marker", "M9LIVEGL1Q_PAIRCURVE1A" in s and "M9LIVEGL1Q_PAIRCURVE1A" in m),
("GL1O retained", "M9LIVEGL1O_TOELOCK1A" in s and "smoothstep(0.015, 0.055, y1N)" in s),
("pair helper", "float m9PairCurve1Q(float y)" in s),
("pair strength uniform reuse", "pairStrength1Q = clamp(uM9HighlightShoulder1F, 0.0, 1.0)" in s),
("pair curve applied", "float y1Q = mix(y1O, yPair1Q, pairStrength1Q)" in s and "linear *= y1Q / y1I" in s),
("neutral default", "DEFAULT_SHOULDER = 0.0f" in t),
("spread activation", "smoothstep(upperSpread, 85.0, 130.0)" in t),
("bright support activation", "smoothstep(bright224, 0.030, 0.090)" in t and "smoothstep(bright240, 0.012, 0.055)" in t),
("body protection", "1.0 - smoothstep(median, 155.0, 205.0)" in t),
("strength product", "spreadKey1Q * brightSupportKey1Q * bodyKey1Q" in t),
("diagnostic calibration", "20260919_17U_same_exposure_ISO50_1over196_aligned_histogram_transfer" in t),
]
for label,ok in checks:
    print(("OK   " if ok else "FAIL ")+label)
    if not ok: raise SystemExit("GL1Q contract failure: "+label)

start=s.find("vec3 m9DisplayTransform(vec3 photonSrgb, vec2 uv)")
end=s.find("\n}",start)
if start<0 or end<0: raise SystemExit("GL1Q transform missing")
xform=s[start:end+2]
for marker in (
    "linear *= uM9ExposureScale1B",
    "gain1I * pow(y1I, gamma1I)",
    "pivot1N * pow(max(y1ITarget, 1e-6) / pivot1N, residualGamma1N)",
    "smoothstep(0.015, 0.055, y1N)",
    "m9PairCurve1Q(y1O)",
    "linear *= y1Q / y1I",
):
    if marker not in xform: raise SystemExit("GL1Q active marker missing "+marker)
for marker in (
    "sourceToM9Target1D(linear)",
    "sat2M9(linear)",
    "tungstenGuard1D(",
    "curve02M9(toned1F.r)",
    "previewLut1F(curved1F)",
):
    if marker in xform: raise SystemExit("GL1Q forbidden live colour op active "+marker)

xs=[0.0,0.0012567,0.0058784,0.0204380,0.0503951,0.0802604,0.1430888,0.2605105,0.3543530,0.4817492,0.6246868,0.8987005,0.9665484,1.0]
ys=[0.0,0.0003035,0.0013435,0.0025576,0.0062605,0.0097955,0.0163085,0.0409161,0.0872869,0.1800684,0.2646380,0.4547111,0.6060910,1.0]
if any(b<=a for a,b in zip(xs,xs[1:])): raise SystemExit("GL1Q x knots not strictly monotone")
if any(b<a for a,b in zip(ys,ys[1:])): raise SystemExit("GL1Q y knots not monotone")
for x,y in zip(xs[1:-1],ys[1:-1]):
    sx=f"{x:.7f}".rstrip("0").rstrip(".")
    sy=f"{y:.7f}".rstrip("0").rstrip(".")
    if sx not in s or sy not in s:
        raise SystemExit("GL1Q knot literal missing "+sx+" -> "+sy)
print("M9LIVEGL1Q_PAIRCURVE1A VERIFY PASS")
print(" - GL1B exposure authority retained")
print(" - GL1O base transform retained")
print(" - scene-weighted monotone luminance residual active")
print(" - hue preserved by luminance-ratio scaling")
