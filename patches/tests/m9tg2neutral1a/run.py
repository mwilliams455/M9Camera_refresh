"""Source/math checks for preview-only M9TG2NEUTRAL1A."""
from pathlib import Path
import math,sys
root=Path(sys.argv[1]).resolve()
shader=(root/"app/src/main/assets/shaders/preview/main_fs.glsl").read_text()
gradle=(root/"app/build.gradle").read_text()
assert "M9TG2NEUTRAL1A" in shader
assert "neutralGate=1.0-smoothstep(38.0,78.0,chroma)" in shader
assert "orangeGate=yellowGate*smoothstep(2.0,20.0,cr)" in shader
assert ("1.61-m9detail1h-tg2neutral1a" in gradle
        or "1.61-m9detail1h-tg2still1a" in gradle)

def bt601(rgb):
 r,g,b=rgb
 y=(4899*r+9617*g+1868*b)>>14
 cb=(-2765*r-5427*g+8192*b)>>14
 cr=(8192*r-6860*g-1332*b)>>14
 cb=((cb+128)&255)-128;cr=((cr+128)&255)-128
 return y,cb,cr
def smooth(a,b,x):
 if x<=a:return 0.0
 if x>=b:return 1.0
 t=(x-a)/(b-a);return t*t*(3-2*t)
def tg2(rgb,w=1.0):
 y,cb0,cr0=bt601(rgb);cb=float(cb0);cr=float(cr0)
 chroma=(cb*cb+cr*cr)**0.5
 neutral=1-smooth(38,78,chroma)
 yg=smooth(2,22,-cb);og=yg*smooth(2,20,cr);gg=smooth(2,18,-cr)
 if cb<0:cb*=1-w*yg*((1-neutral)*.18+neutral*.58)
 if cr>0:cr*=1-w*og*(.42*neutral)
 elif cr<0:cr*=1-w*gg*((1-neutral)*.10+neutral*.22)
 out=[round(max(0,min(255,y+1.402*cr))),
      round(max(0,min(255,y-.344136*cb-.714136*cr))),
      round(max(0,min(255,y+1.772*cb)))]
 return out,(y,cb0,cr0),(cb,cr)
def chroma(v):
 _,cb,cr=bt601(v);return (cb*cb+cr*cr)**.5

warm=[(180,150,110),(170,145,115),(200,165,120)]
for p in warm:
 o,src,dst=tg2(p,1)
 assert abs(bt601(o)[0]-src[0])<=2,(p,o,"Y")
 assert chroma(o)<chroma(p)*.78,(p,o,chroma(p),chroma(o))
 if src[2]>0: assert dst[1]<src[2],"positive Cr must now be corrected"

# Strong real colours must retain most of their chroma.
for p in [(230,190,20),(220,40,30),(30,80,230),(30,190,60),(220,80,180)]:
 o,_,_=tg2(p,1)
 assert chroma(o)>=chroma(p)*.76,(p,o,chroma(p),chroma(o))

# Guard off remains the same integer BT.601 round-trip to within normal rounding.
for p in [(10,20,30),(128,128,128),(240,180,90),(20,220,220)]:
 o,src,_=tg2(p,0)
 assert abs(bt601(o)[0]-src[0])<=2

print("M9TG2NEUTRAL1A math PASS: warm neutral chroma reduced; saturated colours bounded; Y preserved")
