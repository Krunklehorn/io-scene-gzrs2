import os

from mathutils import Vector

from . import import_gzrs2, import_gzrs3, import_rselu, import_rscol, import_rsnav, import_rslm, import_rsani
from . import export_rselu, export_rsnav, export_rslm

from .constants_gzrs2 import *
from .lib_gzrs2 import getEluExportConstants, getMatTreeLinksNodes, getRelevantShaderNodes, checkShaderNodeValidity
from .lib_gzrs2 import getLinkedImageNodes, getShaderNodeByID, getValidImageNodePathSilent, getMatFlagsRender
from .lib_gzrs2 import decomposeTexpath, checkIsEffectNode, checkIsAniTex, processAniTexParameters
from .lib_gzrs2 import setupMatBase, setupMatNodesTransparency, setupMatNodesAdditive, setMatFlagsTransparency
from .lib_gzrs2 import enumIdentifierToIndex, enumIndexToIdentifier

bl_info = {
    'name': 'GZRS2/3 Format',
    'author': 'Krunklehorn',
    'version': (0, 9, 5),
    'blender': (4, 2, 1),
    'location': 'File > Import-Export',
    'description': "GunZ: The Duel RealSpace2/3 content importer.",
    'category': 'Import-Export',
}

if 'bpy' in locals():
    import importlib

    if 'import_gzrs2'   in locals(): importlib.reload(import_gzrs2)
    if 'import_gzrs3'   in locals(): importlib.reload(import_gzrs3)
    if 'import_rselu'   in locals(): importlib.reload(import_rselu)
    if 'import_rscol'   in locals(): importlib.reload(import_rscol)
    if 'import_rsnav'   in locals(): importlib.reload(import_rsnav)
    if 'import_rslm'    in locals(): importlib.reload(import_rslm)
    if 'import_rsani'   in locals(): importlib.reload(import_rsani)
    if 'export_rselu'   in locals(): importlib.reload(export_rselu)
    if 'export_rsnav'   in locals(): importlib.reload(export_rsnav)
    if 'export_rslm'    in locals(): importlib.reload(export_rslm)
else:
    import bpy
    from bpy.types import Operator, Panel, PropertyGroup, AddonPreferences
    from bpy_extras.io_utils import ImportHelper, ExportHelper
    from bpy.props import IntProperty, BoolProperty, FloatProperty, FloatVectorProperty, StringProperty, EnumProperty, PointerProperty

def cleanse_modules():
    import sys

    all_modules = sys.modules
    all_modules = dict(sorted(all_modules.items(), key = lambda x: x[0]))

    for k, v in all_modules.items():
        if k.startswith(__name__):
            del sys.modules[k]

    return

def validateRSDataDirectory(dirpath, isRS3):
    if dirpath == '' or not os.path.exists(dirpath) or not os.path.isdir(dirpath):
        return False

    _, dirnames, _ = next(os.walk(dirpath))

    for token in RS3_VALID_DATA_SUBDIRS if isRS3 else RS2_VALID_DATA_SUBDIRS:
        for dirname in dirnames:
            if token.lower() == dirname.lower():
                return True

    return False

class GZRS2_OT_Apply_Material_Preset(Operator):
    bl_idname = 'gzrs2.apply_material_preset'
    bl_label = "Please select a GunZ 1 material preset..."
    bl_options = { 'REGISTER', 'INTERNAL' }
    bl_description = "Modify a material to make it compatible with the Realspace engine"

    materialPreset: EnumProperty(
        name = 'Preset',
        items = (('COLORED',    'Colored',      "Color material."),
                 ('TEXTURED',   'Textured',     "Textured material."),
                 ('BLENDED',    'Blended',      "Textured, alpha-blended material."),
                 ('TESTED',     'Tested',       "Textured, alpha-tested material."),
                 ('ADDITIVE',   'Additive',     "Textured, additive material."))
    )

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, 'materialPreset')

    def execute(self, context):
        bpy.ops.ed.undo_push()

        version, maxPathLength = getEluExportConstants()

        blObj = context.active_object
        blMat = blObj.active_material
        tree, links, nodes = getMatTreeLinksNodes(blMat)

        shader, output, info, transparent, mix, clip, add = getRelevantShaderNodes(nodes)
        shaderValid, infoValid, transparentValid, mixValid, clipValid, addValid = checkShaderNodeValidity(shader, output, info, transparent, mix, clip, add, links)

        texture, emission, alpha = getLinkedImageNodes(shader, links, clip, clipValid, validOnly = False)

        # Reuse existing image texture nodes
        texture = texture or emission or alpha or getShaderNodeByID(nodes, 'ShaderNodeTexImage')
        emission = emission or texture or alpha
        alpha = alpha or texture or emission

        texpath =       getValidImageNodePathSilent(texture     if texture.image    is not None else None, maxPathLength) if texture    else None
        emitpath =      getValidImageNodePathSilent(emission    if emission.image   is not None else None, maxPathLength) if emission   else None
        alphapath =     getValidImageNodePathSilent(alpha       if alpha.image      is not None else None, maxPathLength) if alpha      else None

        twosided, additive, alphatest, usealphatest, useopacity = getMatFlagsRender(blMat, clip, addValid, clipValid, emission, alpha)

        texBase, texName, _, _ = decomposeTexpath(texpath)
        isEffect = checkIsEffectNode(blObj.name)
        isAniTex = checkIsAniTex(texBase)
        # success, frameCount, frameSpeed, frameGap = processAniTexParameters(isAniTex, texName, silent = True)

        # We avoid links.clear() to preserve the user's material as much as possible
        relevantNodes = [shader, output, info, transparent, mix, clip, add]

        for link in links:
            if link.from_node in relevantNodes or link.to_node in relevantNodes:
                links.remove(link)

        # We assume the setup functions modify valid inputs and only create what is missing
        blMat, tree, links, nodes, shader, output, info, transparent, mix = setupMatBase(blMat.name, blMat = blMat, shader = shader, output = output, info = info, transparent = transparent, mix = mix)

        if self.materialPreset == 'COLORED':
            return { 'FINISHED' }

        texture = texture or nodes.new('ShaderNodeTexImage')
        texture.location = (-440, 300)
        texture.select = False

        links.new(texture.outputs[0], shader.inputs[0]) # Base Color

        if self.materialPreset == 'TEXTURED':
            return { 'FINISHED' }

        if self.materialPreset == 'BLENDED':
            alphatest = 0
            usealphatest = alphatest > 0
            useopacity = True

            clip = setupMatNodesTransparency(blMat, tree, links, nodes, alphatest, usealphatest, useopacity, texture, shader, clip = clip)
        elif self.materialPreset == 'TESTED':
            alphatest = 255.0 / 2.0
            usealphatest = alphatest > 0
            useopacity = False

            clip = setupMatNodesTransparency(blMat, tree, links, nodes, alphatest, usealphatest, useopacity, texture, shader, clip = clip)
        elif self.materialPreset == 'ADDITIVE':
            additive = True

            add = setupMatNodesAdditive(blMat, tree, links, nodes, additive or isEffect, texture, shader, transparent, mix, add = add)

        setMatFlagsTransparency(blMat, usealphatest or useopacity or additive or isEffect, twosided = twosided)

        return { 'FINISHED' }

class GZRS2_OT_Specify_Path_MRS(Operator):
    bl_idname = 'gzrs2.specify_path_mrs'
    bl_label = "Please specify the location of the extracted .mrs data"
    bl_options = { 'REGISTER', 'INTERNAL' }
    bl_description = "Specify the location of the extracted .mrs data"

    dataPath: StringProperty(
        name = 'Path',
        default = '',
        options = { 'ANIMATABLE', 'OUTPUT_PATH' },
        subtype = 'DIR_PATH'
    )

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        self.dataPath = ''
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.dataPath = os.path.abspath(self.dataPath) if self.dataPath != '' else ''
        self.dataPath = os.path.join(self.dataPath, '')

        layout = self.layout
        layout.prop(self, 'dataPath')

    def execute(self, context):
        self.dataPath = os.path.abspath(self.dataPath) if self.dataPath != '' else ''
        self.dataPath = os.path.join(self.dataPath, '')

        if not validateRSDataDirectory(self.dataPath, False):
            self.report({ 'ERROR' }, f"GZRS2: Search path must point to a folder containing a valid data subdirectory!")
            return { 'CANCELLED' }

        context.preferences.addons[__package__].preferences.rs2DataDir = self.dataPath

        return { 'FINISHED' }

class GZRS2_OT_Specify_Path_MRF(Operator):
    bl_idname = 'gzrs2.specify_path_mrf'
    bl_label = "Please specify the location of the extracted .mrf data"
    bl_options = { 'REGISTER', 'INTERNAL' }
    bl_description = "Specify the location of the extracted .mrf data"

    dataPath: StringProperty(
        name = 'Path',
        default = '',
        options = { 'ANIMATABLE', 'OUTPUT_PATH' },
        subtype = 'DIR_PATH'
    )

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        self.dataPath = ''
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.dataPath = os.path.abspath(self.dataPath) if self.dataPath != '' else ''
        self.dataPath = os.path.join(self.dataPath, '')

        layout = self.layout
        layout.prop(self, 'dataPath')

    def execute(self, context):
        self.dataPath = os.path.abspath(self.dataPath) if self.dataPath != '' else ''
        self.dataPath = os.path.join(self.dataPath, '')

        if not validateRSDataDirectory(self.dataPath, True):
            self.report({ 'ERROR' }, f"GZRS2: Search path must point to a folder containing a valid data subdirectory!")
            return { 'CANCELLED' }

        context.preferences.addons[__package__].preferences.rs3DataDir = self.dataPath

        return { 'FINISHED' }

