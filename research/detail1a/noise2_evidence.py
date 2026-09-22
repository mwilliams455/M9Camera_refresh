"""Extract the active Noise2 evidence; requires the canonical user-supplied firmware."""
from pathlib import Path
import argparse, hashlib, json, struct, subprocess, sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'tools'))
from m9_sharpnessforensics1a import parse_ldr, read_overlay
from m9_sharpness_export_fulliso_header import FW_SHA, walk

def sha(data): return hashlib.sha256(data).hexdigest()

def extract(firmware, objdump, out):
    fw=Path(firmware).read_bytes(); assert sha(fw)==FW_SHA
    assets={path:data for path,_,data in walk(fw)}
    ldr=assets['BF561/bf1']; lut=assets['LUTS/PROCESS/LUTS']
    assert sha(ldr)=='06abf2c4ef5e14beeadc033359d7fe4ae955c8a30b4ef26afa756afcf6d21870'
    assert sha(lut)=='25debaf581d3fdbeca6ad7c6426ca5d9e597b98856c540ceddcc912b79409d8d'
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    # Temporary binaries are local evidence only, never application resources.
    temp=out/'bf561.ldr';temp.write_bytes(ldr);_,blocks=parse_ldr(temp);temp.unlink()
    targets=[('ASMBox9CDI',0xff600d48,442),('Gauss5CDI',0xff60272c,452),
        ('Gauss13CDI',0xff60246c,704),('Process_Noise',0xff602bd0,1278),
        ('CalculateNoiseParameter',0xfeb1cd70,350),('LoadLutDataL3',0xfeb1c638,412),
        ('Set',0xfeb1d1bc,1548),('float_to_int',0xfeb19c58,66)]
    functions=[]
    for name,addr,size in targets:
        code=read_overlay(blocks,addr,size);binary=out/'temporary.bin';binary.write_bytes(code)
        r=subprocess.run([str(objdump),'-D','-b','binary','-m','bfin',f'--adjust-vma={addr}',str(binary)],check=True,capture_output=True,text=True)
        lines=[]
        for line in r.stdout.splitlines():
            fields=line.split('\t')
            if len(fields)>2:lines.append(fields[0]+' '+fields[2].split('/*')[0].rstrip())
        binary.unlink();dest=out/f'{name}_{addr:08x}.asm.txt';dest.write_text('\n'.join(lines)+'\n')
        functions.append(dict(name=name,address=hex(addr),size=size,code_sha256=sha(code),file=dest.name,text_sha256=sha(dest.read_bytes())))
    rows=lambda off:[list(struct.unpack_from('<13i',lut,off+52*k)) for k in range(5)]
    tables=dict(schema='m9.noise2.tables.v1',firmware_sha256=sha(fw),resource_sha256=sha(lut),
        # LoadLutDataL3: LUTS+0x200 -> context+0x268, length 0x3f0.
        base_strength=struct.unpack_from('<i',lut,0x200)[0],attenuation=struct.unpack_from('<i',lut,0x208)[0],
        luma_enable=rows(0x20c),chroma_mode=rows(0x310),
        iso_strength=list(struct.unpack_from('<13i',lut,0x47c)),brightness_weight=list(lut[0x4f0:0x5f0]),
        source_offsets=dict(base_strength='0x200',attenuation='0x208',luma_enable='0x20c',chroma_mode='0x310',iso_strength='0x47c',brightness_weight='0x4f0'))
    assert tables['base_strength']==31 and tables['attenuation']==64
    assert tables['chroma_mode'][2]==[1,1,1,2,2,2,2,2,2,3,3,4,5]
    assert tables['luma_enable'][2]==[0]*12+[1]
    assert all(0<x<=16 for x in tables['brightness_weight'])
    (out/'tables.json').write_text(json.dumps(tables,indent=2)+'\n')
    manifest=dict(firmware_sha256=sha(fw),ldr_sha256=sha(ldr),resource_sha256=sha(lut),functions=functions,
        disassembler=subprocess.check_output([str(objdump),'--version'],text=True).splitlines()[0],
        note='Only active call targets are interpreted; overlapping stale map variants are excluded. ASMBox9CDI ends at its RTS; its map size is zero.')
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return tables

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('firmware',type=Path);ap.add_argument('objdump',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args()
    extract(a.firmware,a.objdump,a.out)
