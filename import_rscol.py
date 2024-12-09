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

import bpy, os

from contextlib import redirect_stdout

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .readcol_gzrs2 import *
from .lib_gzrs2 import *

def importCol(self, context):
    state = GZRS2State()

    state.convertUnits = self.convertUnits
    state.doCleanup = self.doCleanup

    if self.panelLogging:
        print()
        print("=======================================================================")
        print("===========================  RSCOL Import  ============================")
        print("=======================================================================")
        print(f"== { self.filepath }")
        print("=======================================================================")
        print()

        state.logColHeaders = self.logColHeaders
        state.logColNodes = self.logColNodes
        state.logColTris = self.logColTris
        state.logCleanup = self.logCleanup

    colpath = self.filepath
    state.directory = os.path.dirname(colpath)
    splitname = os.path.basename(colpath).split(os.extsep)
    state.filename = splitname[0]
    extension = splitname[-1].lower()

    if readCol(self, colpath, state):
        return { 'CANCELLED' }

    if state.doCleanup and state.logCleanup:
        print()
        print("=== Col Mesh Cleanup ===")
        print()

    colName = f"{ state.filename }_Collision"
    blColObj = setupColMesh(colName, state)
    context.collection.objects.link(blColObj)

    for viewLayer in context.scene.view_layers:
        viewLayer.objects.active = blColObj

    if state.doCleanup:
        if state.logCleanup: print(colName)

        reportCount = 0

        bpy.ops.object.select_all(action = 'DESELECT')
        blColObj.select_set(True)
        bpy.ops.object.select_all(action = 'DESELECT')

        bpy.ops.object.mode_set(mode = 'EDIT')

        bpy.ops.mesh.select_mode(type = 'VERT')
        bpy.ops.mesh.select_all(action = 'SELECT')

        reportCount += 3

        def subCleanup():
            nonlocal reportCount

            for _ in range(10):
                bpy.ops.mesh.dissolve_degenerate()
                bpy.ops.mesh.delete_loose()
                bpy.ops.mesh.select_all(action = 'SELECT')
                bpy.ops.mesh.remove_doubles(threshold = 0.0001)
                reportCount += 4

        def cleanupFunc():
            nonlocal reportCount

            if extension == 'col':
                bpy.ops.mesh.intersect(mode = 'SELECT', separate_mode = 'ALL', threshold = 0.0001, solver = 'FAST')
                bpy.ops.mesh.select_all(action = 'SELECT')
                reportCount += 2

                subCleanup()

                bpy.ops.mesh.intersect(mode = 'SELECT', separate_mode = 'ALL')
                bpy.ops.mesh.select_all(action = 'SELECT')
                reportCount += 2

                subCleanup()

                for _ in range(10):
                    bpy.ops.mesh.fill_holes(sides = 0)
                    bpy.ops.mesh.tris_convert_to_quads(face_threshold = 0.0174533, shape_threshold = 0.0174533)
                    reportCount += 2

                    subCleanup()

                bpy.ops.mesh.vert_connect_nonplanar(angle_limit = 0.0174533)
                reportCount += 1

                subCleanup()
            elif extension == 'cl2':
                bpy.ops.mesh.remove_doubles(threshold = 0.0001, use_sharp_edge_from_normals = True)
                bpy.ops.mesh.tris_convert_to_quads(face_threshold = 0.0174533, shape_threshold = 0.0174533)
                reportCount += 2

            bpy.ops.mesh.dissolve_limited(angle_limit = 0.0174533)
            bpy.ops.mesh.delete_loose(use_faces = True)
            bpy.ops.mesh.select_all(action = 'SELECT')
            bpy.ops.mesh.normals_make_consistent(inside = True)
            bpy.ops.mesh.select_all(action = 'DESELECT')
            reportCount += 5

            bpy.ops.object.mode_set(mode = 'OBJECT')

        if state.logCleanup:
            cleanupFunc()
            print()
        else:
            with redirect_stdout(state.silentIO):
                cleanupFunc()

        deleteInfoReports(reportCount, context)

    bpy.ops.object.select_all(action = 'DESELECT')
    deleteInfoReports(1, context)

    return { 'FINISHED' }
