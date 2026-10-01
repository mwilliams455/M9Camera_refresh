package com.particlesdevs.photoncamera.processing;
import java.nio.*;
import java.nio.file.*;
import java.util.Arrays;

/** Exercises the production Java/JNI/native path on host; synthetic inputs only. */
public class StageJniProbe {
    public static void main(String[] args) throws Exception {
        int w=66,h=138,n=w*h;
        double[] p={.0004,.000001,.00038,.0000008,.00039,.0000009,.00042,.0000011};
        float[] black={64,65,66,67},g=new float[4*3*2];
        for(int i=0;i<g.length;i++)g[i]=1+(i%7)*.125f;
        byte[] original=new byte[n*2];
        ByteBuffer generated=ByteBuffer.wrap(original).order(ByteOrder.LITTLE_ENDIAN);
        for(int i=0;i<n;i++)generated.putShort((short)(140+(i*73%31)));
        for(int cfa=0;cfa<4;cfa++) {
            M9DngNoiseStage.Calibration c=M9DngNoiseStage.prepare(w,h,cfa,1023,black,p,g,3,2,true,true);
            ByteBuffer src=ByteBuffer.allocateDirect(n*2).order(ByteOrder.LITTLE_ENDIAN());
            src.put(original);src.position(7);src.mark();src.limit(n*2-3);
            M9DngNoiseStage.Result result=M9DngNoiseStage.process(src,c);
            if(!result.applied || result.scale!=16 || result.buffer==src)throw new AssertionError(result.reason);
            if(src.position()!=7 || src.limit()!=n*2-3)throw new AssertionError("source state changed");
            src.reset();ByteBuffer check=src.duplicate();check.clear();byte[] bytes=new byte[n*2];check.get(bytes);
            if(!Arrays.equals(bytes,original))throw new AssertionError("source pixels changed");
            result.buffer.get(bytes);Files.write(Paths.get(args[0],"jni_cfa"+cfa+".bin"),bytes);
            src.clear();src.putShort(0,(short)1024);
            M9DngNoiseStage.Result bad=M9DngNoiseStage.process(src,c);
            if(bad.applied || bad.buffer!=src || bad.scale!=1 || !bad.reason.equals("native_status_-4"))
                throw new AssertionError("out-of-range fallback failed: "+bad.reason);
        }
        System.out.println("Production Java/JNI buffer ownership and range fallback passed for four CFAs");
    }
}
