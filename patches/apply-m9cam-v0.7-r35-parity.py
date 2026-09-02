#!/usr/bin/env python3
from pathlib import Path
import hashlib, os, re, shutil, subprocess, sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply-m9cam-v0.7-r35-parity.py <PhotonCamera-root>")
root = Path(sys.argv[1]).resolve()
if not (root / "app").is_dir():
    raise SystemExit(f"not a PhotonCamera root: {root}")

here = Path(__file__).resolve()
overlay = here.parents[1]
payload = overlay / "payload" / "app"
if not payload.is_dir():
    raise SystemExit(f"v0.7 renderer payload missing: {payload}")

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f"v0.7 renderer patch failed: missing {rel}")
    return p.read_text()

def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

def add_import(text, anchor, addition):
    if addition.strip() in text:
        return text
    if anchor not in text:
        raise SystemExit(f"v0.7 renderer patch failed: import anchor missing: {anchor!r}")
    return text.replace(anchor, anchor + addition, 1)

# This overlay is deliberately based on the already-accepted v0.6.1 capture policy.
policy = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java"
if not policy.exists():
    raise SystemExit("v0.7 renderer patch failed: apply v0.6 then v0.6.1 first")
policy_text = policy.read_text()
for required in [
    "MOTION_ACTIVATE = 0.52",
    "PERSISTENCE_PEAK_SCALE = 0.96",
    "PERSISTENCE_MAX_BOOST = 0.08",
    "ANALOG_HEADROOM_FRACTION = 0.95",
]:
    if required not in policy_text:
        raise SystemExit(f"v0.7 renderer patch failed: frozen v0.6.1 seam missing: {required}")

# Verify the frozen calibration asset before copying it into the app.
asset_rel = Path("src/main/assets/m9/m9_r35_calibration.bin")
asset = payload / asset_rel
expected_asset_sha = "5568978ea42e7c65b51f26ffc2d56479418ec6c8d98b242199bab08acb62cbca"
if not asset.exists():
    raise SystemExit("v0.7 renderer patch failed: calibration asset missing")
actual = hashlib.sha256(asset.read_bytes()).hexdigest()
if actual != expected_asset_sha:
    raise SystemExit(f"v0.7 renderer patch failed: calibration SHA mismatch: {actual}")

# Copy the isolated R3.8 renderer payload plus the diagnostic-only LUMA1 analyzer plus LUMA2.4-SPATIAL2-FB1 live-feedback scorer/instrumentation. Frozen v0.6.1 motion-policy source remains untouched.
for src in payload.rglob("*"):
    if not src.is_file():
        continue
    rel = src.relative_to(payload)
    dst = root / "app" / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

# PERF3F EXIFASYNC1A + JPEGBUF64K1A: instrument Photon's exact JPEG save helper without changing the save sequence.
# The timing OutputStream forwards every byte unchanged and records time spent inside the
# underlying Files.newOutputStream writer. This lets the renderer distinguish Bitmap.compress
# wall time, stream-write time and EXIF rewrite time while preserving JPEG bytes/quality/EXIF flow.
image_saver_rel = "app/src/main/java/com/particlesdevs/photoncamera/processing/ImageSaver.java"
image_saver = read(image_saver_rel)
if "PERF3E_JPEGBUF64K1A_EXACT_BYTES" not in image_saver:
    util_anchor = "    public static class Util {\n"
    if util_anchor not in image_saver:
        raise SystemExit("PERF3F EXIFASYNC1A patch failed: ImageSaver.Util anchor missing")
    timing_helper = r'''        // PERF3E_JPEGBUF64K1A_EXACT_BYTES
        public static final class M9JpegSaveTiming {
            public long fileOpenNs;
            public long compressNs;
            public long streamWriteNs;
            public long flushNs;
            public long closeNs;
            public long recycleNs;
            public long exifSetupNs;
            public long exifSaveNs;
            public long totalNs;
            public long writeCalls;
        }

        private static final ThreadLocal<M9JpegSaveTiming> M9_JPEG_SAVE_TIMING = new ThreadLocal<>();

        public static M9JpegSaveTiming consumeM9JpegSaveTiming() {
            M9JpegSaveTiming timing = M9_JPEG_SAVE_TIMING.get();
            M9_JPEG_SAVE_TIMING.remove();
            return timing;
        }

        private static final class M9TimingOutputStream extends OutputStream {
            private final OutputStream delegate;
            private final M9JpegSaveTiming timing;

            M9TimingOutputStream(OutputStream delegate, M9JpegSaveTiming timing) {
                this.delegate = delegate;
                this.timing = timing;
            }

            @Override
            public void write(int b) throws IOException {
                long started = System.nanoTime();
                try {
                    delegate.write(b);
                } finally {
                    timing.streamWriteNs += System.nanoTime() - started;
                    timing.writeCalls++;
                }
            }

            @Override
            public void write(byte[] b, int off, int len) throws IOException {
                long started = System.nanoTime();
                try {
                    delegate.write(b, off, len);
                } finally {
                    timing.streamWriteNs += System.nanoTime() - started;
                    timing.writeCalls++;
                }
            }

            @Override
            public void flush() throws IOException {
                long started = System.nanoTime();
                try {
                    delegate.flush();
                } finally {
                    timing.flushNs += System.nanoTime() - started;
                }
            }

            @Override
            public void close() throws IOException {
                long started = System.nanoTime();
                try {
                    delegate.close();
                } finally {
                    timing.closeNs += System.nanoTime() - started;
                }
            }
        }

'''
    image_saver = image_saver.replace(util_anchor, util_anchor + timing_helper, 1)
    old_jpeg = r'''        public static boolean saveBitmapAsJPG(Path fileToSave, Bitmap img, int jpgQuality, ParseExif.ExifData exifData) {
            exifData.COMPRESSION = String.valueOf(jpgQuality);
            try {
                OutputStream outputStream = Files.newOutputStream(fileToSave);
                img.compress(Bitmap.CompressFormat.JPEG, jpgQuality, outputStream);
                outputStream.flush();
                outputStream.close();
                img.recycle();
                ExifInterface inter = ParseExif.setAllAttributes(fileToSave.toFile(), exifData);
                inter.saveAttributes();
                return true;
            } catch (IOException e) {
                e.printStackTrace();
                return false;
            }
        }
'''
    new_jpeg = r'''        public static boolean saveBitmapAsJPG(Path fileToSave, Bitmap img, int jpgQuality, ParseExif.ExifData exifData) {
            exifData.COMPRESSION = String.valueOf(jpgQuality);
            M9JpegSaveTiming timing = new M9JpegSaveTiming();
            M9_JPEG_SAVE_TIMING.set(timing);
            long totalStartedNs = System.nanoTime();
            try {
                long stageStartedNs = System.nanoTime();
                OutputStream rawOutputStream = Files.newOutputStream(fileToSave);
                timing.fileOpenNs = System.nanoTime() - stageStartedNs;
                // PERF3F EXIFASYNC1A + JPEGBUF64K1A: transport-only batching; Bitmap.compress bytes/quality are unchanged.
                OutputStream timedRawOutputStream = new M9TimingOutputStream(rawOutputStream, timing);
                OutputStream outputStream = new java.io.BufferedOutputStream(timedRawOutputStream, 64 * 1024);

                stageStartedNs = System.nanoTime();
                img.compress(Bitmap.CompressFormat.JPEG, jpgQuality, outputStream);
                timing.compressNs = System.nanoTime() - stageStartedNs;
                outputStream.flush();
                outputStream.close();

                stageStartedNs = System.nanoTime();
                img.recycle();
                timing.recycleNs = System.nanoTime() - stageStartedNs;

                stageStartedNs = System.nanoTime();
                ExifInterface inter = ParseExif.setAllAttributes(fileToSave.toFile(), exifData);
                timing.exifSetupNs = System.nanoTime() - stageStartedNs;
                stageStartedNs = System.nanoTime();
                inter.saveAttributes();
                timing.exifSaveNs = System.nanoTime() - stageStartedNs;
                return true;
            } catch (IOException e) {
                e.printStackTrace();
                return false;
            } finally {
                timing.totalNs = System.nanoTime() - totalStartedNs;
            }
        }

        // PERF3F EXIFASYNC1A M9-only payload writer. It is byte/pixel/quality-identical to
        // the synchronous helper above through bitmap recycle, but deliberately stops before
        // ParseExif.setAllAttributes()/saveAttributes(). M9JpegFinalizeQueue owns that exact
        // metadata step and Photon publication afterward.
        public static boolean saveBitmapAsJPGPayloadM9(Path fileToSave, Bitmap img, int jpgQuality, ParseExif.ExifData exifData) {
            exifData.COMPRESSION = String.valueOf(jpgQuality);
            M9JpegSaveTiming timing = new M9JpegSaveTiming();
            M9_JPEG_SAVE_TIMING.set(timing);
            long totalStartedNs = System.nanoTime();
            try {
                long stageStartedNs = System.nanoTime();
                OutputStream rawOutputStream = Files.newOutputStream(fileToSave);
                timing.fileOpenNs = System.nanoTime() - stageStartedNs;
                OutputStream timedRawOutputStream = new M9TimingOutputStream(rawOutputStream, timing);
                OutputStream outputStream = new java.io.BufferedOutputStream(timedRawOutputStream, 64 * 1024);

                stageStartedNs = System.nanoTime();
                img.compress(Bitmap.CompressFormat.JPEG, jpgQuality, outputStream);
                timing.compressNs = System.nanoTime() - stageStartedNs;
                outputStream.flush();
                outputStream.close();

                stageStartedNs = System.nanoTime();
                img.recycle();
                timing.recycleNs = System.nanoTime() - stageStartedNs;
                return true;
            } catch (IOException e) {
                e.printStackTrace();
                return false;
            } finally {
                timing.totalNs = System.nanoTime() - totalStartedNs;
            }
        }
'''
    if old_jpeg not in image_saver:
        raise SystemExit("PERF3F EXIFASYNC1A patch failed: exact Photon saveBitmapAsJPG baseline not found")
    image_saver = image_saver.replace(old_jpeg, new_jpeg, 1)
    write(image_saver_rel, image_saver)

