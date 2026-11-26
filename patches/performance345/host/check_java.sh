#!/usr/bin/env bash
set -eu
src="$1/app/src/main/java/com/particlesdevs/photoncamera"
out=$(mktemp -d)
trap 'rm -rf "$out"' EXIT
# Only constants are inlined into the isolated preview-frame test.
dims=$(sed -n 's/.*public static final int WIDTH=\([0-9]*\), HEIGHT=[0-9]*, STEPS=\([0-9]*\);.*/public static final int WIDTH=\1, STEPS=\2;/p' "$src/m9/preview/M9AutoExposure2D.java")
test -n "$dims"
echo "package com.particlesdevs.photoncamera.m9.preview; final class M9AutoExposure2D { $dims }" > "$out/M9AutoExposure2D.java"
javac -d "$out" "$out/M9AutoExposure2D.java" patches/facehighlight1b/host/android/graphics/Bitmap.java \
    "$src"/m9/preview/{M9TrackedSubjectMeter,M9SubjectMeterFrames}.java "$src/control/tracking/TrackingGeometry.java" \
    "$src/m9/render/M9DngPublication.java" patches/performance345/host/*Test.java
java -ea -cp "$out" com.particlesdevs.photoncamera.m9.render.M9DngPublicationTest
java -ea -cp "$out" com.particlesdevs.photoncamera.m9.preview.M9SubjectMeterFramesTest
