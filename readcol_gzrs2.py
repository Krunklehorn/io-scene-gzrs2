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

    trisRead = 0

    if version == COL1_VERSION:
        nodeCount = readUInt(file)
        totalTris = readUInt(file)
        n = 0

        if state.logColHeaders:
            print(f"Node Count:         { nodeCount }")
            print(f"Total Triangles:    { totalTris }")
            print()

        def openCol1Node():
            nonlocal n, trisRead

            if not state.logColNodes: skipBytes(file, 4 * 4) # skip plane
            else: plane = readPlane(file, True)

            hull = not readBool(file)

            if readBool(file): openCol1Node() # positive
            if readBool(file): openCol1Node() # negative

            triCount = readUInt(file)
            trisRead += triCount

            if state.logColNodes:
                print(f"===== Node { n } =============================")
                print("Plane:              ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*plane))
                print(f"Hull:               { hull }")
                print(f"Triangle Count:     { triCount }")
                print()

            for t in range(triCount):
                if not state.logColTris:
                    if hull:
                        for _ in range(3): state.colVerts.append(readCoordinate(file, state.convertUnits, True))
                    else:
                        skipBytes(file, 4 * 3 * 3)

                    skipBytes(file, 4 * 3) # skip normal
                else:
                    vertices = readCoordinateArray(file, 3, state.convertUnits, True)

                    if hull:
                        state.colVerts.extend(vertices)

                    nor = readDirection(file, True)

                    print(f"===== Triangle { t } ===========================")
                    print("Vertices:           ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*vertices[0]))
                    print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*vertices[1]))
                    print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*vertices[2]))
                    print("Normal:             ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*nor))
                    print()

            n += 1

        openCol1Node()
    else:
        totalTris = readUInt(file)
        nodeCount = readUInt(file)
        n = 0

        if state.logColHeaders:
            print(f"Node Count:         { nodeCount }")
            print(f"Total Triangles:    { totalTris }")
            print()

        def openCol2Node():
            nonlocal n, trisRead

            if not state.logColNodes: skipBytes(file, 4 * 3 * 2) # skip bounding box
            else: bounds = readBounds(file, state.convertUnits, False)

            if not readBool(file):
                openCol2Node() # positive
                openCol2Node() # negative
            else:
                triCount = readUInt(file)
                trisRead += triCount

                if state.logColNodes:
                    print(f"===== Node { n } =============================")
                    print("Bounds:             ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*bounds[0]))
                    print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*bounds[1]))
                    print(f"Triangle Count:     { triCount }")
                    print()

                for t in range(triCount):
                    if not state.logColTris:
                        for _ in range(3): state.colVerts.append(readCoordinate(file, state.convertUnits, False))
                        skipBytes(file, 4 * 2) # skip attributes and material ID
                    else:
                        vertices = readCoordinateArray(file, 3, state.convertUnits, False)
                        for v in vertices: state.colVerts.append(v)
                        attributes = readUInt(file)
                        matID = readUInt(file)

                        print(f"===== Triangle { t } ===========================")
                        print("Vertices:           ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*vertices[0]))
                        print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*vertices[1]))
                        print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*vertices[2]))
                        print(f"Attributes:         { attributes }")
                        print(f"Material ID:        { matID }")
                        print()
            n += 1

        openCol2Node()

    if trisRead != totalTris:
        self.report({ 'ERROR' }, f"GZRS2: The number of Col triangles read did not match the recorded count! { trisRead }, { totalTris }")

    if state.logColHeaders or state.logColNodes or state.logColTris:
        bytesRemaining = fileSize - file.tell()

        if bytesRemaining > 0:
            self.report({ 'ERROR' }, f"GZRS2: COL import finished with bytes remaining! { path }, { hex(id) }, { hex(version) }")

        print(f"Bytes Remaining:    { bytesRemaining }")
        print()
