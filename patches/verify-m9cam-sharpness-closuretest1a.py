#!/usr/bin/env python3
from pathlib import Path
import hashlib, re, struct, sys

ROOT=Path(sys.argv[1]) if len(sys.argv)>1 else Path('PhotonCamera')
CPP=ROOT/'app/src/main/cpp/m9color_jni.cpp'
if not CPP.exists(): raise SystemExit('CLOSURETEST1A verifier missing '+str(CPP))
s=CPP.read_text()
need=[
 'SHARPNESS_CLOSURETEST1A',
 'm9ClosureQ14', 'm9ClosureQ16', 'm9ClosureSlot0Coeff',
 'm9ClosureSharpIso160Standard',
 '16383u + 32767u)/65535u',
 '65535u + 8191u)/16383u',
 'for(int y=2;y<h-2;++y)', 'for(int x=2;x<w-2;++x)',
 'r < -1024', 'r > 1024', '1024+r',
 'const int dr=m9ClosureQ14(base[0])-g14',
 'const int db=m9ClosureQ14(base[2])-g14',
 'm9ClosureClamp14(sg+dr)', 'm9ClosureClamp14(sg+db)',
]
for x in need:
    if x not in s: raise SystemExit('CLOSURETEST1A missing anchor: '+x)
if 'closureSharp14[p]' not in s: raise SystemExit('CLOSURETEST1A sharpened green not consumed')
if re.search(r'Auto.?ISO|autoIso|AUTO_ISO', s):
    # Existing unrelated source may mention AutoISO; only reject inside our helper block.
    a=s.index('// SHARPNESS_CLOSURETEST1A')
    b=s.index('// SPLITDEMOSAIC1A research seam',a)
    if re.search(r'Auto.?ISO|autoIso|AUTO_ISO',s[a:b]):
        raise SystemExit('CLOSURETEST1A unexpectedly depends on Auto ISO')

# Independently reconstruct the compactly encoded canonical slot0 table and pin its byte hash.
lut=[i-1024 for i in range(2050)]
exc={997:-26,998:-25,999:-24,1000:-23,1001:-21,1002:-20,1003:-19,1004:-17,
1005:-16,1006:-15,1007:-13,1008:-12,1009:-11,1010:-10,1011:-9,1012:-8,
1013:-7,1014:-6,1015:-5,1016:-4,1017:-3,1018:-2,1019:-2,1020:-1,1021:-1,
1022:0,1023:0,1025:0,1026:0,1027:1,1028:1,1029:2,1030:2,1031:3,1032:4,
1033:5,1034:6,1035:7,1036:8,1037:9,1038:10,1039:11,1040:12,1041:13,
1042:15,1043:16,1044:17,1045:19,1046:20,1047:21,1048:23,1049:24,1050:25,1051:26}
for i,v in exc.items(): lut[i]=v
digest=hashlib.sha256(struct.pack('<2050h',*lut)).hexdigest()
expected='2317595946f76c3965b7479c1c68fd66e5a9ac8be81292a91f944a6cde85f6e9'
if digest!=expected: raise SystemExit(f'CLOSURETEST1A slot0 hash mismatch {digest}')
if expected not in s: raise SystemExit('CLOSURETEST1A source does not pin canonical slot0 hash')
print('CLOSURETEST1A verify PASS')
print(' fixed_iso=160 slot=0 menu=Standard scale=1x')
print(' slot0_sha256='+digest)
print(' quantization=endpoint-nearest norm16<->14 (explicit mobile-port choice)')
print(' rb_policy=preserve frozen MHC R-G/B-G around sharpened green (diagnostic approximation)')
