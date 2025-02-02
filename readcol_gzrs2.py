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

import os, io

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .io_gzrs2 import *

def readCol(self, file, path, state):
    file.seek(0, os.SEEK_END)
    fileSize = file.tell()
    file.seek(0, os.SEEK_SET)

    if state.logColHeaders or state.logColNodes or state.logColTris:
        print("===================  Read Col  ===================")
        print()

    id = readUInt(file)
    version = readUInt(file)

    if state.logColHeaders:
        print(f"Path:               { path }")
        print(f"ID:                 { hex(id) }")
        print(f"Version:            { hex(version) }")
        print()

    if (id != COL1_ID and id != COL2_ID) or (version != COL1_VERSION and version != COL2_VERSION):
        self.report({ 'ERROR' }, f"GZRS2: Col header invalid! { hex(id) }, { hex(version) }")
        return { 'CANCELLED' }

    trianglesRead = 0

    if version == COL1_VERSION:
        colNodeCount = readUInt(file)
        colTriangleCount = readUInt(file)
        n = 0

        if state.logColHeaders:
            print(f"Node Count:         { colNodeCount }")
            print(f"Total Triangles:    { colTriangleCount }")
            print()

        def openCol1Node():
            nonlocal n, trianglesRead

            plane = readPlane(file, state.convertUnits, True)
            solid = readBool(file)

            positive = None
            negative = None

            if readBool(file): positive = openCol1Node() # positive
            if readBool(file): negative = openCol1Node() # negative

            triangleCount = readUInt(file)
            trianglesRead += triangleCount

            if state.logColNodes:
                print(f"===== Node { n } =============================")
                print("Plane:              ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*plane))
                print(f"Solid:              { solid }")
                print(f"Triangle Count:     { triangleCount }")
                print()

            triangles = []

            for t in range(triangleCount):
                vertices = readCoordinateArray(file, 3, state.convertUnits, True)
                normal = readDirection(file, True)
                triangle = ColTriangle(vertices, normal)
                triangles.append(triangle)

                if not solid:   state.colTrisHull.append(triangle)
                else:           state.colTrisSolid.append(triangle)

                if state.logColTris:
                    print(f"===== Triangle { t } ===========================")
                    print("Vertices:           ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*vertices[0]))
                    print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*vertices[1]))
                    print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*vertices[2]))
                    print("Normal:             ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*normal))
                    print()

            return Col1TreeNode(plane, solid, positive, negative, tuple(triangles))

            n += 1

        state.col1Root = openCol1Node()
    else:
        colTriangleCount = readUInt(file)
        colNodeCount = readUInt(file)
        n = 0

        if state.logColHeaders:
            print(f"Node Count:         { colNodeCount }")
            print(f"Total Triangles:    { colTriangleCount }")
            print()

        def openCol2Node():
            nonlocal n, trianglesRead

            bbmin, bbmax = readBounds(file, state.convertUnits)
            leaf = readBool(file)

            if not leaf:
                openCol2Node() # positive
                openCol2Node() # negative
            else:
                triangleCount = readUInt(file)
                trianglesRead += triangleCount

                if state.logColNodes:
                    print(f"===== Node { n } =============================")
                    print("Bounds:             ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*bbmin))
                    print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*bbmax))
                    print(f"Triangle Count:     { triangleCount }")
                    print()

                for t in range(triangleCount):
                    vertices = readCoordinateArray(file, 3, state.convertUnits, False)

                    sideA = vertices[1] - vertices[0]
                    sideC = vertices[2] - vertices[0]

                    normal = sideC.cross(sideA)
                    normal.normalize()

                    if state.logColTris:
                        attributes = readUInt(file)
                        matID = readUInt(file)

                        print(f"===== Triangle { t } ===========================")
                        print("Vertices:           ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*vertices[0]))
                        print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*vertices[1]))
                        print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*vertices[2]))
                        print(f"Attributes:         { attributes }")
                        print(f"Material ID:        { matID }")
                        print()
                    else:
                        skipBytes(file, 4 * 2) # skip attributes and material ID

                    state.colTrisHull.append(ColTriangle(vertices, normal))
            n += 1

        openCol2Node()

    if trianglesRead != colTriangleCount:
        self.report({ 'ERROR' }, f"GZRS2: The number of Col triangles read did not match the recorded count! { trianglesRead }, { colTriangleCount }")

    if state.logColHeaders or state.logColNodes or state.logColTris:
        bytesRemaining = fileSize - file.tell()

        if bytesRemaining > 0:
            self.report({ 'ERROR' }, f"GZRS2: COL import finished with bytes remaining! { path }, { hex(id) }, { hex(version) }")

        print(f"Bytes Remaining:    { bytesRemaining }")
        print()
