package com.particlesdevs.photoncamera.control.subject;

/**
 * FOCUSANIMAL1C: recoverable preview sampling errors must not permanently
 * disable on-device pet AF. Backoff is bounded and uses elapsed realtime.
 *
 * OOM is handled separately by the owning Android controller: memory
 * exhaustion disables optional preview inference for the current session.
 */
public final class PetPreviewRetryPolicy {
    public static final long INITIAL_BACKOFF_MS = 250L;
    public static final long MAX_BACKOFF_MS = 2000L;
    private int consecutiveFailures;
    private long nextAttemptMs;
    private String lastStage="ready", lastCause="none";

    public synchronized void reset() {
        consecutiveFailures=0;
        nextAttemptMs=0;
        lastStage="ready";
        lastCause="none";
    }
    public synchronized boolean mayAttempt(long nowMs) {
        return nowMs>=nextAttemptMs;
    }
    public synchronized void success() {
        consecutiveFailures=0;
        nextAttemptMs=0;
        lastStage="ready";
        lastCause="none";
    }
    public synchronized long failure(long nowMs,String stage,String cause) {
        if(nowMs<0)throw new IllegalArgumentException("Invalid monotonic clock");
        consecutiveFailures=Math.min(consecutiveFailures+1,32);
        // 250,500,1000,2000... No per-frame error storm.
        long retry=INITIAL_BACKOFF_MS << Math.min(3,consecutiveFailures-1);
        retry=Math.min(retry,MAX_BACKOFF_MS);
        nextAttemptMs=nowMs>Long.MAX_VALUE-retry?Long.MAX_VALUE:nowMs+retry;
        lastStage=safe(stage);
        lastCause=safe(cause);
        return retry;
    }
    private static String safe(String s) {
        if(s==null||s.isEmpty())return "unknown";
        return s.length()>36?s.substring(0,36):s;
    }
    public synchronized long remainingMs(long nowMs) {
        return Math.max(0L,nextAttemptMs-nowMs);
    }
    public synchronized int failures() {return consecutiveFailures;}
    public synchronized String lastStage() {return lastStage;}
    public synchronized String lastCause() {return lastCause;}
}