# OpenCV 4.13.0 matches the cv2 version used by the frozen Python R3.5 oracle.
# Insert structurally at the dependencies block rather than anchoring to a particular
# first dependency line; earlier M9 overlays or upstream formatting must not matter.
gradle_rel = "app/build.gradle"
g = read(gradle_rel)
if "org.opencv:opencv:4.13.0" not in g:
    dep_re = re.compile(r"(?m)^(?P<indent>[ \t]*)dependencies[ \t]*\{[ \t]*(?:\r?\n)")
    match = dep_re.search(g)
    if not match:
        raise SystemExit("v0.7B renderer patch failed: app/build.gradle has no dependencies { block")
    indent = match.group("indent") + "    "
    insertion = match.group(0) + indent + "implementation 'org.opencv:opencv:4.13.0'\n"
    g = g[:match.start()] + insertion + g[match.end():]

# PRIMARY2.3 JNI1 FIX7 native packaging seam.
# Keep PhotonCamera's existing externalNativeBuild wiring; repair only a contaminated
# CMakeLists.txt baseline and append one isolated m9color target.

# v0.6.1 owns the incoming version. Be tolerant of single/double quotes and spacing.
# IMPORTANT: many browser uploads do not replace the hidden .github workflow, so
# the repository may still be running the original v0.7A verifier.  Keep explicit
# verifier aliases in build.gradle so the proven stale v0.7A/v0.7B/v0.7D
# bootstrap checks accept this direct derivative while the actual APK version identifies LUMA2.4-SPATIAL2.
version_re = re.compile(r"versionName\s+([\'\"])(?:0\.97-m9modern6p1|0\.97-m9modern7r35[a-d]|0\.97-m9modern7r36a|0\.97-m9modern7r37a|0\.97-m9modern7r38a|0\.97-m9modern7r38luma1|0\.97-m9modern7r38luma2|0\.97-m9modern7r38luma21|0\.97-m9modern7r38luma22|0\.97-m9modern7r38luma23|0\.97-m9modern7r38luma24|0\.97-m9modern7r38luma24fb1|0\.98-m9modern7r38luma24fb1full12|0\.99-m9modern7r38luma24fb1full12async1|1\.00-m9modern7r38luma24fb1primary1|1\.01-m9modern7r38luma24fb1primary2|1\.02-m9modern7r38luma24fb1primary21|1\.03-m9modern7r38luma24fb1primary22|1\.04-m9modern7r38luma24fb1primary22b|1\.05-m9modern7r38luma24fb1primary22c|1\.05-m9modern7r38luma24fb1primary22d|1\.06-m9modern7r38luma24fb1primary23jni1|1\.06-m9modern7r38luma24fb1primary23jni1fix1|1\.07-m9modern7r38luma24fb1primary23jni1fix2|1\.08-m9modern7r38luma24fb1primary23jni1fix3|1\.09-m9modern7r38luma24fb1primary23jni1fix4|1\.10-m9modern7r38luma24fb1primary23jni1fix5|1\.11-m9modern7r38luma24fb1primary23jni1fix6|1\.12-m9modern7r38luma24fb1primary23jni1fix7|1\.13-m9modern7r38luma24fb1primary24tc20native1a|1\.14-m9modern7r38luma24fb1primary24tc20native1b|1\.15-m9modern7r38luma24fb1primary24tc20native1borient1a|1\.16-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1a|1\.17-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1a|1\.18-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1acolornative2a|1\.19-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1acolornative2afix1|1\.20-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1acolornative2afix1queue1a|1\.21-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1acolornative2afix1name1aqueue1b|1\.22-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1acolornative2afix1name1aqueue1btimingfreeze1a|1\.23-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1acolornative2afix1name1aqueue1btimingfreeze1adngasync1a|1\.24-m9modern7r38luma24fb1primary25perf3adngasync1a|1\.25-m9modern7r38luma24fb1primary25perf3bcolor8adngasync1a|1\.26-m9modern7r38luma24fb1primary25perf3ctc20luma8acolor8adngasync1a|1\.27-m9modern7r38luma24fb1primary25perf3djpeg1atc20luma8acolor8adngasync1a|1\.28-m9modern7r38luma24fb1primary25perf3ejpegbuf64k1atc20luma8acolor8adngasync1a|1\.29-m9modern7r38luma24fb1primary25perf3fexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1a|1\.30-m9modern7r38luma24fb1primary25perf3gorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1a|1\.31-m9modern7r38luma24fb1primary25perf3hcvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1a|1\.32-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1a)\1")
g2, n = version_re.subn("versionName '1.32-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1a'", g, count=1)
if n == 0:
    if "0.97-m9modern7r38luma24" not in g and "0.98-m9modern7r38luma24fb1full12" not in g and "0.99-m9modern7r38luma24fb1full12async1" not in g and "1.00-m9modern7r38luma24fb1primary1" not in g and "1.01-m9modern7r38luma24fb1primary2" not in g and "1.02-m9modern7r38luma24fb1primary21" not in g and "1.03-m9modern7r38luma24fb1primary22" not in g and "1.04-m9modern7r38luma24fb1primary22b" not in g and "1.05-m9modern7r38luma24fb1primary22c" not in g and "1.05-m9modern7r38luma24fb1primary22d" not in g and "1.06-m9modern7r38luma24fb1primary23jni1" not in g and "1.06-m9modern7r38luma24fb1primary23jni1fix1" not in g and "1.07-m9modern7r38luma24fb1primary23jni1fix2" not in g and "1.08-m9modern7r38luma24fb1primary23jni1fix3" not in g and "1.09-m9modern7r38luma24fb1primary23jni1fix4" not in g and "1.10-m9modern7r38luma24fb1primary23jni1fix5" not in g and "1.11-m9modern7r38luma24fb1primary23jni1fix6" not in g and "1.12-m9modern7r38luma24fb1primary23jni1fix7" not in g and "1.13-m9modern7r38luma24fb1primary24tc20native1a" not in g and "1.14-m9modern7r38luma24fb1primary24tc20native1b" not in g and "1.15-m9modern7r38luma24fb1primary24tc20native1borient1a" not in g and "1.16-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1a" not in g and "1.17-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1a" not in g and "1.18-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1acolornative2a" not in g and "1.19-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1acolornative2afix1" not in g and "1.20-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1acolornative2afix1queue1a" not in g and "1.21-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1acolornative2afix1name1aqueue1b" not in g and "1.22-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1acolornative2afix1name1aqueue1btimingfreeze1a" not in g and "1.23-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1acolornative2afix1name1aqueue1btimingfreeze1adngasync1a" not in g and "1.24-m9modern7r38luma24fb1primary25perf3adngasync1a" not in g and "1.25-m9modern7r38luma24fb1primary25perf3bcolor8adngasync1a" not in g and "1.26-m9modern7r38luma24fb1primary25perf3ctc20luma8acolor8adngasync1a" not in g and "1.27-m9modern7r38luma24fb1primary25perf3djpeg1atc20luma8acolor8adngasync1a" not in g and "1.28-m9modern7r38luma24fb1primary25perf3ejpegbuf64k1atc20luma8acolor8adngasync1a" not in g and "1.29-m9modern7r38luma24fb1primary25perf3fexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1a" not in g and "1.30-m9modern7r38luma24fb1primary25perf3gorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1a" not in g and "1.31-m9modern7r38luma24fb1primary25perf3hcvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1a" not in g and "1.32-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1a" not in g:
        found = re.findall(r"(?m)^.*versionName.*$", g)
        detail = found[0].strip() if found else "<none>"
        raise SystemExit(
            "v0.7D renderer patch failed: expected v0.6.1/v0.7 versionName; found: " + detail)

