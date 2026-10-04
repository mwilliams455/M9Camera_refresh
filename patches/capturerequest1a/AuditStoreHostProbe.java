package com.particlesdevs.photoncamera.m9.capture;

import java.util.concurrent.*;
import java.util.*;

public class AuditStoreHostProbe {
    static void check(boolean condition) { if (!condition) throw new AssertionError(); }
    public static void main(String[] args) throws Exception {
        M9CaptureAuditStore s = new M9CaptureAuditStore(3, 256);
        s.put(100, "A"); s.put(101, "B");
        check(s.take(100, 101) == null); // Mismatch must not consume or attach another frame.
        check("B".equals(s.take(101,101)));
        check("A".equals(s.take(100,100)));
        check(s.take(100,100) == null);
        s.put(102,"A");s.put(102,"B");
        check(s.take(102,102).contains("ambiguous_duplicate_timestamp"));
        s.put(103,"A");s.put(103,null);
        check(s.take(103,103).contains("ambiguous_duplicate_timestamp"));
        s.put(-1,"negative");s.put(0,"zero");s.put(104,null);s.put(105,"X".repeat(257));
        check(s.size()==0);
        for (int i=200;i<205;i++) s.put(i,"frame"+i);
        check(s.size()==3 && s.take(200,200)==null && s.take(201,201)==null);
        check("frame202".equals(s.take(202,202)));
        check("frame204".equals(s.take(204,204)));
        check("frame203".equals(s.take(203,203)));
        ExecutorService pool = Executors.newFixedThreadPool(4);
        M9CaptureAuditStore concurrent = new M9CaptureAuditStore(128,256);
        List<Future<?>> writes = new ArrayList<>();
        for(int i=1;i<=100;i++) { final int id=i; writes.add(pool.submit(() -> concurrent.put(id,"policy"+id))); }
        for(Future<?> f:writes) f.get();
        List<Future<?>> reads = new ArrayList<>();
        for(int i=100;i>=1;i--) { final int id=i; reads.add(pool.submit(() -> check(("policy"+id).equals(concurrent.take(id,id))))); }
        for(Future<?> f:reads) f.get();
        pool.shutdown();check(concurrent.size()==0);
        System.out.println("AUDIT_STORE_CASES=10 CONCURRENT_FRAMES=100");
    }
}
