import com.particlesdevs.photoncamera.gallery.viewmodel.M9TiffMetadata1A;
import java.nio.*;import java.nio.channels.*;import java.nio.file.*;import java.util.*;
public class TiffTest {
 static void check(boolean b,String s){if(!b)throw new AssertionError(s);}
 static void field(ByteBuffer b,int id,int type,int count,int value){b.putShort((short)id).putShort((short)type).putInt(count);if(type==3&&count==1)b.putShort((short)value).putShort((short)0);else b.putInt(value);}
 public static void main(String[] args)throws Exception{
  Path path=Paths.get(args[0]);int offset=80*1024*1024;
  for(ByteOrder order:new ByteOrder[]{ByteOrder.LITTLE_ENDIAN,ByteOrder.BIG_ENDIAN})try(FileChannel file=FileChannel.open(path,StandardOpenOption.CREATE,StandardOpenOption.READ,StandardOpenOption.WRITE,StandardOpenOption.TRUNCATE_EXISTING)) {
   ByteBuffer h=ByteBuffer.allocate(8).order(order);h.put((byte)(order==ByteOrder.LITTLE_ENDIAN?'I':'M')).put((byte)(order==ByteOrder.LITTLE_ENDIAN?'I':'M')).putShort((short)42).putInt(offset).flip();file.write(h,0);
   ByteBuffer b=ByteBuffer.allocate(2+7*12+4+16).order(order);b.putShort((short)7);
   field(b,0x100,4,1,4096);field(b,0x101,4,1,3072);field(b,0x8827,3,1,160);
   field(b,0x829a,5,1,offset+90);field(b,0x920a,5,1,offset+98);
   field(b,0x0111,4,1000000000,0); // Huge strip array must never be read.
   field(b,0x8769,4,1,offset); // Cycle must terminate.
   b.putInt(offset);b.putInt(1).putInt(125).putInt(24).putInt(1).flip();file.write(b,offset);
   Map<Integer,String> m=M9TiffMetadata1A.read(file);
   check("4096".equals(m.get(0x100))&&"3072".equals(m.get(0x101)),"dimensions");
   check("160".equals(m.get(0x8827)),"ISO");check("0.008".equals(m.get(0x829a)),"exposure");check("24/1".equals(m.get(0x920a)),"focal");
   ByteBuffer corrupt=ByteBuffer.allocate(4).order(order).putInt(-1);corrupt.flip();file.write(corrupt,4);
   try{M9TiffMetadata1A.read(file);throw new AssertionError("bad offset accepted");}catch(java.io.IOException expected){}
  }
  Files.delete(path);System.out.println("PASS big/little endian TIFF: 80 MiB offset under 16 MiB heap, exact tags, ignored strips, cycles, invalid offsets");
 }
}
