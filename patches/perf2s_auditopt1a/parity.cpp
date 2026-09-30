#include "m9color_jni.cpp"
#include <fstream>
#include <iostream>
#include <stdexcept>

// Compile the unchanged production native implementation. Synthetic inputs only.
static bool sameContext(const ColorContext& a, const ColorContext& b) {
    return a.cw==b.cw && a.camToPp==b.camToPp && a.hsm==b.hsm &&
        a.ppToM9==b.ppToM9 && a.adapt50To65==b.adapt50To65 &&
        a.ppToXyz==b.ppToXyz && a.xyz2Srgb==b.xyz2Srgb && a.curve==b.curve &&
        a.hueDivisions==b.hueDivisions && a.satDivisions==b.satDivisions &&
        a.skyChromaMode1A==b.skyChromaMode1A && a.colourTrialPrepared==b.colourTrialPrepared;
}
static void require(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}
int main(int argc, char** argv) {
    try {
        require(argc==2, "Expected curve02 firmware asset path");
        ColorContext base;
        base.cw={1.8,1.,1.3};
        base.camToPp={.80,.15,.05,.08,.86,.06,.02,.08,.90};
        base.ppToM9={1.1,-.06,-.04,-.03,1.07,-.04,-.01,-.08,1.09};
        base.adapt50To65={.9556,-.023,.0632,-.0283,1.0099,.021,.0123,-.0205,1.3299};
        base.ppToXyz={.7977,.1352,.0313,.288,.7119,.0001,0.,0.,.8252};
        base.xyz2Srgb={3.2406,-1.5372,-.4986,-.9689,1.8758,.0415,.0557,-.204,1.057};
        base.hueDivisions=6; base.satDivisions=3;
        for (int h=0;h<6;h++) for(int s=0;s<3;s++) {
            base.hsm.push_back((h-3)*1.25);
            base.hsm.push_back(.92+s*.04);
            base.hsm.push_back(1.-s*.015);
        }
        base.skyChromaMode1A=9; // Actual production firmware Standard SAT2.
        std::ifstream curve(argv[1],std::ios::binary);
        curve.read(reinterpret_cast<char*>(base.curve.data()),base.curve.size());
        require(curve.gcount()==2048,"Wrong curve02 asset size");
        struct Case {int w,h;double gain,cb,cr;bool prepared;};
        const Case cases[]={{1,1,.5,1,1,true},{31,19,1,1,1,false},
            {257,263,2.5,.96,.98,true},{512,385,1.37,1,1,true},
            {4096,3072,1.37,1,1,true}};
        std::cout << "{\"status\":\"passed\",\"fixture\":\"deterministic_synthetic_camera_RGB16\",\"cases\":[";
        int id=0;
        for (const auto& c:cases) {
            const int n=c.w*c.h;
            std::vector<jshort> input(size_t(n)*3);
            uint32_t state=0x913ac7u;
            for (size_t i=0;i<input.size();i++) {
                state=1664525u*state+1013904223u;
                input[i]=static_cast<jshort>(state>>16);
            }
            // Include exact black, white, primaries and neutral ramp, not only noise.
            for(int p=0;p<std::min(n,512);p++) {
                uint16_t value=uint16_t((uint32_t(p)*65535u)/511u);
                for(int ch=0;ch<3;ch++) input[3*p+ch]=static_cast<jshort>(value);
            }
            if(n>515) for(int p=512;p<515;p++) for(int ch=0;ch<3;ch++)
                input[3*p+ch]=static_cast<jshort>(ch==p-512?65535:0);
            auto audited=input, skipped=input;
            ColorContext on=base,off=base;
            const auto audit=auditSatDomainJson(on,audited.data(),n,c.w,c.h,c.gain);
            require(!audit.empty(),"Audit did not produce diagnostics");
            require(audited==input,"Audit mutated image input");
            require(sameContext(on,base),"Audit mutated colour context");
            if(c.prepared) {
                require(trialPrepareInPlace(on,audited.data(),c.w,c.h,c.gain)==0,"Audited preparation failed");
                require(trialPrepareInPlace(off,skipped.data(),c.w,c.h,c.gain)==0,"Skipped preparation failed");
                require(audited==skipped,"Prepared RGB differs");
                on.colourTrialPrepared=off.colourTrialPrepared=true;
            }
            std::vector<jint> a(n),b(n);
            int64_t sa[12]{},sb[12]{};
            const double gain=c.prepared?1.:c.gain;
            renderStripScalar(on,audited.data(),n,c.w,a.data(),gain,c.cb,c.cr,sa);
            renderStripScalar(off,skipped.data(),n,c.w,b.data(),gain,c.cb,c.cr,sb);
            require(a==b,"Rendered ARGB pixels differ");
            require(std::equal(std::begin(sa),std::end(sa),std::begin(sb)),"Render statistics differ");
            if(id++) std::cout << ',';
            std::cout << "{\"width\":"<<c.w<<",\"height\":"<<c.h
                <<",\"gain\":"<<c.gain<<",\"productionChromaPreparation\":"<<(c.prepared?"true":"false")
                <<",\"inputAndContextUnchanged\":true,\"changedOutputPixels\":0}";
        }
        std::cout << "]}\n";
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
