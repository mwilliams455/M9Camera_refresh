package com.particlesdevs.photoncamera.ui.camera;

import android.content.Context;
import android.graphics.Bitmap;
import com.google.ai.edge.litert.Accelerator;
import com.google.ai.edge.litert.CompiledModel;
import com.google.ai.edge.litert.LiteRtException;
import com.google.ai.edge.litert.TensorBuffer;
import com.particlesdevs.photoncamera.control.subject.AnimalEyeTargetPolicy;
import com.particlesdevs.photoncamera.control.subject.PetTargetPolicy;
import java.util.List;

/**
 * Offline RTMPose Animal AP-10K (17 pose keypoints) using LiteRT CompiledModel.
 * Model and tensors are owned by PetFocusController's existing SERIAL worker.
 *
 * The reported eye/nose scores are a softmax of their two SimCC peaks.
 * These are *localization evidence*, not independently calibrated probabilities
 * that an animal's eyes are in focus.
 *
 * Eye indices 0/1, nose index 2. 256x256 NCHW RGB, MMPose mean/std, SimCC
 * outputs [1,17,512] for X and Y (model card pinned by SHA-256).
 */
final class AnimalEyePoseEstimator implements AutoCloseable {
    static final String MODEL="rtm_animal_fp16.tflite";
    private static final int N=256, COORD_BINS=512, KEYPOINTS=17;
    private static final int INPUT_COUNT=3*N*N;
    private static final float[] MEAN={123.675f,116.28f,103.53f};
    private static final float[] STD={58.395f,57.12f,57.375f};

    private final CompiledModel model;
    private final List<TensorBuffer> inputs, outputs;
    private final float[] chw=new float[INPUT_COUNT];
    private int[] previewPixels=new int[0];
    private boolean closed;
    private String backend="GPU";

    AnimalEyePoseEstimator(Context appContext) throws LiteRtException {
        CompiledModel created=null;
        List<TensorBuffer> in=null,out=null;
        Exception gpuError=null;
        try {
            try {
                created=CompiledModel.create(appContext.getAssets(),MODEL,
                        new CompiledModel.Options(Accelerator.GPU,Accelerator.CPU),null);
            }catch(RuntimeException | LiteRtException unavailable) {
                gpuError=unavailable;
                backend="CPU";
                // A GPU cannot always be used on each supported Android lens/device.
                // CPU fallback may be slow; controller still gates stale AF movement.
                created=CompiledModel.create(appContext.getAssets(),MODEL,
                        new CompiledModel.Options(Accelerator.CPU),null);
            }
            in=created.createInputBuffers();
            out=created.createOutputBuffers();
            if(in.size()!=1||out.size()!=2)
                throw new IllegalStateException("Unexpected AP-10K tensor count");
            this.model=created;
            this.inputs=in;
            this.outputs=out;
        }catch(RuntimeException|LiteRtException|LinkageError failure) {
            closeBuffers(in);
            closeBuffers(out);
            if(created!=null)created.close();
            throw failure;
        }
    }
    String backend(){return backend;}
    AnimalEyeTargetPolicy.Observation estimate(Bitmap preview,
            PetTargetPolicy.Candidate animal,long frameNs,long epoch) throws LiteRtException {
        if(closed||preview==null||preview.isRecycled()
                ||animal==null||!animal.valid()) return null;
        final int width=preview.getWidth(),height=preview.getHeight();
        if(width<=0||height<=0)return null;
        if(previewPixels.length<width*height)
            previewPixels=new int[width*height];
        preview.getPixels(previewPixels,0,width,0,0,width,height);
        // Square crop enclosing the confirmed animal; transparent padding is
        // represented by MMPose mean RGB so its normalized input becomes zero.
        final float cx=animal.cx()*width, cy=animal.cy()*height;
        final float side=Math.max(32f,Math.max(animal.width()*width,
                animal.height()*height)*1.13f);
        final float left=cx-side*.5f,top=cy-side*.5f;
        for(int y=0;y<N;y++) {
            int py=(int)Math.floor(top+(y+.5f)*side/N);
            for(int x=0;x<N;x++) {
                int px=(int)Math.floor(left+(x+.5f)*side/N);
                int idx=y*N+x;
                if(px>=0&&px<width&&py>=0&&py<height) {
                    int argb=previewPixels[py*width+px];
                    chw[idx]=(((argb>>>16)&255)-MEAN[0])/STD[0];
                    chw[N*N+idx]=(((argb>>>8)&255)-MEAN[1])/STD[1];
                    chw[2*N*N+idx]=((argb&255)-MEAN[2])/STD[2];
                } else {
                    chw[idx]=chw[N*N+idx]=chw[2*N*N+idx]=0f;
                }
            }
        }
        inputs.get(0).writeFloat(chw);
        model.run(inputs,outputs);
        final float[] sx=outputs.get(0).readFloat();
        final float[] sy=outputs.get(1).readFloat();
        if(sx.length!=KEYPOINTS*COORD_BINS||sy.length!=KEYPOINTS*COORD_BINS)
            throw new IllegalStateException("Unexpected AP-10K SimCC shapes");
        AnimalEyeTargetPolicy.Point leftEye=decode(0,sx,sy,left,top,side,width,height);
        AnimalEyeTargetPolicy.Point rightEye=decode(1,sx,sy,left,top,side,width,height);
        AnimalEyeTargetPolicy.Point nose=decode(2,sx,sy,left,top,side,width,height);
        return new AnimalEyeTargetPolicy.Observation(animal.species,
                animal.left,animal.top,animal.right,animal.bottom,
                leftEye,rightEye,nose,frameNs,epoch);
    }
    private static AnimalEyeTargetPolicy.Point decode(int k,float[] sx,float[] sy,
            float cropLeft,float cropTop,float side,int w,int h) {
        int a=k*COORD_BINS;
        int bestX=argmax(sx,a),bestY=argmax(sy,a);
        float confX=peakProbability(sx,a,bestX),confY=peakProbability(sy,a,bestY);
        float confidence=(float)Math.sqrt(confX*confY);
        // AP-10K SimCC bin index = pixel * 2; two bins per pixel.
        float imageX=(cropLeft+((bestX+.5f)/2f)*side/N)/w;
        float imageY=(cropTop+((bestY+.5f)/2f)*side/N)/h;
        return new AnimalEyeTargetPolicy.Point(imageX,imageY,confidence);
    }
    private static int argmax(float[] data,int begin) {
        int best=0;float max=-Float.MAX_VALUE;
        for(int i=0;i<COORD_BINS;i++){
            float value=data[begin+i];
            if(Float.isFinite(value)&&value>max){best=i;max=value;}
        }
        return best;
    }
    private static float peakProbability(float[] data,int begin,int index){
        float max=-Float.MAX_VALUE;
        for(int i=0;i<COORD_BINS;i++)
            if(Float.isFinite(data[begin+i]))max=Math.max(max,data[begin+i]);
        if(max==-Float.MAX_VALUE)return 0f;
        double sum=0d;
        for(int i=0;i<COORD_BINS;i++)
            if(Float.isFinite(data[begin+i]))
                sum+=Math.exp(Math.max(-80, data[begin+i]-max));
        double best=Math.exp(Math.max(-80,data[begin+index]-max));
        return sum>0?(float)(best/sum):0f;
    }
    private static void closeBuffers(List<TensorBuffer> buffers){
        if(buffers!=null)for(TensorBuffer b:buffers)if(b!=null)b.close();
    }
    @Override public void close(){
        if(closed)return;
        closed=true;
        closeBuffers(inputs);
        closeBuffers(outputs);
        model.close();
    }
}