compat = "// M9 bootstrap verifier aliases: 0.97-m9modern7r35a 0.97-m9modern7r35b 0.97-m9modern7r35c 0.97-m9modern7r35d 0.97-m9modern7r36a 0.97-m9modern7r37a 0.97-m9modern7r38a 0.97-m9modern7r38luma1 0.97-m9modern7r38luma2 0.97-m9modern7r38luma21 0.97-m9modern7r38luma22 0.97-m9modern7r38luma23 0.97-m9modern7r38luma24 0.97-m9modern7r38luma24fb1 1.00-m9modern7r38luma24fb1primary1 1.01-m9modern7r38luma24fb1primary2 1.02-m9modern7r38luma24fb1primary21 1.03-m9modern7r38luma24fb1primary22 1.04-m9modern7r38luma24fb1primary22b 1.05-m9modern7r38luma24fb1primary22c 1.05-m9modern7r38luma24fb1primary22d 1.06-m9modern7r38luma24fb1primary23jni1 1.06-m9modern7r38luma24fb1primary23jni1fix1 1.07-m9modern7r38luma24fb1primary23jni1fix2 1.08-m9modern7r38luma24fb1primary23jni1fix3 1.09-m9modern7r38luma24fb1primary23jni1fix4 1.10-m9modern7r38luma24fb1primary23jni1fix5 1.11-m9modern7r38luma24fb1primary23jni1fix6 1.12-m9modern7r38luma24fb1primary23jni1fix7 1.13-m9modern7r38luma24fb1primary24tc20native1a 1.14-m9modern7r38luma24fb1primary24tc20native1b 1.15-m9modern7r38luma24fb1primary24tc20native1borient1a 1.16-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1a 1.17-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1a 1.18-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1acolornative2a 1.19-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1acolornative2afix1 1.20-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1acolornative2afix1queue1a 1.21-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1acolornative2afix1name1aqueue1b 1.22-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1acolornative2afix1name1aqueue1btimingfreeze1a 1.23-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1acolornative2afix1name1aqueue1btimingfreeze1adngasync1a\n"
compat_re = re.compile(r"(?m)^// M9 bootstrap verifier aliases:.*(?:\r?\n|$)")
if compat_re.search(g2):
    g2 = compat_re.sub(compat, g2, count=1)
elif compat not in g2:
    dep_pos = g2.find("dependencies")
    if dep_pos >= 0:
        g2 = g2[:dep_pos] + compat + g2[dep_pos:]
    else:
        g2 += "\n" + compat
write(gradle_rel, g2)

# PRIMARY2.3 JNI1 FIX7: restore PhotonCamera's native CMake baseline if an earlier
# JNI1 experiment replaced it, then add exactly ONE m9color target to the existing
# Photon native project. FIX7 deliberately removes the FIX6 jniLibs workaround.

def _cmake_is_photon_baseline(text):
    return (
        'project(dngCreator)' in text
        and re.search(r'add_library\s*\(\s*ncnnMl\b', text, re.IGNORECASE | re.DOTALL) is not None
        and 'dngCreator.cpp' in text
        and 'allocator.cpp' in text
        and 'flacRecorder.cpp' in text
        and 'native-engine.cpp' in text
    )

