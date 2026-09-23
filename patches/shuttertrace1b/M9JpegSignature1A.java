package com.particlesdevs.photoncamera.m9.preview;

import java.io.*;
import java.security.MessageDigest;
import java.util.*;

/** Streaming JPEG coding digest excluding APP/COM metadata; includes all scans and restart bytes. */
public final class M9JpegSignature1A {
    public static final class Result {
        public String codingSha256, iccSha256, sampling;
        public int width,height,iccSegments;
        public long codingBytes, digestUpdates;
    }
    // Batch provider calls: Android's SHA provider must not receive one JNI call per byte.
    private static final class CodingDigest {
        final MessageDigest digest=MessageDigest.getInstance("SHA-256");
        final byte[] buffer=new byte[65536];int used;long updates;
        CodingDigest() throws java.security.NoSuchAlgorithmException {}
        void flush(){if(used>0){digest.update(buffer,0,used);updates++;used=0;}}
        void update(byte b){buffer[used++]=b;if(used==buffer.length)flush();}
        void update(byte[] bytes){int offset=0;while(offset<bytes.length){int n=Math.min(buffer.length-used,bytes.length-offset);System.arraycopy(bytes,offset,buffer,used,n);used+=n;offset+=n;if(used==buffer.length)flush();}}
        byte[] digest(){flush();return digest.digest();}
    }
    private static String hex(byte[] b){StringBuilder s=new StringBuilder();for(byte v:b)s.append(String.format(Locale.ROOT,"%02x",v&255));return s.toString();}
    private static int read(InputStream in)throws IOException{int v=in.read();if(v<0)throw new EOFException("truncated JPEG");return v;}
    public static Result read(File file)throws Exception {
        CodingDigest digest=new CodingDigest();MessageDigest icc=MessageDigest.getInstance("SHA-256");
        Result out=new Result();boolean scan=false,done=false;int pending=-1;
        try(InputStream in=new BufferedInputStream(new FileInputStream(file),65536)) {
            if(read(in)!=255||read(in)!=216)throw new IOException("not JPEG");
            digest.update(new byte[]{(byte)255,(byte)216});out.codingBytes=2;
            while(!done) {
                int marker;
                if(scan) {
                    int v=read(in);
                    if(v!=255){digest.update((byte)v);out.codingBytes++;continue;}
                    int count=1;marker=read(in);
                    while(marker==255){count++;marker=read(in);}
                    if(marker==0||(marker>=208&&marker<=215)) {
                        for(int i=0;i<count;i++)digest.update((byte)255);
                        digest.update((byte)marker);out.codingBytes+=count+1;continue;
                    }
                    // Marker fill bytes do not affect decoded samples. Canonicalize the marker prefix.
                    scan=false;
                } else {
                    if(pending>=0){marker=pending;pending=-1;}
                    else {if(read(in)!=255)throw new IOException("invalid JPEG marker");do{marker=read(in);}while(marker==255);}
                }
                if(marker==217){digest.update(new byte[]{(byte)255,(byte)217});out.codingBytes+=2;done=true;continue;}
                if(marker==216||marker==0||marker==1||(marker>=208&&marker<=215))throw new IOException("unexpected standalone marker");
                int hi=read(in),lo=read(in),length=(hi<<8)|lo;
                if(length<2)throw new IOException("invalid JPEG segment length");
                byte[] data=new byte[length-2];int pos=0,n;
                while(pos<data.length&&(n=in.read(data,pos,data.length-pos))>0)pos+=n;
                if(pos!=data.length)throw new EOFException("truncated JPEG segment");
                boolean metadata=(marker>=224&&marker<=239)||marker==254;
                if(!metadata){digest.update(new byte[]{(byte)255,(byte)marker,(byte)hi,(byte)lo});digest.update(data);out.codingBytes+=length+2;}
                if(marker==226&&data.length>=14&&new String(data,0,12,"US-ASCII").equals("ICC_PROFILE\0")){
                    icc.update(data);out.iccSegments++;
                }
                if((marker>=192&&marker<=195)||(marker>=197&&marker<=199)||(marker>=201&&marker<=203)||(marker>=205&&marker<=207)) {
                    if(data.length<6)throw new IOException("short SOF");
                    out.height=((data[1]&255)<<8)|(data[2]&255);out.width=((data[3]&255)<<8)|(data[4]&255);
                    int channels=data[5]&255;if(data.length<6+3*channels)throw new IOException("short SOF components");
                    StringBuilder s=new StringBuilder();
                    for(int i=0;i<channels;i++){if(i>0)s.append(',');int v=data[7+i*3]&255;s.append(data[6+i*3]&255).append(':').append(v>>4).append('x').append(v&15);}
                    out.sampling=s.toString();
                }
                if(marker==218)scan=true;
            }
        }
        out.codingSha256=hex(digest.digest());out.digestUpdates=digest.updates;out.iccSha256=out.iccSegments==0?null:hex(icc.digest());return out;
    }
}
