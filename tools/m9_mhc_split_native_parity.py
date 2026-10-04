#!/usr/bin/env python3
"""Compile the exact assembled MHC helper bodies and prove split-vs-monolithic parity.

This is a stronger gate than the Python oracle because the tested functions are
extracted verbatim from assembled m9color_jni.cpp and executed as C++ with the
same std::llround/type behavior. Leica Sharpness remains disabled.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import tempfile


def extract_function(src: str, marker: str) -> str:
    st = src.find(marker)
    if st < 0:
        raise SystemExit(f"missing marker: {marker}")
    br = src.find("{", st)
    if br < 0:
        raise SystemExit(f"missing opening brace: {marker}")
    depth = 0
    for i in range(br, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[st:i + 1]
    raise SystemExit(f"unterminated function: {marker}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    src = args.source.read_text()

    markers = [
        "inline uint16_t u16(jshort v)",
        "inline int mhcClampCoord(int v, int hi)",
        "inline double mhcNAt(const jshort* raw,int w,int h,int y,int x,double ir,double ig,double ib)",
        "inline uint16_t mhcND(double v)",
        "inline void mhcPixelNeutralRggb(const jshort* raw,int w,int h,int y,int x,uint16_t* rgb,double nr,double nb,double ir,double ib)",
        "inline uint16_t mhcNeutralGreenRggb(const jshort* raw,int w,int h,int y,int x,",
        "inline void mhcPixelNeutralRbCompleteRggb(const jshort* raw,int w,int h,int y,int x,",
    ]
    funcs = [extract_function(src, m) for m in markers]
    fragment = "\n\n".join(funcs) + "\n"
    fragment_sha = hashlib.sha256(fragment.encode()).hexdigest()

    harness = r'''
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>
using jshort = int16_t;
''' + fragment + r'''
static uint32_t xs=0x4D394D48u;
static uint16_t rnd16(){ xs^=xs<<13; xs^=xs>>17; xs^=xs<<5; return static_cast<uint16_t>(xs & 0xffffu); }
static std::vector<uint16_t> fixture(int id,int w,int h){
    std::vector<uint16_t> a(static_cast<size_t>(w)*h);
    for(int y=0;y<h;++y) for(int x=0;x<w;++x){
        uint16_t v=0;
        if(id==0) v=rnd16();
        else if(id==1) v=static_cast<uint16_t>((((uint32_t)x*65535u)/(w-1) + (uint32_t)y*257u)&0xffffu);
        else if(id==2) v=(((x/2+y/2)&1)?65535u:0u);
        else if(id==3) v=(x==w/2 && y==h/2)?65535u:0u;
        else v=(x>=w/2)?65535u:((y>=h/2)?16383u:0u);
        a[static_cast<size_t>(y)*w+x]=v;
    }
    return a;
}
int main(){
    const int w=37,h=31;
    const double ns[4][2]={{1.0,1.0},{0.70,1.30},{1.80,0.60},{0.253,0.914}};
    int cases=0; unsigned long long samples=0;
    for(int f=0;f<5;++f){
        auto u=fixture(f,w,h); std::vector<jshort> raw(u.size());
        for(size_t i=0;i<u.size();++i) raw[i]=static_cast<jshort>(u[i]);
        for(auto &n:ns){
            double nr=n[0],nb=n[1],ir=1.0/nr,ib=1.0/nb;
            std::vector<uint16_t> mono(u.size()*3), split(u.size()*3), green(u.size());
            for(int y=0;y<h;++y) for(int x=0;x<w;++x){
                size_t p=(size_t)y*w+x;
                mhcPixelNeutralRggb(raw.data(),w,h,y,x,mono.data()+p*3,nr,nb,ir,ib);
                green[p]=mhcNeutralGreenRggb(raw.data(),w,h,y,x,ir,ib);
            }
            for(int y=0;y<h;++y) for(int x=0;x<w;++x){
                size_t p=(size_t)y*w+x;
                mhcPixelNeutralRbCompleteRggb(raw.data(),w,h,y,x,green[p],split.data()+p*3,nr,nb,ir,ib);
            }
            for(size_t i=0;i<mono.size();++i){
                if(mono[i]!=split[i]){
                    size_t p=i/3;
                    std::cerr<<"FAIL fixture="<<f<<" nr="<<nr<<" nb="<<nb
                             <<" y="<<(p/w)<<" x="<<(p%w)<<" ch="<<(i%3)
                             <<" mono="<<mono[i]<<" split="<<split[i]<<"\n";
                    return 2;
                }
            }
            ++cases; samples+=mono.size();
        }
    }
    std::cout<<"PASS cases="<<cases<<" rgb_samples="<<samples<<"\n";
    return 0;
}
'''

    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        cpp = td / "m9_split_native_parity.cpp"
        exe = td / "m9_split_native_parity"
        cpp.write_text(harness)
        cmd = ["g++", "-std=c++17", "-O2", "-fno-fast-math", "-Wall", "-Wextra", str(cpp), "-o", str(exe)]
        comp = subprocess.run(cmd, text=True, capture_output=True)
        if comp.returncode:
            raise SystemExit("compile failed\n" + comp.stdout + comp.stderr)
        run = subprocess.run([str(exe)], text=True, capture_output=True)
        if run.returncode:
            raise SystemExit("native parity failed\n" + run.stdout + run.stderr)

    report = {
        "schema": "m9.mhc-split-native-parity.v1",
        "source": str(args.source),
        "extracted_fragment_sha256": fragment_sha,
        "compiler": "g++ -std=c++17 -O2 -fno-fast-math",
        "cases": 20,
        "width": 37,
        "height": 31,
        "rgb_samples_compared": 20 * 37 * 31 * 3,
        "all_pixel_exact": True,
        "sharpness_applied": False,
        "stdout": run.stdout.strip(),
        "note": "Compiled from exact assembled C++ helper bodies; closes host-native C++ split parity with Sharp disabled.",
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
