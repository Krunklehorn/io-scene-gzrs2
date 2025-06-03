#####
# Most of the code is based on logic found in...
#
### GunZ 1
# - RBspObject.h/.cpp
# - RBspObject_bsp.cpp
#
# Please report maps and models with unsupported features to me on Discord: Krunk#6051
#####

import math, io

from ..constants_gzrs2 import *
from ..classes_gzrs2 import *
from ..io_gzrs2 import *
from ..lib.lib_gzrs2 import *

def readLm(self, file, path, state):
    file.seek(0, os.SEEK_END)
    fileSize = file.tell()
    file.seek(0, os.SEEK_SET)

    if state.logLmHeaders or state.logLmImages:
        print("===================  Read Lm  ===================")
        print()

    id = readUInt(file)
    version = readUInt(file)
    lmCPolygonCount = readUInt(file)
    lmONodeCount = readUInt(file)
    imageCount = readUInt(file)

    if state.logLmHeaders:
        print(f"Path:               { path }")
        print(f"ID:                 { hex(id) }")
        print(f"Version:            { hex(version) }")
        print(f"Image Count:        { imageCount }")
        print()

    if id != LM_ID or version not in (LM_VERSION, LM_VERSION_EXT):
        self.report({ 'ERROR' }, f"GZRS2: LM header invalid! { hex(id) }, { hex(version) }")
        return { 'CANCELLED' }

    if state.rsCPolygonCount is not None or state.rsONodeCount is not None:
        if lmCPolygonCount != state.rsCPolygonCount or lmONodeCount != state.rsONodeCount:
            self.report({ 'ERROR' }, f"GZRS2: LM topology does not match! { lmCPolygonCount }, { state.rsCPolygonCount }, { lmONodeCount }, { state.rsONodeCount }")
            return { 'CANCELLED' }

    for i in range(imageCount):
        byteCount = readUInt(file)
        type = decodeBytes(file, 2)

        if type == 'BM':
            skipBytes(file, 4) # skip bmp size
            skipBytes(file, 4 + 4) # skip reserved shorts and start address
            bmpHeaderSize = readUInt(file)

            if bmpHeaderSize != 40:
                self.report({ 'ERROR' }, f"GZRS2: Lm BMP header is not supported yet! Lightmap will not load properly! Please submit to Krunk#6051 for testing! { bmpHeaderSize }")
                return { 'CANCELLED' }

            width = readInt(file)
            height = readInt(file)

            if width != height:
                self.report({ 'ERROR' }, f"GZRS2: Lm BMP dimensions are not equal! Lightmap will not load properly! Please submit to Krunk#6051 for testing! { width }, { height }")
                return { 'CANCELLED' }

            if not math.log2(width).is_integer():
                self.report({ 'ERROR' }, f"GZRS2: Lm BMP dimensions are not a power of two! Lightmap will not load properly! Please submit to Krunk#6051 for testing! { width }, { height }")
                return { 'CANCELLED' }

            skipBytes(file, 2 * 2 + 4 * 6) # skip color plane count, bit depth and compression info

            if state.logLmImages:
                print(f"===== BMP { i } ==============================")
                print(f"Byte Count:         { byteCount }")
                print(f"Header Size:        { bmpHeaderSize }")
                print(f"Dimensions:         { width } x { height }")
                print()

            state.lmImages.append(LmImage(width, tuple(readUChar(file) / 255.0 for _ in range(width * height * 3))))
        elif type == 'DD':
            skipBytes(file, 2)
            skipBytes(file, 4) # skip dds size
            ddsFlags = readUInt(file)
            width = readUInt(file)
            height = readUInt(file)
            skipBytes(file, 4 + 4) # skip pitch/linearsize and depth
            mipCount = readUInt(file)
            for _ in range(11):
                skipBytes(file, 4)

            skipBytes(file, 4) # skip ddspf size
            ddspfFlags = readUInt(file)
            ddspfFourCC = decodeBytes(file, 4)
            for _ in range(5): # skip rgb bit count and masks
                skipBytes(file, 4)

            if ddspfFlags & (1 << DDPF_FOURCC):
                self.report({ 'ERROR' }, f"GZRS2: Lm DDS unsupported pixel format! Currently, FourCC is the only supported format. { ddspfFlags }")
                return { 'CANCELLED' }

            if ddspfFourCC != 'DXT1':
                self.report({ 'ERROR' }, f"GZRS2: Lm DDS unsupported compression type! Currently, DXT1 is the only supported type. { ddspfFourCC }")
                return { 'CANCELLED' }

            ddsCaps = readUInt(file)
            for _ in range(4):
                skipBytes(file, 4)

            if state.logLmImages:
                print(f"===== DDS { i } ==============================")
                print(f"Byte Count:         { byteCount }")
                print(f"Main Flags:         { ddsFlags }")
                print(f"Dimensions:         { width } x { height }")
                print(f"Mip Count:          { mipCount }")
                print(f"Format Flags:       { ddspfFlags }")
                print(f"FourCC:             { ddspfFourCC }")
                print(f"Caps:               { ddsCaps }")
                print()

            pixelCount = width * height
            blockLength = 4
            blockStride = blockLength ** 2
            blockCount = pixelCount // blockStride
            blockSpan = int(math.sqrt(blockCount))

            imageData = readBytes(file, pixelCount // 2)
            imageShorts = memoryview(imageData).cast('H')
            imageInts = memoryview(imageData).cast('I')

            pixels = [0 for _ in range(width * height * 3)]

            for b in range(blockCount):
                p0 = rgb565ToVector(imageShorts[b * 4 + 0])
                p1 = rgb565ToVector(imageShorts[b * 4 + 1])
                indices = imageInts[b * 2 + 1]

                if p0 > p1:
                    p2 = (2.0 * p0 + p1) / 3.0
                    p3 = (2.0 * p1 + p0) / 3.0
                else:
                    p2 = (p0 + p1) / 2.0
                    p3 = Vector((0, 0, 0))

                bx = b % blockSpan
                by = b // blockSpan

                for p in range(blockStride):
                    s = p * 2

                    index = (indices & (3 << s)) >> s

                    if index == 0: pixel = p0
                    elif index == 1: pixel = p1
                    elif index == 2: pixel = p2
                    elif index == 3: pixel = p3

                    px = p % blockLength
                    py = p // blockLength

                    f = bx * blockLength
                    f += by * blockLength * width
                    f += px + py * width

                    pixels[f * 3 + 2] = pixel.x
                    pixels[f * 3 + 1] = pixel.y
                    pixels[f * 3 + 0] = pixel.z

            imageShorts.release()
            imageInts.release()

            state.lmImages.append(LmImage(width, tuple(pixels)))
        else:
            self.report({ 'ERROR' }, f"GZRS2: Lm data type is not supported yet! Lightmap will not load properly! Please submit to Krunk#6051 for testing! { type }")
            return { 'CANCELLED' }

    if not state.rsOPolygonCount:
        return

    state.lmPolygonOrder = readUIntArray(file, state.rsOPolygonCount)
    lightmapIDs = readUIntArray(file, state.rsOPolygonCount)
    sortedIDs = [0 for p in range(state.rsOPolygonCount)]

    for p in range(state.rsOPolygonCount):
        sortedIDs[state.lmPolygonOrder[p]] = lightmapIDs[p]

    state.lmLightmapIDs = tuple(sortedIDs)
    state.lmUVs = readUV2Array(file, state.rsOVertexCount)

    if state.logLmHeaders or state.logLmImages:
        bytesRemaining = fileSize - file.tell()

        if bytesRemaining > 0:
            self.report({ 'ERROR' }, f"GZRS2: LM import finished with bytes remaining! { path }, { hex(id) }, { hex(version) }")

        print(f"Bytes Remaining:    { bytesRemaining }")
        print()
