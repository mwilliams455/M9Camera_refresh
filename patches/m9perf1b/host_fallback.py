"""Execute the actual parent/candidate block orchestration with deterministic native/Bitmap adapters.

This checks allocation and fallback routing, not the unchanged photographic JNI kernels.
"""
from pathlib import Path
import argparse,json,subprocess
p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('candidate',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
path='app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
def block(root):
 s=(root/path).read_text();start=s.index('            // Metering/audits finish before spatial detail;')
 first=s.index('            int[] argbBlock = null;',start) if '            int[] argbBlock = null;' in s[start:] else s.index('            final int[] argbBlock = new int[maxBlockPixels];',start)
 end=s.index('            cam16.release();',first)
 return s[first:end]
header=r'''
import java.nio.ByteBuffer;
import java.util.Arrays;
public class FallbackHarness {
 static final int NATIVE_COLOR_BLOCK_ROWS=384,NATIVE_COLOR_WORKERS=8;
 static int currentWidth,currentHeight,rejectAt,bitmapCalls,currentY;
 static int[] seenFallback;
 static void check(boolean condition,String detail){if(!condition)throw new AssertionError(detail);}
 static int color(int x,int y){return 0xff000000|((x*9781^y*7919)&0xffffff);}
 static void init(int w,int h,int reject){currentWidth=w;currentHeight=h;rejectAt=reject;bitmapCalls=0;seenFallback=null;}
 static class Bitmap {
  enum Config {ARGB_8888}
  final int width,height;final boolean mutable;final int[] pixels;
  Bitmap(int w,int h,boolean m){width=w;height=h;mutable=m;pixels=new int[w*h];}
  boolean isMutable(){return mutable;}Config getConfig(){return Config.ARGB_8888;}
  int getWidth(){return width;}int getHeight(){return height;}int getRowBytes(){return width*4;}
  void setPixels(int[] src,int offset,int stride,int x,int y,int w,int h){
   check(src!=null,"missing fallback buffer");
   for(int row=0;row<h;row++)System.arraycopy(src,offset+row*stride,pixels,(y+row)*width+x,w);
  }
 }
 static class Mat {void get(int y,int x,short[] b){check(b!=null,"missing camera fallback");currentY=y;}}
 static class Context {double cct=4500;}
 static double tungstenGuardWeight(double cct){return 0.;}
 static final double TG_NEG_CB_COMPRESSION=.1,TG_NEG_CR_COMPRESSION=.1;
 static class M9RenderCrash1D {static void stage(String ignored){}}
 static void stats(long[] s,int count){Arrays.fill(s,0);s[0]=count;s[4]=8;}
 static int destinationX(int x,int y,int w,int h,int r){return r==90?h-1-y:r==180?w-1-x:r==270?y:x;}
 static int destinationY(int x,int y,int w,int h,int r){return r==90?x:r==180?h-1-y:r==270?w-1-x:y;}
 static void fallback(int[] argb,int w,int h,int y0,int rows,int rotation,long[] s){
  check(argb!=null,"native fallback received null");
  if(seenFallback!=null)check(seenFallback==argb,"fallback storage was reallocated within the frame");
  seenFallback=argb;int ow=rotation==90||rotation==270?rows:w;
  for(int y=0;y<rows;y++)for(int x=0;x<w;x++){
   int dx=destinationX(x,y,w,rows,rotation),dy=destinationY(x,y,w,rows,rotation);
   argb[dy*ow+dx]=color(x,y+y0);
  }stats(s,w*rows);
 }
 static class M9ColourTrial1C {
  static boolean renderBlockParallelDirectBitmap(long context,long address,int count,int w,Bitmap bmp,int y0,int h,
      double gain,double cb,double cr,int rotation,int workers,long[] s,ByteBuffer q){
   int call=bitmapCalls++;if(call==rejectAt)return false;
   for(int y=y0;y<y0+count/w;y++)for(int x=0;x<w;x++){
    int dx=destinationX(x,y,w,h,rotation),dy=destinationY(x,y,w,h,rotation);
    bmp.pixels[dy*bmp.width+dx]=color(x,y);
   }stats(s,count);return true;
  }
  static void renderBlockParallelDirect(long context,long address,int count,int w,int[] argb,double gain,
      double cb,double cr,int rotation,int workers,long[] s,ByteBuffer q,int y0,int h){fallback(argb,w,h,y0,count/w,rotation,s);}
 }
 static class M9NativeColorCore {
  static boolean renderFramePersistentDirectBitmap(long c,long addr,int w,int h,Bitmap b,int rows,double gain,
      double cb,double cr,int rotation,int workers,long[] stats){throw new AssertionError("rolled-back scheduler activated");}
  static void renderBlockParallel(long context,short[] input,int count,int w,int[] argb,double gain,double cb,double cr,
      int rotation,int workers,long[] s){fallback(argb,w,currentHeight,currentY,count/w,rotation,s);}
 }
 static class Run {
  final int[] pixels;final long allocated,direct,fallback;
  Run(Bitmap b,int[] argb,long direct,long fallback){pixels=b.pixels;allocated=argb==null?0:4L*argb.length;this.direct=direct;this.fallback=fallback;}
 }
'''
setup=r'''
 static Run run(int width,int height,int rotation,boolean cv,boolean mutable,int reject){
  init(width,height,reject);
  final int orientedWidth=rotation==90||rotation==270?height:width;
  final int orientedHeight=rotation==90||rotation==270?width:height;
  Bitmap oriented=new Bitmap(orientedWidth,orientedHeight,mutable);Mat cam16=new Mat();
  final int maxBlockPixels=width*NATIVE_COLOR_BLOCK_ROWS;
  final boolean nativeColorCvDirectEligible=cv;
  final long nativeColorCvBaseAddress=1,nativeColorCvRowBytes=width*6L,nativeContextForFrame=1;
  final double effectiveRenderGain=1.;final Context ctx=new Context();
  final ByteBuffer colourTrialQ14=ByteBuffer.allocate(0);
  final short[] camBlock=cv?null:new short[maxBlockPixels*3];
'''
source=header
for name,root in [('Before',a.parent),('After',a.candidate)]:
 source+=' static class '+name+' {\n'+setup+block(root)+'\nreturn new Run(oriented,argbBlock,nativeColorBitmapDirectBlocks,nativeColorBitmapFallbackBlocks);\n}}\n'
source+=r'''
 static int cases;
 static void compare(int w,int h,int rotation,int mode){
  int blocks=(h+383)/384;
  int reject=mode==1?0:mode==2?blocks/2:mode==3?blocks-1:-1;
  boolean cv=mode!=5,mutable=mode!=4;
  Run old=Before.run(w,h,rotation,cv,mutable,reject),next=After.run(w,h,rotation,cv,mutable,reject);
  check(Arrays.equals(old.pixels,next.pixels),"before/after routing mismatch");
  check(old.direct==next.direct&&old.fallback==next.fallback,"routing counters changed");
  check(old.allocated==w*384L*4,"parent allocation");
  check(next.allocated==(mode==0?0:w*384L*4),"candidate allocation");
  check(next.direct+next.fallback==blocks,"lost or double-rendered block");
  int ow=rotation==90||rotation==270?h:w;
  for(int y=0;y<h;y++)for(int x=0;x<w;x++){
   int dx=destinationX(x,y,w,h,rotation),dy=destinationY(x,y,w,h,rotation);
   check(next.pixels[dy*ow+dx]==color(x,y),"orientation or block seam mismatch");
  }
  int expectedCalls=mode>=4?0:mode==0?blocks:reject+1;
  check(bitmapCalls==expectedCalls,"direct rendering retried after rejection");
  cases++;
 }
 public static void main(String[] args){
  for(int w:new int[]{71,128})for(int h:new int[]{1,383,384,385,769})
   for(int r:new int[]{0,90,180,270})for(int mode=0;mode<6;mode++)compare(w,h,r,mode);
  for(int r:new int[]{0,90,180,270})compare(4096,3072,r,0);
  System.out.println("{\"status\":\"PASS\",\"routingCases\":"+cases+
    ",\"normal4096WideFallbackAllocationBeforeBytes\":6291456,\"normal4096WideFallbackAllocationAfterBytes\":0}");
 }
}
'''
(out/'FallbackHarness.java').write_text(source)
subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-d',str(out),str(out/'FallbackHarness.java')],check=True)
raw=subprocess.check_output(['java','-Xmx1024m','-cp',str(out),'FallbackHarness'],text=True)
report=json.loads(raw);report['scope']='Actual source orchestration; deterministic native and Bitmap adapters. No photographic JNI or phone benchmark.'
report['covers']=['direct success','first/middle/final block rejection','pre-declined bitmap','copied-input fallback','four rotations','odd widths and partial final blocks','one buffer reused after rejection','rolled-back scheduler remains disabled']
for dest in [out,Path(__file__).resolve().parent]:(dest/'FALLBACK_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
