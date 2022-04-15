import bpy
from bpy.types import Operator, Panel
from bpy_extras.io_utils import ImportHelper
from bpy.props import BoolProperty, StringProperty, EnumProperty

from . import import_gzrs2

bl_info = {
    "name": "GZRS2 Format",
    "author": "Krunklehorn",
    "version": (0, 8, 0),
    "blender": (3, 1, 0),
    "location": "File > Import",
    "description": "GunZ: The Duel RealSpace2.0 map import for geometry, models, materials, lights and more.",
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
    bl_label = "Import GZRS2"
    bl_options = { "UNDO", "PRESET" }

    filter_glob: StringProperty(
        default = "*.RS",
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

    convertUnits: BoolProperty(
        name = "Convert Units",
        description = "Convert location data from centimeters to meters.",
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
        description = "Import lense flares, spawn points and more as empties.",
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

    def draw(self, context):
        pass

    def execute(self, context):
        result = import_gzrs2.load(self, context)
        return result

class GZRS2_PT_Import_Main(Panel):
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOL_PROPS"
    bl_label = "Main"
    bl_parent_id = "FILE_PT_operator"

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelMain
        layout.prop(operator, "convertUnits")
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

classes = (
    ImportGZRS2,
    GZRS2_PT_Import_Main,
    GZRS2_PT_Import_Drivers
)

def menu_func_import(self, context):
    self.layout.operator(ImportGZRS2.bl_idname, text = "GunZ RS2 (.RS)")

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
