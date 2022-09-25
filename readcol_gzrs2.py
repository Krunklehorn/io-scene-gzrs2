#####
# Most of the code is based on logic found in...
#
### GunZ 1
# - RTypes.h
# - RToken.h
# - RBspObject.h/.cpp
# - RMaterialList.h/.cpp
# - RMesh_Load.cpp
# - RMeshUtil.h
# - MZFile.cpp
# - R_Mtrl.cpp
# - EluLoader.h/cpp
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

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .io_gzrs2 import *

def readCol(self, path, state: GZRS2State):
    file = open(path, 'rb')

    id = readUInt(file)
    version = readUInt(file)

    if (id != R_COL1_ID and id != R_COL2_ID) or (version != R_COL1_VERSION and version != R_COL2_VERSION):
        self.report({ 'ERROR' }, f"GZRS2: Col header invalid! { id }, { version }")
        file.close()

        return

    if version == R_COL1_VERSION:
        skipBytes(file, 4) # skip node count
        totalPolys = readInt(file)

        def openCol1Node():
            skipBytes(file, 4 * 4 + 1) # skip plane data and solidity bool

            if readBool(file): openCol1Node() # positive
            if readBool(file): openCol1Node() # negative

            for _ in range(readInt(file)):
                state.colVerts.append(readCoordinate(file, state.convertUnits, True))
                state.colVerts.append(readCoordinate(file, state.convertUnits, True))
                state.colVerts.append(readCoordinate(file, state.convertUnits, True))
                skipBytes(file, 4 * 3) # skip normal

        openCol1Node()
    else:
        totalPolys = readInt(file)
        skipBytes(file, 4) # skip node count

        def openCol2Node():
            skipBytes(file, 4 * 3 * 2) # skip bounding box

            if not readBool(file):
                openCol2Node() # positive
                openCol2Node() # negative

            for _ in range(readInt(file)):
                state.colVerts.append(readCoordinate(file, state.convertUnits, False))
                state.colVerts.append(readCoordinate(file, state.convertUnits, False))
                state.colVerts.append(readCoordinate(file, state.convertUnits, False))
                skipBytes(file, 4 * 2) # skip attributes and material ID

        openCol2Node()

    if len(state.colVerts) / 3 != totalPolys:
        self.report({ 'ERROR' }, f"GZRS2: The number of collider polygons read did not match the recorded count! { len(state.colVerts) / 3 }, { totalPolys }")

    file.close()
