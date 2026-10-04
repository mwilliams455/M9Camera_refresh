// COLORPERF1A PERSISTENTBLOCKS: one worker team + one Bitmap lock for the full
// frame, while retaining the exact 384-row bounded scratch model and frozen
// renderStripScalar / orientation mapping.
//
// This is append-only relative to PERF3I. The Java caller falls back to the
// retained PERF3I block loop if validation or Bitmap locking fails before any
// pixel write. No colour arithmetic, pair order, BT.601 pairing, TG1, SAT2,
// curve02, rotation mapping, block size or worker count changes.

class M9ColorReusableBarrier {
public:
    explicit M9ColorReusableBarrier(int count) : count_(count) {}
    void wait() {
        std::unique_lock<std::mutex> lock(mutex_);
        const int generation = generation_;
        if (++waiting_ == count_) {
            waiting_ = 0;
            ++generation_;
            cv_.notify_all();
        } else {
            cv_.wait(lock, [&] { return generation_ != generation; });
        }
    }
private:
    std::mutex mutex_;
    std::condition_variable cv_;
    int count_;
    int waiting_ = 0;
    int generation_ = 0;
};

// Pure core used by both the production JNI wrapper and host parity tests.
// outStats keeps PERF3I's 12-slot meanings. In particular slot 8 remains the
// SUM of the slowest worker's render+orientation time for each 384-row block,
// so existing diagnostics remain comparable.
static int renderFramePersistentCoreExact(
        const ColorContext& ctx,
        const jshort* camBase,
        int width,
        int sourceHeight,
        uint8_t* bitmapBase,
        uint32_t bitmapStride,
        int blockRows,
        double gain,
        double tgCbGain,
        double tgCrGain,
        int cameraRotation,
        int workers,
        std::array<int64_t,12>& outStats) {
    if (!camBase || !bitmapBase || width <= 0 || sourceHeight <= 0
            || blockRows <= 0 || workers <= 0) return -1;

    const auto nativeStarted = std::chrono::steady_clock::now();
    const int boundedRows = std::min(blockRows, sourceHeight);
    const int workerCount = std::max(1, std::min(workers, boundedRows));
    const size_t maxBlockPixels = static_cast<size_t>(width) * static_cast<size_t>(boundedRows);

    thread_local std::vector<jint> argbScratch;
    const auto scratchStarted = std::chrono::steady_clock::now();
    argbScratch.resize(maxBlockPixels);
    const auto scratchEnded = std::chrono::steady_clock::now();

    std::vector<std::array<int64_t, 3>> workerStats(static_cast<size_t>(workerCount));
    std::vector<int64_t> renderElapsedNs(static_cast<size_t>(workerCount), 0);
    std::vector<int64_t> orientationElapsedNs(static_cast<size_t>(workerCount), 0);
    std::vector<int64_t> blockCombinedNs(static_cast<size_t>(workerCount), 0);
    std::vector<std::thread> threads;
    threads.reserve(static_cast<size_t>(workerCount));
    M9ColorReusableBarrier blockDone(workerCount);
    M9ColorReusableBarrier blockStatsConsumed(workerCount);

    jint* const argbBase = argbScratch.data();
    int64_t blockMaxNsSum = 0;
    const auto workerWallStarted = std::chrono::steady_clock::now();

    for (int worker = 0; worker < workerCount; ++worker) {
        threads.emplace_back([&, worker, camBase, argbBase, bitmapBase]() {
            std::array<int64_t, 3> totals{0, 0, 0};
            int64_t renderNs = 0;
            int64_t orientNs = 0;

            for (int blockY0 = 0; blockY0 < sourceHeight; blockY0 += blockRows) {
                const int rows = std::min(blockRows, sourceHeight - blockY0);
                const int y0 = (rows * worker) / workerCount;
                const int y1 = (rows * (worker + 1)) / workerCount;
                const auto combinedStarted = std::chrono::steady_clock::now();

                if (y1 > y0) {
                    const int localRows = y1 - y0;
                    const int localPixels = localRows * width;
                    const size_t localPixelOffset =
                            static_cast<size_t>(y0) * static_cast<size_t>(width);
                    const size_t sourcePixelOffset =
                            static_cast<size_t>(blockY0 + y0) * static_cast<size_t>(width);
                    const size_t camOffset = sourcePixelOffset * 3u;
                    std::array<int64_t, 3> local{0, 0, 0};

                    const auto renderStarted = std::chrono::steady_clock::now();
                    renderStripScalar(ctx,
                                      camBase + camOffset,
                                      localPixels,
                                      width,
                                      argbBase + localPixelOffset,
                                      gain, tgCbGain, tgCrGain,
                                      local.data());
                    const auto renderEnded = std::chrono::steady_clock::now();

                    writeCompletedSubrangeToBitmap(argbBase, bitmapBase, bitmapStride,
                                                   rows, width, blockY0, sourceHeight,
                                                   y0, y1, cameraRotation);
                    const auto orientEnded = std::chrono::steady_clock::now();

                    totals[0] += local[0];
                    totals[1] += local[1];
                    totals[2] += local[2];
                    renderNs += static_cast<int64_t>(
                            std::chrono::duration_cast<std::chrono::nanoseconds>(
                                    renderEnded - renderStarted).count());
                    orientNs += static_cast<int64_t>(
                            std::chrono::duration_cast<std::chrono::nanoseconds>(
                                    orientEnded - renderEnded).count());
                }

                blockCombinedNs[static_cast<size_t>(worker)] = static_cast<int64_t>(
                        std::chrono::duration_cast<std::chrono::nanoseconds>(
                                std::chrono::steady_clock::now() - combinedStarted).count());

                // Scratch is block-local. Do not let any worker start the next block
                // until every destination copy is complete and worker 0 has consumed
                // the per-block max statistic.
                blockDone.wait();
                if (worker == 0) {
                    int64_t blockMax = 0;
                    for (int ww = 0; ww < workerCount; ++ww) {
                        blockMax = std::max(blockMax, blockCombinedNs[static_cast<size_t>(ww)]);
                    }
                    blockMaxNsSum += blockMax;
                }
                blockStatsConsumed.wait();
            }

            workerStats[static_cast<size_t>(worker)] = totals;
            renderElapsedNs[static_cast<size_t>(worker)] = renderNs;
            orientationElapsedNs[static_cast<size_t>(worker)] = orientNs;
        });
    }
    for (auto& thread : threads) thread.join();
    const auto workerWallEnded = std::chrono::steady_clock::now();

    int64_t even = 0;
    int64_t edge = 0;
    int64_t nearWhite = 0;
    int64_t workerNsSum = 0;
    int64_t orientationNsSum = 0;
    for (int worker = 0; worker < workerCount; ++worker) {
        const auto& local = workerStats[static_cast<size_t>(worker)];
        even += local[0];
        edge += local[1];
        nearWhite += local[2];
        workerNsSum += renderElapsedNs[static_cast<size_t>(worker)];
        orientationNsSum += orientationElapsedNs[static_cast<size_t>(worker)];
    }

    const auto nativeEnded = std::chrono::steady_clock::now();
    outStats = {
            even,
            edge,
            nearWhite,
            workerNsSum,
            workerCount,
            static_cast<int64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                    scratchEnded - scratchStarted).count()),
            0,
            static_cast<int64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                    workerWallEnded - workerWallStarted).count()),
            blockMaxNsSum,
            orientationNsSum,
            0,
            static_cast<int64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                    nativeEnded - nativeStarted).count())
    };
    return 0;
}

