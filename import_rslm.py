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

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .readlm_gzrs2 import *
from .lib_gzrs2 import *

def importLm(self, context):
    state = GZRS2State()

    if self.logLmHeaders or self.logLmImages:
        print()
        print("=======================================================================")
        print("===========================  RSLM Import  =============================")
        print("=======================================================================")
        print(f"== { self.filepath }")
        print("=======================================================================")
        print()

        state.logLmHeaders = self.logLmHeaders
        state.logLmImages = self.logLmImages

    lmpath = self.filepath
    state.directory = os.path.dirname(lmpath)
    state.filename = os.path.basename(lmpath).split(os.extsep)[0]

    readLm(self, lmpath, state)
    unpackLmImages(state)

    return { 'FINISHED' }
