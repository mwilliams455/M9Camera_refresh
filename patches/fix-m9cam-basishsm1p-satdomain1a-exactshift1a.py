#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv)!=2:
    raise SystemExit('usage: fix-m9cam-basishsm1p-satdomain1a-exactshift1a.py <PhotonCamera-root>')
root=Path(sys.argv[1]).resolve()
cp=root/'app/src/main/cpp/m9color_jni.cpp'
if not cp.exists(): raise SystemExit('SATDOMAIN1A C++ source missing')
c=cp.read_text()
old='''    const double unclamped[3] = {
        static_cast<double>(a0) / 65536.0,
        static_cast<double>(a1) / 65536.0,
        static_cast<double>(a2) / 65536.0
    };
    const int64_t clamped[3] = {'''
new='''    // EXACTSHIFT1A: the renderer's literal pre-clamp SAT coordinate is the signed
    // arithmetic >>16 result. Keep accumulator/65536 scaling out of the causal hue
    // discriminator so any measured unclamped->clamped hue change is due only to the
    // first required 0..2047 boundary clamp, not fractional fixed-point representation.
    const double unclamped[3] = {
        static_cast<double>(shifted[0]),
        static_cast<double>(shifted[1]),
        static_cast<double>(shifted[2])
    };
    const int64_t clamped[3] = {'''
if c.count(old)!=1:
    raise SystemExit('SATDOMAIN1A EXACTSHIFT1A anchor count='+str(c.count(old)))
c=c.replace(old,new,1)
old2='''    os << "\\\"matrixAccumulatorDomain\\\":\\\"signed_int64_Q_family_dot_product\\\",";
    os << "\\\"firstSatClamp\\\":\\\"arithmetic_shift_16_then_independent_0_2047_curve02_index_clamp\\\",";'''
new2='''    os << "\\\"matrixAccumulatorDomain\\\":\\\"signed_int64_Q_family_dot_product\\\",";
    os << "\\\"unclampedSatCoordinateDomain\\\":\\\"exact_signed_arithmetic_shift_16_integer_coordinate\\\",";
    os << "\\\"firstSatClamp\\\":\\\"arithmetic_shift_16_then_independent_0_2047_curve02_index_clamp\\\",";'''
if c.count(old2)!=1:
    raise SystemExit('SATDOMAIN1A EXACTSHIFT1A JSON anchor count='+str(c.count(old2)))
c=c.replace(old2,new2,1)
cp.write_text(c)
print('SATDOMAIN1A EXACTSHIFT1A applied')
print(' - hue/chroma unclamped state now uses exact renderer a>>16 signed coordinates')
print(' - clamp-induced hue delta isolates only the 0..2047 boundary operation')
