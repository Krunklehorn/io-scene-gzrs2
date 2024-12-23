#####
# Most of the code is based on logic found in...
#
### GunZ 1
# - RNavigationMesh.h/.cpp
#
# Please report maps and models with unsupported features to me on Discord: Krunk#6051
#####

import os, io, shutil

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .io_gzrs2 import *
from .lib_gzrs2 import *

def exportNav(self, context):
    state = RSNAVExportState()

    state.convertUnits = self.convertUnits

    if self.panelLogging:
        print()
        print("=======================================================================")
        print("===========================  RSNAV Export  ============================")
        print("=======================================================================")
        print(f"== { self.filepath }")
        print("=======================================================================")
        print()

        state.logNavHeaders = self.logNavHeaders
        state.logNavData = self.logNavData

    navpath = self.filepath
    directory = os.path.dirname(navpath)
    basename = os.path.basename(navpath)
    splitname = basename.split(os.extsep)
    filename = splitname[0]

    id = NAV_ID
    version = NAV_VERSION

    blObj = context.active_object if context.active_object in context.selected_objects else None

    if blObj is None or blObj.type != 'MESH':
        self.report({ 'ERROR' }, f"GZRS2: NAV export requires a selected mesh as a reference!")
        return { 'CANCELLED' }

    blObj.update_from_editmode()
    blMesh = blObj.data

    vertexCount = len(blMesh.vertices)
    vertices = tuple(vertex.co for vertex in blMesh.vertices)

    if state.logNavData:
        output = "Vertices:           {:<6d}".format(vertexCount)
        output += "      Min: ({:>5.02f}, {:>5.02f}, {:>5.02f})     Max: ({:>5.02f}, {:>5.02f}, {:>5.02f})".format(*vecArrayMinMax(vertices, 3)) if vertexCount > 0 else ''
        print(output)

    faceCount = len(blMesh.loop_triangles)
    indices = tuple(index for triangle in blMesh.loop_triangles for index in triangle.vertices)

    if state.logNavData:
        output = "Faces:              {:<3d}".format(faceCount)
        output += "      Min & Max: ({:>3d}, {:>3d})".format(min(indices), max(indices)) if faceCount > 0 else ''
        print(output)

    uniquePairs = tuple((t1, t2) for t1 in blMesh.loop_triangles for t2 in blMesh.loop_triangles if t2 != t1)
    degenerateCount = sum(1 for t1, t2 in uniquePairs if sum(1 for v1 in t1.vertices for v2 in t2.vertices if v2 == v1) == 3)

    if degenerateCount > 0:
        self.report({ 'ERROR' }, f"GZRS2: NAV export found { degenerateCount } degenerate triangles!")
        return { 'CANCELLED' }

    linkIndices = []

    for t1, k1 in iter((t1, k1) for t1 in blMesh.loop_triangles for k1 in t1.edge_keys):
        for t2, k2 in iter((t2, k2) for t2 in blMesh.loop_triangles for k2 in t2.edge_keys if t2 != t1):
            if k2 == k1:
                linkIndices.append(t2.index)
                break
        else:
            linkIndices.append(-1)

    linkIndices = tuple(linkIndices)

    if state.logNavData:
        output = "Links:              {:<3d}".format(faceCount)
        output += "      Min & Max: ({:>3d}, {:>3d})".format(min(linkIndices), max(linkIndices)) if faceCount > 0 else ''
        print(output)
        print()

    if state.logNavHeaders or state.logNavData:
        print("===================  Write Nav  ===================")
        print()

    if state.logNavHeaders:
        print(f"Path:               { navpath }")
        print(f"ID:                 { hex(id) }")
        print(f"Version:            { hex(version) }")
        print()

    if os.path.isfile(navpath):
        shutil.copy2(navpath, os.path.join(directory, filename + "_backup") + '.' + splitname[1])

    file = io.open(navpath, 'wb')

    writeUInt(file, id)
    writeUInt(file, version)

    writeInt(file, vertexCount)
    writeCoordinateArray(file, vertices, state.convertUnits, True)
    writeInt(file, faceCount)
    writeShortArray(file, indices)
    writeIntArray(file, linkIndices)

    file.close()

    return { 'FINISHED' }
