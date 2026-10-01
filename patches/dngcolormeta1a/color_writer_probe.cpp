#include "dngCreator.cpp"
#include <fstream>
// Calls the production native class and serializer, including illuminant omission.
int main(int argc,char** argv) {
    if(argc!=3) return 2;
    DngCreator creator;
    creator.setMake("Probe"); creator.setModel("Synthetic");
    creator.setUniqueCameraModel("Synthetic colour calibration probe");
    creator.setSoftware("M9DNGCOLORMETA1A host native probe");
    creator.setOrientation(1); creator.setCFAPattern(0); creator.setWhiteLevel(1023);
    unsigned short black[4]={64,64,64,64}; creator.setBlackLevel(black);
    creator.setCalibrationIlluminant2(0);
    std::ifstream input(argv[1]);int tag,n;
    while(input>>tag>>n) {
        if(n<1||n>9)return 3;double a[9]={0};
        for(int i=0;i<n;i++) if(!(input>>a[i]))return 4;
        switch(tag) {
            case 50778:creator.setCalibrationIlluminant1(a[0]);break;
            case 50779:creator.setCalibrationIlluminant2(a[0]);break;
            case 50721:creator.setColorMatrix1(a);break;
            case 50722:creator.setColorMatrix2(a);break;
            case 50723:creator.setCameraCalibration1(a);break;
            case 50724:creator.setCameraCalibration2(a);break;
            case 50964:creator.setForwardMatrix1(a);break;
            case 50965:creator.setForwardMatrix2(a);break;
            case 50728:creator.setAsShotNeutral(a);break;
            default:return 5;
        }
    }
    std::vector<unsigned short> raw(66*34);
    for(size_t i=0;i<raw.size();i++)raw[i]=64+(i*7)%960;
    const auto before=raw;
    size_t size=0;void* bytes=creator.createDng(raw.data(),66,34,size);
    if(!bytes||before!=raw)return 6;
    std::ofstream output(argv[2],std::ios::binary);output.write((const char*)bytes,size);
    free(bytes);return output?0:7;
}
