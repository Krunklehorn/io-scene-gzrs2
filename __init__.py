from . import import_gzrs2, import_gzrs3, import_rselu, import_rscol, import_rslm
from . import export_rselu, export_rslm

bl_info = {
    "name": "GZRS2/3 Format",
    "author": "Krunklehorn",
    "version": (0, 9, 2),
    "blender": (3, 6, 2),
    "location": "File > Import-Export",
    "description": "GunZ: The Duel RealSpace2/3 content importer.",
    "category": "Import-Export",
}

if "bpy" in locals():
    import importlib

    if "import_gzrs2" in locals(): importlib.reload(import_gzrs2)
    if "import_gzrs3" in locals(): importlib.reload(import_gzrs3)
    if "import_rselu" in locals(): importlib.reload(import_rselu)
    if "import_rscol" in locals(): importlib.reload(import_rscol)
    if "import_rslm" in locals(): importlib.reload(import_rslm)
    if "export_rselu" in locals(): importlib.reload(export_rselu)
    if "export_rslm" in locals(): importlib.reload(export_rslm)
else:
    import bpy
    from bpy.types import Operator, Panel
    from bpy_extras.io_utils import ImportHelper, ExportHelper
    from bpy.props import BoolProperty, StringProperty, EnumProperty

def cleanse_modules():
    import sys

    all_modules = sys.modules
    all_modules = dict(sorted(all_modules.items(), key = lambda x: x[0]))

    for k, v in all_modules.items():
        if k.startswith(__name__):
            del sys.modules[k]

    return None

