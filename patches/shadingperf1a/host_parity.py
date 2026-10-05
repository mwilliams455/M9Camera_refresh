"""Compile actual before/after shading helpers; compare exact RAW/stats and time them.
Only class names and Camera2's read-only LensShadingMap adapter change for the host.
This is a shading-stage check, not an Android/whole-JPEG performance measurement.
"""
from pathlib import Path
import argparse,hashlib,json,subprocess
p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('candidate',type=Path);p.add_argument('--json-jar',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
here=Path(__file__).resolve().parent;a.output.mkdir(parents=True,exist_ok=True)
hashes={}
for mode in ['m9','monochrom']:
 for revision,root in [('Before',a.parent),('After',a.candidate)]:
  name=revision+mode.capitalize();rel=Path('app/src/main/java/com/particlesdevs/photoncamera')/mode/'render'
  source=(root/rel/'M9R35Renderer.java').read_text();hashes[name]=hashlib.sha256(source.encode()).hexdigest()
  marker='    // SHADINGPERF1A:' if revision=='After' else '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMapLumaDecomp1A('
  helpers=source[source.index(marker):source.rfind('}')]
  cfa=(root/rel/'M9CfaResolver.java').read_text();assert cfa==(a.parent/rel/'M9CfaResolver.java').read_text()
  cfa=cfa[cfa.index('\n')+1:].replace('public final class','final class').replace('M9CfaResolver',name+'Cfa')
  helpers=helpers.replace('M9CfaResolver',name+'Cfa')
  wrapper='''
 static String run(int kind,short[] raw,int w,int h,LensShadingMap map,double alpha,int cfa,int ox,int oy) {
  NativeProspectiveShadingStats s;
  switch(kind) {
   case 0:s=applyNativeProspectiveGainMap(raw,w,h,map);break;
   case 1:s=applyNativeProspectiveGainMapLumaDecomp1A(raw,w,h,map,alpha);break;
   case 2:s=applyNativeProspectiveGainMapBayer(raw,w,h,map,cfa,ox,oy);break;
   case 3:s=applyNativeProspectiveGainMapLumaDecomp1ABayer(raw,w,h,map,alpha,cfa,ox,oy);break;
   default:throw new AssertionError();
  }
  return s.applied+":"+s.mapWidth+":"+s.mapHeight+":"+Double.doubleToLongBits(s.minGain)+":"+Double.doubleToLongBits(s.maxGain)+":"+s.correctedPixels+":"+Double.doubleToLongBits(s.representationScale)+":"+s.aboveNominalBeforeScale+":"+s.postScaleClipCount;
 }
'''
  (a.output/(name+'.java')).write_text('class '+name+' {\n'+helpers+wrapper+'}\n'+cfa)
(a.output/'Parity.java').write_text((here/'Parity.java').read_text())
cp=str(a.json_jar.resolve())
subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-cp',cp,'-d',str(a.output)]+[str(x) for x in a.output.glob('*.java')],check=True)
r=subprocess.check_output(['java','-Xms256m','-Xmx1g','-cp',str(a.output)+':'+cp,'Parity'],text=True)
report=json.loads(r);report['sourceSha256']=hashes
(a.output/'HOST_PARITY_BENCHMARK.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
