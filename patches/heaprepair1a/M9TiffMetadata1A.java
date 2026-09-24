package com.particlesdevs.photoncamera.gallery.viewmodel;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Gallery-only TIFF/DNG labels. Never reads image strips, thumbnails or unknown tag payloads. */
public final class M9TiffMetadata1A {
    private final FileChannel file;
    private final long size;
    private ByteOrder order;
    private int bytesRead;
    private final Map<Integer,String> tags=new HashMap<>();
    private final Set<Long> seen=new HashSet<>();
    private final ArrayDeque<Long> pending=new ArrayDeque<>();
    private long largestArea;
    private M9TiffMetadata1A(FileChannel f)throws IOException{file=f;size=f.size();}
    public static Map<Integer,String> read(FileChannel file)throws IOException {
        return new M9TiffMetadata1A(file).parse();
    }
    private ByteBuffer at(long offset,int count)throws IOException {
        if(count<0 || count>8192 || offset<0 || offset>size-count || bytesRead>262144-count)
            throw new IOException("M9HEAPREPAIR1A TIFF metadata bounds");
        bytesRead+=count;
        ByteBuffer b=ByteBuffer.allocate(count).order(order==null?ByteOrder.BIG_ENDIAN:order);
        while(b.hasRemaining()) {
            int n=file.read(b,offset+b.position());
            if(n<=0)throw new IOException("truncated TIFF metadata");
        }
        b.flip();return b;
    }
    private Map<Integer,String> parse()throws IOException {
        ByteBuffer head=at(0,8);
        if(head.get(0)=='I'&&head.get(1)=='I')order=ByteOrder.LITTLE_ENDIAN;
        else if(head.get(0)=='M'&&head.get(1)=='M')order=ByteOrder.BIG_ENDIAN;
        else return null; // Let the normal JPEG/PNG metadata reader handle other formats.
        head.order(order);
        if((head.getShort(2)&65535)!=42)throw new IOException("unsupported TIFF header");
        enqueue(Integer.toUnsignedLong(head.getInt(4)));
        while(!pending.isEmpty()) {
            long offset=pending.removeFirst();
            if(!seen.add(offset))continue;
            if(seen.size()>32)throw new IOException("too many TIFF directories");
            int count=at(offset,2).getShort()&65535;
            if(count>512)throw new IOException("too many TIFF fields");
            long width=0,height=0;
            for(int i=0;i<count;i++) {
                long entry=offset+2L+12L*i;
                ByteBuffer field=at(entry,12);
                int tag=field.getShort()&65535,type=field.getShort()&65535;
                long n=Integer.toUnsignedLong(field.getInt());
                boolean pointer=tag==0x8769||tag==0x014a;
                if(!pointer&&!wanted(tag))continue;
                int unit=type==1||type==2?1:type==3?2:type==4||type==9?4:type==5||type==10?8:0;
                if(unit==0||n<1||n>8192/unit || (pointer&&n>32))continue;
                int length=(int)n*unit;
                long pos=length<=4?entry+8:Integer.toUnsignedLong(field.getInt(8));
                ByteBuffer data=at(pos,length);
                if(pointer) {
                    if(type==4)for(int j=0;j<n;j++)enqueue(Integer.toUnsignedLong(data.getInt()));
                    continue;
                }
                String value=value(data,type);
                if(value==null)continue;
                if(tag==0x0100)width=positive(value);
                else if(tag==0x0101)height=positive(value);
                else if((tag==0x829a||tag==0x829d) && (type==5||type==10)) {
                    data.rewind();double a=number(data,type),b=number(data,type);
                    if(b!=0)tags.put(tag,Double.toString(a/b));
                } else tags.putIfAbsent(tag,value);
            }
            if(width>0&&height>0&&width<=100000&&height<=100000&&width*height>largestArea) {
                largestArea=width*height;tags.put(0x0100,Long.toString(width));tags.put(0x0101,Long.toString(height));
            }
            enqueue(Integer.toUnsignedLong(at(offset+2L+12L*count,4).getInt()));
        }
        return tags;
    }
    private void enqueue(long offset)throws IOException {
        if(offset==0||seen.contains(offset)||pending.contains(offset))return;
        if(pending.size()+seen.size()>=32)throw new IOException("too many TIFF links");
        pending.add(offset);
    }
    private static long positive(String s){try{return Long.parseLong(s);}catch(NumberFormatException e){return 0;}}
    private static boolean wanted(int t) {
        return t==0x0100||t==0x0101||t==0x010f||t==0x0110||t==0x0132||t==0x9003
            ||t==0x829a||t==0x829d||t==0x8827||t==0x8833||t==0x920a;
    }
    private static long number(ByteBuffer b,int type){return type==9||type==10?b.getInt():Integer.toUnsignedLong(b.getInt());}
    private static String value(ByteBuffer b,int type) {
        if(type==2){byte[] a=b.array();int n=0;while(n<a.length&&a[n]!=0)n++;return new String(a,0,n,StandardCharsets.UTF_8);}
        if(type==1)return Integer.toString(b.get()&255);
        if(type==3)return Integer.toString(b.getShort()&65535);
        if(type==4||type==9)return Long.toString(number(b,type));
        if(type==5||type==10)return number(b,type)+"/"+number(b,type);
        return null;
    }
}
