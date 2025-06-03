#####
# Most of the code is based on logic found in...
#
### GunZ 1
# - RNavigationMesh.h/.cpp
#
# Please report maps and models with unsupported features to me on Discord: Krunk#6051
#####

import os, io

from ..constants_gzrs2 import *
from ..classes_gzrs2 import *
from ..io_gzrs2 import *
from ..lib.lib_gzrs2 import *

def readNav(self, file, path, state):
    file.seek(0, os.SEEK_END)
    fileSize = file.tell()
    file.seek(0, os.SEEK_SET)

    if state.logNavHeaders or state.logNavData:
        print("===================  Read Nav  ===================")
        print()

    id = readUInt(file)
    version = readUInt(file)

    if state.logNavHeaders:
        print(f"Path:               { path }")
        print(f"ID:                 { hex(id) }")
        print(f"Version:            { hex(version) }")
        print()

    if id != NAV_ID or version != NAV_VERSION:
        self.report({ 'ERROR' }, f"GZRS2: NAV header invalid! { hex(id) }, { hex(version) }")
        return { 'CANCELLED' }

    vertexCount = readInt(file)
    vertices = readCoordinateArray(file, vertexCount, state.convertUnits, True)
    if state.logNavData:
        output = "Vertices:           {:<6d}".format(vertexCount)
        output += "      Min: ({:>5.02f}, {:>5.02f}, {:>5.02f})     Max: ({:>5.02f}, {:>5.02f}, {:>5.02f})".format(*vecArrayMinMax(vertices, 3)) if vertexCount > 0 else ''
        print(output)

    state.navVerts = vertices

    faceCount = readInt(file)
    indices = readUShortArray(file, faceCount * 3)
    if state.logNavData:
        output = "Faces:              {:<3d}".format(faceCount)
        output += "      Min & Max: ({:>3d}, {:>3d})".format(min(indices), max(indices)) if faceCount > 0 else ''
        print(output)

    state.navFaces = tuple(tuple(indices[f * 3 + i] for i in range(3)) for f in range(faceCount))

    invalidCount = 0

    for face in state.navFaces:
        if (face[0] < 0                 or face[1] < 0              or face[2] < 0 or
            face[0] >= vertexCount      or face[1] >= vertexCount   or face[2] >= vertexCount or
            face[0] == face[1]          or face[1] == face[2]       or face[2] == face[0]):
            invalidCount += 1

    if invalidCount > 0:
        self.report({ 'ERROR' }, f"GZRS2: NAV import contained { invalidCount } invalid face indices! { path }")
        return { 'CANCELLED' }

    linkIndices = readIntArray(file, faceCount * 3)
    if state.logNavData:
        output = "Links:              {:<3d}".format(faceCount)
        output += "      Min & Max: ({:>3d}, {:>3d})".format(min(linkIndices), max(linkIndices)) if faceCount > 0 else ''
        print(output)
        print()

    invalidCount = sum(1 for index in linkIndices if index >= faceCount)

    if invalidCount > 0:
        self.report({ 'ERROR' }, f"GZRS2: NAV import contained { invalidCount } negative link indices! { path }")
        return { 'CANCELLED' }

    state.navLinks = tuple(tuple(linkIndices[f * 3 + i] for i in range(3)) for f in range(faceCount))

    if state.logNavHeaders or state.logNavData:
        bytesRemaining = fileSize - file.tell()

        if bytesRemaining > 0:
            self.report({ 'ERROR' }, f"GZRS2: NAV import finished with bytes remaining! { path }, { hex(id) }, { hex(version) }")

        print(f"Bytes Remaining:    { bytesRemaining }")
        print()
