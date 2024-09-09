#####
# Most of the code is based on logic found in...
#
### GunZ 1
# - RTypes.h
# - RToken.h
# - RealSpace2.h/.cpp
# - RBspObject.h/.cpp
# - RMaterialList.h/.cpp
# - RMesh_Load.cpp
# - RMeshUtil.h
# - MZFile.cpp
# - R_Mtrl.cpp
# - EluLoader.h/cpp
# - LightmapGenerator.h/.cpp
# - MCPlug2_Mesh.cpp
#
### GunZ 2
# - RVersions.h
# - RTypes.h
# - RD3DVertexUtil.h
# - RStaticMeshResource.h
# - RStaticMeshResourceFileLoadImpl.cpp
# - MTypes.h
# - MVector3.h
# - MSVector.h
# - RMesh.cpp
# - RMeshNodeData.h
# - RMeshNodeLoadImpl.h/.cpp
# - RSkeleton.h/.cpp
#
# Please report maps and models with unsupported features to me on Discord: Krunk#6051
#####

import math, io

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .io_gzrs2 import *
from .lib_gzrs2 import *

def readLm(self, path, state):
    file = io.open(path, 'rb')
    file.seek(0, os.SEEK_END)
    fileSize = file.tell()
    file.seek(0, os.SEEK_SET)

    if state.logLmHeaders or state.logLmImages:
        print("===================  Read Lm  ===================")
        print()

    id = readUInt(file)
    version = readUInt(file)
    skipBytes(file, 4 + 4) # skip invalid polygon count and unused node count
    imageCount = readUInt(file)

    if state.logLmHeaders:
        print(f"Path:               { path }")
        print(f"ID:                 { hex(id) }")
        print(f"Version:            { hex(version) }")
        print(f"Image Count:        { imageCount }")
        print()

    if id != R_LM_ID or (version != R_LM_VERSION and version != R_LM_VERSION_EXT):
        self.report({ 'ERROR' }, f"GZRS2: Lm header invalid! { hex(id) }, { hex(version) }")
        file.close()

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
                file.close()

                return { 'CANCELLED' }

            width = readInt(file)
            height = readInt(file)

            if width != height:
                self.report({ 'ERROR' }, f"GZRS2: Lm BMP dimensions are not equal! Lightmap will not load properly! Please submit to Krunk#6051 for testing! { width }, { height }")
                file.close()

                return { 'CANCELLED' }

            if not math.log2(width).is_integer():
                self.report({ 'ERROR' }, f"GZRS2: Lm BMP dimensions are not a power of two! Lightmap will not load properly! Please submit to Krunk#6051 for testing! { width }, { height }")
                file.close()

                return { 'CANCELLED' }

            skipBytes(file, 2 * 2 + 4 * 6) # skip color plane count, bit depth and compression info

            if state.logLmImages:
                print(f"===== BMP { i + 1 } ==============================")
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
                file.close()

                return { 'CANCELLED' }

            if ddspfFourCC != 'DXT1':
                self.report({ 'ERROR' }, f"GZRS2: Lm DDS unsupported compression type! Currently, DXT1 is the only supported type. { ddspfFourCC }")
                file.close()

                return { 'CANCELLED' }

            ddsCaps = readUInt(file)
            for _ in range(4):
                skipBytes(file, 4)

            if state.logLmImages:
                print(f"===== DDS { i + 1 } ==============================")
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
            file.close()

            return { 'CANCELLED' }

    state.lmPolygonIDs = readUIntArray(file, state.rsPolygonCount)
    state.lmIndices = readUIntArray(file, state.rsPolygonCount)
    state.lmUVs = readUV2Array(file, state.rsVertexCount)

    if state.logLmHeaders or state.logLmImages:
        bytesRemaining = fileSize - file.tell() if state.rsVertexCount > 0 else 0

        if bytesRemaining > 0:
            self.report({ 'ERROR' }, f"GZRS2: LM import finished with bytes remaining! { path }, { hex(id) }, { hex(version) }")

        print(f"Bytes Remaining:    { bytesRemaining }")
        print()

    file.close()
