from pathlib import Path
import os,subprocess,sys,shutil
here=Path(__file__).resolve().parent
root=Path(sys.argv[1]).resolve();ndk=Path(sys.argv[2]).resolve()
clang=ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'
for abi,target in [('arm64-v8a','aarch64-linux-android26'),('armeabi-v7a','armv7a-linux-androideabi26')]:
    out=root/'app/src/main/jniLibs'/abi/'libm9sharpness.so';out.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run([str(clang/(target+'-clang++')),'-std=c++17','-O3','-fno-fast-math','-fPIC','-shared','-static-libstdc++','-Wl,-z,max-page-size=16384','-Wl,-z,common-page-size=16384','-Wl,--no-undefined',str(here/'m9_sharpness.cpp'),'-o',str(out)],check=True)
    print(abi,out.stat().st_size)
