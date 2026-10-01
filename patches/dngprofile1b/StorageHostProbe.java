package com.particlesdevs.photoncamera.processing;

import java.nio.file.*;
import java.security.Permission;
import java.util.Arrays;

/** Java 17 host fault injection, not an Android/FUSE emulator. Never packaged in the APK. */
@SuppressWarnings("removal")
public final class StorageHostProbe {
    static final class MediaDirectoryPolicy extends SecurityManager {
        final Path original, directory;
        final boolean denyCommit;
        int stagingChecks;
        MediaDirectoryPolicy(Path original, boolean denyCommit) {
            this.original=original.toAbsolutePath(); directory=this.original.getParent();
            this.denyCommit=denyCommit;
        }
        @Override public void checkPermission(Permission permission) { }
        @Override public void checkWrite(String file) {
            Path path=Path.of(file).toAbsolutePath();
            if (!directory.equals(path.getParent())) return;
            if (!path.getFileName().toString().endsWith(".dng"))
                throw new SecurityException("Simulated media directory: non-DNG creation rejected");
            if (!path.equals(original)) stagingChecks++;
            if (denyCommit && path.equals(original))
                throw new SecurityException("Injected failure before atomic replacement");
        }
    }
    public static void main(String[] args) throws Exception {
        Path path=Path.of(args[1]).toAbsolutePath();
        String mode=args[2];
        byte[] before=Files.readAllBytes(path);
        M9DngProfile profile=new M9DngProfile(new double[]{1.07,-.04,-.03,.02,.89,.09,-.02,.25,.77},
                1.25,Files.readAllBytes(Path.of(args[0])));
        MediaDirectoryPolicy policy=new MediaDirectoryPolicy(path,mode.equals("deny_commit"));
        Exception failure=null;
        System.setSecurityManager(policy);
        try { M9DngProfileWriter.embed(path,profile,"M9 App1B storage regression"); }
        catch(Exception e) { failure=e; }
        finally { System.setSecurityManager(null); }
        byte[] after=Files.readAllBytes(path);
        if(mode.equals("success")) {
            if(failure!=null) throw failure;
            if(policy.stagingChecks==0 || after.length<=before.length)
                throw new AssertionError("No staged profile committed");
            if(!Arrays.equals(Arrays.copyOfRange(before,8,before.length),Arrays.copyOfRange(after,8,before.length)))
                throw new AssertionError("Original payload changed");
        } else {
            String expected=mode.equals("old_writer")?"non-DNG creation rejected":"before atomic replacement";
            if(failure==null || !failure.toString().contains(expected) || !Arrays.equals(before,after))
                throw new AssertionError("Expected failure did not preserve complete original: "+failure);
        }
        try(var files=Files.list(path.getParent())) {
            if(files.anyMatch(p -> p.getFileName().toString().startsWith("M9_PROFILE_PENDING_")
                    || p.getFileName().toString().startsWith(".m9-profile-")))
                throw new AssertionError("Staging file not cleaned up");
        }
        System.out.println(mode+": passed; staging write checks="+policy.stagingChecks);
    }
}
