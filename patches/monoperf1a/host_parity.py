"""Compile the actual parent/candidate pre-demosaic blocks and unchanged helpers.
Only Camera2's read-only map/result accessors are adapted for the host JVM.
Pass org.json 20250517 JAR. Timings are host stage timings, not phone/JPEG timings.
"""
from pathlib import Path
import argparse,hashlib,json,subprocess
p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('candidate',type=Path);p.add_argument('--json-jar',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=True)
rel=Path('app/src/main/java/com/particlesdevs/photoncamera/monochrom/render')
parents=[]
for name,root in [('Before',a.parent),('After',a.candidate)]:
 s=(root/rel/'M9R35Renderer.java').read_text();parents.append(s)
 start=s.index('        LensShadingMap nativeLiveGainMap =',s.index('final MonoSourceRawOrigin2A sourceRawOrigin'))
 end=s.index('        final int monoContrast1A =',start)
 block=s[start:end]
 helpers=s[s.index('    private static JSONObject rawShadingResidualAudit1A('):s.rfind('}')]
 rawtail=s[s.index('    private static final class RawTail {'):s.index('    private static RawTail rawTail(')]
 code='import org.json.*;\nclass '+name+' {\nprivate static final boolean MONO1A_ENABLED=true;\nprivate static final double TC_TAIL_CURVATURE_THRESHOLD=0.25, TC_HEADROOM_TARGET=0.95;\n'+rawtail+helpers+'''
 static Object[] run(short[] norm16,int width,int height,LensShadingMap map,int sourceCfaPattern,int sourceRawOriginX,int sourceRawOriginY,int cameraRotation,boolean applyNativeShading) throws Exception {
 CaptureResult nativeCaptureResult=new CaptureResult(map);
 boolean applyShadingLumaDecomp1A=false,normalizeShadingLumaOutsideMedian1A=false,applyShadedGuard1A=false,applyShadedGuardCap20Ev1A=false;
 double shadingLumaAuthorityAlpha=1.0,shadingLumaTargetOutsideMedianEv1A=0.30;
 RawTail tail=new RawTail();tail.q=.999;tail.tailValue=.85;
'''+block+'''
 String stats=nativeShading.applied+":"+nativeShading.mapWidth+":"+nativeShading.mapHeight+":"+nativeShading.minGain+":"+nativeShading.maxGain+":"+nativeShading.correctedPixels+":"+nativeShading.representationScale+":"+nativeShading.aboveNominalBeforeScale+":"+nativeShading.postScaleClipCount;
 return new Object[]{stats,rawShadingResidual1A,shadingLumaDecomp1AJson,shadedTailAuditStats,shadedTailSpatial1AJson};
 }
}
'''
 (a.output/(name+'.java')).write_text(code)
