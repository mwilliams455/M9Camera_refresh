package com.particlesdevs.photoncamera.m9;

import com.particlesdevs.photoncamera.app.PhotonCamera;
import com.particlesdevs.photoncamera.settings.SettingsManager;
import com.particlesdevs.photoncamera.processing.M9DngRawPair;
import java.nio.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicBoolean;

/** Production optional RAW writer, metadata ownership and both sidecar transports. */
public final class OutputHostProbe {
    private static void check(boolean v,String why){if(!v)throw new AssertionError(why);}
    private static void setting(String key,boolean on){PhotonCamera.settings.values.put(key,on?"1":"0");}
    public static void main(String[] args)throws Exception {
        Path root=Path.of(args[0]);Files.createDirectories(root);
        PhotonCamera.context=new android.content.Context(root.resolve("private").toFile());
        check(!M9OutputSettings.saveUnfilteredDng()&&!M9OutputSettings.diagnosticsEnabled(),"defaults");
        int cases=0;
        for(boolean raw:new boolean[]{false,true})for(boolean diag:new boolean[]{false,true}){
            setting(M9OutputSettings.UNFILTERED_DNG_KEY,raw);setting(M9OutputSettings.DIAGNOSTICS_KEY,diag);
            Path dir=root.resolve("combination-"+raw+"-"+diag);Files.createDirectories(dir);
            Path normal=dir.resolve("shot.dng"),jpeg=dir.resolve("shot.jpg");
            byte[] primary={9,8,7,6};Files.write(normal,primary);Files.write(jpeg,primary);
            ByteBuffer buffer=ByteBuffer.allocateDirect(32);for(int i=0;i<32;i++)buffer.put(i,(byte)i);
            AtomicBoolean called=new AtomicBoolean();
            M9DngRawPair.Result result=M9DngRawPair.saveIfEnabled(M9OutputSettings.saveUnfilteredDng(),normal,true,buffer,4,4,(output,source)->{
                called.set(true);output.write(new byte[16]);while(source.hasRemaining())output.write(source.get());
            });
            check(called.get()==raw&&result.saved==raw,"RAW toggle independent");
            check(Files.exists(M9DngRawPair.pathFor(normal))==raw,"RAW file presence");
            if(!raw)check(result.path==null&&result.sourceBeforeSha256==null&&result.sourceAfterSha256==null,"disabled avoids buffer work");
            Path json=dir.resolve("shot_M9_PRIMARY.json");
            check(M9DiagnosticSidecarIO.persist(json,new byte[]{1,2,3},"test"),"handled sidecar");
            check(Files.exists(json)==diag,"JSON toggle independent");
            check(Arrays.equals(Files.readAllBytes(normal),primary)&&Arrays.equals(Files.readAllBytes(jpeg),primary),"primary files changed");
            for(int i=0;i<32;i++)check(buffer.get(i)==(byte)i,"source RAW changed");
            cases++;
        }
        setting(M9OutputSettings.DIAGNOSTICS_KEY,false);
        // Disabling must return before inspecting even invalid paths/buffers or invoking a writer.
        M9DngRawPair.Result disabled=M9DngRawPair.saveIfEnabled(false,null,true,null,-1,-1,(o,s)->{throw new AssertionError("writer called");});
        check("disabled_by_setting".equals(disabled.status),"disabled result");cases++;
        Path off=root.resolve("never-create/sub/sidecar.json");
        check(M9DiagnosticBurstSpool.stage(off,new byte[]{4},"primary_timing"),"spool suppression handled");
        check(!Files.exists(root.resolve("private"))&&!Files.exists(off),"disabled spool touched filesystem");cases++;
        // Metadata needed by the colour pipeline survives even with every extra file disabled.
        Path dng=root.resolve("capture.dng");byte[] bytes={5,4,3,2};
        check(M9DeferredMetadataStore.stage(M9DeferredMetadataStore.sidecarPath(dng),bytes),"metadata stage");
        bytes[0]=0;
        check(Arrays.equals(M9DeferredMetadataStore.consumeRenderSnapshotForDng(dng),new byte[]{5,4,3,2}),"immutable render metadata lost");
        check(!M9DeferredMetadataStore.persistAsyncForDng(dng),"disabled metadata scheduled");
        check(!Files.exists(M9DeferredMetadataStore.sidecarPath(dng)),"metadata file leaked");cases++;
        // Recovery and delayed priority exports re-read the setting instead of leaking old queued files.
        setting(M9OutputSettings.DIAGNOSTICS_KEY,true);Files.createDirectories(root.resolve("private"));
        Files.write(root.resolve("private/m9diag_spool_reset1a.done"),new byte[]{1});
        M9DiagnosticBurstSpool.setAppVisible(true);
        java.lang.reflect.Field executor=M9DiagnosticBurstSpool.class.getDeclaredField("BUNDLE_EXECUTOR");
        executor.setAccessible(true);
        ((java.util.concurrent.ScheduledThreadPoolExecutor)executor.get(null)).submit(()->{}).get(2,java.util.concurrent.TimeUnit.SECONDS);
        Path delayed=root.resolve("delayed.json");
        check(M9DiagnosticBurstSpool.stage(delayed,new byte[]{9,9},"primary_timing"),"enabled spool stage");
        check(Files.isDirectory(root.resolve("private/m9diag_spool")),"enabled stage not persisted");
        setting(M9OutputSettings.DIAGNOSTICS_KEY,false);
        Thread.sleep(350);check(!Files.exists(delayed),"delayed export ignored disable");
        check(M9DiagnosticSidecarIO.persist(delayed,new byte[]{9},"legacy_fallback"),"legacy suppression");
        check(!Files.exists(delayed),"legacy fallback escaped toggle");cases++;
        M9DiagnosticBurstSpool.setAppVisible(false);
        System.out.println("OUTPUT_CASES="+cases+" FOUR_COMBINATIONS=4 CAPTURE_METADATA_PRESERVED=true DELAYED_EXPORT_BLOCKED=true");
    }
}
