#####
# Most of the code is based on logic found in...
#
### GunZ 1
# - RNavigationMesh.h/.cpp
#
# Please report maps and models with unsupported features to me on Discord: Krunk#6051
#####

import bpy, os

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .readnav_gzrs2 import *
from .lib_gzrs2 import *

def importNav(self, context):
    state = GZRS2State()
    ensureLmMixGroup()

    state.convertUnits = self.convertUnits

    if self.panelLogging:
        print()
        print("=======================================================================")
        print("===========================  RSNAV Import  ============================")
        print("=======================================================================")
        print(f"== { self.filepath }")
        print("=======================================================================")
        print()

        state.logNavHeaders = self.logNavHeaders
        state.logNavData = self.logNavData

    navpath = self.filepath
    state.directory = os.path.dirname(navpath)
    splitname = os.path.basename(navpath).split(os.extsep)
    state.filename = splitname[0]
    extension = splitname[-1].lower()

    with open(navpath, 'rb') as file:
        if readNav(self, file, navpath, state):
            return { 'CANCELLED' }

    blNavFacesObj, blNavLinksObj = setupNavMesh(state)
    context.collection.objects.link(blNavFacesObj)
    context.collection.objects.link(blNavLinksObj)

    for viewLayer in context.scene.view_layers:
        viewLayer.objects.active = blNavFacesObj

    return { 'FINISHED' }
