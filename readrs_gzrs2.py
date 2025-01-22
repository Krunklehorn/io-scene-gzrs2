#####
# Most of the code is based on logic found in...
#
### GunZ 1
# - RTypes.h
# - RToken.h
# - RealSpace2.h/.cpp
# - RBspObject.h/.cpp
# - RBspObject_bsp.h/.cpp
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

import os, io, math

# import struct
# from struct import unpack

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .io_gzrs2 import *

def readRs(self, file, path, state):
    file.seek(0, os.SEEK_END)
    fileSize = file.tell()
    file.seek(0, os.SEEK_SET)

    if state.logRsHeaders or state.logRsPortals or state.logRsCells or state.logRsGeometry or state.logRsTrees or state.logRsPolygons or state.logRsVerts:
        print("===================  Read RS  ===================")
        print()

    id = readUInt(file)
    version = readUInt(file)

    if state.logRsHeaders:
        print(f"Path:               { path }")
        print(f"ID:                 { hex(id) }")
        print(f"Version:            { hex(version) }")
        print()

    if not (id == RS2_ID or id == RS3_ID) or version < RS3_VERSION1:
        self.report({ 'ERROR' }, f"GZRS2: RS header invalid! { hex(id) }, { hex(version) }")
        return { 'CANCELLED' }

    if id == RS2_ID and version == RS2_VERSION:
        matCount = readInt(file)

        if matCount != len(state.xmlRsMats):
            self.report({ 'WARNING' }, f"GZRS2: RS material count did not match the XML parse! Corruption may occur! { matCount }, { len(state.xmlRsMats) }")

        for _ in range(matCount): # skip packed material strings
            for __ in range(256):
                if file.read(1) == b'\x00':
                    break

        state.rsCPolygonCount = readUInt(file)
        state.rsCVertexCount = readUInt(file)

        if state.logRsHeaders:
            print(f"Convex Polygons:    { state.rsCPolygonCount }")
            print(f"Convex Vertices:    { state.rsCVertexCount }")
            print()

        for p in range(state.rsCPolygonCount):
            skipBytes(file, 4 + 4 + 4 * 4 + 4) # skip material id, draw flags, plane and area data
            skipBytes(file, 2 * readUInt(file) * 3 * 4) # skip vertex positions and normals

        # TODO: Improve performance of convex id matching
        '''
        vertexOffset = 0

        for p in range(state.rsCPolygonCount):
            matID = readInt(file)
            drawFlags = readUInt(file)
            skipBytes(file, 4 * 4 + 4) # skip plane and area data
            vertexCount = readUInt(file)

            positions = readCoordinateArray(file, vertexCount, state.convertUnits, True)
            normals = readDirectionArray(file, vertexCount, True)

            for v in range(vertexCount):
                pos = positions[v]
                nor = normals[v]

                state.rsConvexVerts.append(Rs2ConvexVertex(pos, nor, (0, 0), (0, 0), -1))

                if state.logRsVerts:
                    print(f"===== Vertex { v }   ===========================")
                    print("Position:           ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*pos))
                    print("Normal:             ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*nor))
                    print()

            state.rsConvexPolygons.append(RsConvexPolygon(matID, drawFlags, vertexCount, vertexOffset))
            vertexOffset += vertexCount

            if state.logRsPolygons:
                print(f"===== Polygon { p }  =============================")
                print(f"Material ID:        { matID }")
                print(f"Draw Flags:         { drawFlags }")
                print(f"Vertex Count:       { vertexCount }")
                print(f"Vertex Offset:      { vertexOffset }")
                print()

        if state.rsCPolygonCount != len(state.rsConvexPolygons):
            self.report({ 'ERROR' }, f"GZRS2: RS convex polygon count did not match polygons written! { state.rsCPolygonCount }, { len(state.rsConvexPolygons) }")

        if state.rsCVertexCount != len(state.rsConvexVerts):
            self.report({ 'ERROR' }, f"GZRS2: RS convex vertex count did not match vertices written! { state.rsCVertexCount }, { len(state.rsConvexVerts) }")
        '''
        state.rsBNodeCount = readUInt(file)
        state.rsBPolygonCount = readUInt(file)
        state.rsBVertexCount = readUInt(file)
        skipBytes(file, 4) # skip bsp indices count

        state.rsONodeCount = readUInt(file)
        state.rsOPolygonCount = readUInt(file)
        state.rsOVertexCount = readInt(file)
        skipBytes(file, 4) # skip octree indices count

        if state.logRsHeaders:
            print(f"Octree Nodes:       { state.rsONodeCount }")
            print(f"Octree Polygons:    { state.rsOPolygonCount }")
            print(f"Octree Vertices:    { state.rsOVertexCount }")
            print()

        nodeCount = 0
        vertexOffset = 0
        p = 0

        def openRS2OctreeNode():
            nonlocal nodeCount, vertexOffset, p

            state.rsOctreeBounds.append(readBounds(file, state.convertUnits, True))

            skipBytes(file, 4 * 4) # skip plane

            if readBool(file): openRS2OctreeNode() # positive
            if readBool(file): openRS2OctreeNode() # negative

            for _ in range(readUInt(file)):
                matID = readInt(file)
                convexID = readUInt(file)
                drawFlags = readUInt(file)
                vertexCount = readUInt(file)

                for v in range(vertexCount):
                    pos = readCoordinate(file, state.convertUnits, True)
                    nor = readDirection(file, True)
                    uv1 = readUV2(file)
                    uv2 = readUV2(file) # lightmap uvs are always garbled for vanilla maps, so we get them from the .lm file instead

                    state.rsOctreeVerts.append(Rs2OctreeVertex(pos, nor, uv1, uv2))

                    if state.logRsVerts:
                        print(f"===== Vertex { v }   ===========================")
                        print("Position:           ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*pos))
                        print("Normal:             ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*nor))
                        print("UV1:                ({:>6.03f}, {:>6.03f})".format(*uv1))
                        print("UV2:                ({:>6.03f}, {:>6.03f})".format(*uv2))
                        print()

                skipBytes(file, 4 * 3) # skip face normal

                if convexID < 0 or convexID >= state.rsCPolygonCount:
                    self.report({ 'ERROR' }, f"GZRS2: Convex ID out of bounds! Please submit to Krunk#6051 for testing!")
                    return { 'CANCELLED' }
                # TODO: Improve performance of convex id matching
                '''
                elif state.rsConvexPolygons[convexID].matID != matID:
                    self.report({ 'WARNING' }, f"GZRS2: Octree material ID did not match convex material ID! Please submit to Krunk#6051 for testing!")
                '''

                if not (0 <= matID < len(state.xmlRsMats)): # TODO: Perhaps we should wait and assign the error material instead...
                    self.report({ 'WARNING' }, f"GZRS2: Material ID out of bounds, setting to 0 and continuing. { matID }, { len(state.xmlRsMats) }")
                    matID = 0

                state.rsOctreePolygons.append(Rs2OctreePolygon(matID, convexID, drawFlags, vertexCount, vertexOffset))
                vertexOffset += vertexCount

                if state.logRsPolygons:
                    print(f"===== Polygon { p }  =============================")
                    print(f"Material ID:        { matID }")
                    print(f"Convex ID:          { convexID }")
                    print(f"Draw Flags:         { drawFlags }")
                    print(f"Vertex Count:       { vertexCount }")
                    print(f"Vertex Offset:      { vertexOffset }")
                    print()

                p += 1
            nodeCount += 1

        openRS2OctreeNode()

        if state.rsONodeCount != nodeCount:
            self.report({ 'ERROR' }, f"GZRS2: RS octree node count did not match nodes traversed! { state.rsONodeCount }, { nodeCount }")

        if state.rsOPolygonCount != len(state.rsOctreePolygons):
            self.report({ 'ERROR' }, f"GZRS2: RS octree polygon count did not match polygons written! { state.rsOPolygonCount }, { len(state.rsOctreePolygons) }")

        if state.rsOVertexCount != len(state.rsOctreeVerts):
            self.report({ 'ERROR' }, f"GZRS2: RS octree vertex count did not match vertices written! { state.rsOVertexCount }, { len(state.rsOctreeVerts) }")

        # TODO: Improve performance of convex id matching
        '''
        # The octree polygons hold the UV data, so we need to infer them
        # This will fail if any polygons are degenerate or just too small
        warnDistanceThreshold = False
        warnNormalThreshold = False

        for p1, convexPolygon in enumerate(state.rsConvexPolygons):
            for v1 in range(convexPolygon.vertexOffset, convexPolygon.vertexOffset + convexPolygon.vertexCount):
                convexVertex = state.rsConvexVerts[v1]
                convexNormal = state.rsConvexVerts[v1].nor
                octreeMatches = []

                for octreePolygon in state.rsOctreePolygons:
                    if octreePolygon.convexID != p1:
                        continue

                    for v2 in range(octreePolygon.vertexOffset, octreePolygon.vertexOffset + octreePolygon.vertexCount):
                        octreeMatches.append((v2, (convexVertex.pos - state.rsOctreeVerts[v2].pos).length_squared))

                if len(octreeMatches) == 0:
                    self.report({ 'ERROR' }, f"GZRS2: RS vertex match failed! Please submit to Krunk#6051 for testing!")
                    return { 'CANCELLED' }

                octreeMatch = sorted(octreeMatches, key = lambda x : x[1])[0]
                octreeVertex = state.rsOctreeVerts[octreeMatch[0]]
                octreeNormal = octreeVertex.nor

                if octreeMatch[1] > RS_VERTEX_THRESHOLD_SQUARED:
                    warnDistanceThreshold = True

                if not all((math.isclose(convexNormal.x, octreeNormal.x, abs_tol = RS_VERTEX_THRESHOLD),
                            math.isclose(convexNormal.y, octreeNormal.y, abs_tol = RS_VERTEX_THRESHOLD),
                            math.isclose(convexNormal.z, octreeNormal.z, abs_tol = RS_VERTEX_THRESHOLD))):
                    warnNormalThreshold = True

                convexVertex.uv1 = octreeVertex.uv1
                convexVertex.uv2 = octreeVertex.uv2
                convexVertex.oid = octreeMatch[0]

        if warnDistanceThreshold:
            self.report({ 'WARNING' }, f"GZRS2: RS vertex match indexed a convex vertex beyond the threshold! Please submit to Krunk#6051 for testing!")

        if warnNormalThreshold:
            self.report({ 'WARNING' }, f"GZRS2: RS vertex match indexed a convex vertex with a normal outside the acceptable tolerance! Please submit to Krunk#6051 for testing!")
        '''
    elif id == RS3_ID and version >= RS3_VERSION1:
        if version not in RS_SUPPORTED_VERSIONS:
            self.report({ 'ERROR' }, f"GZRS2: RS3 version is not supported yet! Model will not load properly! Please submit to Krunk#6051 for testing! { path }, { hex(version) }")
            return { 'CANCELLED' }

        for p in range(readUInt(file)):
            name = readString(file, readInt(file))
            vertices = tuple(readVec3(file) for _ in range(readUInt(file)))
            cellID1 = readInt(file)
            cellID2 = readInt(file)

            state.smrPortals.append(RsPortal(name, vertices, cellID1, cellID2))

            if state.logRsPortals:
                print(f"===== Portal { p }   ===========================")
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
                skipBytes(file, 4 + 4) # skip node count and polygon info count
                geoVertexCount = readInt(file)
                indexCount = readInt(file)

                for v in range(geoVertexCount):
                    pos = readCoordinate(file, state.convertUnits, False)
                    nor = readDirection(file, False)

                    if version >= RS3_VERSION2:
                        col = readVec3(file)
                        col = Vector((col.x, col.y, col.z, min(col.x + col.y + col.z / 3, 1)))
                    else:
                        col = (1, 1, 1, 1)

                    uv1 = readUV2(file)
                    uv2 = readUV2(file)

                    state.rsOctreeVerts.append(Rs3OctreeVertex(pos, nor, col, uv1, uv2))

                    if state.logRsVerts:
                        print(f"===== Vertex { v }   ===========================")
                        print("Position:           ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*pos))
                        print("Normal:             ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*nor))
                        print("Color:              ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*col))
                        print("UV1:                ({:>6.03f}, {:>6.03f})".format(*uv1))
                        print("UV2:                ({:>6.03f}, {:>6.03f})".format(*uv2))
                        print()

                vertexOffset = 0

                trees = []
                for t in range(readUInt(file)):
                    matCount = readInt(file)
                    lightmapID = readInt(file)
                    treeVertexCount = readInt(file)
                    p = 0

                    def openRS3OctreeNode():
                        nonlocal vertexOffset, p

                        state.rsOctreeBounds.append(readBounds(file, state.convertUnits, False))

                        if not readBool(file):
                            openRS3OctreeNode() # positive
                            openRS3OctreeNode() # negative

                        for _ in range(readUInt(file)):
                            matID = readInt(file)
                            drawFlags = readUInt(file)

                            if version >= RS3_VERSION2:
                                drawFlags = RM_FLAG_COLLISION_MESH

                            vertexCount = readInt(file)
                            skipBytes(file, 4) # skip vertex offset, we determine our own TODO: verify?

                            state.rsOctreePolygons.append(Rs3OctreePolygon(matID, drawFlags, vertexCount, vertexOffset))
                            vertexOffset += vertexCount

                            if state.logRsPolygons:
                                print(f"===== Polygon { p }  =============================")
                                print(f"Material ID:        { matID }")
                                print(f"Draw Flags:         { drawFlags }")
                                print(f"Vertex Count:       { vertexCount }")
                                print(f"Vertex Offset:      { vertexOffset }")
                                print()

                            p += 1

                    openRS3OctreeNode()

                    trees.append(RsTree(matCount, lightmapID, treeVertexCount))

                    if state.logRsTrees:
                        print(f"===== Tree { t }     =============================")
                        print(f"Material Count:     { matCount }")
                        print(f"Lightmap ID:        { lightmapID }")
                        print(f"Vertex Count:       { treeVertexCount }")
                        print(f"Vertex Offset:      { vertexOffset }")
                        print()

                geometry.append(RsGeometry(geoVertexCount, indexCount, tuple(trees)))

                if state.logRsGeometry:
                    print(f"===== Geometry { g } =============================")
                    print(f"Vertex Count:       { geoVertexCount }")
                    print(f"Index Count:        { indexCount }")
                    print(f"Trees:              { len(trees) }")
                    print()

            state.smrCells.append(RsCell(name, planes, faces, tuple(geometry)))

            if state.logRsCells:
                print(f"===== Cell { c }     =============================")
                print(f"Name:               { name }")
                print(f"Planes:             { len(planes) }")
                print(f"Faces:              { len(faces) }")
                print(f"Geometry:           { len(geometry) }")
                print()

    if state.logRsHeaders or state.logRsPortals or state.logRsCells or state.logRsGeometry or state.logRsTrees or state.logRsPolygons or state.logRsVerts:
        bytesRemaining = fileSize - file.tell()

        if bytesRemaining > 0:
            self.report({ 'ERROR' }, f"GZRS2: RS import finished with bytes remaining! { path }, { hex(id) }, { hex(version) }")

        print(f"Bytes Remaining:    { bytesRemaining }")
        print()