assert parents[0][parents[0].index('    private static JSONObject rawShadingResidualAudit1A('):]==parents[1][parents[1].index('    private static JSONObject rawShadingResidualAudit1A('):], 'A photographic helper changed'
cfa=(a.parent/rel/'M9CfaResolver.java').read_text();assert cfa==(a.candidate/rel/'M9CfaResolver.java').read_text()
(a.output/'M9CfaResolver.java').write_text(cfa[cfa.index('/**'):])
(a.output/'Parity.java').write_text(r'''
import java.util.*;
import org.json.*;
class LensShadingMap {
 final float[] gains;final int w,h;int reads;
 LensShadingMap(float[] g,int w,int h){this.gains=g.clone();this.w=w;this.h=h;}
 int getColumnCount(){return w;}int getRowCount(){return h;}int getGainFactorCount(){return gains.length;}
 void copyGainFactors(float[] dst,int off){reads++;System.arraycopy(gains,0,dst,off,gains.length);}
}
class CaptureResult {
 static final Object STATISTICS_LENS_SHADING_CORRECTION_MAP=new Object();final LensShadingMap map;
 CaptureResult(LensShadingMap m){map=m;}LensShadingMap get(Object key){return map;}
}
public class Parity {
 static volatile Object sink;
 static LensShadingMap map(int kind){
  int w=kind==0?1:17,h=kind==0?1:13;float[] g=new float[w*h*4];
  for(int y=0;y<h;y++)for(int x=0;x<w;x++)for(int c=0;c<4;c++)g[(y*w+x)*4+c]=kind<2?1f:1f+(float)(Math.pow((x-w/2.0)/w,2)+Math.pow((y-h/2.0)/h,2))*(c+1)*2;
  return new LensShadingMap(g,w,h);
 }
 static short[] raw(int w,int h,int pattern){short[] r=new short[w*h];Random rnd=new Random(500+pattern);
  for(int i=0;i<r.length;i++)r[i]=(short)(pattern==0?0:pattern==1?65535:pattern==2?(i*65535L/Math.max(1,r.length-1)):rnd.nextInt(65536));return r;}
 static int cases=0;
 static void compare(int w,int h,int pattern,int mk,int cfa,int ox,int oy,int rot,boolean shade)throws Exception{
  short[] b=raw(w,h,pattern),n=b.clone();LensShadingMap m=map(mk);float[] original=m.gains.clone();
  Object[] bs=Before.run(b,w,h,m,cfa,ox,oy,rot,shade);int beforeReads=m.reads;m.reads=0;
  Object[] ns=After.run(n,w,h,m,cfa,ox,oy,rot,shade);
  if(!Arrays.equals(b,n)||!bs[0].equals(ns[0])||!Arrays.equals(original,m.gains))throw new AssertionError("parity "+cases);
  for(int k=1;k<5;k++)if(ns[k]!=null)throw new AssertionError("discarded audit executed");
  if(m.reads!=(shade?1:0)||beforeReads!=(shade?5:1))throw new AssertionError("map passes "+beforeReads+"/"+m.reads);
  cases++;
 }
 static void reject(LensShadingMap m)throws Exception{
  String b="",n="";try{Before.run(new short[64],8,8,m,0,0,0,0,true);}catch(Exception ex){b=ex.getClass().getName();}
  try{After.run(new short[64],8,8,m,0,0,0,0,true);}catch(Exception ex){n=ex.getClass().getName();}
  if(b.isEmpty()||n.isEmpty())throw new AssertionError("invalid map accepted");cases++;
 }
 static double timed(boolean before,short[] frame,int w,int h,LensShadingMap m)throws Exception{
  short[] data=frame.clone();long t=System.nanoTime();
  sink=before?Before.run(data,w,h,m,0,0,0,90,true):After.run(data,w,h,m,0,0,0,90,true);
  return (System.nanoTime()-t)/1e6;
 }
 static double median(double[] x){double[] a=x.clone();Arrays.sort(a);return a[a.length/2];}
 public static void main(String[] args)throws Exception{
  for(int c=0;c<4;c++)for(int origin=0;origin<4;origin++)for(int r=0;r<4;r++)for(int pat=0;pat<4;pat++)
   compare(97,65,pat,(c+pat+origin)%3,c,origin&1,origin>>1,r*90,true);
  compare(1,1,0,0,0,0,0,0,true);compare(1,17,3,2,3,1,1,270,true);compare(19,1,3,2,1,0,1,90,true);
  compare(97,65,3,2,0,0,0,0,false);
  reject(null);reject(new LensShadingMap(new float[]{Float.NaN,1,1,1},1,1));reject(new LensShadingMap(new float[]{0,1,1,1},1,1));
  compare(4096,3072,2,2,0,0,0,90,true);compare(4000,3000,3,2,3,1,1,270,true);
  short[] frame=raw(4096,3072,3);LensShadingMap m=map(2);
  for(int i=0;i<3;i++){timed(true,frame,4096,3072,m);timed(false,frame,4096,3072,m);}
  double[] b=new double[7],n=new double[7];
  for(int i=0;i<7;i++)if((i&1)==0){b[i]=timed(true,frame,4096,3072,m);n[i]=timed(false,frame,4096,3072,m);}else{n[i]=timed(false,frame,4096,3072,m);b[i]=timed(true,frame,4096,3072,m);}
  JSONObject out=new JSONObject();out.put("status","PASS");out.put("parityCases",cases);out.put("rawAndRepresentationStatsExact",true);out.put("mapUnmodified",true);
  out.put("scope","Actual pre-demosaic Java blocks with read-only Camera2 host adapters; unchanged downstream math and native binaries checked separately. Not a whole-JPEG or phone benchmark.");
  out.put("hostJava",System.getProperty("java.version"));out.put("dimensions","4096x3072");out.put("warmups",3);out.put("rounds",7);
  out.put("parentStageMs",b);out.put("candidateStageMs",n);out.put("parentMedianMs",median(b));out.put("candidateMedianMs",median(n));out.put("medianSavedMs",median(b)-median(n));out.put("stageReductionPercent",100*(1-median(n)/median(b)));
  out.put("rawCloneAllocationBytesAvoidedPerFrame",4096L*3072*2*2);out.put("phoneValidationPending",true);System.out.println(out.toString(2));
 }
}
''')
cp=str(a.json_jar.resolve())
subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-cp',cp,'-d',str(a.output)]+[str(p) for p in a.output.glob('*.java')],check=True)
r=subprocess.check_output(['java','-Xmx1g','-cp',str(a.output)+':'+cp,'Parity'],text=True)
report=json.loads(r);report['parentRendererSha256']=hashlib.sha256(parents[0].encode()).hexdigest();report['candidateRendererSha256']=hashlib.sha256(parents[1].encode()).hexdigest()
(a.output/'HOST_PARITY_BENCHMARK.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
