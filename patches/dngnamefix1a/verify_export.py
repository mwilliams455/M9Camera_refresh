"""Exercise real profile generation, real TIFF writing and save-status handling on synthetic DNGs.

Only Android logging and asset access are adapted. The writer is never mocked.
Uses the Python standard library and Java 17 plus org.json.
"""
from pathlib import Path
import argparse,hashlib,json,re,struct,subprocess
p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('candidate',type=Path)
p.add_argument('--json-jar',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
out=args.output.resolve();out.mkdir(parents=True,exist_ok=True);jar=args.json_jar.resolve()
sizes={1:1,2:1,3:2,4:4,5:8,7:1,10:8,11:4,12:8}
def fixture():
 def u16(*n):return struct.pack('<'+'H'*len(n),*n)
 def u32(*n):return struct.pack('<'+'I'*len(n),*n)
 def rational(values,signed=False):return struct.pack('<'+('i' if signed else 'I')*len(values),*values)
 tags={256:(4,1,u32(64)),257:(4,1,u32(48)),258:(3,1,u16(16)),259:(3,1,u16(1)),
       262:(3,1,u16(32803)),271:(2,10,b'Synthetic\0'),272:(2,8,b'Fixture\0'),273:(4,1,u32(0)),
       274:(3,1,u16(1)),277:(3,1,u16(1)),278:(4,1,u32(48)),279:(4,1,u32(64*48*2)),
       33421:(3,2,u16(2,2)),33422:(1,4,bytes([0,1,1,2])),50706:(1,4,bytes([1,3,0,0])),
       50708:(2,21,b'Synthetic M9 fixture\0'),50713:(3,2,u16(2,2)),50714:(5,4,rational([64,1]*4)),
       50717:(4,1,u32(4095)),50721:(10,9,rational([10000,10000,0,10000,0,10000,0,10000,10000,10000,0,10000,0,10000,0,10000,10000,10000],True)),
       50728:(5,3,rational([1,2,1,1,2,3])),50730:(10,1,rational([-1,2],True)),50778:(3,1,u16(21))}
 entries=[];payload=bytearray();start=8+2+12*len(tags)+4
 for tag,(typ,count,data) in sorted(tags.items()):
  assert len(data)==sizes[typ]*count,(tag,len(data),count)
  if len(data)<=4:value=data.ljust(4,b'\0')
  else:
   while (start+len(payload))%4:payload.append(0)
   value=u32(start+len(payload));payload.extend(data)
  entries.append([tag,typ,count,value])
 raw=u16(*[1024+(i*17)%2800 for i in range(64*48)])
 for e in entries:
  if e[0]==273:e[3]=u32(start+len(payload))
 return b'II'+u16(42)+u32(8)+u16(len(tags))+b''.join(struct.pack('<HHI',t,k,n)+v for t,k,n,v in entries)+u32(0)+payload+raw
def tags(data):
 assert data[:4]==b'II*\0';pos=struct.unpack_from('<I',data,4)[0];count=struct.unpack_from('<H',data,pos)[0];result={}
 for i in range(count):
  at=pos+2+12*i;tag,typ,n=struct.unpack_from('<HHI',data,at);length=sizes[typ]*n
  pointer=at+8 if length<=4 else struct.unpack_from('<I',data,at+8)[0]
  result[tag]=(typ,n,data[pointer:pointer+length])
 assert struct.unpack_from('<I',data,pos+2+12*count)[0]==0
 return result
original=bytes(fixture());original_tags=tags(original);(out/'original.dng').write_bytes(original)
stubs=out/'stubs'
code={
 'android/util/Log.java':'package android.util;public class Log{public static void e(String t,String m,Throwable e){}}',
 'com/particlesdevs/photoncamera/app/PhotonCamera.java':'''package com.particlesdevs.photoncamera.app;import java.nio.file.*;import java.io.*;public class PhotonCamera{public static Path assets;public static Resource getResourcesStatic(){return new Resource();}public static class Resource{public Resource getAssets(){return this;}public InputStream open(String p)throws IOException{return Files.newInputStream(assets.resolve(p));}}}''',
 'ExportProbe.java':r'''import java.nio.file.*;import java.util.*;import org.json.*;
import com.particlesdevs.photoncamera.processing.*;import com.particlesdevs.photoncamera.app.PhotonCamera;
import com.particlesdevs.photoncamera.m9.*;
public class ExportProbe {
 static JSONObject frame(int bank,int contrast,int mode)throws Exception{return new JSONObject()
  .put("nativeSaturationBankActuallySelected",bank).put("nativeContrastLevelActuallySelected",contrast)
  .put("identityHsmApplied",true).put("jpegRequested",mode==1)
  .put("targetDomainTrace1A",new JSONObject().put("currentPpToM9Composed",new JSONArray("[[1.07,-0.04,-0.03],[0.02,0.89,0.09],[-0.02,0.25,0.77]]")).put("effectiveRenderGain",1.25));}
 static void check(boolean ok,String why){if(!ok)throw new AssertionError(why);}
 static void run(Path dir,byte[] original,String label,int bank,int contrast,int mode,String failure)throws Exception{
  Path file=dir.resolve(label+".dng");Files.write(file,original);JSONObject f=frame(bank,contrast,mode);
  if(failure.equals("missing_target"))f.remove("targetDomainTrace1A");
  JSONObject report=M9DngProfileExport.embed(file,f.toString(),!failure.equals("renderer_failed"));
  boolean success="embedded".equals(report.getString("status"));
  check(success==failure.isEmpty(),report.toString());
  if(success){check(report.getInt("leicaSaturationBank")==bank,"saturation");check(report.getInt("leicaContrastIndex")==contrast,"contrast");}
  else{check(Arrays.equals(original,Files.readAllBytes(file)),"original RAW changed on failure");
   if(failure.equals("old_name"))check(report.getString("reason").contains("Invalid profile name"),report.toString());}
  M9SaveStatus state=new M9SaveStatus();M9SaveSelection selection=M9SaveSelection.fromMode(mode,false);
  M9SaveStatus.Ticket ticket=state.begin(selection);ticket.complete(selection.jpeg,true,success,false,true);
  check(state.snapshot().pending==0,"save pending");check(state.snapshot().issues==(success?0:M9SaveStatus.PROFILE),"incorrect save warning");
  report.put("fixture",label).put("mode",mode).put("saveIssues",state.snapshot().issues);
  System.out.println(report);System.out.flush();
 }
 public static void main(String[] a)throws Exception{
  PhotonCamera.assets=Path.of(a[0]);Path dir=Path.of(a[1]);byte[] original=Files.readAllBytes(dir.resolve("original.dng"));
  if(a[2].equals("parent")){run(dir,original,"parent_reproduction",2,2,2,"old_name");return;}
  for(int bank=0;bank<5;bank++)for(int contrast=0;contrast<5;contrast++)for(int mode:new int[]{1,2})
   run(dir,original,"capture_"+bank+"_"+contrast+"_"+mode,bank,contrast,mode,"");
  run(dir,original,"invalid_contrast",2,9,2,"invalid_contrast");
  run(dir,original,"missing_target",2,2,1,"missing_target");
  run(dir,original,"renderer_failed",2,2,2,"renderer_failed");
 }
}'''}
for name,content in code.items():
 target=stubs/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(content)
results=[]
for mode,root in [('parent',args.parent.resolve()),('candidate',args.candidate.resolve())]:
 classes=out/(mode+'_classes');classes.mkdir(exist_ok=True);base=root/'app/src/main/java/com/particlesdevs/photoncamera'
 prod=[base/'processing'/n for n in ['M9Contrast.java','M9Saturation.java','M9DngProfile.java','M9DngProfileExport.java','M9DngProfileWriter.java']]
 prod+=[base/'m9/render/M9TargetFirmwareCalibration.java',base/'m9/M9SaveSelection.java',base/'m9/M9SaveStatus.java']
 subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-cp',str(jar),'-d',str(classes),*map(str,stubs.rglob('*.java')),*map(str,prod)],check=True)
 command=['java','-Xmx256m','-cp',str(classes)+':'+str(jar),'ExportProbe',str(root/'app/src/main/assets'),str(out),mode]
 with subprocess.Popen(command,stdout=subprocess.PIPE,text=True) as process:
  for line in process.stdout:
   result=json.loads(line);path=out/(result['fixture']+'.dng');data=path.read_bytes();t=tags(data)
   if result['status']=='embedded':
    assert data[:4]==original[:4] and data[8:len(original)]==original[8:],'Original RAW/calibration bytes changed'
    for tag,value in original_tags.items():
     if tag!=50706:assert t[tag]==value,tag
    name=t[50936][2].rstrip(b'\0').decode();assert name==result['profileName'] and ' C-' in name and ' C:' not in name
    assert t[50934][2]==t[50936][2]
    assert t[50982][:2]==(11,180*65*129*3) and t[50940][:2]==(11,129*2)
    xmp=t[700][2].decode();assert 'crs:CameraProfile="'+name+'"' in xmp
    assert 'crs:CameraProfileDigest="'+result['profileDigest']+'"' in xmp
    assert 'crs:Sharpness="0"' in xmp and 'crs:Exposure2012="0.00"' in xmp
    assert result['saveIssues']==0
    result['rawAndPhysicalTagsExact']=True;result['profileAndXmpVerified']=True
   else:assert data==original and result['saveIssues']==4
   result['fileSha256']=hashlib.sha256(data).hexdigest();results.append(result)
   # Fixtures are reproducible and large after embedding; retain metadata evidence only.
   path.unlink()
   if len(results)%10==0:print('Verified export fixtures:',len(results),flush=True)
  if process.wait()!=0:raise RuntimeError('Real exporter/writer regression failed in '+mode)
 assert not list(out.glob('M9_PROFILE_PENDING_*')),'Staging files leaked'
report=dict(status='PASS',successfulExports=50,settingsCombinations=25,outputModes=['RAW+JPEG','RAW-only'],
 parentInvalidNameReproduced=True,failedExportsPreserveOriginal=4,writerMocked=False,
 actualFirmwareAssetLoader=True,actualSaveStatus=True,rawPixelsAndPhysicalTagsPreserved=True,
 sourceScope='Actual Java exporter, profile generator, firmware loader, TIFF writer and save-status classes. Android logging and asset access are adapted. Synthetic RAW fixtures; phone filesystem and editor validation pending.',cases=results)
for target in [out,Path(__file__).resolve().parent]:(target/'EXPORT_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))
