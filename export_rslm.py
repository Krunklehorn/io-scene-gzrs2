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

import bpy, os, io, shutil, array
from struct import pack
from mathutils import Vector

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .io_gzrs2 import *
from .lib_gzrs2 import *

def exportLm(self, context):
    lmpath = self.filepath
    directory = os.path.dirname(lmpath)
    basename = os.path.basename(lmpath)
    filename = basename.split(os.extsep)[0]

    if self.doUVs:
        blMeshObj = context.active_object

        if blMeshObj is None or blMeshObj.type != 'MESH':
            self.report({ 'ERROR' }, "GZRS2: Lightmap UV export requires an active mesh object with valid UVs in channel 3!")
            return { 'CANCELLED' }

        blMesh = blMeshObj.data

        if len(blMesh.uv_layers) < 3:
            self.report({ 'ERROR' }, "GZRS2: Lightmap UV export requires an active mesh object with valid UVs in channel 3!")
            return { 'CANCELLED' }

        uvLayer3 = blMesh.uv_layers[2]

        rspath = pathExists(os.path.splitext(lmpath)[0])

        if not rspath:
            self.report({ 'ERROR' }, "GZRS2: Lightmap UV export requires a GunZ 1 .rs file for the same map in the same directory!")
            return { 'CANCELLED' }

        file = open(rspath, 'rb')

        id = readUInt(file)
        version = readUInt(file)

        if not (id == RS2_ID or id == RS3_ID) or version < RS3_VERSION1:
            self.report({ 'ERROR' }, f"GZRS2: RS header invalid! { hex(id) }, { version }")
            file.close()

            return { 'CANCELLED' }

        if id == RS2_ID and version == RS2_VERSION:
            for _ in range(readInt(file)): # skip packed material strings
                for __ in range(256):
                    if file.read(1) == b'\x00':
                        break

            rsPolyCount = readInt(file)
            skipBytes(file, 4) # skip total vertex count

            for _ in range(rsPolyCount):
                skipBytes(file, 4 + 4 + (4 * 4) + 4) # skip material id, draw flags, plane and area data
                skipBytes(file, 2 * readInt(file) * 4 * 3) # skip vertex data and normal data

            skipBytes(file, 4 * 4) # skip unused, unknown counts
            skipBytes(file, 4) # skip node count
            lmPolygonCount = readUInt(file)
            lmVertexCount = readInt(file)
        else:
            self.report({ 'ERROR' }, f"GZRS2: RS file must be for GunZ 1! { hex(id) }, { version }")
            file.close()

            return { 'CANCELLED' }

        file.close()

    imageDatas = []

    imageTarget = f"{ filename }_LmImage"
    atlasTarget = f"{ filename }_LmAtlas"
    found = False

    for image in bpy.data.images:
        imageName = image.name

        if image.size[0] == 0 or image.size[0] != image.size[1]:
            continue

        mipCount = math.log2(image.size[0])

        if not mipCount.is_integer():
            continue

        mipCount = int(mipCount)

        if imageName == imageTarget:
            imageSize = image.size[0]
            floats = tuple(image.pixels)

            imageDatas.append(packLmImageData(self.lmVersion4, imageSize, floats))

            found = True
            break
        elif imageName.startswith(atlasTarget):
            numCells = imageName[-1]

            if not numCells.isdigit():
                continue

            numCells = int(numCells)

            if numCells < 2:
                continue

            cellSpan = int(math.sqrt(nextSquare(numCells)))
            atlasSize = image.size[0]
            imageSize = atlasSize // cellSpan
            floats = tuple(image.pixels)

            for c in range(numCells):
                cx = c % cellSpan
                cy = cellSpan - 1 - c // cellSpan # OpenGL -> DirectX

                imageDatas.append(packLmImageData(self.lmVersion4, imageSize, floats, True, atlasSize, cx, cy))

            found = True
            break

    if not found:
        self.report({ 'ERROR' }, "GZRS2: No valid lightmap found! Image must be a square, power of two texture and the name must match \'<mapname>_LmImage\' or \'<mapname>_LmAtlas<# of cells>\'")
        return { 'CANCELLED' }

    if self.doUVs:
        # newPolyIDs = bytearray(lmPolygonCount * 4)
        newIndices = bytearray(lmPolygonCount * 4)
        newUVs = bytearray(lmVertexCount * 2 * 4)

        # newPolyIDInts = memoryview(newPolyIDs).cast('I')
        newIndexInts = memoryview(newIndices).cast('I')
        newUVFloats = memoryview(newUVs).cast('f')

        # TODO: can we determine these ourselves?
        for p in range(lmPolygonCount):
            # newPolyIDInts[p] = p
            newIndexInts[p] = 0

        for v in range(lmVertexCount):
            uv3 = uvLayer3.data[v].uv

            newUVFloats[v * 2 + 0] = uv3.x
            newUVFloats[v * 2 + 1] = 1 - uv3.y

        # newPolyIDInts.release()
        newIndexInts.release()
        newUVFloats.release()

    shutil.copy2(lmpath, lmpath.replace(filename, filename + "_backup"))

    file = open(lmpath, 'r+b')

    file.seek(0, os.SEEK_END)
    fileSize = file.tell()
    file.seek(0, os.SEEK_SET)

    id = readUInt(file)
    version = readUInt(file)

    if id != R_LM_ID or (version != R_LM_VERSION and version != R_LM_VERSION_EXT):
        self.report({ 'ERROR' }, f"GZRS2: Lm header invalid! { hex(id) }, { version }")
        file.close()

        return { 'CANCELLED' }

    skipBytes(file, 4 + 4) # skip invalid polygon count and unused node count

    for _ in range(readUInt(file)):
        skipBytes(file, readUInt(file)) # skip image data

    if self.doUVs:
        lmData = file.read(4 * lmPolygonCount) # TODO: if we can determine the polygon IDs ourselves, we can just skip the originals
    else:
        lmData = file.read(fileSize - file.tell())

    file.seek(4, os.SEEK_SET)
    writeInt(file, R_LM_VERSION_EXT if self.lmVersion4 else R_LM_VERSION)

    skipBytes(file, 4 + 4) # skip invalid polygon count and unused node count

    writeInt(file, len(imageDatas))

    pixelCount = imageSize ** 2

    ddsSize = 76 + 32 + 20 + pixelCount // 2
    bmpSize = 14 + 40 + pixelCount * 3

    for d, imageData in enumerate(imageDatas):
        if self.lmVersion4:
            writeInt(file, ddsSize)

            # DDS header
            writeBytes(file, b'DDS ')
            writeInt(file, ddsSize)
            # writeInt(file, DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_MIPMAPCOUNT | DDSD_LINEARSIZE)
            writeInt(file, DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_LINEARSIZE)
            writeInt(file, imageSize)
            writeInt(file, imageSize)
            writeInt(file, pixelCount // 2)
            writeInt(file, 0)
            # writeInt(file, mipCount)
            writeInt(file, 0)
            for _ in range(11):
                writeInt(file, 0)

            writeInt(file, 32)
            writeInt(file, DDPF_FOURCC)
            writeBytes(file, b'DXT1')
            for _ in range(5):
                writeInt(file, 0)

            # writeInt(file, DDSCAPS_COMPLEX | DDSCAPS_TEXTURE | DDSCAPS_MIPMAP)
            writeInt(file, DDSCAPS_TEXTURE)
            for _ in range(4):
                writeInt(file, 0)
        else:
            writeInt(file, bmpSize)

            # BMP header
            writeBytes(file, b'BM')
            writeInt(file, bmpSize)
            writeShort(file, 0)
            writeShort(file, 0)
            writeInt(file, 14 + 40)

            writeInt(file, 40)
            writeInt(file, imageSize)
            writeInt(file, imageSize)
            writeShort(file, 1)
            writeShort(file, 24)
            for _ in range(6):
                writeInt(file, 0)

        file.write(imageData)

    if self.doUVs:
        file.write(lmData) # file.write(newPolyIDInts)
        file.write(newIndices)
        file.write(newUVs)
    else:
        file.write(lmData)

    file.truncate()
    file.close()

    return { 'FINISHED' }
