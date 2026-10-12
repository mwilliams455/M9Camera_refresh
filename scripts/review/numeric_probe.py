#!/usr/bin/env python3
"""Run v2.88 numeric review probes against unchanged reconstructed Java source.

Usage: python3 scripts/review/numeric_probe.py /path/to/PhotonCamera_288
Requires JDK 17. No Android SDK, app build, or production edits are involved.
Color classes are compiled verbatim. computeNoise/mul are extracted verbatim;
only their Android/app dependencies are replaced with small data/log stubs.
These probes document existing behavior; they are not desired-behavior tests.
"""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile


def method(text, signature):
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


root = Path(sys.argv[1]).resolve() / "app/src/main/java/com/particlesdevs/photoncamera"
with tempfile.TemporaryDirectory(prefix="numeric-review-") as directory:
    scratch = Path(directory)
    pkg = scratch / "com/particlesdevs/photoncamera/processing/render"
    pkg.mkdir(parents=True)
    util = scratch / "com/particlesdevs/photoncamera/util"
    util.mkdir(parents=True)
    (util / "Log.java").write_text("package com.particlesdevs.photoncamera.util; public class Log { public static int d(String t, String s) { return 0; } }")
    paths = ["processing/render/ColorCorrectionCube.java", "processing/render/ColorCorrectionTransform.java", "processing/opengl/postpipeline/PostPipeline.java", "capture/CaptureController.java"]
    texts = {}
    for path in paths:
        data = (root / path).read_bytes()
        texts[path] = data.decode()
        print("SOURCE", path, hashlib.sha256(data).hexdigest(), flush=True)
        if "/render/" in path:
            (pkg / Path(path).name).write_bytes(data)
    noise = method(texts[paths[2]], "private void computeNoise(Parameters parameters)")
    mul = method(texts[paths[3]], "private void mul(Rect in, double k)")
    (pkg / "Extracted.java").write_text("""package com.particlesdevs.photoncamera.processing.render;
import com.particlesdevs.photoncamera.util.Log;
class Extracted {
    float noiseS, noiseO;
    float constShift = 0.0f;
    Settings mSettings = new Settings();
    static class Settings { double noiseRstr; }
    static class Pair { Double first, second; Pair(double s, double o) { first=s; second=o; } }
    static class NoiseModeler { Pair[] computeModel; }
    static class Parameters { NoiseModeler noiseModeler; }
    static class Rect { int left, top, right, bottom; Rect(int l,int t,int r,int b){left=l;top=t;right=r;bottom=b;} }
    void runNoise(double strength, double s, double o) {
        mSettings.noiseRstr = strength;
        Parameters p = new Parameters(); p.noiseModeler = new NoiseModeler();
        p.noiseModeler.computeModel = new Pair[]{new Pair(s,o),new Pair(s,o),new Pair(s,o)};
        computeNoise(p);
    }
    void scale(Rect rect, double k) { mul(rect,k); }
""" + noise + "\n" + mul + "\n}\n")
    (pkg / "NumericProbe.java").write_bytes(Path(__file__).with_name("NumericProbe.java").read_bytes())
    # Some runtimes include jdk.compiler but omit the javac launcher from PATH.
    subprocess.run(["java", "-m", "jdk.compiler/com.sun.tools.javac.Main", "--release", "17", "-d", str(scratch), *map(str, scratch.rglob("*.java"))], check=True)
    subprocess.run(["java", "-cp", str(scratch), "com.particlesdevs.photoncamera.processing.render.NumericProbe"], check=True)
