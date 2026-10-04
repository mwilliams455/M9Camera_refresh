"""Compile the actual continuity policy and verify the production TG1 fallback wiring."""
from pathlib import Path
import shutil, subprocess, sys, tempfile

root=Path(sys.argv[1]).resolve()
helper=root/"app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewSourceContinuity1A.java"
gpu=root/"app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9GpuPreview2A.java"
renderer=root/"app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java"
shader=root/"app/src/main/assets/shaders/preview/main_fs.glsl"
state=root/"app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewFrameState1W.java"

assert "M9TUNGSTENCONT1A" in helper.read_text()
assert "heldForContinuity" in gpu.read_text()
assert "frame1W.source2A.continuityHeld || !frame1W.source2A.ready" in renderer.read_text()
assert "glUniform1f(uTungsten2A, source.tungstenWeight)" not in renderer.read_text()
assert "return tungsten2A(fallback1A);" in shader.read_text()
assert "processed_OES_exposure_plus_TG1_fallback" in state.read_text()

stub='''package com.particlesdevs.photoncamera.m9.preview;
public final class M9GpuPreview2A {
 public static final class Frame {
  public final boolean ready,continuityHeld; public final String reason,cameraId,continuityContractReason;
  public final long continuityLastGoodAgeMs;
  private Frame(boolean r,String why,String id,boolean held,String contract,long age){
   ready=r;reason=why;cameraId=id;continuityHeld=held;continuityContractReason=contract;continuityLastGoodAgeMs=age;
  }
  public static Frame fallback(String why){return new Frame(false,why,"",false,why,-1);}
  public static Frame good(String id){return new Frame(true,"good",id,false,"good",0);}
  public Frame heldForContinuity(String why,long age){return new Frame(true,"held_last_valid_source",cameraId,true,why,age);}
 }
}'''

with tempfile.TemporaryDirectory() as td:
    d=Path(td); src=d/"src"; out=d/"classes"; out.mkdir()
    p=src/"com/particlesdevs/photoncamera/m9/preview/M9GpuPreview2A.java";p.parent.mkdir(parents=True);p.write_text(stub)
    shutil.copyfile(helper,src/"com/particlesdevs/photoncamera/m9/preview/M9PreviewSourceContinuity1A.java")
    shutil.copyfile(Path(__file__).with_name("ContinuityTest.java"),src/"ContinuityTest.java")
    subprocess.run(["java","-m","jdk.compiler/com.sun.tools.javac.Main","-d",str(out),
                    *[str(x) for x in src.rglob("*.java")]],check=True)
    subprocess.run(["java","-ea","-cp",str(out),"ContinuityTest"],check=True)

print("M9TUNGSTENCONT1A production wiring PASS")
