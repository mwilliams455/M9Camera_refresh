package com.particlesdevs.photoncamera.m9.preview;
import java.nio.file.*;
import org.json.*;
import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D.*;

final class RegionalFixture {
 final JSONObject root;
 RegionalFixture(String path)throws Exception{root=new JSONObject(Files.readString(Path.of(path)));}
 static int[] ints(JSONArray a){int[] v=new int[a.length()];for(int i=0;i<v.length;i++)v[i]=a.getInt(i);return v;}
 static double[] doubles(JSONArray a){double[] v=new double[a.length()];for(int i=0;i<v.length;i++)v[i]=a.getDouble(i);return v;}
 static Stats read(JSONObject o){return new Stats(o.getInt("weightedMedianCode"),o.getDouble("darkFraction"),
  o.getDouble("brightFraction"),o.getDouble("channelClipFraction"),o.getInt("centerMedianCode"),
  o.getInt("centerQ25Code"),o.getInt("outerQ90Code"),o.getDouble("centerDarkFraction"),
  o.getDouble("outerBrightFraction"),o.getDouble("centerBrightFraction"),o.getDouble("centerClipFraction"),
  o.getDouble("outerClipFraction"),ints(o.getJSONArray("fieldMedianCode")),ints(o.getJSONArray("fieldQ25Code")),
  ints(o.getJSONArray("fieldQ90Code")),doubles(o.getJSONArray("fieldBrightFraction")),doubles(o.getJSONArray("fieldClipFraction")));}
 Stats[] shutter(){JSONArray a=root.getJSONArray("shutterBracket");Stats[] s=new Stats[a.length()];for(int i=0;i<s.length;i++)s[i]=read(a.getJSONObject(i));return s;}
 // Only base and +0.50 are recorded for each selected moment. Other slots are
 // explicitly synthetic: neutral at +0.25, a global clipping stop at >=+0.75.
 // This isolates the real two-pixel/three-pixel boundary; it is not a replay
 // of the missing complete temporal brackets or the whole recorded scene.
 Stats[] boundary(boolean after){
  JSONObject e=root.getJSONObject(after?"after":"before");
  Stats b=read(e.getJSONObject("base")),v=read(e.getJSONObject(after?"firstRejected":"lastSafe"));
  Stats hard=new Stats(v.median,v.dark,.4,.2,v.centerMedian,v.centerQ25,v.outerQ90,v.centerDark,
   v.outerBright,v.centerBright,v.centerClipped,v.outerClipped,v.fieldMedian,v.fieldQ25,v.fieldQ90,v.fieldBright,v.fieldClipped);
  Stats[] s=new Stats[M9AutoExposure2D.STEPS];s[0]=b;s[1]=b;s[2]=v;
  for(int i=3;i<s.length;i++)s[i]=hard;return s;
 }
 static Stats[] clear(Stats[] s){
  // A synthetic, genuinely clear scene, retaining the same placement request.
  for(Stats v:s){java.util.Arrays.fill(v.fieldClipped,0);}
  return s;
 }
}
