package com.particlesdevs.photoncamera.m9.render;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;

public class M9DngPublicationTest {
    public static void main(String[] args) throws Exception {
        Path dir = Files.createTempDirectory("m9-publication-");
        Path target = dir.resolve("IMG_001.dng");
        byte[] raw = {73,73,42,0,8,0,0,0};
        Path stage = Files.write(M9DngPublication.createStagingFile(target),raw);
        Path saved = M9DngPublication.publishStagedDng(stage,target);
        assert saved.equals(target) && !Files.exists(stage) && Arrays.equals(raw,Files.readAllBytes(saved));
        Files.delete(target);
        Files.createDirectory(target);
        Files.write(target.resolve("occupied"), new byte[]{1});
        stage = Files.write(M9DngPublication.createStagingFile(target),raw);
        saved = M9DngPublication.publishStagedDng(stage,target);
        assert saved.equals(stage) && Arrays.equals(raw,Files.readAllBytes(saved));
        assert saved.getFileName().toString().startsWith("IMG_001_recovered_");
        Path second = M9DngPublication.createStagingFile(target);
        assert !second.equals(stage);
        Files.delete(second);
        Files.delete(stage);
        try {
            M9DngPublication.publishStagedDng(stage,target);
            throw new AssertionError("Missing RAW reported as saved");
        } catch (java.io.IOException expected) { }
        Files.delete(target.resolve("occupied"));
        Files.delete(target);
        Files.delete(dir);
        System.out.println("DNG publication, recovery, unique names and missing-source checks passed");
    }
}
