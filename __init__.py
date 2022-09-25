import bpy
from bpy.types import Operator, Panel
from bpy_extras.io_utils import ImportHelper
from bpy.props import BoolProperty, StringProperty, EnumProperty

from . import import_gzrs2
from . import import_rselu

bl_info = {
    "name": "GZRS2/3 Format",
    "author": "Krunklehorn",
    "version": (0, 9, 0),
    "blender": (3, 3, 0),
    "location": "File > Import",
    "description": "GunZ: The Duel RealSpace2.0/3.0 map and model importer.",
    "category": "Import-Export",
}

def cleanse_modules():
    import sys

    all_modules = sys.modules
    all_modules = dict(sorted(all_modules.items(), key = lambda x:x[0]))

    for k,v in all_modules.items():
        if k.startswith(__name__):
            del sys.modules[k]

    return None

class ImportGZRS2(Operator, ImportHelper):
    bl_idname = "import_scene.gzrs2"
    bl_label = "Import RS2/3"
    bl_options = { "UNDO", "PRESET" }

    filter_glob: StringProperty(
        default = "*.rs",
        options = { "HIDDEN" }
    )

    panelMain: BoolProperty(
        name = "Main",
        description = "Main panel of options.",
        default = True
    )

    panelDrivers: BoolProperty(
        name = "Drivers",
        description = "Generate drivers to quickly adjust map data.",
        default = True
    )

    panelLogging: BoolProperty(
        name = "Logging",
        description = "Log details to the console.",
        default = False
    )

    convertUnits: BoolProperty(
        name = "Convert Units",
        description = "Convert measurements from centimeters to meters.",
        default = True
    )

    doCleanup: BoolProperty(
        name = "Clean & Merge",
        description = "Deletes loose geometry, removes doubles and sets each mesh to render smooth.",
        default = True
    )

    doCollision: BoolProperty(
        name = "Collision",
        description = "Import collision data.",
        default = True
    )

    doLights: BoolProperty(
        name = "Lights",
        description = "Import light data.",
        default = True
    )

    tweakLights: BoolProperty(
        name = "Tweak Lights",
        description = "Tweaks light data to give comparable results directly in Blender.",
        default = True
    )

    doProps: BoolProperty(
        name = "Props",
        description = "Import model data.",
        default = True
    )

    doDummies: BoolProperty(
        name = "Dummies",
        description = "Import cameras, lense flares, spawn points and more as empties.",
        default = True
    )

    doOcclusion: BoolProperty(
        name = "Occlusion",
        description = "Import occlusion planes.",
        default = True
    )

    doFog: BoolProperty(
        name = "Fog",
        description = "Create fog volume with Volume Scatter/Absorption nodes from fog settings.",
        default = True
    )

    doSounds: BoolProperty(
        name = "Sounds",
        description = "Import ambient sounds.",
        default = True
    )

    doItems: BoolProperty(
        name = "Items",
        description = "Import item particles.",
        default = True
    )

    doBspBounds: BoolProperty(
        name = "BSP Bounds",
        description = "Create empties from BSP bounds data.",
        default = True
    )

    doLightDrivers: BoolProperty(
        name = "Lights",
        description = "Generate drivers to quickly control groups of similar lights.",
        default = True
    )

    doFogDriver: BoolProperty(
        name = "Fog",
        description = "Generate driver to control fog settings.",
        default = True
    )

    logRsPortals: BoolProperty(
        name = "RS Portals",
        description = "Log RS portal data.",
        default = True
    )

    logRsCells: BoolProperty(
        name = "RS Cells",
        description = "Log RS cell data.",
        default = True
    )

    logRsGeometry: BoolProperty(
        name = "RS Geometry",
        description = "Log RS geometry data.",
        default = True
    )

    logRsTrees: BoolProperty(
        name = "RS Trees",
        description = "Log RS tree data.",
        default = True
    )

    logRsLeaves: BoolProperty(
        name = "RS Leaves",
        description = "Log RS leaf data.",
        default = False
    )

    logRsVerts: BoolProperty(
        name = "RS Vertices",
        description = "Log RS vertex data.",
        default = False
    )

    logEluHeaders: BoolProperty(
        name = "Elu Headers",
        description = "Log ELU header data.",
        default = True
    )

    logEluMats: BoolProperty(
        name = "Elu Materials",
        description = "Log ELU material data.",
        default = True
    )

    logEluMeshNodes: BoolProperty(
        name = "Elu Mesh Nodes",
        description = "Log ELU mesh node data.",
        default = True
    )

    logVerboseIndices: BoolProperty(
        name = "Verbose Indices",
        description = "Log indices verbosely.",
        default = False
    )

    logVerboseWeights: BoolProperty(
        name = "Verbose Weights",
        description = "Log weights verbosely.",
        default = False
    )

    logCleanup: BoolProperty(
        name = "Cleanup",
        description = "Log results of the the cleanup routine.",
        default = False
    )

    def draw(self, context):
        pass

    def execute(self, context):
        result = import_gzrs2.importRs(self, context)
        return result

class GZRS2_PT_Import_Main(Panel):
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOL_PROPS"
    bl_label = "Main"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "IMPORT_SCENE_OT_gzrs2"

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelMain

        layout.prop(operator, "convertUnits")
        layout.prop(operator, "doCleanup")
        layout.prop(operator, "doCollision")
        layout.prop(operator, "doLights")

        row = layout.row()
        row.prop(operator, "tweakLights")
        row.enabled = operator.doLights

        layout.prop(operator, "doProps")

        layout.prop(operator, "doDummies")
        layout.prop(operator, "doOcclusion")
        layout.prop(operator, "doFog")
        layout.prop(operator, "doSounds")
        layout.prop(operator, "doItems")
        layout.prop(operator, "doBspBounds")

