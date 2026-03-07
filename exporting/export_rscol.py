#####
# Most of the code is based on logic found in...
#
### GunZ 1
# - RBspObject.h/.cpp
# - RBspExporter.cpp
#
# Please report maps and models with unsupported features to me on Discord: Krunk#6051
#####

import bpy, os, math
import xml.dom.minidom as minidom

from contextlib import redirect_stdout
from mathutils import Vector, Matrix, Quaternion

from ..constants_gzrs2 import *
from ..classes_gzrs2 import *
from ..parse_gzrs2 import *
from ..io_gzrs2 import *
from ..lib.lib_gzrs2 import *

def exportCol(self, context):
    state = GZRS2ExportState()

    serverProfile = context.preferences.addons['io_scene_gzrs2'].preferences.serverProfile

    state.convertUnits      = self.convertUnits
    state.filterMode        = self.filterMode
    state.includeChildren   = self.includeChildren and self.filterMode == 'SELECTED'

    if self.panelLogging:
        print()
        print("=======================================================================")
        print("===========================  RSCOL Export  ============================")
        print("=======================================================================")
        print(f"== { self.filepath }")
        print("=======================================================================")
        print()

        state.logCol    = self.logCol

    colpath = self.filepath
    directory = os.path.dirname(colpath)
    basename = bpy.path.basename(colpath)
    splitname = basename.split(os.extsep)
    filename = splitname[0]
    
    createBackupFile(colpath)

    windowManager = context.window_manager

    objects = getFilteredObjects(context, state)

    # Gather data into list
    blColObjs = []

    foundValid = False
    invalidCount = 0

    windowManager.progress_begin(0, len(objects))

    for o, object in enumerate(objects):
        windowManager.progress_update(o)

        if object is None:
            continue

        if object.type == 'MESH':
            foundValid = True
            props = object.data.gzrs2
            meshType = props.meshType

            if meshType == 'WORLD':
                if props.worldCollision:    blColObjs.append(object)
                else:                       invalidCount += 1
            elif meshType == 'COLLISION':   blColObjs.append(object)
        else:
            invalidCount += 1

    if not foundValid:
        self.report({ 'ERROR' }, "GZRS2: COL export requires objects of type MESH!")
        return { 'CANCELLED' }

    if invalidCount > 0:
        self.report({ 'WARNING' }, f"GZRS2: COL export skipped { invalidCount } invalid objects...")

    if len(blColObjs) == 0:
        self.report({ 'ERROR' }, f"GZRS2: COL export requires at least one collision mesh!")
        return { 'CANCELLED' }

    # Generate Col nodes
    coltreeVertices = []
    coltreePolygons = []
    o = 0

    windowManager.progress_end()
    windowManager.progress_begin(0, len(blColObjs))

    for c, blColObj in enumerate(blColObjs):
        windowManager.progress_update(c)

        blMesh = blColObj.data

        worldMatrix = blColObj.matrix_world
        coltreeVertices += tuple(worldMatrix @ vertex.co for vertex in blMesh.vertices)

        for polygon in blMesh.polygons:
            positions = tuple(coltreeVertices[o + i] for i in polygon.vertices)
            normal = polygon.normal.normalized()

            coltreePolygons.append(Col1HullPolygon(len(positions), positions, normal, False))

        o += len(blMesh.vertices)

    coltreeVertices = tuple(coltreeVertices)
    coltreePolygons = tuple(coltreePolygons)

    colBBMin, colBBMax = calcCoordinateBounds(coltreeVertices)
    coltreeBoundsQuads = tuple(createBoundsQuad(colBBMin, colBBMax, s) for s in range(6))

    windowManager.progress_end()
    windowManager.progress_begin(0, 1000)

    try:
        col1Root = createColtreeNode(coltreePolygons, coltreeBoundsQuads, windowManager)
    except (GZRS2EdgePlaneIntersectionError, GZRS2DegeneratePolygonError) as error:
        self.report({ 'ERROR' }, error.message)
        return { 'CANCELLED' }

    colNodeCount        = getTreeNodeCount(col1Root)
    colTriangleCount    = getTreeTriangleCount(col1Root)
    colTreeDepth        = getTreeDepth(col1Root)

    # Write Col
    id = COL1_ID
    version = COL1_VERSION

    if state.logCol:
        print("===================  Write Col  ===================")
        print()
        print(f"Path:               { colpath }")
        print(f"ID:                 { hex(id) }")
        print(f"Version:            { hex(version) }")
        print()
        print(f"Node Count:         { colNodeCount }")
        print(f"Triangle Count:     { colTriangleCount }")
        print(f"Depth:              { colTreeDepth }")
        print()

    with open(colpath, 'wb') as file:
        writeUInt(file, id)
        writeUInt(file, version)

        writeUInt(file, colNodeCount)
        writeUInt(file, colTriangleCount)

        def writeCol1Node(node):
            writePlane(file, node.plane, state.convertUnits, True)
            writeBool(file, node.solid)

            writeBool(file, node.positive is not None)
            if node.positive is not None:
                writeCol1Node(node.positive)

            writeBool(file, node.negative is not None)
            if node.negative is not None:
                writeCol1Node(node.negative)

            writeUInt(file, len(node.triangles))

            for triangle in node.triangles:
                writeCoordinateArray(file, triangle.vertices, state.convertUnits, True)
                writeDirection(file, triangle.normal, True)

        writeCol1Node(col1Root)

    windowManager.progress_end()

    return { 'FINISHED' }
