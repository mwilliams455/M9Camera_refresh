package com.particlesdevs.photoncamera.util;

import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

/** Controllable stand-in for the Android storage provider; copies still hit real files. */
public class SimpleStorageHelper {
    public static volatile String blockedName;
    public static volatile String failingName;
    public static volatile boolean blockOnce;
    public static volatile CountDownLatch entered = new CountDownLatch(1);
    public static volatile CountDownLatch release = new CountDownLatch(1);
    public static final List<String> opened = Collections.synchronizedList(new ArrayList<>());
    public static final AtomicInteger largestWrite = new AtomicInteger();
    public static final AtomicInteger traceActive = new AtomicInteger();
    public static final AtomicInteger traceMaxActive = new AtomicInteger();

    public static OutputStream openOutputStreamByAbsPath(String path) throws Exception {
        String name=Path.of(path).getFileName().toString();
        opened.add(name);
        if (name.equals(failingName)) throw new IOException("injected provider failure");
        if (name.equals(blockedName)) {
            if (blockOnce) blockedName=null;
            entered.countDown();
            if (!release.await(20,TimeUnit.SECONDS)) throw new IOException("test latch timeout");
        }
        OutputStream delegate=Files.newOutputStream(Path.of(path));
        boolean trace=name.startsWith("trace");
        if(trace) traceMaxActive.accumulateAndGet(traceActive.incrementAndGet(),Math::max);
        return new FilterOutputStream(delegate) {
            boolean closed;
            @Override public void write(byte[] b,int off,int len)throws IOException {
                largestWrite.accumulateAndGet(len,Math::max);out.write(b,off,len);
            }
            @Override public void close()throws IOException {
                try {super.close();} finally {if(!closed && trace)traceActive.decrementAndGet();closed=true;}
            }
        };
    }
}
