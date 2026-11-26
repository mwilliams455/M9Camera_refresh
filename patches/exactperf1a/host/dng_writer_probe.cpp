// EXACTPERF1A host probe: drive the production dngCreator.cpp DngCreator exactly as the
// M9 DNG path does (RAW16, uncompressed, physical metadata, gain map, noise profile,
// baseline exposure) and write the DNG bytes. Built at -O0 and -O2 to prove the
// optimization level does not change the file.
#include "dngCreator.cpp"
#include <fstream>
#include <random>

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    const std::string out(argv[1]);
    const int sizes[3][2] = {{4096, 3072}, {642, 481}, {66, 34}};
    for (int k = 0; k < 4; ++k) {
        const int w = sizes[k % 3][0], h = sizes[k % 3][1];
        DngCreator c;
        c.setBitsPerSample(16);
        c.setCompression(false);
        c.setWhiteLevel(k == 3 ? 65535.0 : 1023.0);
        const unsigned short black[4] = {64, 65, 64, 63};
        c.setBlackLevel(black);
        const double cm1[9] = {0.8123, -0.2071, 0.1093, -0.1189, 1.1031, 0.1502, 0.0517, 0.1009, 0.7013};
        const double cm2[9] = {0.7712, -0.1913, 0.0855, -0.1499, 1.0507, 0.1206, 0.0601, 0.0904, 0.6631};
        const double fm1[9] = {0.6011, 0.3019, 0.0642, 0.2003, 0.7007, 0.0990, 0.0201, 0.1002, 0.7049};
        const double cc[9] = {1.0123, 0, 0, 0, 1, 0, 0, 0, 0.9877};
        c.setColorMatrix1(cm1); c.setColorMatrix2(cm2);
        c.setForwardMatrix1(fm1); c.setForwardMatrix2(fm1);
        c.setCameraCalibration1(cc); c.setCameraCalibration2(cc);
        const double neutral[3] = {0.4931, 1.0, 0.6123};
        c.setAsShotNeutral(neutral);
        const double analog[3] = {1, 1, 1};
        c.setAnalogBalance(analog);
        c.setCalibrationIlluminant1(17); c.setCalibrationIlluminant2(21);
        c.setUniqueCameraModel("Synthetic M9 probe");
        c.setDescription("EXACTPERF1A host probe");
        c.setSoftware("3.43-exactperf1a");
        c.setIso(static_cast<unsigned short>(100 + 37 * k));
        c.setExposureTime(1.0 / (60.0 + k));
        if (!c.setBaselineExposure(-0.5)) return 3;
        c.setAperture(1.8); c.setFocalLength(6.9);
        c.setMake("Probe"); c.setModel("Synthetic");
        c.setDateTime("2026:11:26 12:00:0" + std::to_string(k));
        const double noise[8] = {2.1e-4, 1.9e-6, 1.6e-4, 1.5e-6, 1.7e-4, 1.6e-6, 2.3e-4, 2.2e-6};
        c.setNoiseProfile(noise, 8);
        c.setCFAPattern(k);
        const int gw = 17, gh = 13;
        std::vector<float> gain(size_t(gw) * gh * 4);
        for (int y = 0; y < gh; ++y) for (int x = 0; x < gw; ++x) for (int p = 0; p < 4; ++p) {
            const double dx = (x - 8) / 8.0, dy = (y - 6) / 6.0;
            gain[(size_t(y) * gw + x) * 4 + p] = float((1 + 1.3 * (dx * dx + dy * dy)) * (p == 0 ? 1.04 : p == 3 ? 1.07 : 1.0));
        }
        c.setGainMap(gain.data(), 0, 0, w, h, gw, gh);
        std::vector<uint16_t> raw(size_t(w) * h);
        std::mt19937 rng(1000 + k);
        for (auto& v : raw) v = uint16_t(rng() % (k == 3 ? 65536u : 1024u));
        size_t size = 0;
        void* bytes = c.createDng(raw.data(), w, h, size);
        if (!bytes || size == 0) return 4;
        std::ofstream f(out + "/probe" + std::to_string(k) + ".dng", std::ios::binary);
        f.write(static_cast<const char*>(bytes), std::streamsize(size));
        free(bytes);
    }
    return 0;
}
