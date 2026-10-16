"""Compile the three verbatim old/new expressions with their production types.

Identical class bytes prove that the explicit casts preserve the compiler's
original arithmetic, including operand evaluation order and narrowing point.
This host check does not replace the Android build or regression suite.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import tempfile

candidate, parent = (Path(x).resolve() for x in sys.argv[1:])
here = Path(__file__).resolve().parent
java_root = "app/src/main/java/com/particlesdevs/photoncamera/"
smart = java_root + "processing/opengl/postpipeline/SmartNR.java"
overlay = java_root + "ui/camera/views/viewfinder/SurfaceViewOverViewfinder.java"


def statements(root):
    noise = (root / smart).read_text()
    debug = (root / overlay).read_text()
    settings = (root / (java_root + "api/Settings.java")).read_text()
    assert re.search(r"\bdouble\s+noiseRstr\s*[;=]", settings)
    result = []
    for name in ["LumaDenoiseLevel", "ChromaDenoiseLevel"]:
        matches = [line.strip() for line in noise.splitlines()
                   if line.strip().startswith(name) and "basePipeline.mSettings.noiseRstr" in line]
        assert len(matches) == 1, matches
        result.append(matches[0])
    matches = [line.strip() for line in debug.splitlines()
               if line.strip().startswith("y ") and "textPaint.descent()" in line]
    assert len(matches) == 1, matches
    return result + matches


def source(lines):
    return """public final class Probe {
  static final class Settings { double noiseRstr; }
  static final class Pipeline { Settings mSettings = new Settings(); }
  static final class TextPaint {
    float d, a;
    float descent() { return d; }
    float ascent() { return a; }
  }
  public static float luma(float LumaDenoiseLevel, double strength) {
    Pipeline basePipeline = new Pipeline(); basePipeline.mSettings.noiseRstr = strength;
    %s
    return LumaDenoiseLevel;
  }
  public static float chroma(float ChromaDenoiseLevel, double strength) {
    Pipeline basePipeline = new Pipeline(); basePipeline.mSettings.noiseRstr = strength;
    %s
    return ChromaDenoiseLevel;
  }
  public static int debug(int y, float descent, float ascent) {
    TextPaint textPaint = new TextPaint(); textPaint.d = descent; textPaint.a = ascent;
    %s
    return y;
  }
}
""" % tuple(lines)


with tempfile.TemporaryDirectory() as temporary:
    directories = [Path(temporary) / name for name in ["parent", "candidate"]]
    extracted = [statements(root) for root in [parent, candidate]]
    bytecode = []
    for directory, lines in zip(directories, extracted):
        directory.mkdir()
        (directory / "Probe.java").write_text(source(lines))
        subprocess.run(["java", "-m", "jdk.compiler/com.sun.tools.javac.Main",
                        "--release", "17", "-g:none", "Probe.java"], cwd=directory, check=True)
        bytecode.append({file.name: file.read_bytes() for file in directory.glob("*.class")})
    assert bytecode[0] == bytecode[1], "Explicit conversions changed compiled arithmetic"
    assert "Probe.class" in bytecode[0]
    report = {"status": "PASS", "expressionsCompared": 3,
              "parentStatements": extracted[0], "candidateStatements": extracted[1],
              "compiledClassBytesIdentical": True,
              "compiledProbeSha256": hashlib.sha256(bytecode[0]["Probe.class"]).hexdigest(),
              "scope": "Three verbatim expressions with original double/float/int types; no Android runtime simulation"}
    (here / "HOST_VERIFICATION.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
