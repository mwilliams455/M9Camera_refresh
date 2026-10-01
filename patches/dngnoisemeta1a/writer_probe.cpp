#define TINY_DNG_WRITER_IMPLEMENTATION
#include "tiny_dng_writer.h"
#include <fstream>
#include <limits>

// Exercise the production serializer without Android/JNI or private fixtures.
int main(int argc, char** argv) {
  if (argc != 2) return 2;
  const std::string out(argv[1]);
  for (int k = 0; k < 4; ++k) {
    tinydngwriter::DNGImage im;
    im.SetBigEndian(false);
    im.SetSubfileType(false, false, false);
    im.SetSamplesPerPixel(1);
    const unsigned short bits = 16;
    im.SetBitsPerSample(1, &bits);
    im.SetPhotometric(tinydngwriter::PHOTOMETRIC_CFA);
    im.SetPlanarConfig(tinydngwriter::PLANARCONFIG_CONTIG);
    im.SetDNGVersion(1, 3, 0, 0);
    im.SetImageDescription(std::string(5 + k, 'x'));
    im.SetMake("Probe");
    im.SetModel("Synthetic");
    im.SetUniqueCameraModel("Synthetic DNG writer probe");
    im.SetSoftware("M9DNGNOISEMETA1A host probe");
    im.SetImageWidth(66); im.SetImageLength(34); im.SetRowsPerStrip(34);
    unsigned int active[4] = {0, 0, 34, 66}; im.SetActiveArea(active);
    im.SetBlackLevelRepeatDim(2, 2);
    const unsigned short blacks[4] = {64, 65, 66, 67};
    im.SetBlackLevel(4, blacks);
    const double ev[4] = {-0.5, 0.0, 0.5, -1.5};
    if (!im.SetBaselineExposure(ev[k])) return 8;
    double white = 65535;
    if (!im.SetWhiteLevelRational(1, &white)) return 3;
    im.SetCFARepeatPatternDim(2, 2);
    const unsigned char cfa[4][4] = {{0,1,1,2},{1,0,2,1},{1,2,0,1},{2,1,1,0}};
    im.SetCFAPattern(4, cfa[k]);
    double cm[9] = {1,0,0,0,1,0,0,0,1}, neutral[3] = {0.5,1,0.75};
    im.SetColorMatrix1(3, cm); im.SetAsShotNeutral(3, neutral);
    im.SetCalibrationIlluminant1(21);
    const double noise[6] = {0.01,0.001,0.03,0.002,0.04,0.003};
    if (!im.SetNoiseProfile(3, noise)) return 10;
    float grid[6] = {1,1.5f,2,1,1.5f,2};
    std::vector<tinydngwriter::GainMap> maps;
    maps.emplace_back(grid, 3, 2, 0, 0, 66, 34);
    im.SetGainMap(maps);
    std::vector<unsigned short> pixels(66*34);
    for (size_t i=0; i<pixels.size(); ++i) pixels[i] = (i*73u + k*123u) & 65535u;
    im.SetImageData(reinterpret_cast<const unsigned char*>(pixels.data()), pixels.size()*2);
    tinydngwriter::DNGWriter writer(false); writer.AddImage(&im);
    size_t size=0; std::string error;
    void* bytes=writer.WriteToMemory(&size, &error);
    if (!bytes) return 4;
    std::ofstream f(out + "/cfa" + std::to_string(k) + ".dng", std::ios::binary);
    f.write(static_cast<const char*>(bytes), size); free(bytes);
  }
  // Odd byte counts exercise IFD alignment and multi-image offsets.
  tinydngwriter::DNGWriter writer(false);
  tinydngwriter::DNGImage odd[2];
  for (int k=0;k<2;++k) {
    odd[k].SetBigEndian(false); odd[k].SetSamplesPerPixel(1);
    const unsigned short bits=8; odd[k].SetBitsPerSample(1,&bits);
    odd[k].SetImageWidth(3); odd[k].SetImageLength(3); odd[k].SetRowsPerStrip(3);
    odd[k].SetImageDescription("ABCD");
    unsigned char pixels[9]={0,1,2,3,4,5,6,7,8};
    odd[k].SetImageData(pixels,9); writer.AddImage(&odd[k]);
  }
  size_t size=0; std::string error; void* bytes=writer.WriteToMemory(&size,&error);
  if (!bytes) return 5;
  std::ofstream f(out + "/odd_multi.tif",std::ios::binary);
  f.write(static_cast<const char*>(bytes),size); free(bytes);
#ifdef CHECK_INVALID_WHITE
  tinydngwriter::DNGImage bad; bad.SetSamplesPerPixel(1);
  const double values[]={-1,1.5,4294967296.0,std::numeric_limits<double>::infinity(),
                        std::numeric_limits<double>::quiet_NaN()};
  for(double value:values) if(bad.SetWhiteLevelRational(1,&value)) return 6;
  double valid=1023;
  if(bad.SetWhiteLevelRational(0,&valid) || bad.SetWhiteLevelRational(1,nullptr)) return 7;
#endif
  tinydngwriter::DNGImage baselineBad;
  for (double ev : {-17.0, 17.0, std::numeric_limits<double>::infinity(), std::numeric_limits<double>::quiet_NaN()})
    if (baselineBad.SetBaselineExposure(ev)) return 9;
  return 0;
}
