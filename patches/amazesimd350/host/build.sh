#!/usr/bin/env bash
# Usage: build.sh SOURCE_TREE OUT_BINARY COMPILER [extra flags...]
set -euo pipefail
src=$1; out=$2; cxx=$3; shift 3
here=$(cd "$(dirname "$0")" && pwd)
cpp=$src/app/src/main/cpp; ct=$cpp/colourtrial1c
stub=$(mktemp -d); mkdir -p "$stub/android"
cat > "$stub/android/bitmap.h" <<'H'
#pragma once
#include <jni.h>
#include <cstdint>
#define ANDROID_BITMAP_FORMAT_RGBA_8888 1
#define ANDROID_BITMAP_RESULT_SUCCESS 0
struct AndroidBitmapInfo {uint32_t width,height,stride;int32_t format;uint32_t flags;};
inline int AndroidBitmap_getInfo(JNIEnv*,jobject,AndroidBitmapInfo*){return -1;}
inline int AndroidBitmap_lockPixels(JNIEnv*,jobject,void**){return -1;}
inline int AndroidBitmap_unlockPixels(JNIEnv*,jobject){return 0;}
H
jinc=$(dirname "$(dirname "$(readlink -f "$(which javac)")")")/include
"$cxx" -std=c++17 -O3 -pthread -fopenmp -ffp-contract=off -fno-fast-math "$@" \
  -I"$stub" -I"$jinc" -I"$jinc/linux" -I"$cpp" -I"$ct/upstream/include" \
  "$here/amaze_simd_parity.cpp" "$here/../../prepperf1b/host.cpp" \
  "$ct/reconstruct.cpp" "$ct/phase_noise.cpp" "$ct/chroma.cpp" "$ct/upstream/amaze.cc" "$ct/upstream/border.cc" \
  -o "$out" 2> >(grep -v -i "warning\|note:\|^ *|\|^ *[0-9]* |\|~~~\|\^" >&2)
rm -rf "$stub"
