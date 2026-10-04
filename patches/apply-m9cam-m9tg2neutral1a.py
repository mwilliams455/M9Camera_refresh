#!/usr/bin/env python3
"""Apply preview-only TG2 warm-neutral correction after M9TUNGSTENCONT1A."""
from pathlib import Path
import hashlib,sys
if len(sys.argv)!=2: raise SystemExit("usage: apply-m9cam-m9tg2neutral1a.py <PhotonCamera-root>")
root=Path(sys.argv[1]).resolve()
shader=root/"app/src/main/assets/shaders/preview/main_fs.glsl"
gradle=root/"app/build.gradle"
still=root/"app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java"
if not shader.exists() or not gradle.exists() or not still.exists(): raise SystemExit("TG2 baseline missing")
still_before=hashlib.sha256(still.read_bytes()).hexdigest()
OLD="""vec3 tungsten2A(vec3 rgb) {
    // Same integer BT.601/TG1 for a flat pixel pair; no extra preview chroma subsampling.
    ivec3 c=ivec3(round(rgb*255.0));
    int y=(4899*c.r+9617*c.g+1868*c.b)>>14;
    int cb=(-2765*c.r-5427*c.g+8192*c.b)>>14;
    int cr=(8192*c.r-6860*c.g-1332*c.b)>>14;
    cb=((cb+128)&255)-128; cr=((cr+128)&255)-128;
    float b=float(cb)*(cb<0?1.0-.25*uM9Tungsten2A:1.0);
    float r=float(cr)*(cr<0?1.0-.16*uM9Tungsten2A:1.0);
    return floor(clamp(vec3(float(y)+1.402*r,float(y)-.344136*b-.714136*r,
            float(y)+1.772*b),vec3(0),vec3(255))+.5)/255.0;
}"""
NEW="""vec3 tungsten2A(vec3 rgb) {
    // M9TG2NEUTRAL1A — preview-only warm residual correction.
    // Preserve BT.601 Y exactly. Correct low/moderate-chroma yellow/orange cast
    // more strongly than saturated subject colour; leave blue/cyan untouched.
    ivec3 c=ivec3(round(rgb*255.0));
    int y=(4899*c.r+9617*c.g+1868*c.b)>>14;
    int cbi=(-2765*c.r-5427*c.g+8192*c.b)>>14;
    int cri=(8192*c.r-6860*c.g-1332*c.b)>>14;
    cbi=((cbi+128)&255)-128; cri=((cri+128)&255)-128;
    float cb=float(cbi), cr=float(cri);
    float w=clamp(uM9Tungsten2A,0.0,1.0);
    float chroma=length(vec2(cb,cr));
    float neutralGate=1.0-smoothstep(38.0,78.0,chroma);
    float yellowGate=smoothstep(2.0,22.0,-cb);
    float orangeGate=yellowGate*smoothstep(2.0,20.0,cr);
    float greenGate=smoothstep(2.0,18.0,-cr);
    if (cb<0.0) cb*=1.0-w*yellowGate*mix(0.18,0.58,neutralGate);
    if (cr>0.0) cr*=1.0-w*orangeGate*(0.42*neutralGate);
    else if (cr<0.0) cr*=1.0-w*greenGate*mix(0.10,0.22,neutralGate);
    return floor(clamp(vec3(float(y)+1.402*cr,float(y)-.344136*cb-.714136*cr,
            float(y)+1.772*cb),vec3(0),vec3(255))+.5)/255.0;
}"""
s=shader.read_text()
if s.count(OLD)!=1: raise SystemExit("TG2 tungsten2A anchor mismatch")
shader.write_text(s.replace(OLD,NEW,1))
g=gradle.read_text()
oldv="versionName '1.61-m9detail1h-tg1rollback1a'"
newv="versionName '1.61-m9detail1h-tg2neutral1a'"
if g.count(oldv)!=1: raise SystemExit("TG2 version anchor mismatch")
gradle.write_text(g.replace(oldv,newv,1))
if hashlib.sha256(still.read_bytes()).hexdigest()!=still_before: raise SystemExit("TG2 still renderer changed")
print("M9TG2NEUTRAL1A applied: preview shader only; Photon transport/still renderer frozen")
