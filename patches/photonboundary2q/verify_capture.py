#!/usr/bin/env python3
"""Compare saved DNG decoded RAW samples to PHOTONBOUNDARY2Q live byte hashes.
Usage: python verify_capture.py CAPTURE.dng CAPTURE_M9_PRIMARY.json
Requires numpy and tifffile. No image processing, WB, shading or demosaic.
"""
import hashlib, json, sys
from pathlib import Path
import numpy as np
import tifffile

def verify(dng_path, primary_path):
    root=json.loads(Path(primary_path).read_text())
    renderer=root['renderer']; trace=renderer['photonBoundary2Q']
    if trace.get('revision')!='M9PHOTONBOUNDARY2Q_READONLY':raise ValueError('Wrong diagnostic revision')
    with tifffile.TiffFile(dng_path) as tif:
        raw_pages=[p for p in tif.pages if int(p.photometric)==32803]
        if len(raw_pages)!=1:raise ValueError('Expected one top-level CFA RAW IFD')
        raw=raw_pages[0].asarray()
    if raw.ndim!=2 or raw.dtype.kind!='u' or raw.dtype.itemsize!=2:
        raise ValueError('Expected untouched uint16 CFA samples')
    data=np.ascontiguousarray(raw,dtype='<u2').tobytes()
    digest=hashlib.sha256(data).hexdigest()
    stages=trace.get('stages',{})
    names=['cameraPlaneBeforeCopy','photonOwnedAfterCopy','rendererEntry','dngWriterInput','dngWriterReturn']
    comparisons={name:stages.get(name,{}).get('sha256')==digest
                 and stages.get(name,{}).get('byteCount')==len(data) for name in names}
    acquisition=trace.get('acquisition',{})
    capture=renderer.get('sourceCalibrationAudit1A',{}).get('captureColorMetadata1A',{})
    ts=acquisition.get('imageTimestampNs')
    metadata_match=ts is not None and ts==capture.get('sensorTimestampNs')
    dimensions_match=raw.shape==(acquisition.get('copyHeight'),acquisition.get('copyWidth'))
    passes=(trace.get('status')=='buffer_handoffs_match_saved_DNG_decode_pending'
            and trace.get('allRawBytesEqual') is True
            and trace.get('allImageResultTimestampsEqual') is True
            and all(comparisons.values()) and metadata_match and dimensions_match)
    return dict(status='tested_boundaries_match' if passes else 'needs_investigation',
                dng=Path(dng_path).name,primary=Path(primary_path).name,
                decodedRawShape=list(raw.shape),decodedRawSha256=digest,
                savedDngMatchesStages=comparisons,dimensionsMatch=dimensions_match,
                sourceCalibrationResultTimestampMatchesRaw=metadata_match,
                liveTraceStatus=trace.get('status'),
                scope='This capture only: camera plane, Photon allocation, renderer handoff, DNG input/output. Does not rule out HAL, optics, demosaic or color rendering.')

if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit(__doc__)
    print(json.dumps(verify(*sys.argv[1:]),indent=2))
