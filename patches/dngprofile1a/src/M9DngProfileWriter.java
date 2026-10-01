package com.particlesdevs.photoncamera.processing;

import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;

/** Append-only classic TIFF transport, committed by same-directory atomic replacement.
 * Original RAW bytes, physical-camera tags, opcodes and EXIF retain their offsets/values.
 * Only the root IFD pointer changes in the original prefix. No SDK/third-party DCP runtime.
 */
public final class M9DngProfileWriter {
    private static final int[] TYPE_SIZE={0,1,1,2,4,8,1,1,2,4,8,4,8,4};
    private static final int[] PROFILE_TAGS={700,50934,50936,50940,50941,50981,50982,51108,51109,51110};
    private static final double[] D50={.3457/.3585,1,(1-.3457-.3585)/.3585};
    private M9DngProfileWriter() {}

    public static final class Result {
        public final String name,digest;
        public final long addedBytes;
        Result(String name,String digest,long addedBytes) { this.name=name;this.digest=digest;this.addedBytes=addedBytes; }
    }
    static final class Entry {
        final int type,count;final byte[] entry;final long offset;
        Entry(byte[] entry,long length) throws IOException {
            this.entry=entry;ByteBuffer b=wrap(entry);type=b.getShort(2)&65535;
            long n=Integer.toUnsignedLong(b.getInt(4));
            if(type<=0||type>=TYPE_SIZE.length||n>Integer.MAX_VALUE) throw new IOException("Unsupported TIFF field");
            count=(int)n;long size=n*TYPE_SIZE[type];offset=Integer.toUnsignedLong(b.getInt(8));
            if(size>4&&(offset>length||size>length-offset)) throw new IOException("TIFF field outside file");
        }
        byte[] read(RandomAccessFile f) throws IOException {
            int size=Math.multiplyExact(count,TYPE_SIZE[type]);
            if(size>1024*1024) throw new IOException("Unexpected large calibration field");
            if(size<=4) return Arrays.copyOfRange(entry,8,8+size);
            byte[] out=new byte[size];f.seek(offset);f.readFully(out);return out;
        }
    }
    static ByteBuffer wrap(byte[] data) { return ByteBuffer.wrap(data).order(ByteOrder.LITTLE_ENDIAN); }
    private static TreeMap<Integer,Entry> readRoot(RandomAccessFile f) throws IOException {
        byte[] header=new byte[8];f.seek(0);f.readFully(header);
        if(header[0]!='I'||header[1]!='I'||header[2]!=42||header[3]!=0) throw new IOException("Classic little-endian TIFF required");
        long position=Integer.toUnsignedLong(wrap(header).getInt(4));
        if(position<8||position>f.length()-6) throw new IOException("Invalid IFD offset");
        f.seek(position);int count=(f.readUnsignedByte()|(f.readUnsignedByte()<<8));
        if(count==0||count>4096||position+6L+12L*count>f.length()) throw new IOException("Invalid IFD size");
        TreeMap<Integer,Entry> out=new TreeMap<>();
        for(int i=0;i<count;i++) {
            byte[] raw=new byte[12];f.readFully(raw);int tag=wrap(raw).getShort(0)&65535;
            if(out.put(tag,new Entry(raw,f.length()))!=null) throw new IOException("Duplicate TIFF tag");
        }
        if(f.readInt()!=0) throw new IOException("Unexpected chained IFD");
        return out;
    }
    private static Entry required(Map<Integer,Entry> tags,int code) throws IOException {
        Entry e=tags.get(code);if(e==null) throw new IOException("Missing TIFF tag "+code);return e;
    }
    private static int integer(RandomAccessFile f,Map<Integer,Entry> tags,int code) throws IOException {
        Entry e=required(tags,code);if(e.count!=1) throw new IOException("Expected scalar tag "+code);
        ByteBuffer b=wrap(e.read(f));if(e.type==3) return b.getShort()&65535;if(e.type==4) return b.getInt();
        throw new IOException("Expected integer tag "+code);
    }
    private static double[] rationals(RandomAccessFile f,Entry e,int count) throws IOException {
        if(e.count!=count||(e.type!=5&&e.type!=10)) throw new IOException("Invalid rational calibration tag");
        ByteBuffer b=wrap(e.read(f));double[] out=new double[count];
        for(int i=0;i<count;i++) {
            int n=b.getInt(),d=b.getInt();if(d==0) throw new IOException("Zero rational denominator");
            out[i]=(e.type==10?(double)n:Integer.toUnsignedLong(n))/(e.type==10?(double)d:Integer.toUnsignedLong(d));
            if(!Double.isFinite(out[i])) throw new IOException("Nonfinite calibration");
        }
        return out;
    }
    private static void fingerprintMatrix(MessageDigest digest,RandomAccessFile f,Entry e,boolean normalize) throws IOException {
        double[] m=rationals(f,e,9);
        if(normalize) {
            double max=-Double.MAX_VALUE;
            for(int i=0;i<3;i++) max=Math.max(max,m[i*3]*D50[0]+m[i*3+1]+m[i*3+2]*D50[2]);
            if(max>0&&(max<.99||max>1.01)) for(int i=0;i<9;i++) m[i]/=max;
        }
        ByteBuffer out=M9DngProfile.le(72);
        for(double value:m) {
            double rounded=roundSdk(value*10000)*.0001;
            out.putInt(roundSdk(rounded*10000)).putInt(10000);
        }
        digest.update(out.array());
    }
    private static int roundSdk(double value) { return (int)(value>0?value+.5:value-.5); }
    /** DNG profile MD5 serialization: normalized CMs, rounded FMs, name, policy,
     * table dimensions/data/encoding, baseline offset, black policy, float32 curve.
     * MD5 is the format's profile identifier, not a security primitive.
     */
    static String fingerprint(RandomAccessFile f,Map<Integer,Entry> tags,M9DngProfile profile,String name,double offset) throws Exception {
        MessageDigest md5=MessageDigest.getInstance("MD5");
        for(int i=0;i<2;i++) {
            Entry cm=tags.get(50721+i);if(cm==null) { if(i==0) throw new IOException("Missing physical ColorMatrix1");break; }
            int light=integer(f,tags,50778+i);md5.update(M9DngProfile.le(2).putShort((short)light).array());
            fingerprintMatrix(md5,f,cm,true);
            Entry fm=tags.get(50964+i);if(fm!=null) fingerprintMatrix(md5,f,fm,false);
        }
        md5.update(name.getBytes(StandardCharsets.UTF_8));
        // No profile calibration signature, copyright, HSM or reduction matrices are added.
        md5.update(M9DngProfile.le(4).putInt(1).array());
        md5.update(M9DngProfile.le(12).putInt(M9DngProfile.H).putInt(M9DngProfile.S).putInt(M9DngProfile.V).array());
        md5.update(profile.look);md5.update(M9DngProfile.le(4).putInt(1).array());
        if(offset!=0) md5.update(M9DngProfile.le(8).putDouble(offset).array());
        md5.update(M9DngProfile.le(4).putInt(1).array());md5.update(profile.tone);
        return M9DngProfile.hex(md5.digest()).toUpperCase(Locale.ROOT);
    }
    private static void add(RandomAccessFile f,TreeMap<Integer,Entry> tags,int code,int type,int count,byte[] data) throws IOException {
        if(data.length!=(long)TYPE_SIZE[type]*count) throw new IOException("Invalid profile field size");
        ByteBuffer b=M9DngProfile.le(12).putShort((short)code).putShort((short)type).putInt(count);
        if(data.length<=4) b.put(Arrays.copyOf(data,4));
        else {
            align(f);long offset=f.getFilePointer();if(offset+data.length>0xffffffffL) throw new IOException("DNG too large");
            b.putInt((int)offset);f.write(data);
        }
        tags.put(code,new Entry(b.array(),f.length()));
    }
    private static void align(RandomAccessFile f) throws IOException { while((f.getFilePointer()&3)!=0) f.write(0); }
    private static String xml(String s) { return s.replace("&","&amp;").replace("<","&lt;").replace("\"","&quot;").replace(">","&gt;"); }
    static byte[] xmp(String name,String digest) {
        StringBuilder b=new StringBuilder("<?xpacket begin=\"\ufeff\" id=\"W5M0MpCehiHzreSzNTczkc9d\"?>\n<x:xmpmeta xmlns:x=\"adobe:ns:meta/\"><rdf:RDF xmlns:rdf=\"http://www.w3.org/1999/02/22-rdf-syntax-ns#\"><rdf:Description rdf:about=\"\" xmlns:crs=\"http://ns.adobe.com/camera-raw-settings/1.0/\"");
        String[][] fields={{"Version","18.5.1"},{"ProcessVersion","15.4"},{"WhiteBalance","As Shot"},
            {"Exposure2012","0.00"},{"Contrast2012","0"},{"Highlights2012","0"},{"Shadows2012","0"},
            {"Texture","0"},{"Dehaze","0"},{"Vibrance","0"},{"Saturation","0"},
            {"ParametricShadows","0"},{"ParametricDarks","0"},{"ParametricLights","0"},{"ParametricHighlights","0"},
            {"ParametricShadowSplit","25"},{"ParametricMidtoneSplit","50"},{"ParametricHighlightSplit","75"},
            {"ConvertToGrayscale","False"},{"OverrideLookVignette","False"},{"ToneCurveName2012","Linear"},
            {"HDREditMode","0"},{"HasSettings","True"},{"HasCrop","False"},{"AlreadyApplied","False"},
            {"Whites2012","0"},{"Blacks2012","0"},{"Clarity2012","0"},{"Sharpness","0"},
            {"LuminanceSmoothing","0"},{"ColorNoiseReduction","0"},{"CameraProfile",name},{"CameraProfileDigest",digest}};
        for(String[] field:fields) b.append(" crs:").append(field[0]).append("=\"").append(xml(field[1])).append('"');
        b.append('>');
        for(String suffix:new String[]{"","Red","Green","Blue"}) b.append("<crs:ToneCurvePV2012").append(suffix)
            .append("><rdf:Seq><rdf:li>0, 0</rdf:li><rdf:li>255, 255</rdf:li></rdf:Seq></crs:ToneCurvePV2012").append(suffix).append('>');
        b.append("</rdf:Description></rdf:RDF></x:xmpmeta>\n<?xpacket end=\"w\"?>");return b.toString().getBytes(StandardCharsets.UTF_8);
    }
    public static Result embed(Path path,M9DngProfile profile,String name) throws Exception {
        if(name==null||!name.matches("[A-Za-z0-9 _.-]{1,120}")) throw new IOException("Invalid profile name");
        Path temp=null;
        try {
            temp=Files.createTempFile(path.toAbsolutePath().getParent(),".m9-profile-",".tmp");
            Files.copy(path,temp,StandardCopyOption.REPLACE_EXISTING);
            Result result;
            try(RandomAccessFile f=new RandomAccessFile(temp.toFile(),"rw")) {
                long originalLength=f.length();TreeMap<Integer,Entry> tags=readRoot(f);
                if(integer(f,tags,258)!=16||integer(f,tags,259)!=1||integer(f,tags,262)!=32803
                        ||integer(f,tags,277)!=1) throw new IOException("Expected uncompressed RAW16 Bayer DNG");
                required(tags,50706);required(tags,50708);required(tags,50728);
                for(int code:PROFILE_TAGS) if(tags.containsKey(code)) throw new IOException("Existing profile/XMP must not be overwritten");
                for(int code:new int[]{330,50725,50726,50931,50932,50937,50938,50939,50942,51022})
                    if(tags.containsKey(code)) throw new IOException("Unsupported existing profile structure "+code);
                double baseline=rationals(f,required(tags,50730),1)[0];
                if(baseline!=-.5) throw new IOException("Unexpected camera baseline exposure");
                String digest=fingerprint(f,tags,profile,name,.5);
                f.seek(originalLength);
                add(f,tags,50706,1,4,new byte[]{1,4,0,0});add(f,tags,50707,1,4,new byte[]{1,4,0,0});
                byte[] ascii=(name+'\0').getBytes(StandardCharsets.US_ASCII);
                add(f,tags,50934,2,ascii.length,ascii);add(f,tags,50936,2,ascii.length,ascii);
                add(f,tags,50940,11,profile.tone.length/4,profile.tone);
                add(f,tags,50941,4,1,M9DngProfile.le(4).putInt(1).array());
                add(f,tags,50981,4,3,M9DngProfile.le(12).putInt(M9DngProfile.H).putInt(M9DngProfile.S).putInt(M9DngProfile.V).array());
                add(f,tags,50982,11,profile.look.length/4,profile.look);
                add(f,tags,51108,4,1,M9DngProfile.le(4).putInt(1).array());
                add(f,tags,51109,10,1,M9DngProfile.le(8).putInt(1).putInt(2).array());
                add(f,tags,51110,4,1,M9DngProfile.le(4).putInt(1).array());
                byte[] packet=xmp(name,digest);add(f,tags,700,1,packet.length,packet);
                align(f);long root=f.getFilePointer();
                if(root+6+12L*tags.size()>0xffffffffL) throw new IOException("DNG too large");
                f.write(M9DngProfile.le(2).putShort((short)tags.size()).array());
                for(Entry e:tags.values()) f.write(e.entry);f.write(new byte[4]);
                f.seek(4);f.write(M9DngProfile.le(4).putInt((int)root).array());f.getFD().sync();
                TreeMap<Integer,Entry> check=readRoot(f);
                if(check.size()!=tags.size()||!fingerprint(f,check,profile,name,.5).equals(digest))
                    throw new IOException("Written profile verification failed");
                result=new Result(name,digest,f.length()-originalLength);
            }
            // Never publish a partial profile. Unsupported atomic replacement leaves original intact.
            Files.move(temp,path,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
            temp=null;return result;
        } finally { if(temp!=null) Files.deleteIfExists(temp); }
    }
}
