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

    colName = f"{ state.filename }_Collision"
    blColObj = setupColMesh(colName, context.collection, context, extension, state)

    for viewLayer in context.scene.view_layers:
        blColObj.hide_set(False, view_layer = viewLayer)
        viewLayer.objects.active = blColObj

    return { 'FINISHED' }
