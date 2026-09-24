package com.particlesdevs.photoncamera.gallery.viewmodel;

import android.content.ContentResolver;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import androidx.exifinterface.media.ExifInterface;
import java.io.*;
import java.util.*;

/** Bounded, read-only gallery metadata. DNG directory offsets are seeks, never buffered skips. */
final class M9GalleryMetadata1A {
    private static final String[] NAMES={ExifInterface.TAG_MAKE,ExifInterface.TAG_MODEL,
        ExifInterface.TAG_EXPOSURE_TIME,ExifInterface.TAG_IMAGE_WIDTH,ExifInterface.TAG_IMAGE_LENGTH,
        ExifInterface.TAG_PHOTOGRAPHIC_SENSITIVITY,ExifInterface.TAG_F_NUMBER,
        ExifInterface.TAG_FOCAL_LENGTH,ExifInterface.TAG_DATETIME};
    private static final int[] IDS={0x010f,0x0110,0x829a,0x0100,0x0101,0x8827,0x829d,0x920a,0x0132};
    static Map<String,String> read(ContentResolver resolver,Uri uri)throws IOException {
        Map<String,String> result=new HashMap<>();
        ParcelFileDescriptor descriptor=resolver.openFileDescriptor(uri,"r");
        if(descriptor==null)throw new IOException("metadata descriptor unavailable");
        try(ParcelFileDescriptor.AutoCloseInputStream in=new ParcelFileDescriptor.AutoCloseInputStream(descriptor)) {
            Map<Integer,String> tiff=M9TiffMetadata1A.read(in.getChannel());
            if(tiff!=null) {
                for(int i=0;i<IDS.length;i++)result.put(NAMES[i],tiff.get(IDS[i]));
                if(result.get(ExifInterface.TAG_DATETIME)==null)result.put(ExifInterface.TAG_DATETIME,tiff.get(0x9003));
                if(result.get(ExifInterface.TAG_PHOTOGRAPHIC_SENSITIVITY)==null)result.put(ExifInterface.TAG_PHOTOGRAPHIC_SENSITIVITY,tiff.get(0x8833));
                return result;
            }
            // Positional TIFF probing did not advance the descriptor. Bound other formats as well.
            ExifInterface exif=new ExifInterface(new LimitedInput(in));
            for(String name:NAMES)result.put(name,exif.getAttribute(name));
            return result;
        }
    }
    private static final class LimitedInput extends FilterInputStream {
        private int left=1024*1024;
        LimitedInput(InputStream in){super(in);}
        @Override public int read()throws IOException{if(left==0)return -1;int n=in.read();if(n>=0)left--;return n;}
        @Override public int read(byte[] b,int off,int len)throws IOException{if(len==0)return 0;if(left==0)return -1;int n=in.read(b,off,Math.min(len,left));if(n>0)left-=n;return n;}
        @Override public long skip(long n)throws IOException{long done=in.skip(Math.min(Math.max(n,0),left));left-=done;return done;}
    }
}