class GZRS2Preferences(AddonPreferences):
    bl_idname = __package__

    rs2DataDir: StringProperty(
        name = 'RS2/.mrs',
        description = "Path to a folder containing extracted .mrs data",
        default = '',
        options = { 'ANIMATABLE', 'OUTPUT_PATH' },
        subtype = 'DIR_PATH'
    )

    rs3DataDir: StringProperty(
        name = 'RS3/.mrf',
        description = "Path to a folder containing extracted .mrf data",
        default = '',
        options = { 'ANIMATABLE', 'OUTPUT_PATH' },
        subtype = 'DIR_PATH'
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text = "Working Directories")

        column = layout.column()
        column.label(text = "Many of the vanilla maps and models share data between packages.")
        column.label(text = "You need to extract ALL of them to a CLEAN working directory.")
        column.label(text = "Any sub-packages you find you will extract in-place.")
        column.label(text = "Don't move them around; the heirarchy must be maintained.")

        box = layout.box()

        column = box.column()
        column.label(text = "Valid data subdirectories for .mrs include:")
        column.label(text = "\'Interface\', \'Maps\', \'Model\', \'Quest\', \'Sfx\', \'Shader\', \'Sound\' and \'System\'")
        column.label(text = "Example: \'C:\\Users\\krunk\\Documents\\GunZ\\clean\\")

        row = column.row()
        row.label(text = self.rs2DataDir)
        row.operator(GZRS2_OT_Specify_Path_MRS.bl_idname, text = "Set .mrs (GunZ 1) data path...")

        column = box.column()
        column.label(text = "Valid data subdirectories for .mrf include:")
        column.label(text = "\'Data\' and \'EngineRes\'")
        column.label(text = "Example: \'C:\\Users\\krunk\\Documents\\GunZ2\\z3ResEx\\datadump\\")

        row = column.row()
        row.label(text = self.rs3DataDir)
        row.operator(GZRS2_OT_Specify_Path_MRF.bl_idname, text = "Set .mrf (GunZ 2) data path...")


class ImportGZRS2(Operator, ImportHelper):
    bl_idname = 'import_scene.gzrs2'
    bl_label = 'Import RS2'
    bl_options = { 'UNDO', 'PRESET' }
    bl_description = "Load an RS file"

    filter_glob: StringProperty(
        default = '*.rs',
        options = { 'HIDDEN' }
    )

    panelMain: BoolProperty(
        name = 'Main',
        description = "Main panel of options",
        default = True
    )

    panelDrivers: BoolProperty(
        name = 'Drivers',
        description = "Generate drivers to quickly adjust map data",
        default = True
    )

    panelLogging: BoolProperty(
        name = 'Logging',
        description = "Log details to the console",
        default = False
    )

    convertUnits: BoolProperty(
        name = 'Convert Units',
        description = "Convert measurements from centimeters to meters",
        default = True
    )

    meshMode: EnumProperty(
        name = 'Mesh Mode',
        items = (('STANDARD',   'Standard',     "Split geometry by material, optionally perform cleanup."),
                 ('BAKE',       'Bake',         "Don't split geometry or perform any cleanup."))
    )

    texSearchMode: EnumProperty(
        name = 'Texture Mode',
        items = (('PATH',       'Path',         "Search for textures using the specified path (faster)"),
                 ('BRUTE',      'Brute',        "Search for textures in surrounding filesystem (slow, may freeze)"),
                 ('SKIP',       'Skip',         "Don't search for or load any textures (fastest)"))
    )

    doBsptree: BoolProperty(
        name = 'Bsptree (slow)',
        description = "Import Bsptree data",
        default = False
    )

    doCollision: BoolProperty(
        name = 'Collision',
        description = "Import collision data",
        default = True
    )

    doNavigation: BoolProperty(
        name = 'Navigation',
        description = "Import navigation data",
        default = True
    )

    doLightmap: BoolProperty(
        name = 'Lightmap',
        description = "Import lightmap data",
        default = True
    )

    doLights: BoolProperty(
        name = 'Lights',
        description = "Import light data",
        default = True
    )

    tweakLights: BoolProperty(
        name = 'Tweak Lights',
        description = "Tweaks light data to give comparable results directly in Blender",
        default = True
    )

    doProps: BoolProperty(
        name = 'Props',
        description = "Import model data",
        default = True
    )

    doDummies: BoolProperty(
        name = 'Dummies',
        description = "Import cameras, lense flares, spawn points and more as empties",
        default = True
    )

    doOcclusion: BoolProperty(
        name = 'Occlusion',
        description = "Import occlusion planes",
        default = True
    )

    doFog: BoolProperty(
        name = 'Fog',
        description = "Create fog volume with Volume Scatter/Absorption nodes from fog settings",
        default = True
    )

    doSounds: BoolProperty(
        name = 'Sounds',
        description = "Import ambient sounds",
        default = True
    )

    doMisc: BoolProperty(
        name = 'Misc',
        description = "Import item, flag and smoke data",
        default = True
    )

    doBounds: BoolProperty(
        name = 'Bounds (slow)',
        description = "Create empties for bsptree and octree bounding boxes",
        default = False
    )

    doLightDrivers: BoolProperty(
        name = 'Lights',
        description = "Generate drivers to quickly control groups of similar lights",
        default = True
    )

    doFogDriver: BoolProperty(
        name = 'Fog',
        description = "Generate driver to control fog settings",
        default = True
    )

    doCleanup: BoolProperty(
        name = 'Cleanup',
        description = "Deletes loose geometry, removes doubles and sets each mesh to render smooth",
        default = True
    )

    logRsHeaders: BoolProperty(
        name = 'RS Headers',
        description = "Log RS header data",
        default = True
    )

    logRsPortals: BoolProperty(
        name = 'RS Portals',
        description = "Log RS portal data",
        default = True
    )

    logRsCells: BoolProperty(
        name = 'RS Cells',
        description = "Log RS cell data",
        default = True
    )

    logRsGeometry: BoolProperty(
        name = 'RS Geometry',
        description = "Log RS geometry data",
        default = True
    )

    logRsTrees: BoolProperty(
        name = 'RS Trees',
        description = "Log RS tree data",
        default = True
    )

    logRsPolygons: BoolProperty(
        name = 'RS Polygons',
        description = "Log RS polygon data",
        default = False
    )

    logRsVerts: BoolProperty(
        name = 'RS Vertices',
        description = "Log RS vertex data",
        default = False
    )

    logBspHeaders: BoolProperty(
        name = 'BSP Headers',
        description = "Log BSP header data",
        default = True
    )

    logBspPolygons: BoolProperty(
        name = 'BSP Polygons',
        description = "Log BSP polygon data",
        default = False
    )

    logBspVerts: BoolProperty(
        name = 'BSP Vertices',
        description = "Log BSP vertex data",
        default = False
    )

    logColHeaders: BoolProperty(
        name = 'Col Headers',
        description = "Log Col header data",
        default = True
    )

    logColNodes: BoolProperty(
        name = 'Col Nodes',
        description = "Log Col node data",
        default = False
    )

    logColTris: BoolProperty(
        name = 'Col Triangles',
        description = "Log Col triangle data",
        default = False
    )

    logNavHeaders: BoolProperty(
        name = 'Nav Headers',
        description = "Log Nav header data",
        default = True
    )

    logNavData: BoolProperty(
        name = 'Nav Data',
        description = "Log Nav data",
        default = True
    )

    logLmHeaders: BoolProperty(
        name = 'Lm Headers',
        description = "Log Lm header data",
        default = True
    )

    logLmImages: BoolProperty(
        name = 'Lm Images',
        description = "Log Lm image data",
        default = False
    )

    logEluHeaders: BoolProperty(
        name = 'Elu Headers',
        description = "Log ELU header data",
        default = True
    )

    logEluMats: BoolProperty(
        name = 'Elu Materials',
        description = "Log ELU material data",
        default = True
    )

    logEluMeshNodes: BoolProperty(
        name = 'Elu Mesh Nodes',
        description = "Log ELU mesh node data",
        default = True
    )

    logVerboseIndices: BoolProperty(
        name = 'Verbose Indices',
        description = "Log ELU indices verbosely",
        default = False
    )

    logVerboseWeights: BoolProperty(
        name = 'Verbose Weights',
        description = "Log ELU weights verbosely",
        default = False
    )

    logCleanup: BoolProperty(
        name = 'Cleanup',
        description = "Log results of the the cleanup routine",
        default = False
    )

    def draw(self, context):
        pass

    def execute(self, context):
        return import_gzrs2.importRS2(self, context)