class GZRS2_PT_Import_Drivers(Panel):
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOL_PROPS"
    bl_label = "Drivers"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "IMPORT_SCENE_OT_gzrs2"

    def draw_header(self, context):
        self.layout.prop(context.space_data.active_operator, "panelDrivers", text = "")

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelDrivers

        layout.prop(operator, "doLightDrivers")
        layout.prop(operator, "doFogDriver")

class GZRS2_PT_Import_Logging(Panel):
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOL_PROPS"
    bl_label = "Logging"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "IMPORT_SCENE_OT_gzrs2"

    def draw_header(self, context):
        self.layout.prop(context.space_data.active_operator, "panelLogging", text = "")

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelLogging

        layout.prop(operator, "logRsPortals")
        layout.prop(operator, "logRsCells")
        layout.prop(operator, "logRsGeometry")
        layout.prop(operator, "logRsTrees")
        layout.prop(operator, "logRsLeaves")
        layout.prop(operator, "logRsVerts")
        layout.prop(operator, "logEluHeaders")
        layout.prop(operator, "logEluMats")
        layout.prop(operator, "logEluMeshNodes")
        layout.prop(operator, "logVerboseIndices")
        layout.prop(operator, "logVerboseWeights")
        layout.prop(operator, "logCleanup")

class ImportRSELU(Operator, ImportHelper):
    bl_idname = "import_scene.rselu"
    bl_label = "Import ELU"
    bl_options = { "UNDO", "PRESET" }

    filter_glob: StringProperty(
        default = "*.elu",
        options = { "HIDDEN" }
    )

    panelMain: BoolProperty(
        name = "Main",
        description = "Main panel of options.",
        default = True
    )

    panelLogging: BoolProperty(
        name = "Logging",
        description = "Log details to the console.",
        default = False
    )

    convertUnits: BoolProperty(
        name = "Convert Units",
        description = "Convert measurements from centimeters to meters.",
        default = True
    )

    doCleanup: BoolProperty(
        name = "Clean & Merge",
        description = "Deletes loose geometry, removes doubles and sets each mesh to render smooth.",
        default = True
    )

    doBoneRolls: BoolProperty(
        name = "Bone Rolls",
        description = "Re-calculate all bone rolls to the positive world z-axis. Required for twist bone constraints to work properly.",
        default = False
    )

    doTwistConstraints: BoolProperty(
        name = "Twist Constraints",
        description = "Automatically add constraints for twist bones. Bone rolls are required to be re-calculated first.",
        default = True
    )

    logEluHeaders: BoolProperty(
        name = "Elu Headers",
        description = "Log ELU header data.",
        default = True
    )

    logEluMats: BoolProperty(
        name = "Elu Materials",
        description = "Log ELU material data.",
        default = True
    )

    logEluMeshNodes: BoolProperty(
        name = "Elu Mesh Nodes",
        description = "Log ELU mesh node data.",
        default = True
    )

    logVerboseIndices: BoolProperty(
        name = "Verbose Indices",
        description = "Log indices verbosely.",
        default = False
    )

    logVerboseWeights: BoolProperty(
        name = "Verbose Weights",
        description = "Log weights verbosely.",
        default = False
    )

    logCleanup: BoolProperty(
        name = "Cleanup",
        description = "Log results of the the cleanup routine.",
        default = False
    )

    def draw(self, context):
        pass

    def execute(self, context):
        result = import_rselu.importElu(self, context)
        return result

class RSELU_PT_Import_Main(Panel):
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOL_PROPS"
    bl_label = "Main"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "IMPORT_SCENE_OT_rselu"

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelMain

        layout.prop(operator, "convertUnits")
        layout.prop(operator, "doCleanup")
        layout.prop(operator, "doBoneRolls")

        row = layout.row()
        row.prop(operator, "doTwistConstraints")
        row.enabled = operator.doBoneRolls

class RSELU_PT_Import_Logging(Panel):
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOL_PROPS"
    bl_label = "Logging"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "IMPORT_SCENE_OT_rselu"

    def draw_header(self, context):
        self.layout.prop(context.space_data.active_operator, "panelLogging", text = "")

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelLogging

        layout.prop(operator, "logEluHeaders")
        layout.prop(operator, "logEluMats")
        layout.prop(operator, "logEluMeshNodes")
        layout.prop(operator, "logVerboseIndices")
        layout.prop(operator, "logVerboseWeights")
        layout.prop(operator, "logCleanup")

classes = (
    ImportGZRS2,
    GZRS2_PT_Import_Main,
    GZRS2_PT_Import_Drivers,
    GZRS2_PT_Import_Logging,
    ImportRSELU,
    RSELU_PT_Import_Main,
    RSELU_PT_Import_Logging,
)

def menu_func_import(self, context):
    self.layout.operator(ImportGZRS2.bl_idname, text = "GunZ RS2/3 (.rs)")
    self.layout.operator(ImportRSELU.bl_idname, text = "GunZ ELU (.elu)")

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

    for cls in classes:
        bpy.utils.unregister_class(cls)

    cleanse_modules()


if __name__ == "__main__":
    register()
