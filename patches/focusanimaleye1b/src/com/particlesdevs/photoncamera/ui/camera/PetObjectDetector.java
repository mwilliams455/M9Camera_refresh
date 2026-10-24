package com.particlesdevs.photoncamera.ui.camera;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.RectF;
import com.google.mediapipe.framework.image.BitmapImageBuilder;
import com.google.mediapipe.framework.image.MPImage;
import com.google.mediapipe.tasks.core.BaseOptions;
import com.google.mediapipe.tasks.components.containers.Category;
import com.google.mediapipe.tasks.components.containers.Detection;
import com.google.mediapipe.tasks.vision.core.RunningMode;
import com.google.mediapipe.tasks.vision.objectdetector.ObjectDetector;
import com.google.mediapipe.tasks.vision.objectdetector.ObjectDetectorResult;
import com.particlesdevs.photoncamera.control.subject.PetTargetPolicy;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Model in app assets, no remote inference or Play Services dependency.
 * MediaPipe Tasks 0.10.35 is used for 16-KiB Android memory-page support.
 * This whole adapter is exclusively owned by the single inference worker.
 */
final class PetObjectDetector implements AutoCloseable {
    static final String MODEL="efficientdet-lite0.tflite";
    private final ObjectDetector detector;
    private boolean closed;
    private String lastSummary = "no_sample";
    String lastSummary() {return lastSummary;}

    PetObjectDetector(Context appContext) {
        ObjectDetector.ObjectDetectorOptions options =
            ObjectDetector.ObjectDetectorOptions.builder()
                .setBaseOptions(BaseOptions.builder().setModelAssetPath(MODEL).build())
                .setRunningMode(RunningMode.IMAGE)
                .setMaxResults(25)
                .setScoreThreshold(.15f)
                .build();
        detector=ObjectDetector.createFromOptions(appContext,options);
    }
    List<PetTargetPolicy.Candidate> detect(Bitmap image) {
        if(closed || image==null || image.isRecycled())return Collections.emptyList();
        // BitmapImageContainer.close() calls Bitmap.recycle(). This source
        // Bitmap is ALSO used by AnimalEyePoseEstimator, so never transfer
        // ownership of the shared PixelCopy preview into the MediaPipe wrapper.
        // Own an isolated, bounded detector-only copy instead.
        Bitmap detectorFrame=image.copy(Bitmap.Config.ARGB_8888,false);
        if(detectorFrame==null)throw new IllegalStateException("Detector frame copy failed");
        MPImage mpImage;
        try {
            mpImage=new BitmapImageBuilder(detectorFrame).build();
        }catch(RuntimeException creationError) {
            if(!detectorFrame.isRecycled())detectorFrame.recycle();
            throw creationError;
        }
        ArrayList<PetTargetPolicy.Candidate> animals=new ArrayList<>();
        int count=0, petCount=0;
        float bestCat=0, bestDog=0;
        String topLabel="none";
        float bestOverall=-1;
        try {
        ObjectDetectorResult result=detector.detect(mpImage);
        for(Detection detection:result.detections()) {
            count++;
            RectF box=detection.boundingBox();
            if(box==null)continue;
            for(Category cat:detection.categories()) {
                if(cat==null)continue;
                if(cat.score()>bestOverall){bestOverall=cat.score();topLabel=cat.categoryName();}
                PetTargetPolicy.Species species=PetTargetPolicy.speciesFor(cat.categoryName());
                if(species==null)continue;
                petCount++;
                if(species==PetTargetPolicy.Species.CAT)bestCat=Math.max(bestCat,cat.score());
                else bestDog=Math.max(bestDog,cat.score());
                animals.add(new PetTargetPolicy.Candidate(
                    cat.categoryName(),cat.score(),
                    clamp(box.left/image.getWidth()),
                    clamp(box.top/image.getHeight()),
                    clamp(box.right/image.getWidth()),
                    clamp(box.bottom/image.getHeight())));
            }
        }
        } finally {
            // Recycles detectorFrame ONLY; never recycles the shared preview.
            mpImage.close();
        }
        if(image.isRecycled())
            throw new IllegalStateException("Unexpected original preview recycling");
        lastSummary="boxes="+count+" pet="+petCount+" cat="+
                Math.round(bestCat*100)+" dog="+Math.round(bestDog*100)+
                " top="+topLabel;
        return animals;
    }
    private static float clamp(float x){return Math.max(0f,Math.min(1f,x));}
    @Override public void close() {
        if(!closed) {closed=true;detector.close();}
    }
}