class ImportGZRS2(Operator, ImportHelper):
    bl_idname = "import_scene.gzrs2"
    bl_label = "Import RS2"
    bl_options = { 'UNDO', 'PRESET' }
    bl_description = "Load an RS file"

    filter_glob: StringProperty(
        default = "*.rs",
        options = { 'HIDDEN' }
    )

    panelMain: BoolProperty(
        name = "Main",
        description = "Main panel of options",
        default = True
    )

    panelDrivers: BoolProperty(
        name = "Drivers",
        description = "Generate drivers to quickly adjust map data",
        default = True
    )

    panelLogging: BoolProperty(
        name = "Logging",
        description = "Log details to the console",
        default = False
    )

    convertUnits: BoolProperty(
        name = "Convert Units",
        description = "Convert measurements from centimeters to meters",
        default = True
    )

    doCleanup: BoolProperty(
        name = "Cleanup",
        description = "Deletes loose geometry, removes doubles and sets each mesh to render smooth",
        default = True
    )

    meshMode: EnumProperty(
        name = "Mesh Mode",
        items = (('STANDARD',   "Standard",     "Split geometry by material, optionally perform cleanup."),
                 ('BAKE',       "Bake",         "Don't split geometry or perform any cleanup."))
    )

    doCollision: BoolProperty(
        name = "Collision",
        description = "Import collision data",
        default = True
    )

    doLightmap: BoolProperty(
        name = "Lightmap",
        description = "Import lightmap data",
        default = True
    )

    linkInMaterials: BoolProperty(
        name = "Link In Materials",
        description = "Tweaks light data to give comparable results directly in Blender",
        default = True
    )

    doLights: BoolProperty(
        name = "Lights",
        description = "Import light data",
        default = True
    )

    tweakLights: BoolProperty(
        name = "Tweak Lights",
        description = "Tweaks light data to give comparable results directly in Blender",
        default = True
    )

    doProps: BoolProperty(
        name = "Props",
        description = "Import model data",
        default = True
    )

    doDummies: BoolProperty(
        name = "Dummies",
        description = "Import cameras, lense flares, spawn points and more as empties",
        default = True
    )

    doOcclusion: BoolProperty(
        name = "Occlusion",
        description = "Import occlusion planes",
        default = True
    )

    doFog: BoolProperty(
        name = "Fog",
        description = "Create fog volume with Volume Scatter/Absorption nodes from fog settings",
        default = True
    )

    doSounds: BoolProperty(
        name = "Sounds",
        description = "Import ambient sounds",
        default = True
    )

    doItems: BoolProperty(
        name = "Items",
        description = "Import item particles",
        default = True
    )

    doBspBounds: BoolProperty(
        name = "BSP Bounds",
        description = "Create empties from BSP bounds data",
        default = True
    )

    doLightDrivers: BoolProperty(
        name = "Lights",
        description = "Generate drivers to quickly control groups of similar lights",
        default = True
    )

    doFogDriver: BoolProperty(
        name = "Fog",
        description = "Generate driver to control fog settings",
        default = True
    )

    logRsPortals: BoolProperty(
        name = "RS Portals",
        description = "Log RS portal data",
        default = True
    )

    logRsCells: BoolProperty(
        name = "RS Cells",
        description = "Log RS cell data",
        default = True
    )

    logRsGeometry: BoolProperty(
        name = "RS Geometry",
        description = "Log RS geometry data",
        default = True
    )

    logRsTrees: BoolProperty(
        name = "RS Trees",
        description = "Log RS tree data",
        default = True
    )

    logRsLeaves: BoolProperty(
        name = "RS Leaves",
        description = "Log RS leaf data",
        default = False
    )

    logRsVerts: BoolProperty(
        name = "RS Vertices",
        description = "Log RS vertex data",
        default = False
    )

    logColHeaders: BoolProperty(
        name = "Col Headers",
        description = "Log Col header data",
        default = True
    )

    logColNodes: BoolProperty(
        name = "Col Nodes",
        description = "Log Col node data",
        default = False
    )

    logColTris: BoolProperty(
        name = "Col Triangles",
        description = "Log Col triangle data",
        default = False
    )

    logLmHeaders: BoolProperty(
        name = "Lm Headers",
        description = "Log Lm header data",
        default = True
    )

    logLmImages: BoolProperty(
        name = "Lm Images",
        description = "Log Lm image data",
        default = False
    )

    logEluHeaders: BoolProperty(
        name = "Elu Headers",
        description = "Log ELU header data",
        default = True
    )

    logEluMats: BoolProperty(
        name = "Elu Materials",
        description = "Log ELU material data",
        default = True
    )

    logEluMeshNodes: BoolProperty(
        name = "Elu Mesh Nodes",
        description = "Log ELU mesh node data",
        default = True
    )

    logVerboseIndices: BoolProperty(
        name = "Verbose Indices",
        description = "Log ELU indices verbosely",
        default = False
    )

    logVerboseWeights: BoolProperty(
        name = "Verbose Weights",
        description = "Log ELU weights verbosely",
        default = False
    )

    logCleanup: BoolProperty(
        name = "Cleanup",
        description = "Log results of the the cleanup routine",
        default = False
    )

    def draw(self, context):
        pass

    def execute(self, context):
        return import_gzrs2.importRs2(self, context)

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
        layout.prop(operator, "meshMode")

        column = layout.column()
        column.prop(operator, "doCollision")
        column.enabled = operator.meshMode != 'BAKE'

        layout.prop(operator, "doLightmap")
        layout.prop(operator, "doLights")

        column = layout.column()
        column.prop(operator, "tweakLights")
        column.enabled = operator.doLights

        layout.prop(operator, "doProps")

        column = layout.column()
        column.prop(operator, "doDummies")
        column.prop(operator, "doOcclusion")
        column.enabled = operator.meshMode != 'BAKE'

        layout.prop(operator, "doFog")

        column = layout.column()
        column.prop(operator, "doSounds")
        column.prop(operator, "doItems")
        column.prop(operator, "doBspBounds")
        column.enabled = operator.meshMode != 'BAKE'

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
        layout.prop(operator, "logColHeaders")
        layout.prop(operator, "logColNodes")
        layout.prop(operator, "logColTris")
        layout.prop(operator, "logLmHeaders")
        layout.prop(operator, "logLmImages")
        layout.prop(operator, "logEluHeaders")
        layout.prop(operator, "logEluMats")
        layout.prop(operator, "logEluMeshNodes")

        column = layout.column()
        column.prop(operator, "logVerboseIndices")
        column.prop(operator, "logVerboseWeights")
        column.enabled = operator.logEluMeshNodes

        layout.prop(operator, "logCleanup")

