#!/usr/bin/env python3
"""Generate the Saha Dışı monochrome speech/pitch app icon using stdlib only."""
import struct, zlib
from pathlib import Path

S=1024
WHITE=(250,250,250,255); DARK=(20,24,28,255)
pix=bytearray(WHITE*(S*S))

def setpx(x,y,c):
    if 0<=x<S and 0<=y<S:
        i=(y*S+x)*4; pix[i:i+4]=bytes(c)

def rounded_rect(x0,y0,x1,y1,r,c):
    r2=r*r
    for y in range(y0,y1):
        for x in range(x0,x1):
            dx=0 if x0+r<=x<x1-r else (x0+r-x if x<x0+r else x-(x1-r-1))
            dy=0 if y0+r<=y<y1-r else (y0+r-y if y<y0+r else y-(y1-r-1))
            if dx==0 or dy==0 or dx*dx+dy*dy<=r2:setpx(x,y,c)

def rect(x0,y0,x1,y1,c):
    for y in range(y0,y1):
        for x in range(x0,x1):setpx(x,y,c)

def circle(cx,cy,r,c,inner=0):
    r2=r*r; i2=inner*inner
    for y in range(cy-r,cy+r+1):
        for x in range(cx-r,cx+r+1):
            d=(x-cx)*(x-cx)+(y-cy)*(y-cy)
            if i2<=d<=r2:setpx(x,y,c)

def triangle(a,b,c0,color):
    minx,maxx=max(0,min(a[0],b[0],c0[0])),min(S-1,max(a[0],b[0],c0[0]))
    miny,maxy=max(0,min(a[1],b[1],c0[1])),min(S-1,max(a[1],b[1],c0[1]))
    def edge(p1,p2,p):return (p[0]-p1[0])*(p2[1]-p1[1])-(p[1]-p1[1])*(p2[0]-p1[0])
    for y in range(miny,maxy+1):
        for x in range(minx,maxx+1):
            e1,e2,e3=edge(a,b,(x,y)),edge(b,c0,(x,y)),edge(c0,a,(x,y))
            if (e1>=0 and e2>=0 and e3>=0) or (e1<=0 and e2<=0 and e3<=0):setpx(x,y,color)

# white background and dark speech bubble
rounded_rect(155,150,870,805,135,DARK)
triangle((235,720),(185,930),(445,780),DARK)
# pitch boundary
rounded_rect(225,235,800,625,62,WHITE)
rounded_rect(250,260,775,600,45,DARK)
# midfield line and center circle
rect(501,260,523,600,WHITE)
circle(512,430,76,WHITE,54)
# penalty boxes
for x0,x1 in ((250,370),(655,775)):
    rect(x0,330,x1,352,WHITE); rect(x0,510,x1,532,WHITE)
    if x0==250: rect(348,330,370,532,WHITE)
    else: rect(655,330,677,532,WHITE)
# commentary dots
for x in (430,512,594): circle(x,706,22,WHITE)

def chunk(kind,data):
    return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
raw=b''.join(b'\x00'+bytes(pix[y*S*4:(y+1)*S*4]) for y in range(S))
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',S,S,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')
out=Path('ios/SahaDisi/SahaDisi/Assets.xcassets/AppIcon.appiconset/AppIcon.png')
out.write_bytes(png)
print('Generated',out,len(png),'bytes')
