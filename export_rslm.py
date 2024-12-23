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

import bpy, os, io, math, shutil

from .classes_gzrs2 import *
from .io_gzrs2 import *
from .lib_gzrs2 import *

def writeDDSHeader(file, imageSize, pixelCount, ddsSize):
    writeBytes(file, b'DDS ')
    writeUInt(file, ddsSize)
    # writeUInt(file, DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_MIPMAPCOUNT | DDSD_LINEARSIZE)
    writeUInt(file, DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_LINEARSIZE)
    writeInt(file, imageSize)
    writeInt(file, imageSize)
    writeUInt(file, pixelCount // 2)
    writeUInt(file, 0)
    writeUInt(file, 0) # writeUInt(file, mipCount)
    for _ in range(11):
        writeUInt(file, 0)

    writeUInt(file, 32)
    writeUInt(file, DDPF_FOURCC)
    writeBytes(file, b'DXT1')
    for _ in range(5):
        writeUInt(file, 0)

    # writeUInt(file, DDSCAPS_COMPLEX | DDSCAPS_TEXTURE | DDSCAPS_MIPMAP)
    writeUInt(file, DDSCAPS_TEXTURE)
    for _ in range(4):
        writeUInt(file, 0)

def writeBMPHeader(file, imageSize, bmpSize):
    writeBytes(file, b'BM')
    writeUInt(file, bmpSize)
    writeShort(file, 0)
    writeShort(file, 0)
    writeUInt(file, 14 + 40)

    writeUInt(file, 40)
    writeUInt(file, imageSize)
    writeUInt(file, imageSize)
    writeShort(file, 1)
    writeShort(file, 24)
    for _ in range(6):
        writeUInt(file, 0)

def exportLm(self, context):
    state = RSLMExportState()

    state.doUVs = self.doUVs
    state.lmVersion4 = self.lmVersion4

    if self.panelLogging:
        print()
        print("=======================================================================")
        print("===========================  RSLM Export  =============================")
        print("=======================================================================")
        print(f"== { self.filepath }")
        print("=======================================================================")
        print()

        state.logLmHeaders = self.logLmHeaders
        state.logLmImages = self.logLmImages

    lmpath = self.filepath
    directory = os.path.dirname(lmpath)
    basename = os.path.basename(lmpath)
    splitname = basename.split(os.extsep)
    filename = splitname[0]

    if state.doUVs:
        blMeshObj = context.active_object if context.active_object in context.selected_objects else None

        if blMeshObj is None or blMeshObj.type != 'MESH' or not blMeshObj.select_get():
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

        file = io.open(rspath, 'rb')

        id = readUInt(file)
        version = readUInt(file)

        if not (id == RS2_ID or id == RS3_ID) or version < RS3_VERSION1:
            self.report({ 'ERROR' }, f"GZRS2: RS header invalid! { hex(id) }, { hex(version) }")
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
            rsOPolygonCount = readUInt(file)
            rsOVertexCount = readInt(file)
        else:
            self.report({ 'ERROR' }, f"GZRS2: RS file must be for GunZ 1! { hex(id) }, { hex(version) }")
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
            floats = image.pixels[:]

            imageDatas.append(packLmImageData(self, imageSize, floats))

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
            floats = image.pixels[:]

            for c in range(numCells):
                cx = c % cellSpan
                cy = cellSpan - 1 - c // cellSpan

                imageDatas.append(packLmImageData(self, imageSize, floats, True, atlasSize, cx, cy))

            found = True
            break

    if not found:
        self.report({ 'ERROR' }, "GZRS2: No valid lightmap found! Image must be a square, power of two texture and the name must match \'<mapname>_LmImage\' or \'<mapname>_LmAtlas<# of cells>\'")
        return { 'CANCELLED' }

    if state.doUVs:
        # newPolyIDs = bytearray(rsOPolygonCount * 4)
        newIndices = bytearray(rsOPolygonCount * 4)
        newUVs = bytearray(rsOVertexCount * 2 * 4)

        # newPolyIDInts = memoryview(newPolyIDs).cast('I')
        newIndexInts = memoryview(newIndices).cast('I')
        newUVFloats = memoryview(newUVs).cast('f')

        # TODO: the polgyon IDs aren't as they seem...
        for p in range(rsOPolygonCount):
            # newPolyIDInts[p] = 0
            newIndexInts[p] = 0 # Never atlas

        for v in range(rsOVertexCount):
            uv3 = uvLayer3.data[v].uv

            newUVFloats[v * 2 + 0] = uv3.x
            newUVFloats[v * 2 + 1] = 1 - uv3.y

        # newPolyIDInts.release()
        newIndexInts.release()
        newUVFloats.release()

    shutil.copy2(lmpath, os.path.join(directory, filename + "_backup") + '.' + splitname[1] + '.' + splitname[2])

    file = io.open(lmpath, 'r+b')
    file.seek(0, os.SEEK_END)
    fileSize = file.tell()
    file.seek(0, os.SEEK_SET)

    id = readUInt(file)
    version = readUInt(file)

    if state.logLmHeaders or state.logLmImages:
        print("===================  Write Lm  ===================")
        print()

    if state.logLmHeaders:
        print(f"Path:               { lmpath }")
        print(f"ID:                 { hex(id) }")
        print(f"Version:            { hex(version) }")
        print()

    skipBytes(file, 4 + 4) # skip invalid (auxiliary?) polygon count and unused node count

    for _ in range(readUInt(file)):
        skipBytes(file, readUInt(file)) # skip image data

    if state.doUVs:
        lmData = file.read(4 * rsOPolygonCount)
    else:
        lmData = file.read(fileSize - file.tell())

    file.seek(4, os.SEEK_SET)
    writeUInt(file, LM_VERSION_EXT if state.lmVersion4 else LM_VERSION)

    skipBytes(file, 4 + 4) # skip invalid (auxiliary?) polygon count and unused node count

    writeUInt(file, len(imageDatas))

    pixelCount = imageSize ** 2

    ddsSize = 76 + 32 + 20 + pixelCount // 2
    bmpSize = 14 + 40 + pixelCount * 3

    for d, imageData in enumerate(imageDatas):
        writeUInt(file, ddsSize if state.lmVersion4 else bmpSize)

        if state.lmVersion4:    writeDDSHeader(file, imageSize, pixelCount, bmpSize)
        else:                   writeBMPHeader(file, imageSize, bmpSize)

        file.write(imageData)

    if state.doUVs:
        file.write(lmData) # file.write(newPolyIDs)
        file.write(newIndices)
        file.write(newUVs)
    else:
        file.write(lmData)

    file.truncate()
    file.close()

    imgpath = os.path.join(directory, filename) + "_LmImage" + ('.dds' if state.lmVersion4 else '.bmp')
    file = io.open(imgpath, 'wb')

    for d, imageData in enumerate(imageDatas):
        if state.lmVersion4:    writeDDSHeader(file, imageSize, pixelCount, ddsSize)
        else:                   writeBMPHeader(file, imageSize, bmpSize)

        file.write(imageData)

    file.close()

    return { 'FINISHED' }
