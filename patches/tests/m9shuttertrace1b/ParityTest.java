import com.particlesdevs.photoncamera.m9.preview.*;
import java.io.*;
public class ParityTest {
 public static void main(String[] a)throws Exception {
  int files=0;long bytes=0,updates=0;
  for(File f:new File(a[0]).listFiles())if(f.getName().endsWith(".jpg")&&!f.getName().contains("truncated")){
   M9JpegSignatureLegacy.Result old=M9JpegSignatureLegacy.read(f);
   M9JpegSignature1A.Result now=M9JpegSignature1A.read(f);
   if(!old.codingSha256.equals(now.codingSha256)||!java.util.Objects.equals(old.iccSha256,now.iccSha256)||old.codingBytes!=now.codingBytes||!old.sampling.equals(now.sampling))throw new AssertionError(f);
   if(now.digestUpdates!=(now.codingBytes+65535)/65536)throw new AssertionError("unbatched digest "+f);
   files++;bytes+=now.codingBytes;updates+=now.digestUpdates;
  }
  System.out.println("M9SHUTTERTRACE1B legacy hash parity PASS: "+files+" JPEGs, "+bytes+" coding bytes, "+updates+" digest provider updates");
 }
}
