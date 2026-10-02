import android.hardware.camera2.CameraCharacteristics;
import com.particlesdevs.photoncamera.app.PhotonCamera;
import com.particlesdevs.photoncamera.processing.render.*;
import com.particlesdevs.photoncamera.util.Allocator;
import java.util.concurrent.*;

public class ParametersFreezeProbe extends ParameterFixtures {
 public static void main(String[] args) throws Exception {
  CameraCharacteristics a=lens(64,1),b=lens(512,1.7f);
  select("0",a,0);String immediate=fingerprint(fill(a,false)),raw=fingerprint(fill(a,true));
  M9CaptureParameters first=M9CaptureParameters.freeze(a);
  try(M9CaptureParameters.Scope scope=first.open()){
   check(fingerprint(fill(a,false)).equals(immediate),"same-lens render values changed");
   check(fingerprint(fill(a,true)).equals(raw),"same-lens RAW values changed");
  }
  PhotonCamera.sensor.selectedSensorSpecifics.NoiseModelerArr[0][0]=999;
  select("0-2",b,2);String secondExpected=fingerprint(fill(b,false));
  M9CaptureParameters second=M9CaptureParameters.freeze(b);
  PhotonCamera.settings.compressor=3;PhotonCamera.settings.cfaPattern=3;PhotonCamera.settings.colorMethod=2;Allocator.binning=true;
  try(M9CaptureParameters.Scope scope=first.open()){
   Parameters p=fill(a,false);
   check(fingerprint(p).equals(immediate),"queued capture changed after lens/settings switch");
   p.sensorSpecifics.NoiseModelerArr[0][0]=888;
   check(fingerprint(fill(a,true)).equals(raw),"DNG shares mutable render parameters");
   try(M9CaptureParameters.Scope nested=second.open()){
    check(fingerprint(fill(b,false)).equals(secondExpected),"nested capture has wrong inputs");
   }
   check(fingerprint(fill(a,false)).equals(immediate),"nested fallback failed to restore capture");
  }
  check(fill(b,true).blackLevel[0]==2048,"scope leaked into ordinary Photon path");
  ExecutorService pool=Executors.newFixedThreadPool(2);
  CountDownLatch ready=new CountDownLatch(2),release=new CountDownLatch(1);
  Future<String> render=pool.submit(()->{try(M9CaptureParameters.Scope s=first.open()){ready.countDown();check(release.await(5,TimeUnit.SECONDS),"barrier");return fingerprint(fill(a,false));}});
  Future<String> dng=pool.submit(()->{try(M9CaptureParameters.Scope s=second.open()){ready.countDown();check(release.await(5,TimeUnit.SECONDS),"barrier");return fingerprint(fill(b,false));}});
  check(ready.await(5,TimeUnit.SECONDS),"workers");release.countDown();
  check(render.get(5,TimeUnit.SECONDS).equals(immediate),"render worker mixed capture");
  check(dng.get(5,TimeUnit.SECONDS).equals(secondExpected),"DNG worker mixed capture");
  Future<Boolean> cleanup=pool.submit(()->{try{try(M9CaptureParameters.Scope s=first.open()){throw new IllegalStateException("injected");}}catch(IllegalStateException expected){}return fill(b,true).blackLevel[0]==2048;});
  check(cleanup.get(5,TimeUnit.SECONDS),"exception leaked scope to reused worker");pool.shutdownNow();
  System.out.println("PARAMETER_CASES=10: same-lens JPEG/RAW unchanged; switched lens/settings frozen; sensor arrays isolated; nested fallback restored; unscoped path unchanged; concurrent jobs isolated; exception cleanup passed.");
 }
}