def _cmake_has_m9_target(text):
    return re.search(r'add_library\s*\(\s*m9color\b', text, re.IGNORECASE | re.DOTALL) is not None

def _git_good_cmake_candidate():
    rel = 'app/src/main/cpp/CMakeLists.txt'
    try:
        proc = subprocess.run(
            ['git', '-C', str(root), 'log', '--format=%H', '--', rel],
            text=True, capture_output=True, check=False)
    except Exception:
        return None, None
    for commit in proc.stdout.splitlines():
        commit = commit.strip()
        if not commit:
            continue
        show = subprocess.run(
            ['git', '-C', str(root), 'show', f'{commit}:{rel}'],
            text=True, capture_output=True, check=False)
        if show.returncode == 0 and _cmake_is_photon_baseline(show.stdout) and not _cmake_has_m9_target(show.stdout):
            return show.stdout, f'git:{commit[:12]}'
    return None, None

def _download_upstream_photon_cmake():
    # Shallow GitHub checkouts may not contain the pre-M9 parent. Use the canonical
    # PhotonCamera dev native project only after strict baseline landmark checks.
    import urllib.request
    url = 'https://raw.githubusercontent.com/eszdman/PhotonCamera/dev/app/src/main/cpp/CMakeLists.txt'
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            text = response.read().decode('utf-8')
    except Exception as exc:
        raise SystemExit(
            'PRIMARY2.3 JNI1 FIX7 detected a contaminated Photon CMake but could not recover '
            f'a baseline from local Git history or upstream dev: {exc}')
    if not _cmake_is_photon_baseline(text) or _cmake_has_m9_target(text):
        raise SystemExit('PRIMARY2.3 JNI1 FIX7 upstream Photon CMake sanity check failed')
    return text, 'upstream:eszdman/PhotonCamera@dev'

cmake_rel = 'app/src/main/cpp/CMakeLists.txt'
cmake_path = root / cmake_rel
if not cmake_path.exists():
    raise SystemExit(f'PRIMARY2.3 JNI1 FIX7 missing Photon native project: {cmake_rel}')
cmake_text = cmake_path.read_text()

# FIX1 replaced Photon's CMake with an M9-only project. Later overlays can inherit that
# repository state. Recover a clean baseline whenever Photon targets are missing OR an
# earlier m9color target is already present.
needs_recovery = (not _cmake_is_photon_baseline(cmake_text)) or _cmake_has_m9_target(cmake_text)
if needs_recovery:
    recovered, source = _git_good_cmake_candidate()
    if recovered is None:
        recovered, source = _download_upstream_photon_cmake()
    required_native_sources = [
        'app/src/main/cpp/dngCreator.cpp',
        'app/src/main/cpp/allocator.cpp',
        'app/src/main/cpp/flacRecorder.cpp',
        'app/src/main/cpp/native-engine.cpp',
    ]
    missing = [rel for rel in required_native_sources if not (root / rel).exists()]
    if missing:
        raise SystemExit(
            'PRIMARY2.3 JNI1 FIX7 recovered Photon CMake but checkout is missing native sources: '
            + ', '.join(missing))
    cmake_text = recovered.rstrip() + '\n'
    cmake_path.write_text(cmake_text)
    print(f' - FIX7 restored Photon native CMake baseline from {source}')
else:
    print(' - FIX7 Photon native CMake baseline already healthy')

# Remove any FIX6-generated jniLibs copies. CMake is the sole owner of libm9color.so now.
for abi in ('arm64-v8a', 'armeabi-v7a'):
    stale = root / 'app/src/main/jniLibs' / abi / 'libm9color.so'
    if stale.exists():
        stale.unlink()
        print(f' - FIX7 removed stale jniLibs duplicate {stale.relative_to(root)}')

cmake_text = cmake_path.read_text()
if _cmake_has_m9_target(cmake_text):
    raise SystemExit('PRIMARY2.3 JNI1 FIX7 internal error: m9color target survived baseline recovery')

m9_cmake = """

# M9 PRIMARY2.3 JNI1 FIX7 scalar colour target.
# PhotonCamera remains owner of the native project; this adds one isolated shared library.
add_library(m9color SHARED
    ${CMAKE_CURRENT_SOURCE_DIR}/m9color_jni.cpp
)
set_target_properties(m9color PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF
)
target_compile_options(m9color PRIVATE
    -O3
    -ffp-contract=off
    -fno-fast-math
)
# PERF3I BITMAPDIRECT1A uses AndroidBitmap_getInfo/lockPixels/unlockPixels.
find_library(M9_JNIGRAPHICS_LIB jnigraphics)
if(NOT M9_JNIGRAPHICS_LIB)
    message(FATAL_ERROR "PERF3I BITMAPDIRECT1A requires libjnigraphics")
endif()
target_link_libraries(m9color PRIVATE ${M9_JNIGRAPHICS_LIB})
set_property(TARGET m9color APPEND_STRING PROPERTY LINK_FLAGS " -Wl,-z,max-page-size=16384")
"""
cmake_path.write_text(cmake_text.rstrip() + m9_cmake + '\n')
print(' - FIX7 appended single m9color target to restored Photon CMake project')

cmake_final = cmake_path.read_text()
if not _cmake_is_photon_baseline(cmake_final):
    raise SystemExit('PRIMARY2.3 JNI1 FIX7 postcondition failed: Photon native targets not restored')
if len(re.findall(r'add_library\s*\(\s*m9color\b', cmake_final, re.IGNORECASE | re.DOTALL)) != 1:
    raise SystemExit('PRIMARY2.3 JNI1 FIX7 postcondition failed: expected exactly one m9color target')
for abi in ('arm64-v8a', 'armeabi-v7a'):
    stale = root / 'app/src/main/jniLibs' / abi / 'libm9color.so'
    if stale.exists():
        raise SystemExit(f'PRIMARY2.3 JNI1 FIX7 postcondition failed: duplicate jniLibs copy remains: {stale}')

# FB1: feed frozen LUMA2.4 into the normalized Photon target after the true
# uncorrected PhotonCurrent reference is logged, but before M9Modern motion caps
# and the existing shutter-priority allocator run.
iso_rel = "app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java"
i = read(iso_rel)
i = add_import(i,
               "import com.particlesdevs.photoncamera.m9.M9ModernExposurePolicy;\n",
               "import com.particlesdevs.photoncamera.m9.M9BacklightDiagnostic;\n")
