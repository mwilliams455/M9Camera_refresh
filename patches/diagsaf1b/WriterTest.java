package com.particlesdevs.photoncamera.m9;

import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.atomic.*;

public class WriterTest {
    static int checks;
    static void check(boolean ok, String why) { checks++; if (!ok) throw new AssertionError(why); }
    static OutputStream failAfter(OutputStream output, boolean atClose) {
        return new FilterOutputStream(output) {
            public void write(byte[] bytes, int start, int count) throws IOException {
                out.write(bytes, start, atClose ? count : Math.min(17, count));
                if (!atClose) throw new IOException("injected partial write");
            }
            public void close() throws IOException { out.close(); if (atClose) throw new IOException("injected close failure"); }
        };
    }
    public static void main(String[] args) throws Exception {
        Path root = Files.createTempDirectory("m9-public-writer-");
        try {
            Path source = root.resolve("source"), target = root.resolve("target");
            byte[] payload = new byte[12_013_236]; new Random(42).nextBytes(payload); Files.write(source, payload);
            AtomicInteger providerCalls = new AtomicInteger();
            M9DiagnosticPublicWriter1A writer = new M9DiagnosticPublicWriter1A(Files::newOutputStream, p -> {
                providerCalls.incrementAndGet(); throw new IOException("provider unavailable");
            });
            check(writer.stream(target, source, () -> true), "direct success");
            check(Arrays.equals(payload, Files.readAllBytes(target)), "12 MB byte-exact direct stream");
            check(providerCalls.get() == 0, "successful direct write never contacts provider");
            check(writer.directWrites.get() == 1 && writer.fallbackWrites.get() == 0, "direct metrics");
            AtomicInteger maxChunk = new AtomicInteger();
            M9DiagnosticPublicWriter1A.Opener saf = p -> new FilterOutputStream(Files.newOutputStream(p)) {
                public void write(byte[] b, int off, int len) throws IOException { maxChunk.accumulateAndGet(len, Math::max); out.write(b, off, len); }
            };
            for (int mode = 0; mode < 4; mode++) {
                final int failure = mode;
                writer = new M9DiagnosticPublicWriter1A(p -> {
                    if (failure == 0) throw new AccessDeniedException(p.toString());
                    if (failure == 1) throw new SecurityException("scoped storage");
                    return failAfter(Files.newOutputStream(p), failure == 3);
                }, saf);
                check(writer.stream(target, source, () -> true), "fallback succeeds after failure " + mode);
                check(Arrays.equals(payload, Files.readAllBytes(target)), "fallback restarts source at zero " + mode);
                check(writer.directFailures.get() == 1 && writer.fallbackWrites.get() == 1, "route accounting " + mode);
                check(Arrays.equals(payload, Files.readAllBytes(source)), "source retained " + mode);
            }
            check(maxChunk.get() <= 65536, "bounded 64 KiB fallback stream");
            writer = new M9DiagnosticPublicWriter1A(p -> { throw new IOException("denied"); }, p -> null);
            try { writer.stream(target, source, () -> true); throw new AssertionError("expected failure"); }
            catch (IOException expected) { check(expected.getSuppressed().length == 1, "both route errors retained"); }
            check(writer.fallbackFailures.get() == 1 && Files.exists(source), "both failures preserve source");
            AtomicBoolean enabled = new AtomicBoolean(true);
            writer = new M9DiagnosticPublicWriter1A(p -> { enabled.set(false); throw new IOException("pause during direct open"); }, p -> {
                throw new AssertionError("fallback must not start while disabled");
            });
            check(!writer.stream(target, source, enabled::get), "pause prevents fallback");
            writer = new M9DiagnosticPublicWriter1A(p -> { throw new AssertionError("disabled direct open"); }, saf);
            check(!writer.stream(target, source, () -> false), "disabled work opens neither route");
            byte[] manifest = "manifest payload".getBytes(java.nio.charset.StandardCharsets.UTF_8);
            writer = new M9DiagnosticPublicWriter1A(Files::newOutputStream, saf);
            check(writer.write(target, manifest, () -> true), "manifest uses direct path");
            check(Arrays.equals(manifest, Files.readAllBytes(target)), "manifest replacement truncates old content");
            check(writer.directOpenNs.get() > 0 && writer.transferNs.get() > 0 && writer.lastTotalNs.get() > 0, "timing components recorded");
            System.out.println("{\"scenario\":\"writer_failures_and_exact_bytes\",\"status\":\"PASS\",\"assertions\":" + checks + "}");
        } finally { try (var paths = Files.walk(root)) { for (Path p : paths.sorted(Comparator.reverseOrder()).toList()) Files.deleteIfExists(p); } }
    }
}
