package com.particlesdevs.photoncamera.m9.preview;

/** Pure decisions shared with bounded lifecycle and visibility regression tests. */
public final class M9TracePolicy1B {
    public static final long TIMEOUT_NS=60000000000L, POST_JPEG_NS=8000000000L;
    private M9TracePolicy1B(){}
    public static boolean sampling(long shutter,long jpeg,long now){return now>=shutter&&now-shutter<TIMEOUT_NS&&(jpeg<0||now-jpeg<POST_JPEG_NS);}
    public static boolean unitTransform(float alpha,float sx,float sy,float rotation,float rx,float ry,float tx,float ty){
        return alpha>=.999f&&Math.abs(sx-1)<.0001f&&Math.abs(sy-1)<.0001f&&Math.abs(rotation)<.0001f&&Math.abs(rx)<.0001f&&Math.abs(ry)<.0001f&&Math.abs(tx)<.0001f&&Math.abs(ty)<.0001f;
    }
    public static String localFilename(String scheme,String path){return "file".equals(scheme)&&path!=null?new java.io.File(path).getName():null;}
    public static String role(String name){if(name==null)return "unknown";String n=name.toLowerCase(java.util.Locale.ROOT);return n.endsWith(".jpg")||n.endsWith(".jpeg")?"jpeg":n.endsWith(".dng")?"raw_dng":"unknown";}
}
