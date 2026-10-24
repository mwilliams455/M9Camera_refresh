package com.particlesdevs.photoncamera.m9.provenance;

/** Pure-Java, sensor-agnostic evidence classifier. No colour correction. */
public final class PhysicalSourceEvidence1A {
    public enum Status {
        PHYSICAL_ID_MISMATCH,
        INCOMPLETE_SOURCE_EVIDENCE,
        CAPTURE_SOURCE_PRESENT
    }
    private PhysicalSourceEvidence1A(){}
    public static Status classify(boolean identitiesAgree,boolean hasPhysicalResult,
            boolean hasCharacteristics,boolean hasCalibration,boolean hasShading,
            boolean noAuditErrors,boolean saneBlackWhite,boolean activeArrayPresent) {
        if(!identitiesAgree)return Status.PHYSICAL_ID_MISMATCH;
        if(!hasPhysicalResult||!hasCharacteristics||!hasCalibration||!hasShading
                ||!noAuditErrors||!saneBlackWhite||!activeArrayPresent)
            return Status.INCOMPLETE_SOURCE_EVIDENCE;
        return Status.CAPTURE_SOURCE_PRESENT;
    }
}
