#####
# Most of the code is based on logic found in...
#
### GunZ 1
# - RBspObject.h/.cpp
# - RBspObject_bsp.cpp
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

        # Read RS
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
            uv3 = uvLayer3.data[v].uv

            newUVFloats[v * 2 + 0] = uv3.x
            newUVFloats[v * 2 + 1] = 1 - uv3.y

        # newPolyIDInts.release()
        newIndexInts.release()
        newUVFloats.release()

    shutil.copy2(lmpath, os.path.join(directory, filename + "_backup") + '.' + splitname[1] + '.' + splitname[2])

    # Read LM
    file = io.open(lmpath, 'r+b')
    file.seek(0, os.SEEK_END)
    fileSize = file.tell()
    file.seek(0, os.SEEK_SET)

    id = readUInt(file)
    version = readUInt(file)
    lmOPolygonCount = readUInt(file)
    lmONodeCount = readUInt(file)
    imageCount = readUInt(file)

    if id != LM_ID or version not in (LM_VERSION, LM_VERSION_EXT):
        self.report({ 'ERROR' }, f"GZRS2: LM header invalid! { hex(id) }, { hex(version) }")
        file.close()
        return { 'CANCELLED' }

    if lmOPolygonCount != state.rsOPolygonCount or lmONodeCount != state.rsONodeCount:
        self.report({ 'ERROR' }, f"GZRS2: LM topology does not match! { lmOPolygonCount }, { state.rsOPolygonCount }, { lmONodeCount }, { state.rsONodeCount }")
        file.close()
        return { 'CANCELLED' }

    for _ in range(imageCount):
        skipBytes(file, readUInt(file)) # skip image data

    if state.doUVs:
        lmDataBackup = file.read(4 * state.rsOPolygonCount) # backup polygon order
    else:
        lmDataBackup = file.read(fileSize - file.tell()) # backup polygon order, lightmap ids and uvs

    # Write LM
    file.seek(4, os.SEEK_SET)

    if state.logLmHeaders or state.logLmImages:
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
        file.write(lmDataBackup) # file.write(newPolyIDs)
        file.write(newIndices)
        file.write(newUVs)
    else:
        file.write(lmDataBackup)

    file.truncate()
    file.close()

    # Dump Images
    imgpath = os.path.join(directory, filename) + "_LmImage" + ('.dds' if state.lmVersion4 else '.bmp')
    file = io.open(imgpath, 'wb')

    for d, imageData in enumerate(imageDatas):
        if state.lmVersion4:    writeDDSHeader(file, imageSize, pixelCount, ddsSize)
        else:                   writeBMPHeader(file, imageSize, bmpSize)

        file.write(imageData)

    file.close()

    return { 'FINISHED' }
