"""Compile actual RAW allocator and unchanged legacy curve with recorded tele exposure.
Android plan/request integration is covered separately by MonoRawGainTest.
"""
from pathlib import Path
import argparse,json,subprocess,tempfile
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
base=a.source.resolve()/'app/src/main/java/com/particlesdevs/photoncamera'
s=(base/'processing/parameters/MonoIsoExpoSelector.java').read_text()
def method(sig):
 start=s.index(sig);i=s.index('{',start);depth=1;i+=1
 while depth:
  if s[i]=='{':depth+=1
  if s[i]=='}':depth-=1
  i+=1
 return s[start:i]
legacy='\n'.join(method(x) for x in ['public double normalizedIsoHigh()', 'public void applyShutterPriorityCurve(', 'private long snapToCleanIso(', 'private boolean containsRung(', 'private static double log2('])
probe='''import com.particlesdevs.photoncamera.monochrom.exposure.*;
public class Probe {
 static int checks;
 static void check(boolean b){checks++;if(!b)throw new AssertionError("check "+checks);}
 static double energy(MonoRawExposure1A.Result p){return (double)p.iso*p.exposureNs;}
 static void close(double a,double b){check(Math.abs(Math.log(a/b)/Math.log(2))<0.002);}
 static class Legacy {
 int iso=658,isolow=50,isohigh=6400,isoanalog=2236;long exposure=10000000,exposurelow=36098,exposurehigh=31645064894L;
 static final String TAG="test";static final int MIN_ISO_NORMALIZED=100;static final double CLEAN_ISO_STEP_FACTOR=2;
 static class Log{static void v(String a,String b){}}
 static class ExposureIndex{static String sec2string(double x){return ""+x;}static double time2sec(long x){return x/1e9;}}
 LEGACY
 }
 public static void main(String[] args) {
  Legacy old=new Legacy();old.applyShutterPriorityCurve(2056250,2056250,4);
  check(old.iso/2==1600);check(old.exposure==2056250);
  close(1600.0*old.exposure,3.29e9);
  int cap=MonoRawExposure1A.automaticIsoMaximum(50,6400,1118,10000);check(cap==1118);
  MonoRawExposure1A.Result fixed=MonoRawExposure1A.allocateAutomatic(3.29e9,old.exposure,50,cap,36098,31645064894L);
  check(fixed.iso==1118);check(fixed.exposureNs>old.exposure);close(energy(fixed),3.29e9);
  for(int low:new int[]{25,42,50,64,100})for(int analog:new int[]{0,1,1118,3200,6400,99999})for(int selected:new int[]{160,800,2500,10000}) {
   cap=MonoRawExposure1A.automaticIsoMaximum(low,6400,analog,selected);
   check(cap>=low&&cap<=6400&&cap<=Math.max(low,selected));
   if(analog>=low&&analog<=6400)check(cap<=analog);
   for(double ev:new double[]{-3,-1,-1.0/3,0,1.0/3,1,3})for(long preferred:new long[]{36098,1000000,2056250,16666666,1000000000}) {
    double target=3.29e9*Math.pow(2,ev);
    MonoRawExposure1A.Result r=MonoRawExposure1A.allocateAutomatic(target,preferred,low,cap,36098,31645064894L);
    check(r.iso>=low&&r.iso<=cap);check(r.exposureNs>=36098&&r.exposureNs<=31645064894L);close(energy(r),target);
   }
  }
  MonoRawExposure1A.Result min=MonoRawExposure1A.allocateAutomatic(1,1000000,50,1118,36098,10000000);
  check(min.iso==50&&min.exposureNs==36098);
  MonoRawExposure1A.Result max=MonoRawExposure1A.allocateAutomatic(1e15,1000000,50,1118,36098,10000000);
  check(max.iso==1118&&max.exposureNs==10000000);
  check(MonoExposurePlan1A.supportsMode("PHOTO"));check(MonoExposurePlan1A.supportsMode("MOTION"));
  for(String mode:new String[]{"NIGHT","VIDEO","RAWVIDEO",null})check(!MonoExposurePlan1A.supportsMode(mode));
  System.out.println("PASS "+checks+" checks; recorded request reproduced: ISO 1600 / 2056250 ns; corrected ISO "+fixed.iso+" / "+fixed.exposureNs+" ns; no renderer gain");
 }
}'''.replace('LEGACY',legacy)
with tempfile.TemporaryDirectory() as t:
 d=Path(t);(d/'Probe.java').write_text(probe)
 subprocess.run(['java','com.sun.tools.javac.Main','-d',str(d),str(d/'Probe.java'),str(base/'monochrom/exposure/MonoRawExposure1A.java'),str(base/'monochrom/exposure/MonoExposurePlan1A.java')],check=True)
 run=subprocess.run(['java','-ea','-cp',str(d),'Probe'],check=True,capture_output=True,text=True)
 print(run.stdout)
 if a.output:a.output.write_text(json.dumps({'status':'PASS','output':run.stdout.strip(),'scope':'actual pure budget allocator and extracted unchanged legacy curve; synthetic bounds/EV sweep; not HAL validation'},indent=2)+'\n')