extern "C" JNIEXPORT jboolean JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_renderFramePersistentDirectBitmap(
        JNIEnv* env, jclass,
        jlong handle,
        jlong camAddress,
        jint width,
        jint sourceHeight,
        jobject bitmap,
        jint blockRows,
        jdouble gain,
        jdouble tgCbGain,
        jdouble tgCrGain,
        jint cameraRotation,
        jint workers,
        jlongArray statsArray) {
    auto* ctx = reinterpret_cast<ColorContext*>(handle);
    const auto* camBase = reinterpret_cast<const jshort*>(static_cast<uintptr_t>(camAddress));
    if (!ctx || !camBase || !bitmap || !statsArray || width <= 0 || sourceHeight <= 0
            || blockRows <= 0 || workers <= 0
            || (static_cast<uintptr_t>(camAddress) & (alignof(jshort) - 1u)) != 0u
            || env->GetArrayLength(statsArray) < 12) {
        return JNI_FALSE;
    }

    int rotation = cameraRotation % 360;
    if (rotation < 0) rotation += 360;
    const uint32_t expectedWidth = static_cast<uint32_t>(
            (rotation == 90 || rotation == 270) ? sourceHeight : width);
    const uint32_t expectedHeight = static_cast<uint32_t>(
            (rotation == 90 || rotation == 270) ? width : sourceHeight);

    AndroidBitmapInfo info{};
    if (AndroidBitmap_getInfo(env, bitmap, &info) != ANDROID_BITMAP_RESULT_SUCCESS
            || info.format != ANDROID_BITMAP_FORMAT_RGBA_8888
            || info.width != expectedWidth
            || info.height != expectedHeight
            || info.stride < expectedWidth * 4u) {
        return JNI_FALSE;
    }

    void* rawPixels = nullptr;
    if (AndroidBitmap_lockPixels(env, bitmap, &rawPixels) != ANDROID_BITMAP_RESULT_SUCCESS
            || rawPixels == nullptr) {
        return JNI_FALSE;
    }

    std::array<int64_t,12> stats{};
    const int rc = renderFramePersistentCoreExact(
            *ctx, camBase, width, sourceHeight, static_cast<uint8_t*>(rawPixels),
            info.stride, blockRows, gain, tgCbGain, tgCrGain,
            cameraRotation, workers, stats);

    const int unlockResult = AndroidBitmap_unlockPixels(env, bitmap);
    if (rc != 0 || unlockResult != ANDROID_BITMAP_RESULT_SUCCESS) {
        if (unlockResult != ANDROID_BITMAP_RESULT_SUCCESS) {
            throwIllegalArgument(env, "M9 COLORPERF1A could not unlock direct Bitmap");
        }
        return JNI_FALSE;
    }

    jlong jstats[12];
    for (int i = 0; i < 12; ++i) jstats[i] = static_cast<jlong>(stats[static_cast<size_t>(i)]);
    env->SetLongArrayRegion(statsArray, 0, 12, jstats);
    return env->ExceptionCheck() ? JNI_FALSE : JNI_TRUE;
}

extern "C" const char* m9_colorperf1a_revision() {
    return "M9COLORPERF1A_PERSISTENTBLOCKS_EXACT";
}
