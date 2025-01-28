#####
# Most of the code is based on logic found in...
#
### GunZ 1
# - RBspObject.h/.cpp
# - RBspObject_bsp.cpp
#
# Please report maps and models with unsupported features to me on Discord: Krunk#6051
#####

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .readlm_gzrs2 import *
from .lib_gzrs2 import *

def importLm(self, context):
    state = GZRS2State()

    if self.panelLogging:
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
    state.filename = bpy.path.basename(lmpath).split(os.extsep)[0]

    with open(lmpath, 'rb') as file:
        if readLm(self, file, lmpath, state):
            return { 'CANCELLED' }

    unpackLmImages(context, state)

    return { 'FINISHED' }
