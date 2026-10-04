package com.particlesdevs.photoncamera.processing;

import java.nio.ByteBuffer;
import java.nio.file.*;
import java.util.Arrays;
import java.util.concurrent.*;

public final class RawPairHostProbe {
    private static int cases;
    private static void require(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
    private static ByteBuffer source(int offset) {
        ByteBuffer b = ByteBuffer.allocateDirect(512);
        for (int i=0;i<512;i++) b.put(i,(byte)(i+offset));
        b.position(17); b.limit(300); b.mark();
        return b;
    }
    private static void write(java.io.OutputStream out, ByteBuffer input) throws Exception {
        require(input.isDirect() && input.isReadOnly(), "control needs protected direct view");
        require(input.position()==0 && input.remaining()==512, "JNI base-address window");
        out.write(new byte[16]);
        while(input.hasRemaining()) out.write(input.get() & 255);
    }
    private static Path normal(Path root, String name) throws Exception {
        Path p=root.resolve(name+".dng"); Files.write(p,new byte[]{1,2,3,4}); return p;
    }
    private static void normalPreserved(Path p) throws Exception {
        require(Arrays.equals(Files.readAllBytes(p),new byte[]{1,2,3,4}),"normal output changed");
        try(java.util.stream.Stream<Path> s=Files.list(p.getParent())) {
            require(s.noneMatch(x->x.getFileName().toString().startsWith("M9_PAIR_PENDING_")),"staging leaked");
        }
    }
    public static void main(String[] args) throws Exception {
        Path root=Paths.get(args[0]);Files.createDirectories(root);
        Path p=normal(root,"success");ByteBuffer b=source(0);
        M9DngRawPair.Result ok=M9DngRawPair.save(p,true,b,16,16,(out,in)->{
            try(java.util.stream.Stream<Path> files=Files.list(root)) {
                require(files.filter(x->x.getFileName().toString().startsWith("M9_PAIR_PENDING_"))
                        .allMatch(x->x.toString().endsWith(".dng")),"Android-compatible staging suffix");
            }
            write(out,in);
        });
        require(ok.saved && ok.sourceBeforeSha256.equals(ok.sourceAfterSha256),"success hashes");
        byte[] actual=Files.readAllBytes(ok.path);
        for(int i=0;i<512;i++) require(actual[16+i]==(byte)i,"RAW bytes changed");
        require(b.position()==17 && b.limit()==300,"caller buffer window changed");b.reset();
        normalPreserved(p); cases++;

        byte[] existing=Files.readAllBytes(ok.path);
        M9DngRawPair.Result collision=M9DngRawPair.save(p,true,b,16,16,(out,in)->{throw new AssertionError("writer called on collision");});
        require(!collision.saved && Arrays.equals(existing,Files.readAllBytes(ok.path)),"collision clobbered");
        normalPreserved(p);cases++;

        for(String name:new String[]{"io_failure","runtime_failure","oom_failure","native_failure","short_file","mutation"}) {
            Path q=normal(root,name); ByteBuffer src=source(0);
            M9DngRawPair.Result bad=M9DngRawPair.save(q,true,src,16,16,(out,in)->{
                out.write(new byte[16]);
                if(name.equals("io_failure")) throw new java.io.IOException("injected write failure");
                if(name.equals("runtime_failure")) throw new IllegalStateException("injected runtime failure");
                if(name.equals("oom_failure")) throw new OutOfMemoryError("injected allocation failure");
                if(name.equals("native_failure")) throw new UnsatisfiedLinkError("injected native failure");
                if(name.equals("short_file")) return;
                write(out,in);src.put(0,(byte)99);
            });
            require(!bad.saved && !Files.exists(M9DngRawPair.pathFor(q)),name);
            if(name.equals("mutation")) require(!bad.sourceBeforeSha256.equals(bad.sourceAfterSha256),"mutation not detected");
            normalPreserved(q);cases++;
        }
        Path skipped=normal(root,"skipped");
        require(!M9DngRawPair.save(skipped,false,b,16,16,(out,in)->{throw new AssertionError("writer on failed normal");}).saved,"failed normal");
        normalPreserved(skipped);cases++;
        for(int mode=0;mode<3;mode++) {
            Path q=normal(root,"invalid"+mode);
            ByteBuffer src=mode==0?ByteBuffer.allocate(512):b;
            int w=mode==1?Integer.MAX_VALUE:mode==2?0:16;
            require(!M9DngRawPair.save(q,true,src,w,16,(out,in)->{throw new AssertionError("invalid input writer");}).saved,"invalid input accepted");
            normalPreserved(q);cases++;
        }
        ExecutorService executor=Executors.newFixedThreadPool(2);
        try {
            Path one=normal(root,"parallel1"),two=normal(root,"parallel2");
            Future<M9DngRawPair.Result> f1=executor.submit(()->M9DngRawPair.save(one,true,source(1),16,16,RawPairHostProbe::write));
            Future<M9DngRawPair.Result> f2=executor.submit(()->M9DngRawPair.save(two,true,source(2),16,16,RawPairHostProbe::write));
            M9DngRawPair.Result r1=f1.get(),r2=f2.get();
            require(r1.saved && r2.saved && !r1.sourceBeforeSha256.equals(r2.sourceBeforeSha256),"parallel capture crossing");
            normalPreserved(one);normalPreserved(two);cases++;
        } finally {executor.shutdownNow();}
        System.out.println("RAWPAIR_CASES="+cases);
    }
}
