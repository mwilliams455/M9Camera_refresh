import com.particlesdevs.photoncamera.m9.preview.*;
import com.particlesdevs.photoncamera.gallery.adapters.DepthPageTransformer;
import android.view.View;
public class PolicyTest {
 static int count;static void check(boolean b,String why){count++;if(!b)throw new AssertionError(why);}
 public static void main(String[] args){
  long sec=1000000000L;M9TraceLedger1A l=new M9TraceLedger1A(2);
  M9TraceLedger1A.Entry a=l.begin("one","cam",sec),b=l.begin("two","cam",2*sec);
  l.complete("one",100,101,2*sec);l.complete("two",200,201,3*sec);
  check(l.sampling(15*sec),"Camera2 completion must not terminate a slow render");
  l.jpegComplete("one",20*sec);l.jpegComplete("two",21*sec);
  check(l.sampling(28*sec),"second capture keeps its own post-JPEG window");
  check(!l.sampling(29*sec),"eight seconds after final JPEG closes all windows");
  l.jpegComplete("two",35*sec);check(b.jpegCompletedNs==21*sec,"duplicate endpoint cannot extend window");
  check(!M9TracePolicy1B.sampling(sec,-1,61*sec),"missing JPEG bounded even with a Camera2 result");
  check(!M9TracePolicy1B.sampling(sec,59*sec,61*sec),"late JPEG cannot escape hard timeout");
  check(!M9TracePolicy1B.sampling(sec,-1,sec-1),"cannot sample before shutter");
  check(M9TracePolicy1B.sampling(sec,20*sec,28*sec-1),"post-JPEG boundary inclusive until eight seconds");
  check(!M9TracePolicy1B.sampling(sec,20*sec,28*sec),"post-JPEG endpoint exact");
  l.bindFilename(a,"one.jpg");l.bindFilename(b,"two.jpg");
  check(l.byFilename("one.jpg")==a&&l.byFilename("missing.jpg")==null,"exact JPEG join");
  check(l.byFilename("one.dng")==null&&l.byRelatedFilename("one.dng")==a,"RAW alias separate from JPEG join");
  check(l.byRelatedFilename("one.png")==null,"unrelated extension excluded");
  check(M9TracePolicy1B.role("ONE.DNG").equals("raw_dng"),"RAW source labelled");
  check(M9TracePolicy1B.role("one.jpg").equals("jpeg"),"JPEG source labelled");
  check(M9TracePolicy1B.localFilename("file","/camera/example name.jpg").equals("example name.jpg"),"file URI needs no content provider");
  check(M9TracePolicy1B.localFilename("content","/media/123")==null,"content URI requires provider name");
  l.bindFilename(b,"one.jpg");check(l.byRelatedFilename("one.dng")==null,"ambiguous stems rejected");
  check(l.byFilename("one.jpg")==null,"ambiguous exact names rejected");
  l.complete("two",100,201,3*sec);check(l.bySensor(100)==null,"ambiguous timestamps rejected");
  check(l.begin("three","cam",sec)==null,"active entries not evicted");
  l.close("one");check(l.begin("three","cam",40*sec)!=null&&l.get("one")==null,"closed entries bounded");
  DepthPageTransformer transformer=new DepthPageTransformer();
  for(float pos:new float[]{0,.5f,1,2}){
   View v=new View();transformer.transformPage(v,pos);
   boolean valid=M9TracePolicy1B.unitTransform(v.alpha,v.sx,v.sy,0,0,0,v.tx,0);
   check(valid==(pos==0),"actual page transformer eligibility at "+pos);
  }
  check(!M9TracePolicy1B.unitTransform(1,1,1,0,0,0,0,2),"translated ancestor rejected");
  check(!M9TracePolicy1B.unitTransform(1,1,1,0,4,0,0,0),"3D rotation rejected");
  System.out.println("M9SHUTTERTRACE1B lifecycle/filename/page policy PASS: "+count+" assertions");
 }
}
