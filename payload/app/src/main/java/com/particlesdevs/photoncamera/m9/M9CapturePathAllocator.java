package com.particlesdevs.photoncamera.m9;

import java.nio.file.Path;
import java.util.Locale;

/**
 * NAME1A capture-stem allocator.
 *
 * Photon ImagePath currently names stills at one-second resolution. M9 primary
 * rendering is asynchronous, so two accepted/rejected captures in the same second
 * can otherwise share the same DNG/JPEG/_M9/_M9_PRIMARY stem. NAME1A appends an
 * in-process monotonic millisecond token plus a same-millisecond sequence before
 * the extension. The returned DNG path is the single identity propagated to every
 * M9 output, so all derivative files remain paired without filesystem existence
 * probes or I/O on the capture path.
 */
public final class M9CapturePathAllocator {
    private static long lastTokenMs = Long.MIN_VALUE;
    private static int sameTokenSequence = 0;

    private M9CapturePathAllocator() {}

    public static synchronized Path allocate(Path basePath) {
        if (basePath == null) throw new IllegalArgumentException("basePath == null");

        long now = System.currentTimeMillis();
        long tokenMs = Math.max(now, lastTokenMs);
        if (tokenMs == lastTokenMs) {
            sameTokenSequence++;
        } else {
            lastTokenMs = tokenMs;
            sameTokenSequence = 0;
        }

        String name = basePath.getFileName().toString();
        int dot = name.lastIndexOf('.');
        String stem = dot > 0 ? name.substring(0, dot) : name;
        String ext = dot > 0 ? name.substring(dot) : "";
        String suffix = String.format(Locale.US, "_%013d_%02d", tokenMs, sameTokenSequence);
        return basePath.resolveSibling(stem + suffix + ext);
    }
}