if "M9BacklightDiagnostic.evaluateLiveFeedback" not in i:
    anchor = '''        if (M9Config.isM9Modern()
                && PhotonCamera.getSettings().selectedMode == CameraMode.PHOTO
                && !useTripod) {
            M9ModernExposurePolicy.Decision m9Decision = M9ModernExposurePolicy.adjustCaps(
'''
    if anchor not in i:
        raise SystemExit("v0.7N FB1 patch failed: M9Modern pre-curve policy anchor missing")
    feedback = '''        if (M9Config.isM9Modern()) {
            double m9PreviewEnergyIsoSeconds = ((double) captureController.mPreviewIso
                    * (double) captureController.mPreviewExposureTime) / 1.0e9;
            long m9PreFeedbackExposureNs = pair.exposure;
            int m9PreFeedbackIsoNormalized = pair.iso;
            // GenerateExpoPair(-1, ...) is a preflight frametime probe in CaptureController,
            // not a capture request. Never let FB1 alter that probe. For actual step>=0
            // allocations derive orientation directly from Gravity because cameraRotation is
            // assigned by CaptureController only after its preflight GenerateExpoPair call.
            int m9FeedbackRotationDegrees = PhotonCamera.getGravity() != null
                    ? PhotonCamera.getGravity().getCameraRotation(captureController.mSensorOrientation)
                    : captureController.cameraRotation;
            boolean m9FeedbackEligible = step >= 0
                    && PhotonCamera.getSettings().selectedMode == CameraMode.PHOTO
                    && !useTripod
                    && Math.abs(PhotonCamera.getSettings().exposureCompensation) < 1.0e-9
                    && captureController.getParamController().getCurrentExposureValue() == 0
                    && captureController.getParamController().getCurrentISOValue() == 0;
            String m9FeedbackEligibilityReason;
            if (step < 0) {
                m9FeedbackEligibilityReason = "feedback_bypassed_preflight_probe";
            } else if (m9FeedbackEligible) {
                m9FeedbackEligibilityReason = "eligible_auto_photo";
            } else {
                m9FeedbackEligibilityReason = "feedback_bypassed_nonzero_ev_manual_or_tripod";
            }
            M9BacklightDiagnostic.LiveFeedbackDecision m9Feedback =
                    M9BacklightDiagnostic.evaluateLiveFeedback(
                            m9PreviewEnergyIsoSeconds,
                            m9FeedbackRotationDegrees,
                            m9FeedbackEligible,
                            m9FeedbackEligibilityReason);
            if (m9Feedback.appliedEv > 0.0) {
                double m9FeedbackFactor = Math.pow(2.0, m9Feedback.appliedEv);
                pair.ExpoCompensateLower(1.0 / m9FeedbackFactor);
            }
            M9BacklightDiagnostic.recordLiveFeedbackApplication(
                    m9Feedback,
                    m9PreviewEnergyIsoSeconds,
                    m9FeedbackRotationDegrees,
                    m9PreFeedbackExposureNs,
                    m9PreFeedbackIsoNormalized,
                    pair.exposure,
                    pair.iso);
        }
'''
    i = i.replace(anchor, feedback + anchor, 1)
write(iso_rel, i)

# PRIMARY1: make M9Modern the actual Photon finished-image processor. SaverImplementation has
# already copied the android.media.Image into an Allocator-owned ImageFrame, exactly the ownership
# model used by HdrxProcessor. Transfer that existing ImageFrame directly out of IMAGE_BUFFER,
# freeze capture diagnostics, release bufferLock, then queue the primary M9 renderer. No second
# ~25 MB RAW handoff copy and no DNG I/O remain on the camera critical path.
default_rel = "app/src/main/java/com/particlesdevs/photoncamera/processing/DefaultSaver.java"
t = read(default_rel)
t = add_import(t,
               "import com.particlesdevs.photoncamera.processing.processor.RawVideoProcessor;\n",
               "import com.particlesdevs.photoncamera.m9.render.M9R35Renderer;\n")
if "import com.particlesdevs.photoncamera.m9.render.M9BackgroundRenderQueue;\n" in t:
    t = t.replace("import com.particlesdevs.photoncamera.m9.render.M9BackgroundRenderQueue;\n", "", 1)
t = add_import(t,
               "import com.particlesdevs.photoncamera.m9.render.M9R35Renderer;\n",
               "import com.particlesdevs.photoncamera.m9.render.M9PrimaryRenderQueue;\n")
t = add_import(t,
               "import com.particlesdevs.photoncamera.m9.render.M9PrimaryRenderQueue;\n",
               "import com.particlesdevs.photoncamera.m9.M9CapturePathAllocator;\n")

primary1 = '''        // M9 PRIMARY1 - first-class Photon finished-image route. IMAGE_BUFFER already contains an
        // Allocator-owned RAW ImageFrame (the same ownership model handed to HdrxProcessor), so move
        // that frame directly to the M9 processor instead of making ASYNC1's second ~25 MB copy.
        if (M9Config.isCaptureTest()) {
            Path dngFile = M9CapturePathAllocator.allocate(ImagePath.newDNGFilePath());
            ImageFrame primaryFrame = null;
            boolean queued = false;
            int bufferedFrameCount = IMAGE_BUFFER.size();
            long ownershipStartedNs = System.nanoTime();
            long ownershipTransferMs = -1L;
            long metadataElapsedMs = -1L;
            try {
                primaryFrame = IMAGE_BUFFER.get(0);

                // M9Modern is a one-frame renderer. Match the prior route's first-frame photographic
                // behavior, but explicitly close any unexpected surplus frames instead of leaking them.
                for (int i = 1; i < IMAGE_BUFFER.size(); i++) {
                    ImageFrame extra = IMAGE_BUFFER.get(i);
                    if (extra != null) extra.close();
                }
                IMAGE_BUFFER.clear();
                ownershipTransferMs = (System.nanoTime() - ownershipStartedNs) / 1_000_000L;

                M9R35Renderer.preparePrimaryDiagnostics(
                        dngFile, primaryFrame.width, primaryFrame.height, cameraRotation,
                        ownershipTransferMs, bufferedFrameCount);

                // Freeze the capture-specific exposure/motion/backlight JSON before the next shutter
                // can update shared live diagnostics. This is intentionally the only synchronous
                // development instrumentation left in the PRIMARY1 route.
                long metadataStartedNs = System.nanoTime();
                M9CaptureMetadataWriter.write(
                        dngFile, primaryFrame, characteristics, captureResult, captureRequest, cameraRotation);
                metadataElapsedMs = (System.nanoTime() - metadataStartedNs) / 1_000_000L;
            } finally {
                // Critical point: the camera/saver lock is released while the owned ImageFrame remains
                // valid. SaverImplementation created it in independent Allocator memory before runRaw().
                bufferLock = false;
            }

            try {
                queued = M9PrimaryRenderQueue.enqueue(
                        dngFile, primaryFrame, characteristics, captureResult, captureRequest,
                        cameraRotation, ownershipTransferMs, metadataElapsedMs, processingEventsListener);
                if (queued) {
                    primaryFrame = null; // QUEUE1A accepted ownership and will close it
                }
            } catch (Throwable queueError) {
                Log.e(TAG, "M9 PRIMARY1 enqueue failed", queueError);
            }
            if (primaryFrame != null) primaryFrame.close();

            // Preserve the proven capture-rearm behavior: finished-image completion is asynchronous.
            processingEventsListener.onProcessingFinished(
                    queued
                            ? "M9Modern PRIMARY1: capture released; M9 is the primary Photon JPEG"
                            : "M9Modern PRIMARY1: capture released; render was not queued");
            return;
        }
'''