class ImportGZRS3(Operator, ImportHelper):
    bl_idname = "import_scene.gzrs3"
    bl_label = "Import RS3"
    bl_options = { 'UNDO', 'PRESET' }
    bl_description = "Load a SCENE.XML/PROP.XML file"

    filter_glob: StringProperty(
        default = "*.scene.xml;*.prop.xml",
        options = { 'HIDDEN' }
    )

    panelMain: BoolProperty(
        name = "Main",
        description = "Main panel of options",
        default = True
    )

    panelLogging: BoolProperty(
        name = "Logging",
        description = "Log details to the console",
        default = False
    )

    convertUnits: BoolProperty(
        name = "Convert Units",
        description = "Convert measurements from centimeters to meters",
        default = True
    )

    doCleanup: BoolProperty(
        name = "Cleanup",
        description = "Deletes loose geometry, removes doubles and sets each mesh to render smooth",
        default = True
    )

    logSceneNodes: BoolProperty(
        name = "Scene Nodes",
        description = "Log scene node data",
        default = True
    )

    logEluHeaders: BoolProperty(
        name = "Elu Headers",
        description = "Log ELU header data",
        default = True
    )

    logEluMats: BoolProperty(
        name = "Elu Materials",
        description = "Log ELU material data",
        default = True
    )

    logEluMeshNodes: BoolProperty(
        name = "Elu Mesh Nodes",
        description = "Log ELU mesh node data",
        default = True
    )

    logVerboseIndices: BoolProperty(
        name = "Verbose Indices",
        description = "Log ELU indices verbosely",
        default = False
    )

    logVerboseWeights: BoolProperty(
        name = "Verbose Weights",
        description = "Log ELU weights verbosely",
        default = False
    )

    logCleanup: BoolProperty(
        name = "Cleanup",
        description = "Log results of the the cleanup routine",
        default = False
    )

    def draw(self, context):
        pass

    def execute(self, context):
        return import_gzrs3.importRs3(self, context)

class GZRS3_PT_Import_Main(Panel):
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOL_PROPS"
    bl_label = "Main"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "IMPORT_SCENE_OT_gzrs3"

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelMain

        layout.prop(operator, "convertUnits")
        layout.prop(operator, "doCleanup")

class GZRS3_PT_Import_Logging(Panel):
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOL_PROPS"
    bl_label = "Logging"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "IMPORT_SCENE_OT_gzrs3"

    def draw_header(self, context):
        self.layout.prop(context.space_data.active_operator, "panelLogging", text = "")

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelLogging

        layout.prop(operator, "logSceneNodes")
        layout.prop(operator, "logEluHeaders")
        layout.prop(operator, "logEluMats")
        layout.prop(operator, "logEluMeshNodes")

        column = layout.column()
        column.prop(operator, "logVerboseIndices")
        column.prop(operator, "logVerboseWeights")
        column.enabled = operator.logEluMeshNodes

        layout.prop(operator, "logCleanup")

class ImportRSELU(Operator, ImportHelper):
    bl_idname = "import_scene.rselu"
    bl_label = "Import ELU"
    bl_options = { 'UNDO', 'PRESET' }
    bl_description = "Load an ELU file"

    filter_glob: StringProperty(
        default = "*.elu",
        options = { 'HIDDEN' }
    )

    panelMain: BoolProperty(
        name = "Main",
        description = "Main panel of options",
        default = True
    )

    panelLogging: BoolProperty(
        name = "Logging",
        description = "Log details to the console",
        default = False
    )

    convertUnits: BoolProperty(
        name = "Convert Units",
        description = "Convert measurements from centimeters to meters",
        default = True
    )

    doCleanup: BoolProperty(
        name = "Cleanup",
        description = "Deletes loose geometry, removes doubles and sets each mesh to render smooth",
        default = True
    )

    doBoneRolls: BoolProperty(
        name = "Bone Rolls",
        description = "Re-calculate all bone rolls to the positive world z-axis. Required for twist bone constraints to work properly",
        default = False
    )

    doTwistConstraints: BoolProperty(
        name = "Twist Constraints",
        description = "Automatically add constraints for twist bones. Bone rolls are required to be re-calculated first",
        default = True
    )

    logEluHeaders: BoolProperty(
        name = "Elu Headers",
        description = "Log ELU header data",
        default = True
    )

    logEluMats: BoolProperty(
        name = "Elu Materials",
        description = "Log ELU material data",
        default = True
    )

    logEluMeshNodes: BoolProperty(
        name = "Elu Mesh Nodes",
        description = "Log ELU mesh node data",
        default = True
    )

    logVerboseIndices: BoolProperty(
        name = "Verbose Indices",
        description = "Log ELU indices verbosely",
        default = False
    )

    logVerboseWeights: BoolProperty(
        name = "Verbose Weights",
        description = "Log ELU weights verbosely",
        default = False
    )

    logCleanup: BoolProperty(
        name = "Cleanup",
        description = "Log results of the the cleanup routine",
        default = False
    )

    def draw(self, context):
        pass

    def execute(self, context):
        return import_rselu.importElu(self, context)

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

        column = layout.column()
        column.prop(operator, "doTwistConstraints")
        column.enabled = operator.doBoneRolls

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

        column = layout.column()
        column.prop(operator, "logVerboseIndices")
        column.prop(operator, "logVerboseWeights")
        column.enabled = operator.logEluMeshNodes

        layout.prop(operator, "logCleanup")

