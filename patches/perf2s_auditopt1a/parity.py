#!/usr/bin/env python3
"""Verify optional audit preserves native image input, context and rendered pixels.
Usage: parity.py PHOTON_SOURCE OUTPUT_DIRECTORY (JAVA_HOME required).
"""
from pathlib import Path
import json, os, subprocess, sys

root,out=map(lambda x:Path(x).resolve(),sys.argv[1:])
out.mkdir(parents=True,exist_ok=True)
stub=out/'android';stub.mkdir(exist_ok=True)
(stub/'bitmap.h').write_text('''#pragma once
#include <jni.h>
#include <cstdint>
#define ANDROID_BITMAP_FORMAT_RGBA_8888 1
#define ANDROID_BITMAP_RESULT_SUCCESS 0
struct AndroidBitmapInfo {uint32_t width,height,stride;int32_t format;uint32_t flags;};
inline int AndroidBitmap_getInfo(JNIEnv*,jobject,AndroidBitmapInfo*){return -1;}
inline int AndroidBitmap_lockPixels(JNIEnv*,jobject,void**){return -1;}
inline int AndroidBitmap_unlockPixels(JNIEnv*,jobject){return 0;}
''')
jdk=Path(os.environ['JAVA_HOME'])
cpp=root/'app/src/main/cpp'
binary=out/'audit-parity'
subprocess.run(['g++','-std=c++17','-O2','-pthread','-fopenmp','-ffp-contract=off',
    '-fno-fast-math','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',
    '-I'+str(out),'-I'+str(jdk/'include'),'-I'+str(jdk/'include/linux'),'-I'+str(cpp),
    str(Path(__file__).with_name('parity.cpp')),'-o',str(binary)],check=True)
result=subprocess.check_output([str(binary),str(root/'app/src/main/assets/m9/m9_curve02_firmware.bin')],text=True)
report=json.loads(result)
(out/'NATIVE_AUDIT_PARITY.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