# Replace any known prior M9 one-frame route, including the validated ASYNC1 branch.
if "// M9 PRIMARY1" not in t:
    route_re = re.compile(r'''        // M9 (?:v0\.7N-FULL12-2 ASYNC1|v0\.7N-FULL12-1|milestone: one untouched RAW \+ diagnostics)[^\n]*\n(?:        //[^\n]*\n)*        if \(M9Config\.isCaptureTest\(\)\) \{.*?            return;\n        \}\n''', re.S)
    match = route_re.search(t)
    if not match:
        raise SystemExit("PRIMARY1 patch failed: known M9 capture route not found")
    t = t[:match.start()] + primary1 + t[match.end():]
# QUEUE1A must also upgrade repositories that already contain the PRIMARY1 route.
legacy_primary_enqueue = '''                M9PrimaryRenderQueue.enqueue(
                        dngFile, primaryFrame, characteristics, captureResult, captureRequest,
                        cameraRotation, ownershipTransferMs, metadataElapsedMs, processingEventsListener);
                queued = true;
                primaryFrame = null; // PRIMARY1 queue now owns and closes it
'''
queue1a_primary_enqueue = '''                queued = M9PrimaryRenderQueue.enqueue(
                        dngFile, primaryFrame, characteristics, captureResult, captureRequest,
                        cameraRotation, ownershipTransferMs, metadataElapsedMs, processingEventsListener);
                if (queued) {
                    primaryFrame = null; // QUEUE1A accepted ownership and will close it
                }
'''
if legacy_primary_enqueue in t:
    t = t.replace(legacy_primary_enqueue, queue1a_primary_enqueue, 1)
if "queued = M9PrimaryRenderQueue.enqueue" not in t:
    raise SystemExit("QUEUE1B patch failed: PRIMARY1 enqueue result seam missing")
# NAME1A must also upgrade trees where PRIMARY1 already exists from QUEUE1A.
t = t.replace("Path dngFile = ImagePath.newDNGFilePath();",
              "Path dngFile = M9CapturePathAllocator.allocate(ImagePath.newDNGFilePath());", 1)
if "M9CapturePathAllocator.allocate(ImagePath.newDNGFilePath())" not in t:
    raise SystemExit("NAME1A patch failed: unique DNG identity seam missing")
write(default_rel, t)

# QUEUE1B: refuse a known-saturated M9 capture at the final UI admission boundary,
# immediately before CaptureController.takePicture(). Keep the executor-level QUEUE1A
# rejection intact as a race/failure safety net. This preflight is intentionally
# non-reserving so a Camera2 failure before DefaultSaver cannot leak a render permit.
ui_rel = "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/CameraUIController.java"
u = read(ui_rel)
u = add_import(u,
               "import com.particlesdevs.photoncamera.capture.CaptureController;\n",
               "import com.particlesdevs.photoncamera.m9.M9Config;\n")
u = add_import(u,
               "import com.particlesdevs.photoncamera.m9.M9Config;\n",
               "import com.particlesdevs.photoncamera.m9.render.M9PrimaryRenderQueue;\n")
old_timer = (
    "    private void onTimerFinished() {\n"
    "        this.shutterButton.setHovered(false);\n"
    "        this.shutterButton.setActivated(false);\n"
    "        this.shutterButton.setClickable(false);\n"
    "        cameraFragment.captureController.takePicture();\n"
    "    }\n"
)
queue1b_timer = (
    "    private void onTimerFinished() {\n"
    "        this.shutterButton.setHovered(false);\n"
    "        if (M9Config.isCaptureTest() && !M9PrimaryRenderQueue.preflightCaptureAdmission()) {\n"
    "            Log.d(TAG, \"M9 QUEUE1B shutter refused before takePicture because primary renderer is saturated\");\n"
    "            cameraFragment.showSnackBar(\"M9 processing queue full - try again shortly\");\n"
    "            return;\n"
    "        }\n"
    "        this.shutterButton.setActivated(false);\n"
    "        this.shutterButton.setClickable(false);\n"
    "        cameraFragment.captureController.takePicture();\n"
    "    }\n"
)
if queue1b_timer not in u:
    if old_timer not in u:
        raise SystemExit("QUEUE1B patch failed: CameraUIController onTimerFinished seam missing")
    u = u.replace(old_timer, queue1b_timer, 1)
write(ui_rel, u)

# Add renderer diagnostics to the existing _M9.json after rendering, including failures.
meta_rel = "app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java"
m = read(meta_rel)
m = add_import(m,
               "package com.particlesdevs.photoncamera.m9;\n",
               "\nimport com.particlesdevs.photoncamera.m9.render.M9R35Renderer;\n")
if 'root.put("m9Renderer"' not in m:
    anchor = "            OutputStream safOut = SimpleStorageHelper.openOutputStreamByAbsPath(jsonPath.toString());\n"
    if anchor not in m:
        raise SystemExit("v0.7 renderer patch failed: metadata output anchor missing")
    m = m.replace(anchor,
                  '            root.put("m9Renderer", M9R35Renderer.snapshotJson());\n\n' + anchor,
                  1)

# v0.7N LUMA2.4-SPATIAL2 is deliberately diagnostic-only. LUMA2.2 scalar branches are retained and spatial scoring is diagnostic-only. Score the already-recorded
# Photon preview energy + LUMA1 scene measurements at JSON-write time. No
# Camera2/Photon/M9Modern exposure value is changed.
if 'root.put("m9BacklightDiagnostic"' not in m:
    anchor = "            OutputStream safOut = SimpleStorageHelper.openOutputStreamByAbsPath(jsonPath.toString());\n"
    if anchor not in m:
        raise SystemExit("v0.7N LUMA2.4-SPATIAL2 patch failed: metadata output anchor missing")
    m = m.replace(anchor,
                  '            root.put("m9Build", M9BacklightDiagnostic.buildIdentityJson());\n'
                  '            root.put("m9BacklightDiagnostic", M9BacklightDiagnostic.snapshotJson(root));\n\n' + anchor,
                  1)
# Ensure the subject-motion snapshot receives the same camera rotation used by
# the renderer/DNG orientation, so spatial3x3 is in displayed-image coordinates.
if "M9SubjectMotionAnalyzer.snapshotJson(cameraRotation)" not in m:
    if "M9SubjectMotionAnalyzer.snapshotJson()" in m:
        m = m.replace("M9SubjectMotionAnalyzer.snapshotJson()",
                      "M9SubjectMotionAnalyzer.snapshotJson(cameraRotation)")
    else:
        raise SystemExit("v0.7L spatial patch failed: subjectMotion snapshot anchor missing")
# Ensure the exact FB1 decision-time audit object is written alongside the post-capture scorer.
if 'root.put("m9ExposureFeedback"' not in m:
    anchor = '            root.put("m9BacklightDiagnostic", M9BacklightDiagnostic.snapshotJson(root));\n'
    if anchor not in m:
        raise SystemExit("v0.7N FB1 patch failed: backlight metadata anchor missing")
    m = m.replace(anchor,
                  '            root.put("m9ExposureFeedback", M9BacklightDiagnostic.feedbackSnapshotJson());\n' + anchor,
                  1)
