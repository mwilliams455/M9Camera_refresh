package com.particlesdevs.photoncamera.processing;
import java.nio.file.*;
/** Host harness compiles the production Android-independent implementation verbatim. */
public final class ProfileHostProbe {
 public static void main(String[] args) throws Exception {
  byte[] curve=Files.readAllBytes(Path.of(args[0]));
  double gain=Double.parseDouble(args[1]);
  double[] m={1.07,-.04,-.03,.02,.89,.09,-.02,.25,.77};
  if(args[2].equals("invalid")) {
   int caught=0;
   try {new M9DngProfile(m,Double.NaN,curve);}catch(IllegalArgumentException e){caught++;}
   try {new M9DngProfile(m,0,curve);}catch(IllegalArgumentException e){caught++;}
   try {new M9DngProfile(new double[9],gain,curve);}catch(IllegalArgumentException e){caught++;}
   byte[] wrong=curve.clone();wrong[0]^=1;
   try {new M9DngProfile(m,gain,wrong);}catch(IllegalArgumentException e){caught++;}
   if(caught!=4)throw new AssertionError("invalid inputs accepted");
   System.out.println("INVALID_INPUT_GATES=4");return;
  }
  M9DngProfile profile=new M9DngProfile(m,gain,curve);
  if(args[2].equals("tone")) {Files.write(Path.of(args[3]),profile.tone);System.out.println("GENERATION_MS="+profile.elapsedMs);return;}
  Path path=Path.of(args[2]);
  M9DngProfileWriter.Result result=M9DngProfileWriter.embed(path,profile,"M9 App1A synthetic test");
  byte[] successful=Files.readAllBytes(path);boolean rejected=false;
  try {M9DngProfileWriter.embed(path,profile,"M9 App1A overwrite");}catch(java.io.IOException e){rejected=true;}
  if(!rejected||!java.util.Arrays.equals(successful,Files.readAllBytes(path)))throw new AssertionError("existing DNG modified by rejected export");
  System.out.println("GENERATION_MS="+profile.elapsedMs+" DIGEST="+result.digest+" ADDED="+result.addedBytes);
 }
}
