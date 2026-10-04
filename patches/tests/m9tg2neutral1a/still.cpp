#include <cassert>
#include <cmath>
#include <iostream>
#include "../../m9tg2neutral1a/m9tg2_chroma.h"

static double mag(double cb,double cr){return std::sqrt(cb*cb+cr*cr);}
int main(){
    size_t n=0;
    auto check=[&](bool v){++n;if(!v)std::abort();};

    // Weight zero must be exact identity.
    for(double cb=-120;cb<=120;cb+=8)for(double cr=-120;cr<=120;cr+=8){
        auto o=m9Tg2NeutralChroma1A(cb,cr,0.0);
        check(o.cb==cb && o.cr==cr);
    }

    // Warm low/moderate chroma: yellow/orange residual must contract.
    for(auto p: {M9Tg2Chroma1A{-24,10},M9Tg2Chroma1A{-30,18},M9Tg2Chroma1A{-34,24}}){
        auto o=m9Tg2NeutralChroma1A(p.cb,p.cr,1.0);
        check(mag(o.cb,o.cr) < .78*mag(p.cb,p.cr));
        check(std::abs(o.cb) < std::abs(p.cb));
        check(o.cr < p.cr);
    }

    // Strong warm subject colour is protected by chroma gate.
    for(auto p: {M9Tg2Chroma1A{-75,45},M9Tg2Chroma1A{-95,55},M9Tg2Chroma1A{-70,5}}){
        auto o=m9Tg2NeutralChroma1A(p.cb,p.cr,1.0);
        check(mag(o.cb,o.cr) >= .76*mag(p.cb,p.cr));
    }

    // Blue/cyan axis is never treated as tungsten yellow.
    for(auto p: {M9Tg2Chroma1A{20,0},M9Tg2Chroma1A{60,15},M9Tg2Chroma1A{80,-20}}){
        auto o=m9Tg2NeutralChroma1A(p.cb,p.cr,1.0);
        check(o.cb==p.cb);
    }

    // Positive Cr alone (pure red axis without yellow component) is untouched.
    for(double cr: {10.,30.,60.,100.}){
        auto o=m9Tg2NeutralChroma1A(8.0,cr,1.0);
        check(o.cr==cr);
    }
    std::cout<<"M9TG2STILL1A native chroma PASS: "<<n<<" assertions\n";
}