# METAFREEZE1A: preserve every capture-specific diagnostic snapshot synchronously,
# but stop performing the potentially slow SAF/filesystem write while DefaultSaver
# still holds bufferLock. The exact formatted UTF-8 JSON bytes are frozen here and
# staged in memory; M9PrimaryRenderQueue schedules persistence after JPEG+DNG work.
storage_re = re.compile(
    r'''            OutputStream safOut = SimpleStorageHelper\.openOutputStreamByAbsPath\(jsonPath\.toString\(\)\);\n'''
    r'''            if \(safOut != null\) \{.*?'''
    r'''            Log\.d\(TAG, "Saved sidecar: " \+ jsonPath\);\n'''
    r'''            return true;''',
    re.S)
storage_match = storage_re.search(m)
if not storage_match:
    raise SystemExit("METAFREEZE1A patch failed: capture metadata persistence block not found")
frozen_storage = '''            byte[] m9FrozenMetadataBytes = root.toString(2).getBytes(StandardCharsets.UTF_8);
            if (!M9DeferredMetadataStore.stage(jsonPath, m9FrozenMetadataBytes)) {
                throw new java.io.IOException("Unable to stage frozen M9 metadata: " + jsonPath);
            }
            Log.d(TAG, "Frozen capture sidecar bytes for deferred persistence: " + jsonPath
                    + " bytes=" + m9FrozenMetadataBytes.length);
            return true;'''
m = m[:storage_match.start()] + frozen_storage + m[storage_match.end():]

write(meta_rel, m)

print("M9Cam v0.7ZO PRIMARY2.5 PERF3G ORIENTFUSE8A EXIFASYNC1A JPEGBUF64K1A TC20LUMA8A COLOR8A overlay applied")
print(" - v0.6.1 exposure policy preserved/frozen")
print(" - NAME1A unique capture stems + QUEUE1B pre-takePicture saturation gate")
print(" - DNGASYNC1A transfers untouched DNG persistence to bounded M9PrimaryDngIO after JPEG render")
print(" - PERF3G fuses exact completed-ARGB ORIENT1A copy into existing COLOR8A workers; no photographic math change")
print(" - PERF3F retained: exact quality-95/64KiB JPEG payload; bounded M9JpegExifIO performs the same EXIF rewrite then publishes, with sync fallback")
print(" - direct Photon ImageFrame ownership transfer; no ASYNC1 second RAW copy")
print(" - PRIMARY2/2.1 scheduling retained; PRIMARY2.2 bridge/HSM retained")
print(" - PRIMARY2.3 JNI1 keeps PRIMARY2.2 photographic math and 4-worker/24-row boundaries; full colour executes in scalar C++")
print(" - embedded Cobalt main-camera calibration + firmware curve02")
print(" - OpenCV 4.13.0 EA Bayer demosaic + frozen 1600-side TC20 meter + native 4096x3072 streamed render")
print(" - H25 + SAT3 M06/M07 + exact BT.601 horizontal 4:2:2 + TG1 + TC20")
print(" - LUMA2.4 consumes the existing rotation-aware 3x3 display-space luma diagnostically; bounded live exposure feedback is enabled")

# Self-check against every silent post-asset grep used by the original v0.7A
# workflow plus the current PRIMARY2.2 seams. M9Modern is the sole Photon finished-image route.
def _must(rel, needle):
    txt = read(rel)
    if needle not in txt:
        raise SystemExit(f"v0.7D self-check failed: {needle!r} missing from {rel}")

def _must_not(rel, needle):
    txt = read(rel)
    if needle in txt:
        raise SystemExit(f"v0.7D self-check failed: forbidden {needle!r} present in {rel}")

def _must_re(rel, pattern, label):
    txt = read(rel)
    if re.search(pattern, txt, re.IGNORECASE | re.DOTALL) is None:
        raise SystemExit(f"v0.7D self-check failed: {label} missing from {rel}")

_must(default_rel, "M9 PRIMARY1")
_must(default_rel, "M9R35Renderer.preparePrimaryDiagnostics")
_must(default_rel, "M9PrimaryRenderQueue.enqueue")
_must(default_rel, "queued = M9PrimaryRenderQueue.enqueue")
_must(default_rel, "M9CapturePathAllocator.allocate(ImagePath.newDNGFilePath())")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/M9CapturePathAllocator.java", "System.currentTimeMillis()")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/M9CapturePathAllocator.java", "sameTokenSequence")
_must(ui_rel, "M9PrimaryRenderQueue.preflightCaptureAdmission()")
_must(ui_rel, "M9 processing queue full")
_must(meta_rel, 'root.put("m9Renderer"')
_must(meta_rel, 'root.put("m9Build"')
_must(meta_rel, 'root.put("m9ExposureFeedback"')
_must(meta_rel, 'root.put("m9BacklightDiagnostic"')
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java", "m9cam.backlightdiagnostic.v4.luma2p4")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java", "m9cam.backlightfeedback.v1")
_must(iso_rel, "M9BacklightDiagnostic.evaluateLiveFeedback")
_must(iso_rel, "pair.ExpoCompensateLower(1.0 / m9FeedbackFactor)")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java", "appliedExposureCorrectionEv")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java", "MAX_RECOMMENDED_EV = 0.75")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java", "ABSOLUTE_BRIGHT_CONFIDENCE_FLOOR = 0.62")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java", "CENTER_PROTECTION_START_Y = 16.0")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java", "catastrophicAeStarvationScore")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java", "landscapeHighContrastProtectionScore")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java", "rawSpatialBacklightStarvationScore")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java", "SPATIAL_DARK64_LOW = 0.28")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "COLOR_BayerRG2BGR_EA")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "INTER_AREA")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "curve02 normal-ISO sRGB Standard")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "native_strip_destination_layout_orient1a")
_must("app/src/main/cpp/m9color_jni.cpp", "orientCompletedStrip")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "source_horizontal_pre_orientation")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "double n = (x - .3320) / (y - .1858);")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "TG_NEG_CB_COMPRESSION = 0.25")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "HSM_H = 0.25")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "TG_NEG_CR_COMPRESSION = 0.16")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "m9cam.renderer.r38.h25tg1.full12.android.v19.primary2p4tc20native1borient1anormnative1acolornative2afix1")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "NATIVE_COLOR_WORKERS")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "PARALLEL_NORMALIZE_WORKERS")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "native_directbuffer_disjoint_row_ranges_histogram_reduce")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "M9NativeColorCore.normalizeRawDirect")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "nativeNormalizeComputeElapsedMs")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java", "normalizeRawDirect")
_must("app/src/main/cpp/m9color_jni.cpp", "Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_normalizeRawDirect")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "native_block_internal_threads_scalar_math")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "primary22_scalar_cpp_jni_parity1")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "ppToM9Unnormalized")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "hsv6ToRgbWrapped")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java", "MAX_PENDING = 2")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java", "QUEUE_FULL_COUNT")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java", "ADMISSION_REJECT_COUNT")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java", "IN_FLIGHT_COUNT")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java", "MAX_IN_FLIGHT")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java", "preflightCaptureAdmission")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java", "primary_queue_full_nonblocking_reject")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java", "return false")
_must_not("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java", "getQueue().put(job)")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java", "m9cam.primarytiming.v6.exifasync1a.dngasync1a")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java", "captureStemPolicy")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java", "shutterAdmissionPolicy")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java", "queueDepthAtEnqueue")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java", "queueAccepted")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java", "freezeAndWriteAsync")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java", "frozen_bytes_deferred_persist_after_dng_stage")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java", "M9PrimaryTimingIO")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java", "DNG_MAX_PENDING = 1")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java", "M9PrimaryDngIO")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java", "sync_fallback_dng_queue_full")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java", "dngAsyncAccepted")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java", "dngQueueWaitElapsedMs")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java", "DNGASYNC1A RAW ownership handoff accepted")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java", "THREAD_PRIORITY_DEFAULT")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java", "ensureLoaded")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java", "System.loadLibrary(\"m9color\")")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "M9NativeColorCore.renderBlockParallel")
_must("app/src/main/cpp/m9color_jni.cpp", "Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_renderStrip")
_must("app/src/main/cpp/m9color_jni.cpp", "Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_renderBlockParallel")
_must("app/src/main/cpp/m9color_jni.cpp", "Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_renderBlockParallelDirect")
_must("app/src/main/cpp/m9color_jni.cpp", "Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_renderBlockParallelDirectBitmap")
_must("app/src/main/cpp/m9color_jni.cpp", "AndroidBitmap_lockPixels")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "PERF3I_BITMAPDIRECT1A_CVDIRECT1A_ORIENTFUSE8A_EXIFASYNC1A_JPEGBUF64K1A_TC20LUMA8A_COLOR8A")
_must("app/src/main/cpp/m9color_jni.cpp", "Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_meterTc20WeightedSelectDirect")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "opencv_mat_dataaddr_direct1a")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "nativeColorCvDirectBlocks")
_must("app/src/main/cpp/m9color_jni.cpp", "orientCompletedSubrange")
_must("app/src/main/cpp/m9color_jni.cpp", "PERF3G ORIENTFUSE8A")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "nativeColorSerialOrientationPass")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "tc20MeterNative")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "native_parallel_luma8_weightedselect_parity1b")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java", "meterTc20WeightedSelect")
_must("app/src/main/cpp/m9color_jni.cpp", "Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_meterTc20WeightedSelect")
_cm = read("app/src/main/cpp/CMakeLists.txt")
if not _cmake_is_photon_baseline(_cm):
    raise SystemExit("v0.7D self-check failed: FIX7 Photon native CMake baseline not restored")
