#!/usr/bin/env python3
import random

def serial(src, rows, width, rotation):
    dst=[None]*(rows*width)
    r=rotation%360
    if r==0 or r not in (90,180,270):
        dst[:] = src[:]
    elif r==90:
        for y in range(rows):
            sr=y*width; dx=rows-1-y
            for x in range(width): dst[x*rows+dx]=src[sr+x]
    elif r==180:
        for y in range(rows):
            sr=y*width; dr=(rows-1-y)*width
            for x in range(width): dst[dr+(width-1-x)]=src[sr+x]
    else:
        for y in range(rows):
            sr=y*width
            for x in range(width): dst[(width-1-x)*rows+y]=src[sr+x]
    return dst

def subrange(src,dst,rows,width,y0,y1,rotation):
    r=rotation%360
    if r==0 or r not in (90,180,270):
        dst[y0*width:y1*width]=src[y0*width:y1*width]
    elif r==90:
        for y in range(y0,y1):
            sr=y*width; dx=rows-1-y
            for x in range(width): dst[x*rows+dx]=src[sr+x]
    elif r==180:
        for y in range(y0,y1):
            sr=y*width; dr=(rows-1-y)*width
            for x in range(width): dst[dr+(width-1-x)]=src[sr+x]
    else:
        for y in range(y0,y1):
            sr=y*width
            for x in range(width): dst[(width-1-x)*rows+y]=src[sr+x]

def fused(src,rows,width,rotation,workers):
    dst=[None]*(rows*width)
    wc=max(1,min(workers,rows))
    ranges=[]
    for w in range(wc):
        y0=(rows*w)//wc; y1=(rows*(w+1))//wc
        ranges.append((y0,y1))
    # Run in deliberately shuffled order to model independent threads.
    random.shuffle(ranges)
    for y0,y1 in ranges: subrange(src,dst,rows,width,y0,y1,rotation)
    assert all(x is not None for x in dst)
    return dst

random.seed(0xC09A17)
cases=0
for rows in [1,2,3,7,24,47,96,383,384]:
    for width in [1,2,5,16,31,64,257]:
        src=[random.getrandbits(32) for _ in range(rows*width)]
        for rot in [0,90,180,270,-90,450,13]:
            ref=serial(src,rows,width,rot)
            for workers in [1,2,3,4,8,16]:
                got=fused(src,rows,width,rot,workers)
                if got!=ref:
                    raise SystemExit(f'mismatch rows={rows} width={width} rot={rot} workers={workers}')
                cases+=1
print(f'PERF3G ORIENTFUSE8A exact mapping parity PASS: {cases} partition/rotation cases')
