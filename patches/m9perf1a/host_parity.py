"""Compare actual M9 RAW shading orchestration and finished-bitmap report calls.
Camera2 map and Bitmap readback are host adapters; this is not an Android/JPEG benchmark.
"""
from pathlib import Path
import argparse,hashlib,json,subprocess
p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('candidate',type=Path);p.add_argument('--json-jar',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
rel=Path('app/src/main/java/com/particlesdevs/photoncamera/m9/render')
sources=[(r/rel/'M9R35Renderer.java').read_text() for r in [a.parent,a.candidate]]
def span(s,start,end):return s[s.index(start):s.index(end,s.index(start))]
skipped=span(sources[1],'    private static JSONObject readOnlyImageAuditSkipped1A(', '    // BASISHSM1I-FINALCLIPAUDIT1A')
for name,s in zip(['Before','After'],sources):
 block=span(s,'        LensShadingMap nativeLiveGainMap =','        JSONObject colourTrial1CJson =')
 helpers=s[s.index('    private static JSONObject rawShadingResidualAudit1A('):s.rfind('}')]
 rawtail=span(s,'    private static final class RawTail {','    private static RawTail rawTail(')
 final=span(s,'    private static JSONObject finalClipAudit1A(','    // SKINLUMA1A: aggregate diagnostics')
 if name=='After':
  gate=span(s,'        final boolean qualityGate1BSatAuditEnabled =','        // PHYSICALSOURCEAGNOSTIC1A:')
  last=span(s,'            long finalClipReportStartedNs1A =','            return new RenderCore(oriented, d);')
 else:
  gate=''
  last=span(s,'            d.put("finalClipAudit1AEnabled", true);','            return new RenderCore(oriented, d);')
 code='import org.json.*;\nclass '+name+' {\nprivate static final double TC_TAIL_CURVATURE_THRESHOLD=0.25, TC_HEADROOM_TARGET=0.95;\n'+rawtail+helpers+final+skipped+'''
 static Object[] run(short[] norm16,int width,int height,LensShadingMap map,int sourceCfaPattern,int sourceRawOriginX,int sourceRawOriginY,int cameraRotation,Bitmap oriented,int bridgeProbeMode,boolean skinLumaStageAuditEnabled1A) throws Exception {
 CaptureResult nativeCaptureResult=new CaptureResult(map);
 boolean applyNativeShading=true,applyShadingLumaDecomp1A=true,normalizeShadingLumaOutsideMedian1A=true,applyShadedGuard1A=false,applyShadedGuardCap20Ev1A=false;
 double shadingLumaAuthorityAlpha=1.0,shadingLumaTargetOutsideMedianEv1A=0.30;
 RawTail tail=new RawTail();tail.q=.999;tail.tailValue=.85;
'''+gate+block+'''
 JSONObject d=new JSONObject();
'''+last+'''
 String stats=nativeShading.applied+":"+nativeShading.mapWidth+":"+nativeShading.mapHeight+":"+nativeShading.minGain+":"+nativeShading.maxGain+":"+nativeShading.correctedPixels+":"+nativeShading.representationScale+":"+nativeShading.aboveNominalBeforeScale+":"+nativeShading.postScaleClipCount+":"+effectiveShadingLumaAuthorityAlpha+":"+shadingLumaSourceOutsideMedianEv1A;
 return new Object[]{stats,rawShadingResidual1A,shadingLumaDecomp1AJson,d};
 }
}
'''
 (a.output/(name+'.java')).write_text(code)
assert sources[0][sources[0].index('    private static JSONObject rawShadingResidualAudit1A('):]==sources[1][sources[1].index('    private static JSONObject rawShadingResidualAudit1A('):]
assert span(sources[0],'    private static JSONObject finalClipAudit1A(','    // SKINLUMA1A: aggregate diagnostics')==span(sources[1],'    private static JSONObject finalClipAudit1A(','    // SKINLUMA1A: aggregate diagnostics')
cfa=(a.parent/rel/'M9CfaResolver.java').read_text();assert cfa==(a.candidate/rel/'M9CfaResolver.java').read_text();(a.output/'M9CfaResolver.java').write_text(cfa[cfa.index('/**'):])
(a.output/'Parity.java').write_text(r'''
import java.util.*;
import org.json.*;
class LensShadingMap {
 final float[] gains;final int w,h;int reads;
 LensShadingMap(float[] g,int w,int h){gains=g.clone();this.w=w;this.h=h;}
 int getColumnCount(){return w;}int getRowCount(){return h;}int getGainFactorCount(){return gains.length;}
 void copyGainFactors(float[] dst,int off){reads++;System.arraycopy(gains,0,dst,off,gains.length);}
}
class CaptureResult {static final Object STATISTICS_LENS_SHADING_CORRECTION_MAP=new Object();final LensShadingMap map;CaptureResult(LensShadingMap m){map=m;}LensShadingMap get(Object key){return map;}}
class M9RenderDiagnostics {static boolean enabled;static boolean fullFrameSatAuditEnabled(){return enabled;}}
class Bitmap {
 final int w,h;final int[] pixels;int reads;
 Bitmap(int w,int h,int pattern){this.w=w;this.h=h;pixels=new int[w*h];Random r=new Random(997+pattern);for(int i=0;i<pixels.length;i++)pixels[i]=pattern==0?0xff000000:pattern==1?0xffffffff:pattern==2?(0xff000000|((i%256)*0x010101)):(0xff000000|r.nextInt(0x1000000));}
 boolean isRecycled(){return false;}int getWidth(){return w;}int getHeight(){return h;}
 void getPixels(int[] dst,int off,int stride,int x,int y,int width,int height){reads++;for(int row=0;row<height;row++)System.arraycopy(pixels,(y+row)*w+x,dst,off+row*stride,width);}
}
public class Parity {
 static volatile Object sink;static int cases;
 static LensShadingMap map(int kind){int w=17,h=13;float[] g=new float[w*h*4];for(int y=0;y<h;y++)for(int x=0;x<w;x++)for(int c=0;c<4;c++)g[(y*w+x)*4+c]=kind==0?1f:1f+(float)(Math.pow((x-w/2.0)/w,2)+Math.pow((y-h/2.0)/h,2))*(c+1)*2;return new LensShadingMap(g,w,h);}
 static short[] raw(int w,int h,int pat){short[] r=new short[w*h];Random rnd=new Random(50+pat);for(int i=0;i<r.length;i++)r[i]=(short)(pat==0?0:pat==1?65535:pat==2?(i*65535L/Math.max(1,r.length-1)):rnd.nextInt(65536));return r;}
 static void compare(int w,int h,int pat,int cfa,int ox,int oy,int rot,boolean enabled,int bridge,boolean skin)throws Exception{
  short[] b=raw(w,h,pat),n=b.clone();LensShadingMap m=map((pat+cfa)%2);float[] original=m.gains.clone();Bitmap img=new Bitmap(rot==90||rot==270?h:w,rot==90||rot==270?w:h,pat);int[] originalArgb=img.pixels.clone();
  M9RenderDiagnostics.enabled=enabled;Object[] bs=Before.run(b,w,h,m,cfa,ox,oy,rot,img,bridge,skin);int beforeReads=m.reads;m.reads=0;img.reads=0;
  Object[] ns=After.run(n,w,h,m,cfa,ox,oy,rot,img,bridge,skin);boolean audit=enabled||bridge!=0||skin;
  if(!Arrays.equals(b,n)||!bs[0].equals(ns[0])||!Arrays.equals(original,m.gains)||!Arrays.equals(originalArgb,img.pixels))throw new AssertionError("pixel/exposure parity "+cases);
  if(beforeReads!=4||m.reads!=(audit?4:2)||img.reads!=(audit?(img.h+63)/64:0))throw new AssertionError("audit work boundary");
  JSONObject oldFinal=((JSONObject)bs[3]).getJSONObject("finalClipAudit1A"),newFinal=((JSONObject)ns[3]).getJSONObject("finalClipAudit1A");
  if(audit){if(!((JSONObject)bs[1]).similar(ns[1])||!((JSONObject)bs[2]).similar(ns[2])||!oldFinal.similar(newFinal))throw new AssertionError("opt-in report parity");}
  else{for(Object o:new Object[]{ns[1],ns[2],newFinal}){JSONObject j=(JSONObject)o;if(j.getBoolean("executed")||j.getBoolean("valid")||!"extended_diagnostics_off".equals(j.getString("reason")))throw new AssertionError("unmeasured report");}}
  cases++;
 }
 static double timed(boolean before,short[] raw,int w,int h,LensShadingMap map,Bitmap img)throws Exception{short[] r=raw.clone();long t=System.nanoTime();M9RenderDiagnostics.enabled=before;sink=After.run(r,w,h,map,0,0,0,90,img,0,false);return(System.nanoTime()-t)/1e6;}
 static double median(double[] x){double[] a=x.clone();Arrays.sort(a);return a[a.length/2];}
 public static void main(String[] args)throws Exception{
  for(int c=0;c<4;c++)for(int origin=0;origin<4;origin++)for(int rot=0;rot<4;rot++)for(int pat=0;pat<4;pat++)for(boolean on:new boolean[]{false,true})compare(97,65,pat,c,origin&1,origin>>1,rot*90,on,0,false);
  for(int mode:new int[]{3,4,30,54,55})compare(97,65,3,0,0,0,90,false,mode,false);compare(97,65,3,0,0,0,90,false,0,true);
  compare(1,1,0,0,0,0,0,false,0,false);compare(1,17,3,2,1,0,90,false,0,false);compare(19,1,3,3,0,1,270,true,0,false);
  compare(4096,3072,3,0,0,0,90,false,0,false);compare(4000,3000,2,3,1,1,270,true,0,false);
  M9RenderDiagnostics.enabled=false;short[] frame=raw(4096,3072,3);LensShadingMap map=map(1);Bitmap img=new Bitmap(3072,4096,3);
  for(int i=0;i<3;i++){timed(true,frame,4096,3072,map,img);timed(false,frame,4096,3072,map,img);}
  double[] b=new double[9],n=new double[9];for(int i=0;i<9;i++)if((i&1)==0){b[i]=timed(true,frame,4096,3072,map,img);n[i]=timed(false,frame,4096,3072,map,img);}else{n[i]=timed(false,frame,4096,3072,map,img);b[i]=timed(true,frame,4096,3072,map,img);}
  JSONObject j=new JSONObject();j.put("status","PASS");j.put("cases",cases);j.put("correctedRawExact",true);j.put("shadingNormalizationAndRepresentationExact",true);j.put("finishedArgbUnmodified",true);j.put("extendedReportsExactWhenEnabled",true);j.put("explicitProbesRetainReports",true);j.put("normalCaptureSkipsFinishedBitmapReadback",true);
  j.put("scope","Parity uses actual parent/candidate code. Timing compares baseline-equivalent reports on/off in the SAME candidate class and helpers to avoid independent JVM compilation bias. It excludes saturation audit, native colour and JPEG encoding; it is not a whole-render or phone benchmark.");j.put("hostJava",System.getProperty("java.version"));j.put("rawDimensions","4096x3072");j.put("bitmapDimensions","3072x4096");j.put("warmups",3);j.put("rounds",9);j.put("reportsOnMs",b);j.put("reportsOffMs",n);j.put("reportsOnMedianMs",median(b));j.put("reportsOffMedianMs",median(n));j.put("savedMedianMs",median(b)-median(n));j.put("stageReductionPercent",100*(1-median(n)/median(b)));j.put("bitmapReadbackBytesAvoided",4096L*3072*4);j.put("phoneValidationPending",true);System.out.println(j.toString(2));
 }
}
''')
cp=str(a.json_jar.resolve());subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-cp',cp,'-d',str(a.output)]+[str(p) for p in a.output.glob('*.java')],check=True)
r=subprocess.check_output(['java','-Xmx1g','-cp',str(a.output)+':'+cp,'Parity'],text=True);report=json.loads(r)
report['parentRendererSha256']=hashlib.sha256(sources[0].encode()).hexdigest();report['candidateRendererSha256']=hashlib.sha256(sources[1].encode()).hexdigest()
(a.output/'HOST_PARITY_BENCHMARK.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
