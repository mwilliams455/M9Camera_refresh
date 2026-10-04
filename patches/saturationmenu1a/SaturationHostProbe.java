package com.particlesdevs.photoncamera.processing;
import java.nio.file.*;
import java.lang.reflect.Method;
import java.io.*;
/** Exercises the production profile sampler and complete tables using synthetic colour only. */
public final class SaturationHostProbe {
 public static void main(String[] args) throws Exception {
  byte[] curve=Files.readAllBytes(Path.of(args[0]));
  Path out=Path.of(args[1]);
  double[] identity={1,0,0,0,1,0,0,0,1};
  Method ref=M9DngProfile.class.getDeclaredMethod("reference",double.class,double.class,double.class,double[].class);
  ref.setAccessible(true);
  for(int bank=0;bank<5;bank++) {
   M9DngProfile p=new M9DngProfile(identity,1,curve,bank);
   Files.write(out.resolve("tone"+bank+".bin"),p.tone);
   Files.write(out.resolve("look"+bank+".bin"),p.look);
   double[] rgb=new double[3];
   try(DataInputStream in=new DataInputStream(Files.newInputStream(out.resolve("samples.bin")));
       DataOutputStream dst=new DataOutputStream(Files.newOutputStream(out.resolve("profile"+bank+".bin")))) {
    while(in.available()>0) {ref.invoke(p,in.readDouble(),in.readDouble(),in.readDouble(),rgb);for(double v:rgb)dst.writeByte((int)Math.rint(v*255));}
   }
  }
  for(int bank:new int[]{-1,5,Integer.MAX_VALUE}) {
   try {new M9DngProfile(identity,1,curve,bank);throw new AssertionError("Invalid bank accepted");}
   catch(IllegalArgumentException expected) {}
  }
  if(M9Saturation.parse(null)!=2||M9Saturation.parse("broken")!=2||M9Saturation.parse("5")!=2)throw new AssertionError("Bad default");
  long[] copy=M9Saturation.matrix(2,true);copy[0]=0;
  if(M9Saturation.matrix(2,true)[0]!=13659)throw new AssertionError("Mutable table");
  System.out.println("All five production profiles generated; invalid choices default safely");
 }
}
