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

import os, math

import struct
from struct import unpack

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .io_gzrs2 import *

def readRs(self, path, state):
    file = open(path, 'rb')

    if state.logRsPortals or state.logRsCells or state.logRsGeometry or state.logRsTrees or state.logRsLeaves or state.logRsVerts:
        print("===================  Read RS  ===================")
        print()

        file.seek(0, os.SEEK_END)
        fileSize = file.tell()
        file.seek(0, os.SEEK_SET)

    id = readUInt(file)
    version = readUInt(file)

    if state.logRsPortals or state.logRsCells or state.logRsGeometry or state.logRsTrees or state.logRsLeaves or state.logRsVerts:
        print(f"Path:               { path }")
        print(f"ID:                 { hex(id) }")
        print(f"Version:            { hex(version) }")
        print()

    if not (id == RS2_ID or id == RS3_ID) or version < RS3_VERSION1:
        self.report({ 'ERROR' }, f"GZRS2: RS header invalid! { hex(id) }, { hex(version) }")
        file.close()

        return { 'CANCELLED' }

    if id == RS2_ID and version == RS2_VERSION:
        matCount = readInt(file)

        if matCount != len(state.xmlRsMats):
            self.report({ 'ERROR' }, f"GZRS2: RS material count did not match the XML parse! { matCount }, { len(state.xmlRsMats) }")
            file.close()

            return { 'CANCELLED' }

        for _ in range(matCount): # skip packed material strings
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
        state.lmPolygonCount = readUInt(file)
        state.lmVertexCount = readInt(file)
        skipBytes(file, 4) # skip indices count

        vertexOffset = 0
        l = 0

        def openRS2BspNode():
            nonlocal state, vertexOffset, l

            state.bspBounds.append(readBounds(file, state.convertUnits, state.convertUnits))

            skipBytes(file, 4 * 4) # skip plane

            if readBool(file): openRS2BspNode() # positive
            if readBool(file): openRS2BspNode() # negative

            for _ in range(readUInt(file)):
                leafMatID = readInt(file)
                lightmapIndex = readInt(file)
                drawFlags = readUInt(file)
                leafVertexCount = readInt(file)

                for v in range(leafVertexCount):
                    pos = readCoordinate(file, state.convertUnits, True)
                    nor = readDirection(file, True)
                    uv1 = readUV2(file)
                    uv2 = readUV2(file)

                    # Why does the second UV layer end up as garbage? I don't understand...
                    # file.seek(-8, os.SEEK_CUR)
                    # uv1x = file.read(4)
                    # uv1y = file.read(4)
                    # print(v, format(int.from_bytes(uv1x, 'little'), '0>32b'), format(int.from_bytes(uv1y, 'little'), '0>32b'), struct.unpack('<f', uv1x)[0], struct.unpack('<f', uv1y)[0])

                    state.rsVerts.append(RsVertex(pos, nor, (0, 0, 0), 1, uv1, uv2))

                    if state.logRsVerts:
                        print(f"===== Vertex { v + 1 }   ===========================")
                        print("Position:           ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*pos))
                        print("Normal:             ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*nor))
                        print("UV1:                ({:>6.03f}, {:>6.03f})".format(*uv1))
                        print("UV2:                ({:>6.03f}, {:>6.03f})".format(*uv2))
                        print()

                skipBytes(file, 4 * 3) # skip plane normal

                if not (0 <= leafMatID < len(state.xmlRsMats)):
                    self.report({ 'INFO' }, f"GZRS2: Material ID out of bounds, setting to 0 and continuing. { leafMatID }, { len(state.xmlRsMats) }")
                    leafMatID = 0

                state.rsLeaves.append(RsLeaf(leafMatID, drawFlags, leafVertexCount, vertexOffset))
                vertexOffset += leafVertexCount

                if state.logRsLeaves:
                    print(f"===== Leaf { l + 1 }     =============================")
                    print(f"Material ID:        { leafMatID }")
                    print(f"Lightmap Index:     { lightmapIndex }")
                    print(f"Draw Flags:         { drawFlags }")
                    print(f"Vertex Count:       { leafVertexCount }")
                    print(f"Vertex Offset:      { vertexOffset }")
                    print()

                l += 1

        openRS2BspNode()

        if len(state.rsVerts) != state.lmVertexCount:
            self.report({ 'ERROR' }, f"GZRS2: Bsp vertex count did not match vertices written! { len(state.rsVerts) }, { state.lmVertexCount }")
    elif id == RS3_ID and version >= RS3_VERSION1:
        if not version in RS_SUPPORTED_VERSIONS:
            self.report({ 'ERROR' }, f"GZRS2: RS3 version is not supported yet! Model will not load properly! Please submit to Krunk#6051 for testing! { path }, { hex(version) }")
            file.close()

            return { 'CANCELLED' }

        for p in range(readUInt(file)):
            name = readString(file, readInt(file))
            vertices = tuple(readVec3(file) for _ in range(readUInt(file)))
            cellID1 = readInt(file)
            cellID2 = readInt(file)

            state.smrPortals.append(RsPortal(name, vertices, cellID1, cellID2))

            if state.logRsPortals:
                print(f"===== Portal { p + 1 }   ===========================")
                print(f"Name:               { name }")
                print(f"Vertices:           { len(vertices) }")
                print(f"Cell ID 1:          { cellID1 }")
                print(f"Cell ID 2:          { cellID2 }")
                print()

        for c in range(readUInt(file)):
            name = readString(file, readInt(file))
            planes = tuple(readVec4(file) for _ in range(readUInt(file)))
            faces = ()
            geometryCount = 1

            if version >= RS3_VERSION4:
                faces = tuple(tuple(readVec3(file) for _ in range(readUInt(file))) for _ in range(readUInt(file)))

            if version >= RS3_VERSION2:
                geometryCount = readInt(file)

            geometry = []
            for g in range(geometryCount):
                if version >= RS3_VERSION2: skipBytes(file, 4) # skip FVF flags
                skipBytes(file, 4) # skip node count
                polyInfoCount = readInt(file)
                geoVertexCount = readInt(file)
                indexCount = readInt(file)

                for v in range(geoVertexCount):
                    pos = readCoordinate(file, state.convertUnits, False)
                    nor = readDirection(file, False)

                    col = (1, 1, 1)
                    alpha = 1

                    if version >= RS3_VERSION2:
                        col = readVec3(file)
                        alpha = min(col[0] + col[1] + col[2] / 3, 1)

                    uv1 = readUV2(file)
                    uv2 = readUV2(file)

                    state.rsVerts.append(RsVertex(pos, nor, col, alpha, uv1, uv2))

                    if state.logRsVerts:
                        print(f"===== Vertex { v + 1 }   ===========================")
                        print("Position:           ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*pos))
                        print("Normal:             ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*nor))
                        print("Color:              ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*col, alpha))
                        print("UV1:                ({:>6.03f}, {:>6.03f})".format(*uv1))
                        print("UV2:                ({:>6.03f}, {:>6.03f})".format(*uv2))
                        print()

                vertexOffset = 0

                trees = []
                for t in range(readUInt(file)):
                    matCount = readInt(file)
                    lightmapID = readInt(file)
                    treeVertexCount = readInt(file)
                    l = 0

                    def openRS3BspNode():
                        nonlocal state, vertexOffset, l

                        state.bspBounds.append(readBounds(file, state.convertUnits, state.convertUnits))

                        if not readBool(file):
                            openRS3BspNode() # positive
                            openRS3BspNode() # negative

                        for _ in range(readUInt(file)):
                            leafMatID = readInt(file)
                            drawFlags = readUInt(file)

                            if version >= RS3_VERSION2:
                                drawFlags = RM_FLAG_COLLISION_MESH

                            leafVertexCount = readInt(file)
                            skipBytes(file, 4) # skip vertex offset, we determine our own

                            state.rsLeaves.append(RsLeaf(leafMatID, drawFlags, leafVertexCount, vertexOffset))
                            vertexOffset += leafVertexCount

                            if state.logRsLeaves:
                                print(f"===== Leaf { l + 1 }     =============================")
                                print(f"Material ID:        { leafMatID }")
                                print(f"Draw Flags:         { drawFlags }")
                                print(f"Vertex Count:       { leafVertexCount }")
                                print(f"Vertex Offset:      { vertexOffset }")
                                print()

                            l += 1

                    openRS3BspNode()

                    trees.append(RsTree(matCount, lightmapID, treeVertexCount))
                    state.lmVertexCount += vertexOffset

                    if state.logRsTrees:
                        print(f"===== Tree { t + 1 }     =============================")
                        print(f"Material Count:     { matCount }")
                        print(f"Lightmap ID:        { lightmapID }")
                        print(f"Vertex Count:       { treeVertexCount }")
                        print(f"Vertex Offset:      { vertexOffset }")
                        print()

                geometry.append(RsGeometry(geoVertexCount, indexCount, tuple(trees)))

                if state.logRsGeometry:
                    print(f"===== Geometry { g + 1 } =============================")
                    print(f"Vertex Count:       { geoVertexCount }")
                    print(f"Index Count:        { indexCount }")
                    print(f"Trees:              { len(trees) }")
                    print()

            state.smrCells.append(RsCell(name, planes, faces, tuple(geometry)))

            if state.logRsCells:
                print(f"===== Cell { c + 1 }     =============================")
                print(f"Name:               { name }")
                print(f"Planes:             { len(planes) }")
                print(f"Faces:              { len(faces) }")
                print(f"Geometry:           { len(geometry) }")
                print()

    if state.logRsPortals or state.logRsCells or state.logRsGeometry or state.logRsTrees or state.logRsLeaves or state.logRsVerts:
        bytesRemaining = fileSize - file.tell()

        if bytesRemaining > 0:
            self.report({ 'INFO' }, f"GZRS2: RS import finished with bytes remaining! { path }, { hex(id) }, { hex(version) }")

        print(f"Bytes Remaining:    { bytesRemaining }")
        print()

    file.close()
