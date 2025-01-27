#####
# Most of the code is based on logic found in...
#
### GunZ 1
# - RBspObject.h/.cpp
# - RBspObject_bsp.cpp
#
# Please report maps and models with unsupported features to me on Discord: Krunk#6051
#####

import bpy, os, io, math

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

    state.doUVs         = self.doUVs
    state.lmVersion4    = self.lmVersion4
    state.mod4Fix       = self.mod4Fix and not self.lmVersion4

    if self.panelLogging:
        print()
        print("=======================================================================")
        print("===========================  RSLM Export  =============================")
        print("=======================================================================")
        print(f"== { self.filepath }")
        print("=======================================================================")
        print()

        state.logLmHeaders = self.logLmHeaders

    lmpath = self.filepath
    directory = os.path.dirname(lmpath)
    basename = bpy.path.basename(lmpath)
    splitname = basename.split(os.extsep)
    filename = splitname[0]

    if state.doUVs:
        blMeshObj = context.active_object if context.active_object in getSelectedObjects(context) else None

        if blMeshObj is None or blMeshObj.type != 'MESH' or not blMeshObj.select_get():
            self.report({ 'ERROR' }, "GZRS2: Lightmap UV export requires an active mesh object with valid UVs in channel 2!")
            return { 'CANCELLED' }

        blMesh = blMeshObj.data

        if len(blMesh.uv_layers) < 2:
            self.report({ 'ERROR' }, "GZRS2: Lightmap UV export requires an active mesh object with valid UVs in channel 2!")
            return { 'CANCELLED' }

        uvLayer2 = blMesh.uv_layers[1]

        # Read RS
        rspath = pathExists(os.path.splitext(lmpath)[0])

        if not rspath:
            self.report({ 'ERROR' }, "GZRS2: Lightmap UV export requires a GunZ 1 .rs file for the same map in the same directory!")
            return { 'CANCELLED' }

        with open(rspath, 'rb') as file:
            if state.logLmHeaders:
                print("===================  Read Rs  ===================")
                print()

            id = readUInt(file)
            version = readUInt(file)

            if state.logLmHeaders:
                print(f"Path:               { rspath }")
                print(f"ID:                 { hex(id) }")
                print(f"Version:            { hex(version) }")
                print()

            if not (id == RS2_ID or id == RS3_ID) or version < RS3_VERSION1:
                self.report({ 'ERROR' }, f"GZRS2: RS header invalid! { hex(id) }, { hex(version) }")
                return { 'CANCELLED' }

            if id == RS2_ID and version == RS2_VERSION:
                for _ in range(readInt(file)): # skip packed material strings
                    for __ in range(RS_PATH_LENGTH):
                        if file.read(1) == b'\x00':
                            break

                state.rsCPolygonCount = readInt(file)
                skipBytes(file, 4) # skip convex vertex count

                for _ in range(state.rsCPolygonCount):
                    skipBytes(file, 4 + 4 + (4 * 4) + 4) # skip material id, draw flags, plane and area data
                    skipBytes(file, 2 * readInt(file) * 4 * 3) # skip vertex data and normal data

                skipBytes(file, 4 * 4) # skip counts for bsp nodes, polygons, vertices and indices

                state.rsONodeCount = readUInt(file)
                state.rsOPolygonCount = readUInt(file)
                state.rsOVertexCount = readInt(file)
                skipBytes(file, 4) # skip octree indices count
            else:
                self.report({ 'ERROR' }, f"GZRS2: RS file must be for GunZ 1! { hex(id) }, { hex(version) }")
                return { 'CANCELLED' }

    imageDatas = []

    worldProps = ensureWorld(context).gzrs2
    lightmapImage = worldProps.lightmapImage

    if lightmapImage is None:
        self.report({ 'ERROR' }, "GZRS2: No lightmap assigned! Check the World tab!")
        return { 'CANCELLED' }

    imageName = lightmapImage.name
    imageWidth, imageHeight = lightmapImage.size
    mipCount = math.log2(imageWidth)

    if imageWidth == 0 or imageWidth != imageHeight or not mipCount.is_integer():
        self.report({ 'ERROR' }, "GZRS2: Lightmap is not valid! Image must be a square, power of two texture!")
        return { 'CANCELLED' }

    mipCount = int(mipCount)

    # Never atlas, we increase the lightmap resolution instead
    # numCells = worldProps.lightmapNumCells
    numCells = 1

    if numCells < 2:
        imageSize = imageWidth
        floats = image.pixels[:]

        imageDatas.append(packLmImageData(self, imageSize, floats, state))
    '''
    else:
        cellSpan = int(math.sqrt(nextSquare(numCells)))
        atlasSize = imageWidth
        imageSize = atlasSize // cellSpan
        floats = image.pixels[:]

        for c in range(numCells):
            cx = c % cellSpan
            cy = cellSpan - 1 - c // cellSpan

            imageDatas.append(packLmImageData(self, imageSize, floats, state, fromAtlas = True, atlasSize = atlasSize, cx = cx, cy = cy))
    '''

    imageDatas = tuple(imageDatas)

    # Read LM
    createBackupFile(lmpath)

    with open(lmpath, 'r+b') as file:
        file.seek(0, os.SEEK_END)
        fileSize = file.tell()
        file.seek(0, os.SEEK_SET)

        id = readUInt(file)
        version = readUInt(file)
        lmCPolygonCount = readUInt(file) # CONVEX polygon count!
        lmONodeCount = readUInt(file) # OCTREE node count!
        imageCount = readUInt(file)

        if id != LM_ID or version not in (LM_VERSION, LM_VERSION_EXT):
            self.report({ 'ERROR' }, f"GZRS2: LM header invalid! { hex(id) }, { hex(version) }")
            return { 'CANCELLED' }

        if state.rsCPolygonCount is not None or state.rsONodeCount is not None:
            if lmCPolygonCount != state.rsCPolygonCount or lmONodeCount != state.rsONodeCount:
                self.report({ 'ERROR' }, f"GZRS2: LM topology does not match! { lmCPolygonCount }, { state.rsCPolygonCount }, { lmONodeCount }, { state.rsONodeCount }")
                return { 'CANCELLED' }

        for _ in range(imageCount):
            skipBytes(file, readUInt(file)) # skip image data

        if state.doUVs:
            lmDataBackup = file.read(4 * state.rsOPolygonCount) # backup polygon order
        else:
            lmDataBackup = file.read(fileSize - file.tell()) # backup polygon order, lightmap ids and uvs

        # Write LM
        file.seek(4, os.SEEK_SET)

        if state.logLmHeaders:
            print("===================  Write Lm  ===================")
            print()

        writeUInt(file, LM_VERSION_EXT if state.lmVersion4 else LM_VERSION)
        skipBytes(file, 4 + 4) # skip octree polygon count and node count
        writeUInt(file, len(imageDatas))

        if state.logLmHeaders:
            print(f"Path:               { lmpath }")
            print(f"ID:                 { hex(id) }")
            print(f"Version:            { hex(version) }")
            print(f"Image Count:        { len(imageDatas) }")
            print()

        pixelCount = imageSize ** 2

        ddsSize = 76 + 32 + 20 + pixelCount // 2
        bmpSize = 14 + 40 + pixelCount * 3

        for d, imageData in enumerate(imageDatas):
            writeUInt(file, ddsSize if state.lmVersion4 else bmpSize)

            if state.lmVersion4:    writeDDSHeader(file, imageSize, pixelCount, bmpSize)
            else:                   writeBMPHeader(file, imageSize, bmpSize)

            file.write(imageData)

        if state.doUVs:
            # TODO: During .rs export we can determine our own polygon order, otherwise we have to infer it
            # newPolyIDs = bytearray(state.rsOPolygonCount * 4)
            newIndices = bytearray(state.rsOPolygonCount * 4)
            newUVs = bytearray(state.rsOVertexCount * 2 * 4)

            # newPolyIDInts = memoryview(newPolyIDs).cast('I')
            newIndexInts = memoryview(newIndices).cast('I')
            newUVFloats = memoryview(newUVs).cast('f')

            for p in range(state.rsOPolygonCount):
                # newPolyIDInts[p] = p
                newIndexInts[p] = 0 # Never atlas, we increase the lightmap resolution instead

            for v in range(state.rsOVertexCount):
                uv2 = uvLayer2.data[v].uv

                newUVFloats[v * 2 + 0] = uv2.x
                newUVFloats[v * 2 + 1] = 1 - uv2.y

            # newPolyIDInts.release()
            newIndexInts.release()
            newUVFloats.release()

            file.write(lmDataBackup) # file.write(newPolyIDs)
            file.write(newIndices)
            file.write(newUVs)
        else:
            file.write(lmDataBackup)

        file.truncate()

    # Dump Images
    for d, imageData in enumerate(imageDatas):
        imgpath = os.path.join(directory, filename) + f"_LmImage{ d }" + ('.dds' if state.lmVersion4 else '.bmp')
        with open(imgpath, 'wb') as file:
            if state.lmVersion4:    writeDDSHeader(file, imageSize, pixelCount, ddsSize)
            else:                   writeBMPHeader(file, imageSize, bmpSize)

            file.write(imageData)

    return { 'FINISHED' }
