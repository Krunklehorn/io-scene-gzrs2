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
# Please report maps and models with unsupported features to me on Discord: Krunk#6051
#####

import math, io

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .io_gzrs2 import *
from .lib_gzrs2 import *

def readBsp(self, file, path, state):
    file.seek(0, os.SEEK_END)
    fileSize = file.tell()
    file.seek(0, os.SEEK_SET)

    if state.logBspHeaders or state.logBspPolygons or state.logBspVerts:
        print("==================   Read Bsp  ===================")
        print()

    id = readUInt(file)
    version = readUInt(file)

    if state.logBspHeaders:
        print(f"Path:               { path }")
        print(f"ID:                 { hex(id) }")
        print(f"Version:            { hex(version) }")
        print()

    if id != BSP_ID or version != BSP_VERSION:
        self.report({ 'ERROR' }, f"GZRS2: BSP header invalid! { hex(id) }, { hex(version) }")
        return { 'CANCELLED' }

    state.bspNodeCount = readUInt(file)
    state.bspPolygonCount = readUInt(file)
    state.bspVertexCount = readUInt(file)
    skipBytes(file, 4) # skip bsp indices count

    if state.logBspHeaders:
        print(f"Bsptree Nodes:      { state.bspNodeCount }")
        print(f"Bsptree Polygons:   { state.bspPolygonCount }")
        print(f"Bsptree Vertices:   { state.bspVertexCount }")
        print()

    if any((state.rsBNodeCount       is not None,
            state.rsBPolygonCount    is not None,
            state.rsBVertexCount     is not None)):
        if any((state.bspNodeCount       != state.rsBNodeCount,
                state.bspPolygonCount    != state.rsBPolygonCount,
                state.bspVertexCount     != state.rsBVertexCount)):
            output = f"GZRS2: BSP topology does not match!"
            output += f" { state.bspNodeCount },"       + f" { state.rsBNodeCount },"
            output += f" { state.bspPolygonCount },"    + f" { state.rsBPolygonCount },"
            output += f" { state.bspVertexCount },"     + f" { state.rsBVertexCount }"

            self.report({ 'ERROR' }, output)
            return { 'CANCELLED' }

    # readrs_gzrs2.py
    nodeCount = 0
    vertexOffset = 0
    p = 0

    def openRSBsptreeNode():
        nonlocal nodeCount, vertexOffset, p

        state.bspTreeBounds.append(readBounds(file, state.convertUnits))

        skipBytes(file, 4 * 4) # skip plane

        if readBool(file): openRSBsptreeNode() # positive
        if readBool(file): openRSBsptreeNode() # negative

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

                state.bspTreeVerts.append(Rs2BspVertex(pos, nor, uv1, uv2))

                if state.logBspVerts:
                    print(f"===== Vertex { v }   ===========================")
                    print("Position:           ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*pos))
                    print("Normal:             ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*nor))
                    print("UV1:                ({:>6.03f}, {:>6.03f})".format(*uv1))
                    print("UV2:                ({:>6.03f}, {:>6.03f})".format(*uv2))
                    print()

            skipBytes(file, 4 * 3) # skip face normal

            if state.rsCPolygonCount is not None:
                if convexID < 0 or convexID >= state.rsCPolygonCount:
                    self.report({ 'ERROR' }, f"GZRS2: Convex ID out of bounds! Please submit to Krunk#6051 for testing!")
                    return { 'CANCELLED' }

            if not (0 <= matID < len(state.xmlRsMats)): # TODO: Perhaps we should wait and assign the error material instead...
                self.report({ 'WARNING' }, f"GZRS2: Material ID out of bounds, setting to 0 and continuing. { matID }, { len(state.xmlRsMats) }")
                matID = 0

            state.bspTreePolygons.append(Rs2BspPolygon(matID, convexID, drawFlags, vertexCount, vertexOffset))
            vertexOffset += vertexCount

            if state.logBspPolygons:
                print(f"===== Polygon { p }  =============================")
                print(f"Material ID:        { matID }")
                print(f"Convex ID:          { convexID }")
                print(f"Draw Flags:         { drawFlags }")
                print(f"Vertex Count:       { vertexCount }")
                print(f"Vertex Offset:      { vertexOffset }")
                print()

            p += 1
        nodeCount += 1

    openRSBsptreeNode()

    if state.bspNodeCount != nodeCount:
        self.report({ 'ERROR' }, f"GZRS2: BSP node count did not match nodes traversed! { state.bspNodeCount }, { nodeCount }")

    if state.bspPolygonCount != len(state.bspTreePolygons):
        self.report({ 'ERROR' }, f"GZRS2: BSP polygon count did not match polygons written! { state.bspPolygonCount }, { len(state.bspTreePolygons) }")

    if state.bspVertexCount != len(state.bspTreeVerts):
        self.report({ 'ERROR' }, f"GZRS2: BSP vertex count did not match vertices written! { state.bspVertexCount }, { len(state.bspTreeVerts) }")

    # TODO: Improve performance of convex id matching
    # TODO: Add convex id matching for bsp mesh as well

    if state.logBspHeaders or state.logBspPolygons or state.logBspVerts:
        bytesRemaining = fileSize - file.tell() if state.bspVertexCount > 0 else 0

        if bytesRemaining > 0:
            self.report({ 'ERROR' }, f"GZRS2: LM import finished with bytes remaining! { path }, { hex(id) }, { hex(version) }")

        print(f"Bytes Remaining:    { bytesRemaining }")
        print()