class ImportRSCOL(Operator, ImportHelper):
    bl_idname = "import_scene.rscol"
    bl_label = "Import COL"
    bl_options = { 'UNDO', 'PRESET' }
    bl_description = "Load a COL/CL2 file"

    filter_glob: StringProperty(
        default = "*.col;*.cl2",
        options = { 'HIDDEN' }
    )

    panelMain: BoolProperty(
        name = "Main",
        description = "Main panel of options",
        default = True
    )

    panelLogging: BoolProperty(
        name = "Logging",
        description = "Log details to the console",
        default = False
    )

    convertUnits: BoolProperty(
        name = "Convert Units",
        description = "Convert measurements from centimeters to meters",
        default = True
    )

    doCleanup: BoolProperty(
        name = "Cleanup (EXPERIMENTAL)",
        description = "A combination of knife intersection, three types of dissolve, merge by distance, tris-to-quads, and hole filling",
        default = False
    )

    logColHeaders: BoolProperty(
        name = "Col Headers",
        description = "Log Col header data",
        default = True
    )

    logColNodes: BoolProperty(
        name = "Col Nodes",
        description = "Log Col node data",
        default = False
    )

    logColTris: BoolProperty(
        name = "Col Triangles",
        description = "Log Col triangle data",
        default = False
    )

    logCleanup: BoolProperty(
        name = "Cleanup",
        description = "Log results of the the cleanup routine",
        default = False
    )

    def draw(self, context):
        pass

    def execute(self, context):
        return import_rscol.importCol(self, context)

class RSCOL_PT_Import_Main(Panel):
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOL_PROPS"
    bl_label = "Main"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "IMPORT_SCENE_OT_rscol"

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelMain

        layout.prop(operator, "convertUnits")
        layout.prop(operator, "doCleanup")

class RSCOL_PT_Import_Logging(Panel):
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOL_PROPS"
    bl_label = "Logging"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "IMPORT_SCENE_OT_rscol"

    def draw_header(self, context):
        self.layout.prop(context.space_data.active_operator, "panelLogging", text = "")

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelLogging

        layout.prop(operator, "logColHeaders")
        layout.prop(operator, "logColNodes")
        layout.prop(operator, "logColTris")
        layout.prop(operator, "logCleanup")

class ImportRSLM(Operator, ImportHelper):
    bl_idname = "import_scene.rslm"
    bl_label = "Import LM"
    bl_options = { 'UNDO', 'PRESET' }
    bl_description = "Load an LM file"

    filter_glob: StringProperty(
        default = "*.lm",
        options = { 'HIDDEN' }
    )

    panelLogging: BoolProperty(
        name = "Logging",
        description = "Log details to the console",
        default = True
    )

    logLmHeaders: BoolProperty(
        name = "Lm Headers",
        description = "Log Lm header data",
        default = False
    )

    logLmImages: BoolProperty(
        name = "Lm Images",
        description = "Log Lm image data",
        default = False
    )

    def draw(self, context):
        pass

    def execute(self, context):
        return import_rslm.importLm(self, context)

class RSLM_PT_Import_Logging(Panel):
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOL_PROPS"
    bl_label = "Logging"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "IMPORT_SCENE_OT_rslm"

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelLogging

        layout.prop(operator, "logLmHeaders")
        layout.prop(operator, "logLmImages")

class ExportRSELU(Operator, ExportHelper):
    bl_idname = "export_scene.rselu"
    bl_label = "Export ELU"
    bl_options = { 'UNDO', 'PRESET' }
    bl_description = "Save an ELU file"

    filename_ext = ".elu"
    filter_glob: StringProperty(
        default = "*.elu",
        options = { 'HIDDEN' }
    )

    panelMain: BoolProperty(
        name = "Main",
        description = "Main panel of options",
        default = True
    )

    panelLogging: BoolProperty(
        name = "Logging",
        description = "Log details to the console",
        default = False
    )

    convertUnits: BoolProperty(
        name = "Convert Units",
        description = "Convert measurements from meters to centimeters",
        default = True
    )

    selectedOnly: BoolProperty(
        name = "Selected Only",
        description = "Limit export to selected objects only",
        default = False
    )

    visibleOnly: BoolProperty(
        name = "Visible Only",
        description = "Limit export to visible objects only",
        default = False
    )

    includeChildren: BoolProperty(
        name = "Include Children",
        description = "Include children of selected or visible objects",
        default = True
    )

    logEluHeaders: BoolProperty(
        name = "Elu Headers",
        description = "Log ELU header data",
        default = True
    )

    logEluMats: BoolProperty(
        name = "Elu Materials",
        description = "Log ELU material data",
        default = True
    )

    logEluMeshNodes: BoolProperty(
        name = "Elu Mesh Nodes",
        description = "Log ELU mesh node data",
        default = True
    )

    logVerboseIndices: BoolProperty(
        name = "Verbose Indices",
        description = "Log ELU indices verbosely",
        default = False
    )

    logVerboseWeights: BoolProperty(
        name = "Verbose Weights",
        description = "Log ELU weights verbosely",
        default = False
    )

    def draw(self, context):
        pass

    def execute(self, context):
        return export_rselu.exportElu(self, context)