class GZRS2_PT_Import_Main(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'Main'
    bl_parent_id = 'FILE_PT_operator'

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == 'IMPORT_SCENE_OT_gzrs2'

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelMain

        layout.prop(operator, 'convertUnits')
        layout.prop(operator, 'meshMode')
        layout.prop(operator, 'texSearchMode')

        column = layout.column()
        column.prop(operator, 'doBsptree')
        column.prop(operator, 'doCollision')
        column.prop(operator, 'doNavigation')
        column.enabled = operator.meshMode != 'BAKE'

        layout.prop(operator, 'doLightmap')
        layout.prop(operator, 'doLights')

        column = layout.column()
        column.prop(operator, 'tweakLights')
        column.enabled = operator.doLights

        layout.prop(operator, 'doProps')

        column = layout.column()
        column.prop(operator, 'doDummies')
        column.prop(operator, 'doOcclusion')
        column.enabled = operator.meshMode != 'BAKE'

        layout.prop(operator, 'doFog')

        column = layout.column()
        column.prop(operator, 'doSounds')
        column.prop(operator, 'doMisc')
        column.prop(operator, 'doBounds')
        column.enabled = operator.meshMode != 'BAKE'

        layout.prop(operator, 'doCleanup')

class GZRS2_PT_Import_Drivers(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'Drivers'
    bl_parent_id = 'FILE_PT_operator'

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == 'IMPORT_SCENE_OT_gzrs2'

    def draw_header(self, context):
        self.layout.prop(context.space_data.active_operator, 'panelDrivers', text = "")

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelDrivers

        layout.prop(operator, 'doLightDrivers')
        layout.prop(operator, 'doFogDriver')

class GZRS2_PT_Import_Logging(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'Logging'
    bl_parent_id = 'FILE_PT_operator'

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == 'IMPORT_SCENE_OT_gzrs2'

    def draw_header(self, context):
        self.layout.prop(context.space_data.active_operator, 'panelLogging', text = "")

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelLogging

        layout.prop(operator, 'logRsHeaders')
        layout.prop(operator, 'logRsPortals')
        layout.prop(operator, 'logRsCells')
        layout.prop(operator, 'logRsGeometry')
        layout.prop(operator, 'logRsTrees')
        layout.prop(operator, 'logRsPolygons')
        layout.prop(operator, 'logRsVerts')
        layout.prop(operator, 'logBspHeaders')
        layout.prop(operator, 'logBspPolygons')
        layout.prop(operator, 'logBspVerts')
        layout.prop(operator, 'logColHeaders')
        layout.prop(operator, 'logColNodes')
        layout.prop(operator, 'logColTris')
        layout.prop(operator, 'logNavHeaders')
        layout.prop(operator, 'logNavData')
        layout.prop(operator, 'logLmHeaders')
        layout.prop(operator, 'logLmImages')
        layout.prop(operator, 'logEluHeaders')
        layout.prop(operator, 'logEluMats')
        layout.prop(operator, 'logEluMeshNodes')

        column = layout.column()
        column.prop(operator, 'logVerboseIndices')
        column.prop(operator, 'logVerboseWeights')
        column.enabled = operator.logEluMeshNodes

        layout.prop(operator, 'logCleanup')

class ImportGZRS3(Operator, ImportHelper):
    bl_idname = 'import_scene.gzrs3'
    bl_label = 'Import RS3'
    bl_options = { 'UNDO', 'PRESET' }
    bl_description = "Load a SCENE.XML/PROP.XML file"

    filter_glob: StringProperty(
        default = '*.scene.xml;*.prop.xml',
        options = { 'HIDDEN' }
    )

    panelMain: BoolProperty(
        name = 'Main',
        description = "Main panel of options",
        default = True
    )

    panelLogging: BoolProperty(
        name = 'Logging',
        description = "Log details to the console",
        default = False
    )

    convertUnits: BoolProperty(
        name = 'Convert Units',
        description = "Convert measurements from centimeters to meters",
        default = True
    )

    texSearchMode: EnumProperty(
        name = 'Texture Mode',
        items = (('PATH',       'Path',         "Search for textures using the specified path (faster)"),
                 ('BRUTE',      'Brute',        "Search for textures in surrounding filesystem (slow, may freeze)"),
                 ('SKIP',       'Skip',         "Don't search for or load any textures (fastest)"))
    )

    doCleanup: BoolProperty(
        name = 'Cleanup',
        description = "Deletes loose geometry, removes doubles and sets each mesh to render smooth",
        default = True
    )

    logSceneNodes: BoolProperty(
        name = 'Scene Nodes',
        description = "Log scene node data",
        default = True
    )

    logEluHeaders: BoolProperty(
        name = 'Elu Headers',
        description = "Log ELU header data",
        default = True
    )

    logEluMats: BoolProperty(
        name = 'Elu Materials',
        description = "Log ELU material data",
        default = True
    )

    logEluMeshNodes: BoolProperty(
        name = 'Elu Mesh Nodes',
        description = "Log ELU mesh node data",
        default = True
    )

    logVerboseIndices: BoolProperty(
        name = 'Verbose Indices',
        description = "Log ELU indices verbosely",
        default = False
    )

    logVerboseWeights: BoolProperty(
        name = 'Verbose Weights',
        description = "Log ELU weights verbosely",
        default = False
    )

    logCleanup: BoolProperty(
        name = 'Cleanup',
        description = "Log results of the the cleanup routine",
        default = False
    )

    def draw(self, context):
        pass

    def execute(self, context):
        return import_gzrs3.importRS3(self, context)

class GZRS3_PT_Import_Main(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'Main'
    bl_parent_id = 'FILE_PT_operator'

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == 'IMPORT_SCENE_OT_gzrs3'

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelMain

        layout.prop(operator, 'convertUnits')
        layout.prop(operator, 'texSearchMode')

        layout.prop(operator, 'doCleanup')

class GZRS3_PT_Import_Logging(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'Logging'
    bl_parent_id = 'FILE_PT_operator'

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == 'IMPORT_SCENE_OT_gzrs3'

    def draw_header(self, context):
        self.layout.prop(context.space_data.active_operator, 'panelLogging', text = "")

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelLogging

        layout.prop(operator, 'logSceneNodes')
        layout.prop(operator, 'logEluHeaders')
        layout.prop(operator, 'logEluMats')
        layout.prop(operator, 'logEluMeshNodes')

        column = layout.column()
        column.prop(operator, 'logVerboseIndices')
        column.prop(operator, 'logVerboseWeights')
        column.enabled = operator.logEluMeshNodes

        layout.prop(operator, 'logCleanup')

class ImportRSELU(Operator, ImportHelper):
    bl_idname = 'import_scene.rselu'
    bl_label = 'Import ELU'
    bl_options = { 'UNDO', 'PRESET' }
    bl_description = "Load an ELU file"

    filter_glob: StringProperty(
        default = '*.elu',
        options = { 'HIDDEN' }
    )

    panelMain: BoolProperty(
        name = 'Main',
        description = "Main panel of options",
        default = True
    )

    panelLogging: BoolProperty(
        name = 'Logging',
        description = "Log details to the console",
        default = False
    )

    convertUnits: BoolProperty(
        name = 'Convert Units',
        description = "Convert measurements from centimeters to meters",
        default = True
    )

    texSearchMode: EnumProperty(
        name = 'Texture Mode',
        items = (('PATH',       'Path',         "Search for textures using the specified path (faster)"),
                 ('BRUTE',      'Brute',        "Search for textures in surrounding filesystem (slow, may freeze)"),
                 ('SKIP',       'Skip',         "Don't search for or load any textures (fastest)"))
    )

    doBoneRolls: BoolProperty(
        name = 'Bone Rolls',
        description = "Re-calculate all bone rolls to the positive world z-axis. Required for twist bone constraints to work properly",
        default = False
    )

    doTwistConstraints: BoolProperty(
        name = 'Twist Constraints',
        description = "Automatically add constraints for twist bones. Bone rolls are required to be re-calculated first",
        default = True
    )

    doCleanup: BoolProperty(
        name = 'Cleanup',
        description = "Deletes loose geometry, removes doubles and sets each mesh to render smooth",
        default = True
    )

    logEluHeaders: BoolProperty(
        name = 'Elu Headers',
        description = "Log ELU header data",
        default = True
    )

    logEluMats: BoolProperty(
        name = 'Elu Materials',
        description = "Log ELU material data",
        default = True
    )

    logEluMeshNodes: BoolProperty(
        name = 'Elu Mesh Nodes',
        description = "Log ELU mesh node data",
        default = True
    )

    logVerboseIndices: BoolProperty(
        name = 'Verbose Indices',
        description = "Log ELU indices verbosely",
        default = False
    )

    logVerboseWeights: BoolProperty(
        name = 'Verbose Weights',
        description = "Log ELU weights verbosely",
        default = False
    )

    logCleanup: BoolProperty(
        name = 'Cleanup',
        description = "Log results of the the cleanup routine",
        default = False
    )

    def draw(self, context):
        pass

    def execute(self, context):
        return import_rselu.importElu(self, context)

class RSELU_PT_Import_Main(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'Main'
    bl_parent_id = 'FILE_PT_operator'

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == 'IMPORT_SCENE_OT_rselu'

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelMain

        layout.prop(operator, 'convertUnits')
        layout.prop(operator, 'texSearchMode')

        layout.prop(operator, 'doBoneRolls')

        column = layout.column()
        column.prop(operator, 'doTwistConstraints')
        column.enabled = operator.doBoneRolls

        layout.prop(operator, 'doCleanup')

class RSELU_PT_Import_Logging(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'Logging'
    bl_parent_id = 'FILE_PT_operator'

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == 'IMPORT_SCENE_OT_rselu'

    def draw_header(self, context):
        self.layout.prop(context.space_data.active_operator, 'panelLogging', text = "")

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelLogging

        layout.prop(operator, 'logEluHeaders')
        layout.prop(operator, 'logEluMats')
        layout.prop(operator, 'logEluMeshNodes')

        column = layout.column()
        column.prop(operator, 'logVerboseIndices')
        column.prop(operator, 'logVerboseWeights')
        column.enabled = operator.logEluMeshNodes

        layout.prop(operator, 'logCleanup')

class ImportRSANI(Operator, ImportHelper):
    bl_idname = 'import_scene.rsani'
    bl_label = 'Import ANI'
    bl_options = { 'UNDO', 'PRESET' }
    bl_description = "Load an ANI file"

    filter_glob: StringProperty(
        default = '*.ani',
        options = { 'HIDDEN' }
    )

    panelMain: BoolProperty(
        name = 'Main',
        description = "Main panel of options",
        default = True
    )

    panelLogging: BoolProperty(
        name = 'Logging',
        description = "Log details to the console",
        default = False
    )

    convertUnits: BoolProperty(
        name = 'Convert Units',
        description = "Convert measurements from centimeters to meters",
        default = True
    )

    overwriteAction: BoolProperty(
        name = 'Overwrite Action',
        description = "Overwrite action data if found by matching name. Disable to always create a new action",
        default = True
    )

    selectedOnly: BoolProperty(
        name = 'Selected Only',
        description = "Limit import to selected objects only. Does not apply to TRANSFORM or BONE types",
        default = False
    )

    includeChildren: BoolProperty(
        name = 'Include Children',
        description = "Include children of selected objects.  Does not apply to TRANSFORM or BONE types",
        default = True
    )

    visibleOnly: BoolProperty(
        name = 'Visible Only',
        description = "Limit import to visible objects only.  Does not apply to TRANSFORM or BONE types",
        default = False
    )

    logAniHeaders: BoolProperty(
        name = 'Ani Headers',
        description = "Log Ani header data",
        default = True
    )

    logAniNodes: BoolProperty(
        name = 'Ani Nodes',
        description = "Log ANI node data",
        default = True
    )

    def draw(self, context):
        pass

    def execute(self, context):
        return import_rsani.importAni(self, context)

class RSANI_PT_Import_Main(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'Main'
    bl_parent_id = 'FILE_PT_operator'

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == 'IMPORT_SCENE_OT_rsani'

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelMain

        layout.prop(operator, 'convertUnits')
        layout.prop(operator, 'overwriteAction')
        layout.prop(operator, 'selectedOnly')

        column = layout.column()
        column.prop(operator, 'includeChildren')
        column.enabled = operator.selectedOnly

        layout.prop(operator, 'visibleOnly')

class RSANI_PT_Import_Logging(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'Logging'
    bl_parent_id = 'FILE_PT_operator'

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == 'IMPORT_SCENE_OT_rsani'

    def draw_header(self, context):
        self.layout.prop(context.space_data.active_operator, 'panelLogging', text = "")

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelLogging

        layout.prop(operator, 'logAniHeaders')
        layout.prop(operator, 'logAniNodes')

class ImportRSCOL(Operator, ImportHelper):
    bl_idname = 'import_scene.rscol'
    bl_label = 'Import COL'
    bl_options = { 'UNDO', 'PRESET' }
    bl_description = "Load a COL/CL2 file"

    filter_glob: StringProperty(
        default = '*.col;*.cl2',
        options = { 'HIDDEN' }
    )

    panelMain: BoolProperty(
        name = 'Main',
        description = "Main panel of options",
        default = True
    )

    panelLogging: BoolProperty(
        name = 'Logging',
        description = "Log details to the console",
        default = False
    )

    convertUnits: BoolProperty(
        name = 'Convert Units',
        description = "Convert measurements from centimeters to meters",
        default = True
    )

    doCleanup: BoolProperty(
        name = 'Cleanup',
        description = "A combination of knife intersection, three types of dissolve, merge by distance, tris-to-quads, and hole filling",
        default = True
    )

    logColHeaders: BoolProperty(
        name = 'Col Headers',
        description = "Log Col header data",
        default = True
    )

    logColNodes: BoolProperty(
        name = 'Col Nodes',
        description = "Log Col node data",
        default = False
    )

    logColTris: BoolProperty(
        name = 'Col Triangles',
        description = "Log Col triangle data",
        default = False
    )

    logCleanup: BoolProperty(
        name = 'Cleanup',
        description = "Log results of the the cleanup routine",
        default = False
    )

    def draw(self, context):
        pass

    def execute(self, context):
        return import_rscol.importCol(self, context)

class RSCOL_PT_Import_Main(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'Main'
    bl_parent_id = 'FILE_PT_operator'

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == 'IMPORT_SCENE_OT_rscol'

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelMain

        layout.prop(operator, 'convertUnits')
        layout.prop(operator, 'doCleanup')

class RSCOL_PT_Import_Logging(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'Logging'
    bl_parent_id = 'FILE_PT_operator'

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == 'IMPORT_SCENE_OT_rscol'

    def draw_header(self, context):
        self.layout.prop(context.space_data.active_operator, 'panelLogging', text = "")

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelLogging

        layout.prop(operator, 'logColHeaders')
        layout.prop(operator, 'logColNodes')
        layout.prop(operator, 'logColTris')
        layout.prop(operator, 'logCleanup')

class ImportRSNAV(Operator, ImportHelper):
    bl_idname = 'import_scene.rsnav'
    bl_label = 'Import NAV'
    bl_options = { 'UNDO', 'PRESET' }
    bl_description = "Load a NAV file"

    filter_glob: StringProperty(
        default = '*.nav',
        options = { 'HIDDEN' }
    )

    panelMain: BoolProperty(
        name = 'Main',
        description = "Main panel of options",
        default = True
    )

    panelLogging: BoolProperty(
        name = 'Logging',
        description = "Log details to the console",
        default = False
    )

    convertUnits: BoolProperty(
        name = 'Convert Units',
        description = "Convert measurements from centimeters to meters",
        default = True
    )

    logNavHeaders: BoolProperty(
        name = 'Nav Headers',
        description = "Log Nav header data",
        default = True
    )

    logNavData: BoolProperty(
        name = 'Nav Data',
        description = "Log Nav data",
        default = True
    )

    def draw(self, context):
        pass

    def execute(self, context):
        return import_rsnav.importNav(self, context)

class RSNAV_PT_Import_Main(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'Main'
    bl_parent_id = 'FILE_PT_operator'

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == 'IMPORT_SCENE_OT_rsnav'

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelMain

        layout.prop(operator, 'convertUnits')

class RSNAV_PT_Import_Logging(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'Logging'
    bl_parent_id = 'FILE_PT_operator'

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == 'IMPORT_SCENE_OT_rsnav'

    def draw_header(self, context):
        self.layout.prop(context.space_data.active_operator, 'panelLogging', text = "")

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelLogging

        layout.prop(operator, 'logNavHeaders')
        layout.prop(operator, 'logNavData')

class ImportRSLM(Operator, ImportHelper):
    bl_idname = 'import_scene.rslm'
    bl_label = 'Import LM'
    bl_options = { 'UNDO', 'PRESET' }
    bl_description = "Load an LM file"

    filter_glob: StringProperty(
        default = '*.lm',
        options = { 'HIDDEN' }
    )

    logLmHeaders: BoolProperty(
        name = 'Lm Headers',
        description = "Log Lm header data",
        default = False
    )

    logLmImages: BoolProperty(
        name = 'Lm Images',
        description = "Log Lm image data",
        default = False
    )

    def draw(self, context):
        pass

    def execute(self, context):
        return import_rslm.importLm(self, context)

class RSLM_PT_Import_Logging(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'Logging'
    bl_parent_id = 'FILE_PT_operator'

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == 'IMPORT_SCENE_OT_rslm'

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.prop(operator, 'logLmHeaders')
        layout.prop(operator, 'logLmImages')

class ExportRSELU(Operator, ExportHelper):
    bl_idname = 'export_scene.rselu'
    bl_label = 'Export ELU'
    bl_options = { 'UNDO', 'PRESET' }
    bl_description = "Save an ELU file"

    filename_ext = '.elu'
    filter_glob: StringProperty(
        default = '*.elu',
        options = { 'HIDDEN' }
    )

    panelMain: BoolProperty(
        name = 'Main',
        description = "Main panel of options",
        default = True
    )

    panelLogging: BoolProperty(
        name = 'Logging',
        description = "Log details to the console",
        default = False
    )

    convertUnits: BoolProperty(
        name = 'Convert Units',
        description = "Convert measurements from meters to centimeters",
        default = True
    )

    selectedOnly: BoolProperty(
        name = 'Selected Only',
        description = "Limit export to selected objects only",
        default = False
    )

    includeChildren: BoolProperty(
        name = 'Include Children',
        description = "Include children of selected objects",
        default = True
    )

    visibleOnly: BoolProperty(
        name = 'Visible Only',
        description = "Limit export to visible objects only",
        default = False
    )

    logEluHeaders: BoolProperty(
        name = 'Elu Headers',
        description = "Log ELU header data",
        default = True
    )

    logEluMats: BoolProperty(
        name = 'Elu Materials',
        description = "Log ELU material data",
        default = True
    )

    logEluMeshNodes: BoolProperty(
        name = 'Elu Mesh Nodes',
        description = "Log ELU mesh node data",
        default = True
    )

    logVerboseIndices: BoolProperty(
        name = 'Verbose Indices',
        description = "Log ELU indices verbosely",
        default = False
    )

    logVerboseWeights: BoolProperty(
        name = 'Verbose Weights',
        description = "Log ELU weights verbosely",
        default = False
    )

    def draw(self, context):
        pass

    def execute(self, context):
        return export_rselu.exportElu(self, context)

class RSELU_PT_Export_Main(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'Main'
    bl_parent_id = 'FILE_PT_operator'

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == 'EXPORT_SCENE_OT_rselu'

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelMain

        layout.prop(operator, 'convertUnits')
        layout.prop(operator, 'selectedOnly')

        column = layout.column()
        column.prop(operator, 'includeChildren')
        column.enabled = operator.selectedOnly

        layout.prop(operator, 'visibleOnly')

class RSELU_PT_Export_Logging(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'Logging'
    bl_parent_id = 'FILE_PT_operator'

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == 'EXPORT_SCENE_OT_rselu'

    def draw_header(self, context):
        self.layout.prop(context.space_data.active_operator, 'panelLogging', text = "")

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelLogging

        layout.prop(operator, 'logEluHeaders')
        layout.prop(operator, 'logEluMats')
        layout.prop(operator, 'logEluMeshNodes')

        column = layout.column()
        column.prop(operator, 'logVerboseIndices')
        column.prop(operator, 'logVerboseWeights')
        column.enabled = operator.logEluMeshNodes

class ExportRSNAV(Operator, ExportHelper):
    bl_idname = 'export_scene.rsnav'
    bl_label = 'Export NAV'
    bl_options = { 'UNDO', 'PRESET' }
    bl_description = "Save an NAV file"

    filename_ext = '.nav'
    filter_glob: StringProperty(
        default = '*.nav',
        options = { 'HIDDEN' }
    )

    panelMain: BoolProperty(
        name = 'Main',
        description = "Main panel of options",
        default = True
    )

    panelLogging: BoolProperty(
        name = 'Logging',
        description = "Log details to the console",
        default = False
    )

    convertUnits: BoolProperty(
        name = 'Convert Units',
        description = "Convert measurements from meters to centimeters",
        default = True
    )

    logNavHeaders: BoolProperty(
        name = 'Nav Headers',
        description = "Log NAV header data",
        default = True
    )

    logNavData: BoolProperty(
        name = 'Nav Data',
        description = "Log NAV mesh data",
        default = True
    )

    def draw(self, context):
        pass

    def execute(self, context):
        return export_rsnav.exportNav(self, context)

class RSNAV_PT_Export_Main(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'Main'
    bl_parent_id = 'FILE_PT_operator'

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == 'EXPORT_SCENE_OT_rsnav'

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelMain

        layout.prop(operator, 'convertUnits')

class RSNAV_PT_Export_Logging(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'Logging'
    bl_parent_id = 'FILE_PT_operator'

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == 'EXPORT_SCENE_OT_rsnav'

    def draw_header(self, context):
        self.layout.prop(context.space_data.active_operator, 'panelLogging', text = "")

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelLogging

        layout.prop(operator, 'logNavHeaders')
        layout.prop(operator, 'logNavData')

class ExportRSLM(Operator, ExportHelper):
    bl_idname = 'export_scene.rslm'
    bl_label = 'Export LM'
    bl_options = { 'UNDO', 'PRESET' }
    bl_description = "Save an LM file"

    filename_ext = '.lm'
    filter_glob: StringProperty(
        default = '*.rs.lm',
        options = { 'HIDDEN' }
    )

    panelMain: BoolProperty(
        name = 'Main',
        description = "Main panel of options",
        default = True
    )

    panelLogging: BoolProperty(
        name = 'Logging',
        description = "Log details to the console",
        default = False
    )

    doUVs: BoolProperty(
        name = 'UV Data',
        description = "Export UV data, requires an active mesh object with valid UVs in channel 3 as well as a GunZ 1 .rs file for the same map in the same directory",
        default = True
    )

    lmVersion4: BoolProperty(
        name = 'Version 4',
        description = "Fixes bit depth issues and makes use of DXT1 compression, not compatible with vanilla GunZ",
        default = False
    )

    mod4Fix: BoolProperty(
        name = 'MOD4 Fix',
        description = "Compresses the color range to compensate for the D3DTOP_MODULATE4X flag. Disable if re-exporting an existing lightmap",
        default = True
    )

    logLmHeaders: BoolProperty(
        name = 'Lm Headers',
        description = "Log Lm header data",
        default = True
    )

    def draw(self, context):
        pass

    def execute(self, context):
        return export_rslm.exportLm(self, context)

class RSLM_PT_Export_Main(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'Main'
    bl_parent_id = 'FILE_PT_operator'

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == 'EXPORT_SCENE_OT_rslm'

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelMain

        layout.prop(operator, 'doUVs')
        layout.prop(operator, 'lmVersion4')

        column = layout.column()
        column.prop(operator, 'mod4Fix')
        column.enabled = not operator.lmVersion4

class RSLM_PT_Export_Logging(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'Logging'
    bl_parent_id = 'FILE_PT_operator'

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == 'EXPORT_SCENE_OT_rslm'

    def draw_header(self, context):
        self.layout.prop(context.space_data.active_operator, 'panelLogging', text = "")

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelLogging

        layout.prop(operator, 'logLmHeaders')

class GZRS2ObjectProperties(PropertyGroup):
    def ensureAll(self):
        if 'dummyType'          not in self: self['dummyType']          = 'NONE'
        if 'spawnType'          not in self: self['spawnType']          = 'SOLO'
        if 'spawnIndex'         not in self: self['spawnIndex']         = 1
        if 'spawnTeamID'        not in self: self['spawnTeamID']        = 1
        if 'spawnEnemyType'     not in self: self['spawnEnemyType']     = 'MELEE'
        if 'spawnBlitzType'     not in self: self['spawnBlitzType']     = 'BARRICADE'
        if 'soundFileName'      not in self: self['soundFileName']      = ''
        if 'soundSpace'         not in self: self['soundSpace']         = '2D'
        if 'soundShape'         not in self: self['soundShape']         = 'AABB'
        if 'itemGameID'         not in self: self['itemGameID']         = 'SOLO'
        if 'itemType'           not in self: self['itemType']           = 'HP'
        if 'itemID'             not in self: self['itemID']             = 1
        if 'itemTimer'          not in self: self['itemTimer']          = 30000
        if 'smokeType'          not in self: self['smokeType']          = 'SS'
        if 'smokeDirection'     not in self: self['smokeDirection']     = 0
        if 'smokePower'         not in self: self['smokePower']         = 0.0
        if 'smokeDelay'         not in self: self['smokeDelay']         = 100
        if 'smokeSize'          not in self: self['smokeSize']          = 40.0
        if 'smokeLife'          not in self: self['smokeLife']          = 1.0
        if 'smokeToggleMinTime' not in self: self['smokeToggleMinTime'] = 2.0

    def onUpdate(self, context):
        blObj = context.active_object

        if blObj is None or blObj.data is not None:
            return

        props = blObj.gzrs2

        # TODO: Custom sprite gizmos
        if props.dummyType == 'SOUND':
            if props.soundShape == 'AABB':
                blObj.empty_display_type = 'CUBE'
            elif props.soundShape == 'SPHERE':
                blObj.empty_display_type = 'SPHERE'
        elif props.dummyType == 'ITEM':
            blObj.empty_display_type = 'SPHERE'
        else:
            blObj.empty_display_type = 'ARROWS'

    dummyTypeEnumItems = (
        ('NONE',        'None',         "Not a Realspace object. Will not be exported"),
        ('SPAWN',       'Spawn',        "Spawn location for characters"),
        ('SUN',         'Sun',          "Sun spot location. Not an actual light source"),
        ('SOUND',       'Sound',        "Ambient sound, based on proximity to a sphere or axis-aligned bounding box center"),
        ('ITEM',        'Item',         "Health, armor, ammo etc"),
        ('SMOKE',       'Smoke',        "Smoke particle generator")
    )

    spawnTypeEnumItems = (
        ('SOLO',        'Solo',         "Free-for-all and Quest spawn for players"),
        ('TEAM',        'Team',         "Team oriented spawn for players"),
        ('NPC',         'Enemy',        "Quest spawn for enemies"),
        ('BLITZ',       'Blitzkrieg',   "Spawns for the blitzkrieg gametype")
    )

    spawnEnemyTypeEnumItems = (
        ('MELEE',       'Melee',        "Spawn for melee enemies"),
        ('RANGED',      'Ranged',       "Spawn for ranged enemies"),
        ('BOSS',        'Boss',         "Spawn for a boss enemy")
    )

    spawnBlitzTypeEnumItems = (
        ('BARRICADE',   'Barricade',    "Spawn for barricades"),
        ('GUARDIAN',    'Guardian',     "Spawn for guardians"),
        ('RADAR',       'Radar',        "Spawn for radars"),
        ('TREASURE',    'Treasure',     "Spawn for treasures")
    )

    soundSpaceEnumItems = (
        ('2D',          '2D',           "Two-dimensional, no stereo image. Good for reverberant, omnidirectional ambience"),
        ('3D',          '3D',           "Three-dimensional, stereo enabled. Good for directional sounds with a clear source")
    )

    soundShapeEnumItems = (
        ('AABB',        'AABB',         "Proximity through an axis-aligned bounding box toward it's center"),
        ('SPHERE',      'Sphere',       "Proximity through a sphere toward it's center")
    )

    itemGameIDEnumItems = (
        ('SOLO',        'Solo',         "Free-for-all gametypes"),
        ('TEAM',        'Team',         "Team oriented gametypes")
    )

    itemTypeEnumItems = (
        ('HP',          'Health',       "Refills a portion of the player's health"),
        ('AP',          'Armor',        "Refills a portion of the player's armor"),
        ('BULLET',      'Bullet',       "Grants some ammunition for the player's gun")
    )

    smokeTypeEnumItems = (
        ('SS',          'Smoke',        "Standard smoke, think Factory"),
        ('ST',          'Train Steam',  "Train steam"),
        ('TS',          'Train Smoke',  "Train smoke (unused)")
    )

    def onGetDummyType(self):           self.ensureAll(); return enumIdentifierToIndex(self, self['dummyType'],         self.dummyTypeEnumItems)
    def onGetSpawnType(self):           self.ensureAll(); return enumIdentifierToIndex(self, self['spawnType'],         self.spawnTypeEnumItems)
    def onGetSpawnIndex(self):          self.ensureAll(); return self['spawnIndex']
    def onGetSpawnTeamID(self):         self.ensureAll(); return self['spawnTeamID']
    def onGetSpawnEnemyType(self):      self.ensureAll(); return enumIdentifierToIndex(self, self['spawnEnemyType'],    self.spawnEnemyTypeEnumItems)
    def onGetSpawnBlitzType(self):      self.ensureAll(); return enumIdentifierToIndex(self, self['spawnBlitzType'],    self.spawnBlitzTypeEnumItems)
    def onGetSoundFileName(self):       self.ensureAll(); return self['soundFileName']
    def onGetSoundSpace(self):          self.ensureAll(); return enumIdentifierToIndex(self, self['soundSpace'],        self.soundSpaceEnumItems)
    def onGetSoundShape(self):          self.ensureAll(); return enumIdentifierToIndex(self, self['soundShape'],        self.soundShapeEnumItems)
    def onGetItemGameID(self):          self.ensureAll(); return enumIdentifierToIndex(self, self['itemGameID'],        self.itemGameIDEnumItems)
    def onGetItemType(self):            self.ensureAll(); return enumIdentifierToIndex(self, self['itemType'],          self.itemTypeEnumItems)
    def onGetItemID(self):              self.ensureAll(); return self['itemID']
    def onGetItemTimer(self):           self.ensureAll(); return self['itemTimer']
    def onGetSmokeType(self):           self.ensureAll(); return enumIdentifierToIndex(self, self['smokeType'],         self.smokeTypeEnumItems)
    def onGetSmokeDirection(self):      self.ensureAll(); return self['smokeDirection']
    def onGetSmokePower(self):          self.ensureAll(); return self['smokePower']
    def onGetSmokeDelay(self):          self.ensureAll(); return self['smokeDelay']
    def onGetSmokeSize(self):           self.ensureAll(); return self['smokeSize']
    def onGetSmokeLife(self):           self.ensureAll(); return self['smokeLife']
    def onGetSmokeToggleMinTime(self):  self.ensureAll(); return self['smokeToggleMinTime']

    def onSetDummyType(self, value):            self.ensureAll(); self['dummyType']             = enumIndexToIdentifier(value, self.dummyTypeEnumItems)
    def onSetSpawnType(self, value):            self.ensureAll(); self['spawnType']             = enumIndexToIdentifier(value, self.spawnTypeEnumItems)
    def onSetSpawnIndex(self, value):           self.ensureAll(); self['spawnIndex']            = value
    def onSetSpawnTeamID(self, value):          self.ensureAll(); self['spawnTeamID']           = value
    def onSetSpawnEnemyType(self, value):       self.ensureAll(); self['spawnEnemyType']        = enumIndexToIdentifier(value, self.spawnEnemyTypeEnumItems)
    def onSetSpawnBlitzType(self, value):       self.ensureAll(); self['spawnBlitzType']        = enumIndexToIdentifier(value, self.spawnBlitzTypeEnumItems)
    def onSetSoundFileName(self, value):        self.ensureAll(); self['soundFileName']         = value
    def onSetSoundSpace(self, value):           self.ensureAll(); self['soundSpace']            = enumIndexToIdentifier(value, self.soundSpaceEnumItems)
    def onSetSoundShape(self, value):           self.ensureAll(); self['soundShape']            = enumIndexToIdentifier(value, self.soundShapeEnumItems)
    def onSetItemGameID(self, value):           self.ensureAll(); self['itemGameID']            = enumIndexToIdentifier(value, self.itemGameIDEnumItems)
    def onSetItemType(self, value):             self.ensureAll(); self['itemType']              = enumIndexToIdentifier(value, self.itemTypeEnumItems)
    def onSetItemID(self, value):               self.ensureAll(); self['itemID']                = value
    def onSetItemTimer(self, value):            self.ensureAll(); self['itemTimer']             = value
    def onSetSmokeType(self, value):            self.ensureAll(); self['smokeType']             = enumIndexToIdentifier(value, self.smokeTypeEnumItems)
    def onSetSmokeDirection(self, value):       self.ensureAll(); self['smokeDirection']        = value
    def onSetSmokePower(self, value):           self.ensureAll(); self['smokePower']            = value
    def onSetSmokeDelay(self, value):           self.ensureAll(); self['smokeDelay']            = value
    def onSetSmokeSize(self, value):            self.ensureAll(); self['smokeSize']             = value
    def onSetSmokeLife(self, value):            self.ensureAll(); self['smokeLife']             = value
    def onSetSmokeToggleMinTime(self, value):   self.ensureAll(); self['smokeToggleMinTime']    = value

    dummyType: EnumProperty(
        name = 'Type',
        items = dummyTypeEnumItems,
        update = onUpdate,
        get = onGetDummyType,
        set = onSetDummyType
    )

    spawnType: EnumProperty(
        name = 'Spawn Type',
        items = spawnTypeEnumItems,
        update = onUpdate,
        get = onGetSpawnType,
        set = onSetSpawnType
    )

    spawnIndex: IntProperty(
        name = 'Spawn Index',
        default = 1,
        min = 1,
        max = 999,
        soft_min = 1,
        soft_max = 999,
        subtype = 'UNSIGNED',
        update = onUpdate,
        get = onGetSpawnIndex,
        set = onSetSpawnIndex
    )

    spawnTeamID: IntProperty(
        name = 'Team ID',
        default = 1,
        min = 1,
        max = 9,
        soft_min = 1,
        soft_max = 9,
        subtype = 'UNSIGNED',
        update = onUpdate,
        get = onGetSpawnTeamID,
        set = onSetSpawnTeamID
    )

    spawnEnemyType: EnumProperty(
        name = 'Enemy Type',
        items = spawnEnemyTypeEnumItems,
        update = onUpdate,
        get = onGetSpawnEnemyType,
        set = onSetSpawnEnemyType
    )

    spawnBlitzType: EnumProperty(
        name = 'Blitzkrieg Type',
        items = spawnBlitzTypeEnumItems,
        update = onUpdate,
        get = onGetSpawnBlitzType,
        set = onSetSpawnBlitzType
    )

    soundFileName: StringProperty(
        name = 'Filename',
        default = '',
        subtype = 'FILE_NAME',
        update = onUpdate,
        get = onGetSoundFileName,
        set = onSetSoundFileName
    )

    soundSpace: EnumProperty(
        name = 'Space',
        items = soundSpaceEnumItems,
        update = onUpdate,
        get = onGetSoundSpace,
        set = onSetSoundSpace
    )

    soundShape: EnumProperty(
        name = 'Shape',
        items = soundShapeEnumItems,
        update = onUpdate,
        get = onGetSoundShape,
        set = onSetSoundShape
    )

    itemGameID: EnumProperty(
        name = 'Game ID',
        items = itemGameIDEnumItems,
        update = onUpdate,
        get = onGetItemGameID,
        set = onSetItemGameID
    )

    itemType: EnumProperty(
        name = 'Item Type',
        items = itemTypeEnumItems,
        update = onUpdate,
        get = onGetItemType,
        set = onSetItemType
    )

    itemID: IntProperty(
        name = 'Item ID',
        default = 1,
        min = 1,
        max = 2**31 - 1,
        soft_min = 1,
        soft_max = 2**31 - 1,
        subtype = 'UNSIGNED',
        update = onUpdate,
        get = onGetItemID,
        set = onSetItemID
    )

    itemTimer: IntProperty(
        name = 'Timer',
        default = 30000,
        min = 0,
        max = 2**31 - 1,
        soft_min = 0,
        soft_max = 2**31 - 1,
        subtype = 'UNSIGNED',
        update = onUpdate,
        get = onGetItemTimer,
        set = onSetItemTimer
    )

    smokeType: EnumProperty(
        name = 'Smoke Type',
        items = smokeTypeEnumItems,
        update = onUpdate,
        get = onGetSmokeType,
        set = onSetSmokeType
    )

    smokeDirection: IntProperty(
        name = 'Smoke Direction',
        default = 0,
        min = 0,
        max = 359,
        soft_min = 0,
        soft_max = 359,
        subtype = 'ANGLE',
        update = onUpdate,
        get = onGetSmokeDirection,
        set = onSetSmokeDirection
    )

    smokePower: FloatProperty(
        name = 'Smoke Power',
        default = 0.0,
        min = 0.0,
        max = 100.0,
        soft_min = 0.0,
        soft_max = 100.0,
        subtype = 'UNSIGNED',
        update = onUpdate,
        get = onGetSmokePower,
        set = onSetSmokePower
    )

    smokeDelay: IntProperty(
        name = 'Smoke Delay',
        default = 0,
        min = 0,
        max = 1000,
        soft_min = 0,
        soft_max = 1000,
        subtype = 'UNSIGNED',
        update = onUpdate,
        get = onGetSmokeDelay,
        set = onSetSmokeDelay
    )

    smokeSize: FloatProperty(
        name = 'Smoke Size',
        default = 40.0,
        min = 0.0,
        max = 500.0,
        soft_min = 0.0,
        soft_max = 500.0,
        subtype = 'UNSIGNED',
        update = onUpdate,
        get = onGetSmokeSize,
        set = onSetSmokeSize
    )

    smokeLife: FloatProperty(
        name = 'Smoke Life',
        default = 1.0,
        min = 0.0,
        max = 10.0,
        soft_min = 0.0,
        soft_max = 10.0,
        subtype = 'UNSIGNED',
        update = onUpdate,
        get = onGetSmokeLife,
        set = onSetSmokeLife
    )

    smokeToggleMinTime: FloatProperty(
        name = 'Toggle Minimum Time',
        default = 2.0,
        min = 0.0,
        max = 10.0,
        soft_min = 0.0,
        soft_max = 10.0,
        subtype = 'UNSIGNED',
        update = onUpdate,
        get = onGetSmokeToggleMinTime,
        set = onSetSmokeToggleMinTime
    )


    @classmethod
    def register(cls):
        bpy.types.Object.gzrs2 = PointerProperty(type = cls)

    @classmethod
    def unregister(cls):
        del bpy.types.Object.gzrs2

class GZRS2_PT_Realspace_Object(Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_label = 'Realspace'
    bl_idname = 'OBJECT_PT_realspace'
    bl_description = "Custom properties for Realspace engine objects."
    bl_context = 'data'
    bl_options = { 'DEFAULT_CLOSED' }

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.data is None

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        blObj = context.active_object

        props = blObj.gzrs2

        column = layout.column()
        column.prop(props, 'dummyType')

        column = layout.column()

        if props.dummyType == 'SPAWN':
            column.prop(props, 'spawnType')
            column.prop(props, 'spawnIndex')

            if props.spawnType == 'TEAM':
                column.prop(props, 'spawnTeamID')
            elif props.spawnType == 'NPC':
                column.prop(props, 'spawnEnemyType')
            elif props.spawnType == 'BLITZ':
                column.prop(props, 'spawnBlitzType')
        elif props.dummyType == 'SOUND':
            column.prop(props, 'soundFileName')
            column.prop(props, 'soundSpace')
            column.prop(props, 'soundShape')
        elif props.dummyType == 'ITEM':
            column.prop(props, 'itemGameID')
            column.prop(props, 'itemType')
            column.prop(props, 'itemID')
            column.prop(props, 'itemTimer')
        elif props.dummyType == 'SMOKE':
            column.prop(props, 'smokeType')
            column.prop(props, 'smokeDirection')
            column.prop(props, 'smokePower')
            column.prop(props, 'smokeDelay')
            column.prop(props, 'smokeSize')
            column.prop(props, 'smokeLife')
            if props.smokeType == 'SS' or props.smokeType == 'TS':
                column.prop(props, 'smokeToggleMinTime')

class GZRS2MeshProperties(PropertyGroup):
    # TODO: Custom sprite gizmos
    meshType: EnumProperty(
        name = 'Type',
        items = (
            ('NONE',        'None',         "Not a Realspace mesh. Will not be exported"),
            ('RAW',         'Raw',          "Freshly imported, may need modification. Will not be exported"),
            ('WORLD',       'World',        "World mesh, lit statically, necessary for graphics, must be fully sealed with no leaks"),
            ('COLLISION',   'Collision',    "Collision mesh, not visible, necessary for gameplay, must be fully sealed with no leaks"),
            ('NAVIGATION',  'Navigation',   "Navigation mesh, not visible, only necessary for Quest mode"),
            ('OCCLUSION',   'Occlusion',    "Occlusion planes, not visible, used to improve performance by skipping world and detail geometry"),
            ('DETAIL',      'Detail',       "Detail mesh, lit dynamically, does not contribute to bsptree or octree data. Recorded in .rs.xml, exports to .elu")
        )
    )

    meshSubtype: EnumProperty(
        name = 'Subtype',
        items = (
            ('NONE',            'None',         "Mesh has no special properties"),
            ('FLAG',            'Flag',         "Mesh is affected by wind forces")
        )
    )

    flagDirection: IntProperty(
        name = 'Flag Direction',
        default = 0,
        min = 0,
        max = 359,
        soft_min = 0,
        soft_max = 359,
        subtype = 'ANGLE'
    )

    flagPower: FloatProperty(
        name = 'Flag Power',
        default = 0.0,
        min = 0.0,
        max = 10.0,
        soft_min = 0.0,
        soft_max = 10.0,
        subtype = 'UNSIGNED'
    )

    flagWindType: EnumProperty(
        name = 'Type',
        items = FLAG_WINDTYPE_DATA
    )

    flagWindDelay: IntProperty(
        name = 'Wind Delay',
        default = 0,
        min = 0,
        max = 10000,
        soft_min = 0,
        soft_max = 10000,
        subtype = 'UNSIGNED'
    )

    flagLimitAxis: EnumProperty(
        name = 'Limit Axis',
        items = FLAG_LIMIT_AXIS_DATA
    )

    flagLimitOffset: FloatProperty(
        name = 'Limit Offset',
        default = 0.0,
        min = -10000.0,
        max = 10000.0,
        soft_min = -10000.0,
        soft_max = 10000.0
    )

    flagLimitCompare: EnumProperty(
        name = 'Limit Operator',
        items = FLAG_LIMIT_COMPARE_DATA
    )

    @classmethod
    def register(cls):
        bpy.types.Mesh.gzrs2 = PointerProperty(type = cls)

    @classmethod
    def unregister(cls):
        del bpy.types.Mesh.gzrs2

class GZRS2_PT_Realspace_Mesh(Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_label = 'Realspace'
    bl_idname = 'MESH_PT_realspace'
    bl_description = "Custom properties for Realspace engine meshes."
    bl_context = 'data'
    bl_options = { 'DEFAULT_CLOSED' }

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        props = context.active_object.data.gzrs2

        column = layout.column()
        column.prop(props, 'meshType')

        column = layout.column()

        if props.meshType == 'DETAIL':
            column.prop(props, 'meshSubtype')

            if props.meshSubtype == 'FLAG':
                column.prop(props, 'flagDirection')
                column.prop(props, 'flagPower')
                column.prop(props, 'flagWindType')
                column.prop(props, 'flagWindDelay')
                column.prop(props, 'flagLimitAxis')
                column.prop(props, 'flagLimitOffset')
                column.prop(props, 'flagLimitCompare')

class GZRS2CameraProperties(PropertyGroup):
    cameraIndex: IntProperty(
        name = 'Spawn Index',
        default = 1,
        min = 1,
        max = 999,
        soft_min = 1,
        soft_max = 999,
        subtype = 'UNSIGNED'
    )

    cameraType: EnumProperty(
        name = 'Type',
        items = (('WAIT',       'Wait',         "Camera position between rounds, mainly used for Team Deathmatch, Duel etc"),
                 ('TRACK',      'Track',        "Camera position along a track, mainly used on the character select screen"))
    )

    @classmethod
    def register(cls):
        bpy.types.Camera.gzrs2 = PointerProperty(type = cls)

    @classmethod
    def unregister(cls):
        del bpy.types.Camera.gzrs2

class GZRS2_PT_Realspace_Camera(Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_label = 'Realspace'
    bl_idname = 'CAMERA_PT_realspace'
    bl_description = "Custom properties for Realspace engine cameras."
    bl_context = 'data'
    bl_options = { 'DEFAULT_CLOSED' }

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'CAMERA'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        props = context.active_object.data.gzrs2

        column = layout.column()
        column.prop(props, 'cameraIndex')
        column.prop(props, 'cameraType')

class GZRS2MaterialProperties(PropertyGroup):
    def ensureAll(self):
        if 'matID'          not in self: self['matID']          = 0
        if 'isBase'         not in self: self['isBase']         = True
        if 'subMatID'       not in self: self['subMatID']       = -1
        if 'subMatCount'    not in self: self['subMatCount']    = 0

    def onUpdate(self, context):
        self.ensureAll()

        if self['isBase']:  self['subMatID'] = -1
        else:               self['subMatCount'] = 0

    def onGetSubMatID(self):        self.ensureAll(); return self['subMatID']       if not  self['isBase'] else -1
    def onGetSubMatCount(self):     self.ensureAll(); return self['subMatCount']    if      self['isBase'] else 0

    def onSetSubMatID(self, value):     self.ensureAll(); self['subMatID']      = value if not  self['isBase'] else -1
    def onSetSubMatCount(self, value):  self.ensureAll(); self['subMatCount']   = value if      self['isBase'] else 0

    matID: IntProperty(
        name = 'Material ID',
        default = 0,
        min = 0,
        max = 2**31 - 1,
        soft_min = 0,
        soft_max = 256,
        subtype = 'UNSIGNED',
        update = onUpdate
    )

    isBase: BoolProperty(
        name = 'Base',
        default = True,
        update = onUpdate
    )

    subMatID: IntProperty(
        name = 'Sub Material ID',
        default = -1,
        min = -1,
        max = 2**31 - 1,
        soft_min = -1,
        soft_max = 31,
        update = onUpdate,
        get = onGetSubMatID,
        set = onSetSubMatID
    )

    subMatCount: IntProperty(
        name = 'Sub Material Count',
        default = 0,
        min = 0,
        max = 2**31 - 1,
        soft_min = 0,
        soft_max = 256,
        subtype = 'UNSIGNED',
        update = onUpdate,
        get = onGetSubMatCount,
        set = onSetSubMatCount
    )

    # TODO: Automate material IDs
    '''
    parentMat: PointerProperty(
        type = bpy.types.Material,
        name = 'Parent Material'
    )
    '''

    ambient: FloatVectorProperty(
        name = 'Ambient',
        default = (0.588235, 0.588235, 0.588235),
        min = 0.0,
        max = 1.0,
        soft_min = 0.0,
        soft_max = 1.0,
        subtype = 'COLOR',
        size = 3
    )

    diffuse: FloatVectorProperty(
        name = 'Diffuse',
        default = (0.588235, 0.588235, 0.588235),
        min = 0.0,
        max = 1.0,
        soft_min = 0.0,
        soft_max = 1.0,
        subtype = 'COLOR',
        size = 3
    )

    specular: FloatVectorProperty(
        name = 'Specular',
        default = (0.9, 0.9, 0.9),
        min = 0.0,
        max = 1.0,
        soft_min = 0.0,
        soft_max = 1.0,
        subtype = 'COLOR',
        size = 3
    )

    exponent: FloatProperty(
        name = 'Exponent',
        default = 0.0,
        min = 0.0,
        max = 100.0,
        soft_min = 0.0,
        soft_max = 100.0,
        subtype = 'UNSIGNED'
    )

    @classmethod
    def register(cls):
        bpy.types.Material.gzrs2 = PointerProperty(type = cls)

    @classmethod
    def unregister(cls):
        del bpy.types.Material.gzrs2

class GZRS2_PT_Realspace_Material(Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_label = 'Realspace'
    bl_idname = 'MATERIAL_PT_realspace'
    bl_description = "Custom properties for Realspace engine materials."
    bl_context = 'material'
    bl_options = { 'DEFAULT_CLOSED' }

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.active_material is not None

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        version, maxPathLength = getEluExportConstants()

        blObj = context.active_object
        blMat = blObj.active_material
        tree, links, nodes = getMatTreeLinksNodes(blMat)

        shader, output, info, transparent, mix, clip, add = getRelevantShaderNodes(nodes)
        shaderValid, infoValid, transparentValid, mixValid, clipValid, addValid = checkShaderNodeValidity(shader, output, info, transparent, mix, clip, add, links)

        if shaderValid:
            texture, emission, alpha = getLinkedImageNodes(shader, links, clip, clipValid)
            texpath = getValidImageNodePathSilent(texture, maxPathLength)
            alphapath = getValidImageNodePathSilent(alpha, maxPathLength)

            twosided, additive, alphatest, usealphatest, useopacity = getMatFlagsRender(blMat, clip, addValid, clipValid, emission, alpha)

            texBase, texName, texExt, texDir = decomposeTexpath(texpath)
            isEffect = checkIsEffectNode(blObj.name)
            isAniTex = checkIsAniTex(texBase)
            success, frameCount, frameSpeed, frameGap = processAniTexParameters(isAniTex, texName, silent = True)

        shaderLabel =       '' if shaderValid           is None else ('Invalid' if shaderValid ==           False else 'Valid')
        infoLabel =         '' if infoValid             is None else ('Invalid' if infoValid ==             False else 'Valid')
        transparentLabel =  '' if transparentValid      is None else ('Invalid' if transparentValid ==      False else 'Valid')
        mixLabel =          '' if mixValid              is None else ('Invalid' if mixValid ==              False else 'Valid')
        clipLabel =         '' if clipValid             is None else ('Invalid' if clipValid ==             False else 'Valid')
        addLabel =          '' if addValid              is None else ('Invalid' if addValid ==              False else 'Valid')

        props = blMat.gzrs2

        column = layout.column()
        column.prop(props, 'matID')
        column.prop(props, 'isBase')

        row = column.row()
        row.prop(props, 'subMatID')
        row.enabled = not props.isBase

        row = column.row()
        row.prop(props, 'subMatCount')
        row.enabled = props.isBase

        column = layout.column()
        column.prop(props, 'ambient')
        column.prop(props, 'diffuse')
        column.prop(props, 'specular')
        column.prop(props, 'exponent')

        column = layout.column()
        column.operator(GZRS2_OT_Apply_Material_Preset.bl_idname, text = "Change Preset")

        box = layout.box()
        column = box.column()
        row = column.row()
        row.label(text = "Principled BSDF:")
        row.label(text = shaderLabel)
        row = column.row()
        row.label(text = "Object Info:")
        row.label(text = infoLabel)
        row = column.row()
        row.label(text = "Transparent Shader:")
        row.label(text = transparentLabel)
        row = column.row()
        row.label(text = "Mix Shader:")
        row.label(text = mixLabel)
        row = column.row()
        row.label(text = "Clip Math:")
        row.label(text = clipLabel)
        row = column.row()
        row.label(text = "Add Shader:")
        row.label(text = addLabel)

        box = layout.box()
        column = box.column()
        row = column.row()
        row.label(text = "Texpath:")
        row.label(text = texpath if shaderValid else 'N/A')
        row = column.row()
        row.label(text = "Alphapath:")
        row.label(text = alphapath if shaderValid else 'N/A')

        box = layout.box()
        column = box.column()
        row = column.row()
        row.label(text = "Twosided:")
        row.label(text = str(twosided) if shaderValid else 'N/A')
        row = column.row()
        row.label(text = "Additive:")
        row.label(text = str(additive) if shaderValid else 'N/A')
        row = column.row()
        row.label(text = "Alphatest:")
        row.label(text = str(alphatest) if shaderValid else 'N/A')
        row = column.row()
        row.label(text = "Use Opacity:")
        row.label(text = str(useopacity) if shaderValid else 'N/A')

        box = layout.box()
        column = box.column()
        row = column.row()
        row.label(text = "Is Effect:")
        row.label(text = str(isEffect) if shaderValid else 'N/A')
        row = column.row()
        row.label(text = "Is Animated:")
        row.label(text = str(isAniTex) if shaderValid else 'N/A')
        row = column.row()
        row.label(text = "Frame Count:")
        row.label(text = str(frameCount) if shaderValid and success else 'N/A')
        row = column.row()
        row.label(text = "Frame Speed:")
        row.label(text = str(frameSpeed) if shaderValid and success else 'N/A')
        row = column.row()
        row.label(text = "Frame Gap:")
        row.label(text = str(frameGap) if shaderValid and success else 'N/A')

classes = (
    GZRS2_OT_Apply_Material_Preset,
    GZRS2_OT_Specify_Path_MRS,
    GZRS2_OT_Specify_Path_MRF,
    GZRS2Preferences,
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
    ImportRSANI,
    RSANI_PT_Import_Main,
    RSANI_PT_Import_Logging,
    ImportRSCOL,
    RSCOL_PT_Import_Main,
    RSCOL_PT_Import_Logging,
    ImportRSNAV,
    RSNAV_PT_Import_Main,
    RSNAV_PT_Import_Logging,
    ImportRSLM,
    RSLM_PT_Import_Logging,
    ExportRSELU,
    RSELU_PT_Export_Main,
    RSELU_PT_Export_Logging,
    ExportRSNAV,
    RSNAV_PT_Export_Main,
    RSNAV_PT_Export_Logging,
    ExportRSLM,
    RSLM_PT_Export_Main,
    RSLM_PT_Export_Logging,
    GZRS2ObjectProperties,
    GZRS2_PT_Realspace_Object,
    GZRS2MeshProperties,
    GZRS2_PT_Realspace_Mesh,
    GZRS2CameraProperties,
    GZRS2_PT_Realspace_Camera,
    GZRS2MaterialProperties,
    GZRS2_PT_Realspace_Material
)

def menu_func_import(self, context):
    self.layout.operator(ImportGZRS2.bl_idname, text = 'GunZ RS2 (.rs)')
    self.layout.operator(ImportGZRS3.bl_idname, text = 'GunZ RS3 (.scene.xml/.prop.xml)')
    self.layout.operator(ImportRSELU.bl_idname, text = 'GunZ ELU (.elu)')
    self.layout.operator(ImportRSANI.bl_idname, text = 'GunZ ANI (.ani)')
    self.layout.operator(ImportRSCOL.bl_idname, text = 'GunZ COL (.col/.cl2)')
    self.layout.operator(ImportRSNAV.bl_idname, text = 'GunZ NAV (.nav)')
    self.layout.operator(ImportRSLM.bl_idname, text = 'GunZ LM (.lm)')

def menu_func_export(self, context):
    self.layout.operator(ExportRSELU.bl_idname, text = 'GunZ ELU (.elu)')
    self.layout.operator(ExportRSNAV.bl_idname, text = 'GunZ NAV (.nav)')
    self.layout.operator(ExportRSLM.bl_idname, text = 'GunZ LM (.lm)')

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


if __name__ == '__main__':
    register()
