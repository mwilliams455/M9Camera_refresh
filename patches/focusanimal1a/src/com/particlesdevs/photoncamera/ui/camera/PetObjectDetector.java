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
import java.util.Arrays;
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

    PetObjectDetector(Context appContext) {
        ObjectDetector.ObjectDetectorOptions options =
            ObjectDetector.ObjectDetectorOptions.builder()
                .setBaseOptions(BaseOptions.builder().setModelAssetPath(MODEL).build())
                .setRunningMode(RunningMode.IMAGE)
                .setMaxResults(8)
                .setScoreThreshold(.60f)
                .setCategoryAllowlist(Arrays.asList("cat","dog"))
                .build();
        detector=ObjectDetector.createFromOptions(appContext,options);
    }
    List<PetTargetPolicy.Candidate> detect(Bitmap image) {
        if(closed || image==null || image.isRecycled())return Collections.emptyList();
        MPImage mpImage=new BitmapImageBuilder(image).build();
        ObjectDetectorResult result=detector.detect(mpImage);
        ArrayList<PetTargetPolicy.Candidate> animals=new ArrayList<>();
        for(Detection detection:result.detections()) {
            RectF box=detection.boundingBox();
            if(box==null)continue;
            for(Category cat:detection.categories()) {
                if(cat==null || PetTargetPolicy.speciesFor(cat.categoryName())==null)continue;
                animals.add(new PetTargetPolicy.Candidate(
                    cat.categoryName(),cat.score(),
                    clamp(box.left/image.getWidth()),
                    clamp(box.top/image.getHeight()),
                    clamp(box.right/image.getWidth()),
                    clamp(box.bottom/image.getHeight())));
            }
        }
        mpImage.close();
        return animals;
    }
    private static float clamp(float x){return Math.max(0f,Math.min(1f,x));}
    @Override public void close() {
        if(!closed) {closed=true;detector.close();}
    }
}
