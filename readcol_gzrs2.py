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

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .io_gzrs2 import *

'''
from constants_gzrs2 import *
from dataclasses import dataclass, field
from io_gzrs2 import *

@dataclass
class GZRS2State:
    convertUnits:       bool = False

    logColHeaders:      bool = True
    logColNodes:        bool = False
    logColTris:         bool = False

    colVerts:           list = field(default_factory = list)
'''

def readCol(self, path, state):
    file = open(path, 'rb')

    id = readUInt(file)
    version = readUInt(file)

    if state.logColHeaders or state.logColNodes or state.logColTris:
        print("===================  Read Col  ===================")
        print()

    if state.logColHeaders:
        print(f"path:               { path }")
        print(f"ID:                 { hex(id) }")
        print(f"Version:            { hex(version) }")

    if (id != R_COL1_ID and id != R_COL2_ID) or (version != R_COL1_VERSION and version != R_COL2_VERSION):
        self.report({ 'ERROR' }, f"GZRS2: Col header invalid! { hex(id) }, { version }")
        file.close()

        return False

    trisRead = 0

    if version == R_COL1_VERSION:
        nodeCount = readUInt(file)
        totalTris = readUInt(file)
        n = 0

        if state.logColHeaders:
            print(f"Node Count:         { nodeCount }")
            print(f"Total Triangles:    { totalTris }")
            print()

        def openCol1Node():
            nonlocal state, n, trisRead

            if not state.logColNodes: skipBytes(file, 4 * 4) # skip plane
            else: plane = readPlane(file, True)

            hull = not readBool(file)

            if readBool(file): openCol1Node() # positive
            if readBool(file): openCol1Node() # negative

            triCount = readUInt(file)
            trisRead += triCount

            if state.logColNodes:
                print(f"===== Node { n + 1 } =============================")
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
                        for v in vertices: state.colVerts.append(v)

                    nor = readDirection(file, True)

                    print(f"===== Triangle { t + 1 } ===========================")
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
            nonlocal state, n, trisRead

            if not state.logColNodes: skipBytes(file, 4 * 3 * 2) # skip bounding box
            else: bounds = readBounds(file, state.convertUnits, False)

            if not readBool(file):
                openCol2Node() # positive
                openCol2Node() # negative
            else:
                triCount = readUInt(file)
                trisRead += triCount

                if state.logColNodes:
                    print(f"===== Node { n + 1 } =============================")
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
                        materialID = readInt(file)

                        print(f"===== Triangle { t + 1 } ===========================")
                        print("Vertices:           ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*vertices[0]))
                        print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*vertices[1]))
                        print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*vertices[2]))
                        print(f"Attributes:         { attributes }")
                        print(f"Material ID:        { materialID }")
                        print()
            n += 1

        openCol2Node()

    if trisRead != totalTris:
        self.report({ 'ERROR' }, f"GZRS2: The number of Col triangles read did not match the recorded count! { trisRead }, { totalTris }")

    file.close()

'''
class TestSelf:
    def report(self, t, s):
        print(s)

testpaths = [
    "..\\..\\GunZ\\clean\\Maps\\Battle Arena\\Battle Arena.RS.col",
    "..\\..\\GunZ\\clean\\Maps\\Castle\\Castle.RS.col",
    "..\\..\\GunZ\\clean\\Maps\\Catacomb\\Catacomb.RS.col",
    "..\\..\\GunZ\\clean\\Maps\\Citadel\\Citadel.RS.col",
    "..\\..\\GunZ\\clean\\Maps\\Dungeon\\Dungeon.RS.col",
    "..\\..\\GunZ\\clean\\Maps\\Factory\\Factory.RS.col",
    "..\\..\\GunZ\\clean\\Maps\\Garden\\Garden.RS.col",
    "..\\..\\GunZ\\clean\\Maps\\Hall\\Hall.RS.col",
    "..\\..\\GunZ\\clean\\Maps\\Halloween Town\\Halloween Town.RS.col",
    "..\\..\\GunZ\\clean\\Maps\\High_Haven\\High_Haven.RS.col",
    "..\\..\\GunZ\\clean\\Maps\\Island\\Island.RS.col",
    "..\\..\\GunZ\\clean\\Maps\\Jail\\Jail.RS.col",
    "..\\..\\GunZ\\clean\\Maps\\Lost Shrine\\Lost Shrine.RS.col",
    "..\\..\\GunZ\\clean\\Maps\\Mansion\\Mansion.RS.col",
    "..\\..\\GunZ\\clean\\Maps\\Port\\Port.RS.col",
    "..\\..\\GunZ\\clean\\Maps\\Prison\\Prison.RS.col",
    "..\\..\\GunZ\\clean\\Maps\\Prison II\\Prison II.RS.col",
    "..\\..\\GunZ\\clean\\Maps\\Ruin\\Ruin.RS.col",
    "..\\..\\GunZ\\clean\\Maps\\Shower Room\\Shower Room.RS.col",
    "..\\..\\GunZ\\clean\\Maps\\Ruin\\Ruin.RS.col",
    "..\\..\\GunZ\\clean\\Maps\\Snow_Town\\Snow_Town.RS.col",
    "..\\..\\GunZ\\clean\\Maps\\Stairway\\Stairway.RS.col",
    "..\\..\\GunZ\\clean\\Maps\\Station\\Station.RS.col",
    "..\\..\\GunZ\\clean\\Maps\\Town\\Town.RS.col",
    "..\\..\\GunZ2\\z3ResEx\\datadump\\Data\\Maps\\PvP_maps\\pvp_beast_of_steel\\pvp_beast_of_steel.cl2",
    "..\\..\\GunZ2\\z3ResEx\\datadump\\Data\\Maps\\PvP_maps\\pvp_colosseum\\pvp_colosseum.cl2",
    "..\\..\\GunZ2\\z3ResEx\\datadump\\Data\\Maps\\PvP_maps\\pvp_lair_of_beast\\pvp_lair_of_beast.cl2",
    "..\\..\\GunZ2\\z3ResEx\\datadump\\Data\\Maps\\PvP_maps\\pvp_mansion_gt\\pvp_mansion_gt.cl2",
    "..\\..\\GunZ2\\z3ResEx\\datadump\\Data\\Maps\\PvP_maps\\pvp_pier5\\pvp_pier5.cl2"
]

for path in testpaths:
    readCol(TestSelf(), path, GZRS2State())
'''
