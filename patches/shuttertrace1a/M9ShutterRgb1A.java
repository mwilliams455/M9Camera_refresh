package com.particlesdevs.photoncamera.m9.preview;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.BitmapRegionDecoder;
import android.graphics.Rect;
import android.util.Base64;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.util.zip.Deflater;
import java.util.zip.DeflaterOutputStream;

/** Copies five small regions, never retains or mutates the source Bitmap. */
public final class M9ShutterRgb1A {
    public static final class Samples {
        public final int width,height;
        public final int[][] rects,pixels;
        public final String colorSpace,config;
        Samples(int w,int h,int[][] r,int[][] p,String cs,String cfg){width=w;height=h;rects=r;pixels=p;colorSpace=cs;config=cfg;}
    }
    public static Samples captureOne(Bitmap b) {
        int w=b.getWidth(),h=b.getHeight();int[] pixels=new int[w*h];b.getPixels(pixels,0,w,0,0,w,h);
        return new Samples(w,h,new int[][]{{0,0,w,h}},new int[][]{pixels},String.valueOf(b.getColorSpace()),String.valueOf(b.getConfig()));
    }
    public static Samples capture(Bitmap b) {
        int w=b.getWidth(),h=b.getHeight(),size=Math.min(96,Math.min(w,h));
        float[][] positions={{.5f,.5f},{.25f,.5f},{.75f,.5f},{.5f,.25f},{.5f,.75f}};
        int[][] r=new int[5][4],p=new int[5][];
        for(int i=0;i<5;i++) {
            int x=Math.max(0,Math.min(w-size,Math.round(w*positions[i][0]-size/2f)));
            int y=Math.max(0,Math.min(h-size,Math.round(h*positions[i][1]-size/2f)));
            r[i]=new int[]{x,y,size,size};p[i]=new int[size*size];
            b.getPixels(p[i],0,size,x,y,size,size);
        }
        return new Samples(w,h,r,p,String.valueOf(b.getColorSpace()),String.valueOf(b.getConfig()));
    }
    public static Samples decode(String path,Samples reference)throws Exception {
        BitmapRegionDecoder decoder=BitmapRegionDecoder.newInstance(path,false);
        try {
            if(decoder.getWidth()!=reference.width||decoder.getHeight()!=reference.height)throw new IllegalStateException("JPEG dimension mismatch");
            int[][] pixels=new int[reference.rects.length][];String cs="",cfg="";
            BitmapFactory.Options opts=new BitmapFactory.Options();opts.inPreferredConfig=Bitmap.Config.ARGB_8888;opts.inSampleSize=1;opts.inScaled=false;
            for(int i=0;i<pixels.length;i++) {
                int[] r=reference.rects[i];Bitmap b=decoder.decodeRegion(new Rect(r[0],r[1],r[0]+r[2],r[1]+r[3]),opts);
                if(b==null)throw new IllegalStateException("JPEG region unavailable");
                try {pixels[i]=new int[r[2]*r[3]];b.getPixels(pixels[i],0,r[2],0,0,r[2],r[3]);cs=String.valueOf(b.getColorSpace());cfg=String.valueOf(b.getConfig());}
                finally {b.recycle();}
            }
            return new Samples(reference.width,reference.height,reference.rects,pixels,cs,cfg);
        } finally {decoder.recycle();}
    }
    static String encode(byte[] bytes)throws Exception {
        ByteArrayOutputStream out=new ByteArrayOutputStream();Deflater d=new Deflater(1);
        try(DeflaterOutputStream z=new DeflaterOutputStream(out,d)){z.write(bytes);}finally{d.end();}
        return Base64.encodeToString(out.toByteArray(),Base64.NO_WRAP);
    }
    public static JSONObject json(Samples s)throws Exception {
        JSONArray regions=new JSONArray();
        for(int i=0;i<s.pixels.length;i++) {
            int[] px=s.pixels[i];byte[] rgb=new byte[px.length*3];double[] mean=new double[3];int offset=0;
            for(int p:px)for(int c=0;c<3;c++){int value=(p>>(16-8*c))&255;rgb[offset++]=(byte)value;mean[c]+=value;}
            for(int c=0;c<3;c++)mean[c]/=px.length;
            regions.put(new JSONObject().put("rectXYWH",new JSONArray(s.rects[i])).put("rgbZlibBase64",encode(rgb)).put("meanRgb",new JSONArray(mean)));
        }
        return new JSONObject().put("width",s.width).put("height",s.height).put("regions",regions)
            .put("bitmapColorSpace",s.colorSpace).put("bitmapConfig",s.config)
            .put("encoding","base64_zlib_RGB8_top_to_bottom").put("pixelDomain","Bitmap.getPixels_nonpremultiplied_sRGB")
            .put("orientation","stored_oriented_bitmap_coordinates_no_additional_EXIF_rotation");
    }
    public static JSONArray compare(Samples a,Samples b)throws Exception {
        if(a.width!=b.width||a.height!=b.height||a.pixels.length!=b.pixels.length)throw new IllegalArgumentException("incompatible regions");
        JSONArray result=new JSONArray();
        for(int i=0;i<a.pixels.length;i++) {
            if(!java.util.Arrays.equals(a.rects[i],b.rects[i])||a.pixels[i].length!=b.pixels[i].length)throw new IllegalArgumentException("unregistered regions");
            double[] mean=new double[3];double squared=0;int maximum=0,changed=0;
            for(int j=0;j<a.pixels[i].length;j++) {
                boolean differs=false;
                for(int c=0;c<3;c++) {
                    int shift=16-8*c,d=((b.pixels[i][j]>>shift)&255)-((a.pixels[i][j]>>shift)&255);
                    mean[c]+=d;squared+=d*d;maximum=Math.max(maximum,Math.abs(d));differs|=d!=0;
                }
                if(differs)changed++;
            }
            int n=a.pixels[i].length;for(int c=0;c<3;c++)mean[c]/=n;
            result.put(new JSONObject().put("rectXYWH",new JSONArray(a.rects[i])).put("meanRgbDelta",new JSONArray(mean))
                .put("rmsChannelCodes",Math.sqrt(squared/(3*n))).put("maxChannelCodes",maximum).put("changedPixels",changed)
                .put("interpretation","encoding_decode_difference_not_ground_truth_colour_error"));
        }
        return result;
    }
}
