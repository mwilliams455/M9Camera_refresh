import com.particlesdevs.photoncamera.m9.preview.M9JpegSignature1A;
import java.io.*;
public class JpegTest {
 static void check(boolean b,String s){if(!b)throw new AssertionError(s);}
 public static void main(String[] a)throws Exception {
  File d=new File(a[0]);int n=0;
  for(String name:new String[]{"baseline","progressive"}) {
   M9JpegSignature1A.Result base=M9JpegSignature1A.read(new File(d,name+".jpg"));
   check(base.width==131&&base.height==97,"SOF dimensions");
   check(base.sampling.equals("1:2x2,2:1x1,3:1x1"),"actual encoder sampling");
   for(String suffix:new String[]{"-exif","-comment","-icc"}){
    M9JpegSignature1A.Result m=M9JpegSignature1A.read(new File(d,name+suffix+".jpg"));
    check(base.codingSha256.equals(m.codingSha256),"metadata cannot change coding digest");
    if(suffix.equals("-icc"))check(m.iccSegments==1&&m.iccSha256!=null,"ICC remains independently visible");
    n++;
   }
   check(!base.codingSha256.equals(M9JpegSignature1A.read(new File(d,name+"-quant.jpg")).codingSha256),"quantization change detected");
   try{M9JpegSignature1A.read(new File(d,name+"-truncated.jpg"));throw new AssertionError("accepted truncated JPEG");}catch(EOFException expected){}
   n+=4;
  }
  System.out.println("M9SHUTTERTRACE1A JPEG PASS: "+n+" baseline/progressive metadata, ICC, sampling, quantization and truncation cases");
 }
}
