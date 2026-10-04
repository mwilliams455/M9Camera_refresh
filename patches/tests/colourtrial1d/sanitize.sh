#!/usr/bin/env bash
set -euo pipefail
SRC="$1/app/src/main/cpp"
OUT="$2"
JNI_INC="${M9_TRIAL_JNI_INCLUDE:-$JAVA_HOME/include}"
g++ -std=c++17 -O1 -g -pthread -fopenmp -ffp-contract=off -fno-fast-math -fsanitize=address,undefined -fno-omit-frame-pointer -I"$OUT" -I"$JNI_INC" -I"$JNI_INC/linux" -I"$SRC" -I"$SRC/colourtrial1c/upstream/include" patches/tests/colourtrial1d/sanitize.cpp patches/tests/colourtrial1d/host.cpp "$SRC/colourtrial1c/reconstruct.cpp" "$SRC/colourtrial1c/phase_noise.cpp" "$SRC/colourtrial1c/chroma.cpp" "$SRC/colourtrial1c/upstream/amaze.cc" "$SRC/colourtrial1c/upstream/border.cc" -o "$OUT/sanitize"
ASAN_OPTIONS=detect_leaks=${M9_LSAN:-1} UBSAN_OPTIONS=halt_on_error=1 "$OUT/sanitize"
