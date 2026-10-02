package com.particlesdevs.photoncamera.processing;
import java.nio.file.*;
public final class StandardHostProbe {
 public static void main(String[] args) throws Exception {
  M9DngProfile p=new M9DngProfile(new double[]{1,0,0,0,1,0,0,0,1},1,Files.readAllBytes(Path.of(args[0])));
  Files.write(Path.of(args[1],"tone-standard.bin"),p.tone);
  Files.write(Path.of(args[1],"look-standard.bin"),p.look);
 }
}