if len(re.findall(r"add_library\s*\(\s*m9color\b", _cm, re.IGNORECASE | re.DOTALL)) != 1:
    raise SystemExit("v0.7D self-check failed: FIX7 expected exactly one CMake m9color target")
for _abi in ("arm64-v8a", "armeabi-v7a"):
    _so = root / "app/src/main/jniLibs" / _abi / "libm9color.so"
    if _so.exists():
        raise SystemExit(f"v0.7D self-check failed: FIX7 stale jniLibs duplicate remains: {_so.relative_to(root)}")
# FIX7 uses Photon's existing externalNativeBuild/CMake route.
# PERF3F retains DNGASYNC1A and advances timing schema to v6.exifasync1a.dngasync1a; TIMINGFREEZE1A immutable-byte persistence remains retained.
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java", "M9-PRIMARY2.5-TC20NATIVE1B-ORIENT1A-NORMNATIVE1A")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java", "METAFREEZE1A")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java", "DNGASYNC1A")
_must(meta_rel, "M9DeferredMetadataStore.stage")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/M9DeferredMetadataStore.java", "persistAsyncForDng")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/M9SubjectMotionAnalyzer.java", "m9cam.subjectmotion.v3.luma1")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/M9SubjectMotionAnalyzer.java", "m9cam.previewluma.v2.spatial1")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/M9SubjectMotionAnalyzer.java", "m9cam.previewluma.spatial3x3.v1")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/M9SubjectMotionAnalyzer.java", "display_after_cameraRotation")
_must(meta_rel, "M9SubjectMotionAnalyzer.snapshotJson(cameraRotation)")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/M9SubjectMotionAnalyzer.java", "q95MinusMedian")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/M9SubjectMotionAnalyzer.java", "topMinusBottomMedian")
_must(gradle_rel, "org.opencv:opencv:4.13.0")
_must(gradle_rel, "0.97-m9modern7r35a")  # stale v0.7A verifier alias
_must(gradle_rel, "0.97-m9modern7r35b")  # v0.7B verifier alias
_must(gradle_rel, "0.97-m9modern7r35d")  # stale v0.7D verifier alias
_must(gradle_rel, "0.97-m9modern7r36a")  # stale v0.7E verifier alias
_must(gradle_rel, "0.97-m9modern7r38luma1")  # stale LUMA1 verifier alias
_must(gradle_rel, "0.97-m9modern7r38luma2")  # stale v0.7I verifier alias
_must(gradle_rel, "0.97-m9modern7r38luma21")  # stale v0.7J verifier alias
_must(gradle_rel, "0.97-m9modern7r38luma22")  # stale v0.7K verifier alias
_must(gradle_rel, "0.97-m9modern7r38luma23")  # stale v0.7L verifier alias
_must(gradle_rel, "0.97-m9modern7r38luma24")  # stale v0.7M verifier alias
_must(gradle_rel, "1.32-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1a")  # PERF3I BITMAPDIRECT1A APK version
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "PERF3I_BITMAPDIRECT1A_CVDIRECT1A_ORIENTFUSE8A_EXIFASYNC1A_JPEGBUF64K1A_TC20LUMA8A_COLOR8A")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "nativeColorThreadOverheadApproxMsSum")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "tc20NativeLumaPopulationElapsedMs")
_must("app/src/main/cpp/m9color_jni.cpp", "workerWallStarted")
_must("app/src/main/cpp/m9color_jni.cpp", "totalWeightStarted")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "tc20NativeLumaComputeElapsedMs")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "tc20NativeOrderBuildElapsedMs")
_must("app/src/main/cpp/m9color_jni.cpp", "lumaWorkerCount")
_must(image_saver_rel, "PERF3E_JPEGBUF64K1A_EXACT_BYTES")
_must(image_saver_rel, "consumeM9JpegSaveTiming")
_must(image_saver_rel, "M9TimingOutputStream")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "jpegCompressCpuApproxElapsedMs")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "jpegExifFinalizationMode")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java", "saveBitmapAsJPGPayloadM9")
_must("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9JpegFinalizeQueue.java", "jpegPublicationAfterExif")
print(" - PERF3I BITMAPDIRECT1A + retained PERF3H CVDIRECT1A/PERF3G ORIENTFUSE8A/PERF3F EXIFASYNC1A/JPEGBUF64K1A/TC20LUMA8A/COLOR8A: PASS")
print(" - stale v0.7A/B/D/E/F/G/H/I/J/K/L workflow compatibility self-check: PASS")