class RSELU_PT_Export_Main(Panel):
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOL_PROPS"
    bl_label = "Main"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "EXPORT_SCENE_OT_rselu"

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelMain

        layout.prop(operator, "convertUnits")
        layout.prop(operator, "selectedOnly")

        column = layout.column()
        column.prop(operator, "includeChildren")
        column.enabled = operator.selectedOnly

        layout.prop(operator, "visibleOnly")

class RSELU_PT_Export_Logging(Panel):
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOL_PROPS"
    bl_label = "Logging"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "EXPORT_SCENE_OT_rselu"

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

        column = layout.column()
        column.prop(operator, "logVerboseIndices")
        column.prop(operator, "logVerboseWeights")
        column.enabled = operator.logEluMeshNodes

class ExportRSLM(Operator, ExportHelper):
    bl_idname = "export_scene.rslm"
    bl_label = "Export LM"
    bl_options = { 'UNDO', 'PRESET' }
    bl_description = "Save an LM file"

    filename_ext = ".lm"
    filter_glob: StringProperty(
        default = "*.rs.lm",
        options = { 'HIDDEN' }
    )

    panelMain: BoolProperty(
        name = "Main",
        description = "Main panel of options",
        default = True
    )

    doUVs: BoolProperty(
        name = "UV Data",
        description = "Export UV data, requires an active mesh object with valid UVs in channel 3 as well as a GunZ 1 .rs file for the same map in the same directory",
        default = True
    )

    lmVersion4: BoolProperty(
        name = "Version 4",
        description = "Fixes bit depth issues and makes use of DXT1 compression, not compatible with vanilla GunZ",
        default = False
    )

    mod4Fix: BoolProperty(
        name = "MOD4 Fix",
        description = "Compresses the color range to compensate for the D3DTOP_MODULATE4X flag. Disable if re-exporting an existing lightmap",
        default = True
    )

    def draw(self, context):
        pass

    def execute(self, context):
        return export_rslm.exportLm(self, context)

class RSLM_PT_Export_Main(Panel):
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOL_PROPS"
    bl_label = "Main"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == "EXPORT_SCENE_OT_rslm"

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelMain

        layout.prop(operator, "doUVs")
        layout.prop(operator, "lmVersion4")

        column = layout.column()
        column.prop(operator, "mod4Fix")
        column.enabled = not operator.lmVersion4

classes = (
    ImportGZRS2,
    GZRS2_PT_Import_Main,
    GZRS2_PT_Import_Drivers,
    GZRS2_PT_Import_Logging,
    ImportGZRS3,
    GZRS3_PT_Import_Main,
    GZRS3_PT_Import_Logging,
    ImportRSELU,
    RSELU_PT_Import_Main,
    RSELU_PT_Import_Logging,
    ImportRSCOL,
    RSCOL_PT_Import_Main,
    RSCOL_PT_Import_Logging,
    ImportRSLM,
    RSLM_PT_Import_Logging,
    ExportRSELU,
    RSELU_PT_Export_Main,
    RSELU_PT_Export_Logging,
    ExportRSLM,
    RSLM_PT_Export_Main
)

def menu_func_import(self, context):
    self.layout.operator(ImportGZRS2.bl_idname, text = "GunZ RS2 (.rs)")
    self.layout.operator(ImportGZRS3.bl_idname, text = "GunZ RS3 (.scene.xml/.prop.xml)")
    self.layout.operator(ImportRSELU.bl_idname, text = "GunZ ELU (.elu)")
    self.layout.operator(ImportRSCOL.bl_idname, text = "GunZ COL (.col/.cl2)")
    self.layout.operator(ImportRSLM.bl_idname, text = "GunZ LM (.lm)")

def menu_func_export(self, context):
    self.layout.operator(ExportRSELU.bl_idname, text = "GunZ ELU (.elu)")
    self.layout.operator(ExportRSLM.bl_idname, text = "GunZ LM (.lm)")

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

    for cls in classes:
        bpy.utils.unregister_class(cls)

    cleanse_modules()


if __name__ == "__main__":
    register()
