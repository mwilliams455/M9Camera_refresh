package com.particlesdevs.photoncamera.processing;

import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;

/** Same-exposure diagnostic export. Never filters, scales or owns the source RAW. */
public final class M9DngRawPair {
    public static final String ID = "M9DNGRAWPAIR1A";
    private M9DngRawPair() {}

    public interface Writer {
        void write(OutputStream output, ByteBuffer source) throws Exception;
    }

    public static final class Result {
        public Path path;
        public boolean saved;
        public String status = "not_started";
        public String error;
        public String sourceBeforeSha256;
        public String sourceAfterSha256;
        public long fileBytes;
        public long elapsedMs;
    }

    public static Path pathFor(Path normalDng) {
        String name = normalDng.getFileName().toString();
        if (!name.toLowerCase(java.util.Locale.ROOT).endsWith(".dng"))
            throw new IllegalArgumentException("Expected DNG filename");
        return normalDng.resolveSibling(name.substring(0, name.length()-4) + "_RAW_UNFILTERED.dng");
    }

    private static ByteBuffer window(ByteBuffer source, int bytes) {
        if (source == null || !source.isDirect() || bytes <= 0 || bytes > source.capacity())
            throw new IllegalArgumentException("Invalid direct RAW16 window");
        ByteBuffer view = source.asReadOnlyBuffer();
        view.clear();
        view.limit(bytes);
        return view;
    }

    private static String hash(ByteBuffer source, int bytes) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        ByteBuffer view = window(source, bytes);
        byte[] block = new byte[Math.min(65536, bytes)];
        while (view.hasRemaining()) {
            int count = Math.min(view.remaining(), block.length);
            view.get(block, 0, count);
            digest.update(block, 0, count);
        }
        StringBuilder hex = new StringBuilder(64);
        for (byte b : digest.digest()) hex.append(String.format(java.util.Locale.ROOT, "%02x", b & 255));
        return hex.toString();
    }

    /** Normal capture has already been saved; a diagnostic failure cannot undo it. */
    public static Result save(Path normalDng, boolean normalSaved, ByteBuffer source,
                              int width, int height, Writer writer) {
        Result result = new Result();
        long started = System.nanoTime();
        Path staging = null;
        int bytes = 0;
        try {
            result.path = pathFor(normalDng);
            if (!normalSaved) {
                result.status = "skipped_normal_dng_failed";
                return result;
            }
            if (width <= 0 || height <= 0) throw new IllegalArgumentException("Invalid RAW dimensions");
            bytes = Math.multiplyExact(Math.multiplyExact(width, height), 2);
            result.sourceBeforeSha256 = hash(source, bytes);
            if (Files.exists(result.path)) throw new java.io.IOException("Control DNG already exists");
            // Android shared media accepts owned .dng staging; .tmp staging failed in 2.17.
            staging = Files.createTempFile(result.path.getParent(), "M9_PAIR_PENDING_", ".dng");
            try (OutputStream output = new java.io.BufferedOutputStream(Files.newOutputStream(staging), 65536)) {
                writer.write(output, window(source, bytes));
            }
            result.sourceAfterSha256 = hash(source, bytes);
            if (!result.sourceBeforeSha256.equals(result.sourceAfterSha256))
                throw new java.io.IOException("Source RAW changed during diagnostic write");
            result.fileBytes = Files.size(staging);
            if (result.fileBytes <= bytes) throw new java.io.IOException("Incomplete diagnostic DNG");
            // No REPLACE_EXISTING: an existing control is never overwritten.
            Files.move(staging, result.path);
            staging = null;
            result.saved = true;
            result.status = "saved_original_sensor_buffer";
        } catch (Exception | LinkageError | OutOfMemoryError failure) {
            result.status = "failed_normal_capture_preserved";
            result.error = failure.getClass().getSimpleName() + ": " + failure.getMessage();
        } finally {
            if (result.sourceBeforeSha256 != null && result.sourceAfterSha256 == null) {
                try { result.sourceAfterSha256 = hash(source, bytes); }
                catch (Exception | OutOfMemoryError ignored) { /* Report absent evidence. */ }
            }
            if (staging != null) {
                try { Files.deleteIfExists(staging); }
                catch (Exception cleanup) { result.error = String.valueOf(result.error) + "; staging cleanup: " + cleanup; }
            }
            result.elapsedMs = (System.nanoTime()-started)/1000000L;
        }
        return result;
    }
}
