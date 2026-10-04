from pathlib import Path
import sys,ast,subprocess,shutil,ctypes as C,struct,json
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"colourtrial1c"))
from run import configure,REPO
HERE=Path(__file__).resolve().parent
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();src=out/'jni_src';classes=out/'jni_classes';classes.mkdir(exist_ok=True)
# Reuse Android field-type stubs only, never the old test runner.
tree=ast.parse((REPO/'patches/tests/m9detail1h/jni.py').read_text())
stubs=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='STUBS' for t in n.targets)))
stubs={k:v for k,v in stubs.items() if k.startswith(('android/','org/'))}
stubs['android/graphics/Bitmap.java']='''package android.graphics;import java.nio.*;public class Bitmap{
 public final int width,height;public boolean invalid;public final ByteBuffer pixels;
 public Bitmap(int w,int h){width=w;height=h;pixels=ByteBuffer.allocateDirect(w*h*4).order(ByteOrder.nativeOrder());}}'''
for name,body in stubs.items():p=src/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body)
base='com/particlesdevs/photoncamera/m9/render';(src/base).mkdir(parents=True,exist_ok=True)
for n in ['M9ColourTrial1C.java','M9NativeColorCore.java','M9Detail1H.java']:shutil.copyfile(root/'app/src/main/java'/base/n,src/base/n)
shutil.copyfile(HERE/'TrialJniCheck.java',src/base/'TrialJniCheck.java')
compiler=['javac'] if shutil.which('javac') else ['java','com.sun.tools.javac.Main']
subprocess.run([*compiler,'-d',str(classes),*[str(p) for p in src.rglob('*.java')]],check=True)
lib=configure(C.CDLL(str(out/'libtrial.so')));rng=np.random.default_rng(913);paths=[];w,h=65,67
srcgrid=np.array([[[1.+.15*y+.2*x+.07*p for p in range(4)] for x in range(3)] for y in range(2)],np.float32)
common=np.exp(np.log(srcgrid.astype(float)).sum(2)*.25);grid=srcgrid/common[:,:,None]*np.exp(.5*np.log(common))[:,:,None];scale=float(grid.max())
neutral=np.array([.37,1.,.61],np.float32);nr=float(neutral[0]);nb=float(neutral[2]);black=np.array([60,64,67,71],np.float32)
for cfa in range(4):
 pairs=np.array([[.00013+.00002*i,.0000007+.0000001*i] for i in range(4)],float)
 profile=np.r_[pairs[cfa],pairs[cfa^1]*.5+pairs[(3-cfa)^1]*.5,pairs[3-cfa]].astype(float)
 for oy in range(2):
  for ox in range(2):
   phase=((cfa&1)^ox)+2*((cfa>>1)^oy);yy,xx=np.indices((h,w));sensor=rng.integers(100,65000,(h,w),dtype=np.uint16)
   sensor[23,24]=65535;sensor[25,26]=0
   norm=rng.integers(0,65536,(h,w),dtype=np.uint16);v=np.empty((h,w),np.float32);mask=np.empty((h,w),np.uint8)
   assert lib.trial_variance(sensor.ctypes.data,w,h,phase,oy,black.ctypes.data,65535,profile.ctypes.data,grid.ctypes.data,3,2,scale,v.ctypes.data,mask.ctypes.data)==0
   # Independent double-precision physical variance calculation, all phases/origins.
   red=(xx%2==phase%2)&(yy%2==phase//2);blue=(xx%2!=phase%2)&(yy%2!=phase//2)
   ch=np.where(red,0,np.where(blue,2,1));mp=np.where(red,0,np.where(blue,3,np.where((yy+oy)%2,2,1)))
   gx=xx*(2./(w-1));gy=yy*(1./(h-1));x0=gx.astype(int);y0=gy.astype(int);x1=np.minimum(2,x0+1);y1=np.minimum(1,y0+1)
   g0=grid[y0,x0,mp]+(gx-x0)*(grid[y0,x1,mp]-grid[y0,x0,mp]);g1=grid[y1,x0,mp]+(gx-x0)*(grid[y1,x1,mp]-grid[y1,x0,mp]);gain=g0+(gy-y0)*(g1-g0)
   b=black[(yy%2)*2+xx%2].astype(float);den=65535-b;signal=np.clip((sensor-b)/den,0,1)
   expectedv=((profile.reshape(3,2)[ch,0]*signal+profile.reshape(3,2)[ch,1]+1/(12*den*den))*(gain/scale*65535)**2).astype(np.float32)
   assert np.array_equal(v,expectedv),'variance formula'
   assert np.array_equal(mask,(sensor<=b)|(sensor>=65535)),'censor mask'
   expected=[];stats=np.empty(4,float)
   for enabled in [True,False]:
    rgb=np.empty((h,w,3),np.uint16);assert lib.trial_reconstruct(norm.ctypes.data,v.ctypes.data if enabled else None,mask.ctypes.data if enabled else None,w,h,phase,nr,nb,scale,rgb.ctypes.data,4,stats.ctypes.data)==0
    lib.trial_border(norm.ctypes.data,w,h,phase,nr,nb,rgb.ctypes.data);expected.append(rgb)
   p=out/f'jni_{cfa}_{ox}_{oy}.bin'
   with p.open('wb') as f:
    f.write(struct.pack('>5i',w,h,cfa,ox,oy));f.write(black.astype('>f4').tobytes());f.write(neutral.astype('>f4').tobytes());f.write(pairs.astype('>f8').tobytes());f.write(srcgrid.astype('>f4').tobytes());f.write(struct.pack('>d',scale))
    for a in [norm,sensor,*expected]:f.write(a.astype('>u2').tobytes())
   paths.append(str(p))
r=subprocess.run(['java','-Xcheck:jni','-cp',str(classes),'com.particlesdevs.photoncamera.m9.render.TrialJniCheck',str(out/'libtrial.so'),str(root/'app/src/main/assets/m9/m9_curve02_firmware.bin'),*paths],check=True,capture_output=True,text=True)
print(r.stdout);(out/'jni_checks.json').write_text(json.dumps({'result':r.stdout.strip(),'variance_formula_four_CFA_four_origins':'exact float32','actual_Java_and_JNI':True,'Android_bitmap_platform_stub':True,'device_test_pending':True},indent=2)+'\n')
