import os, math, bmesh

from mathutils import Vector, Matrix

from . import import_gzrs2, import_gzrs3, import_rselu, import_rscol, import_rsnav, import_rslm, import_rsani
from . import export_gzrs2, export_rselu, export_rsnav, export_rslm

from .constants_gzrs2 import *
from .lib_gzrs2 import *

bl_info = {
    'name': 'GZRS2/3 Format',
    'author': 'Krunklehorn',
    'version': (0, 9, 7),
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

from bpy.app.handlers import persistent
from bpy.props import IntProperty, BoolProperty, FloatProperty, FloatVectorProperty, StringProperty, EnumProperty, PointerProperty
from bpy.types import Operator, Panel, PropertyGroup, AddonPreferences
from bpy_extras.io_utils import ImportHelper, ExportHelper

def cleanse_modules():
    import sys

    all_modules = sys.modules
    all_modules = dict(sorted(all_modules.items(), key = lambda x: x[0]))

    for k, v in all_modules.items():
        if k.startswith(__name__):
            del sys.modules[k]

    return

@persistent
def gzrs2LoadPost(filepath):
    ensureWorld(bpy.context)
    ensureLmMixGroup()

bpy.app.handlers.load_post.append(gzrs2LoadPost)

def validateRSDataDirectory(dirpath, isRS3):
    if dirpath == '' or not os.path.exists(dirpath) or not os.path.isdir(dirpath):
        return False

    _, dirnames, _ = next(os.walk(dirpath))

    for token in RS3_VALID_DATA_SUBDIRS if isRS3 else RS2_VALID_DATA_SUBDIRS:
        for dirname in dirnames:
            if token.lower() == dirname.lower():
                return True

    return False

class GZRS2_OT_Specify_Path_MRS(Operator):
    bl_idname = 'gzrs2.specify_path_mrs'
    bl_label = "Please specify the location of the extracted .mrs data"
    bl_options = { 'REGISTER', 'INTERNAL' }
    bl_description = "Specify the location of the extracted .mrs data"

    dataPath: StringProperty(
        name = 'Path',
        default = '',
        options = { 'OUTPUT_PATH' },
        subtype = 'DIR_PATH'
    )

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        self.dataPath = ''
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.dataPath = bpy.path.abspath(self.dataPath) if self.dataPath != '' else ''
        self.dataPath = os.path.join(self.dataPath, '')

        layout = self.layout
        layout.prop(self, 'dataPath')

    def execute(self, context):
        self.dataPath = bpy.path.abspath(self.dataPath) if self.dataPath != '' else ''
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
        options = { 'OUTPUT_PATH' },
        subtype = 'DIR_PATH'
    )

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        self.dataPath = ''
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.dataPath = bpy.path.abspath(self.dataPath) if self.dataPath != '' else ''
        self.dataPath = os.path.join(self.dataPath, '')

        layout = self.layout
        layout.prop(self, 'dataPath')

    def execute(self, context):
        self.dataPath = bpy.path.abspath(self.dataPath) if self.dataPath != '' else ''
        self.dataPath = os.path.join(self.dataPath, '')

        if not validateRSDataDirectory(self.dataPath, True):
            self.report({ 'ERROR' }, f"GZRS2: Search path must point to a folder containing a valid data subdirectory!")
            return { 'CANCELLED' }

        context.preferences.addons[__package__].preferences.rs3DataDir = self.dataPath

        return { 'FINISHED' }

class GZRS2_OT_Preprocess_Geometry(Operator):
    bl_idname = 'gzrs2.preprocess_geometry'
    bl_label = "Preprocess Geometry"
    bl_options = { 'REGISTER', 'INTERNAL' }
    bl_description = "Dissolves degenerate and co-linear vertices, deletes loose pieces then splits non-planar and concave faces"

    @classmethod
    def poll(cls, context):
        blObj = context.active_object

        if blObj is None or blObj.type != 'MESH':
            return False

        if blObj.mode != 'OBJECT':
            return False

        blMesh = blObj.data

        if blMesh is None or blMesh.gzrs2.meshType not in ('WORLD', 'COLLISION', 'NAVIGATION'):
            return False

        return True

    def execute(self, context):
        blObj = context.active_object
        blMesh = blObj.data

        for viewLayer in context.scene.view_layers:
            viewLayer.objects.active = blObj

        counts = countInfoReports(context)

        bpy.ops.object.select_all(action = 'DESELECT')
        blObj.select_set(True)

        bpy.ops.object.mode_set(mode = 'EDIT')

        bpy.ops.mesh.select_mode(type = 'VERT')
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.dissolve_degenerate(threshold = RS_COORD_THRESHOLD)

        # Dissolve co-linear points on boundary edges
        bpy.ops.mesh.select_all(action = 'DESELECT')
        bm = bmesh.from_edit_mesh(blMesh)

        for vertices, vertexCount in tuple((face.verts, len(face.verts)) for face in bm.faces):
            triplets = tuple((vertices[v], vertices[(v + 1) % vertexCount], vertices[(v - 1 + vertexCount) % vertexCount]) for v in range(vertexCount))
            triplets = tuple(filter(lambda x: len(x[0].link_edges) == 2, triplets))

            for vertex, nextVertex, prevVertex in triplets:
                edge1 = nextVertex.co - vertex.co
                edge2 = prevVertex.co - vertex.co

                edge1.normalize()
                edge2.normalize()

                if math.isclose(edge1.dot(edge2), -1.0, abs_tol = RS_DOT_THRESHOLD):
                    vertex.select_set(True)

        bmesh.update_edit_mesh(blMesh)
        bpy.ops.mesh.dissolve_verts()

        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.delete_loose()
        bpy.ops.mesh.select_all(action = 'SELECT')

        if blMesh.gzrs2.meshType in ('WORLD', 'COLLISION'):
            bpy.ops.mesh.vert_connect_nonplanar(angle_limit = 0.0174533)
            bpy.ops.mesh.vert_connect_concave()

        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.dissolve_degenerate(threshold = RS_COORD_THRESHOLD)

        bpy.ops.mesh.select_all(action = 'DESELECT')

        bpy.ops.object.mode_set(mode = 'OBJECT')

        deleteInfoReports(context, counts)

        return { 'FINISHED' }

class GZRS2_OT_Unfold_Vertex_Data(Operator):
    bl_idname = 'gzrs2.unfold_vertex_data'
    bl_label = "Unfold Vertex Data"
    bl_options = { 'REGISTER', 'INTERNAL' }
    bl_description = "Copies vertex group data across an object's local x-axis according to Realspace2's bone naming convention. Clears the opposing side while duplicating data along the center"

    sourceHand: EnumProperty(
        name = 'Source',
        items = (('LEFT',       'Left',      ""),
                 ('RIGHT',      'Right',     ""))
    )

    @classmethod
    def poll(cls, context):
        blObj = context.active_object

        if blObj is None or blObj.type != 'MESH':
            return False

        if blObj.mode != 'OBJECT':
            return False

        if len(blObj.vertex_groups) < 2:
            return False

        blMesh = blObj.data

        if blMesh is None or blMesh.gzrs2.meshType != 'PROP':
            return False

        if len(blMesh.vertices) < 2:
            return False

        return True

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        blPropObj = context.active_object
        blPropMesh = blPropObj.data

        leftHand = self.sourceHand == 'LEFT'

        sourcePrefix = 'Bip01 L ' if leftHand else 'Bip01 R '
        targetPrefix = 'Bip01 R ' if leftHand else 'Bip01 L '

        vertexGroups = blPropObj.vertex_groups

        sourceSet = set((getOrNone(vertexGroup.name.split(sourcePrefix), 1), vertexGroup) for vertexGroup in vertexGroups)
        targetSet = set((getOrNone(vertexGroup.name.split(targetPrefix), 1), vertexGroup) for vertexGroup in vertexGroups)

        sourceSet = set(filter(lambda x: x[0] is not None and x[0] != '', sourceSet))
        targetSet = set(filter(lambda x: x[0] is not None and x[0] != '', targetSet))

        sourceSuffixes = set(suffix for suffix, _ in sourceSet)

        # Remove target groups with no source
        targetSet = set(filter(lambda x: x[0] in sourceSuffixes, targetSet))

        targetSuffixes = set(suffix for suffix, _ in targetSet)

        # Create source groups with no target
        for sourceSuffix in sourceSuffixes:
            if sourceSuffix not in targetSuffixes:
                targetSet.add((sourceSuffix, blPropObj.vertex_groups.new(name = targetPrefix + sourceSuffix)))
                targetSuffixes.add(sourceSuffix)

        # Remove target side vertices from source groups
        for vertex in blPropMesh.vertices:
            for _, sourceGroup in sourceSet:
                if any((    leftHand and vertex.co.x <= -MESH_UNFOLD_THRESHOLD,
                        not leftHand and vertex.co.x >=  MESH_UNFOLD_THRESHOLD)):
                    sourceGroup.remove((vertex.index,))

        # Remove all vertices from target groups
        for vertex in blPropMesh.vertices:
            for _, targetGroup in targetSet:
                targetGroup.remove((vertex.index,))

        # Gather vertex data
        vertexData = tuple((vertex.index, vertex.co, vertex.groups) for vertex in blPropMesh.vertices)
        modifiedSuffixes = set()

        def commitVertexData(data):
            for index, groups in data:
                groupSet = set((getOrNone(vertexGroups[vgroupInfo.group].name.split(sourcePrefix), 1), vgroupInfo.weight) for vgroupInfo in groups)
                groupSet = set(filter(lambda x: x[0] is not None and x[0] != '', groupSet))
                relevantPairs = tuple((tg, sw, ts) for ss, sw in groupSet for ts, tg in targetSet if ts == ss)

                for targetGroup, sourceWeight, suffix in relevantPairs:
                    targetGroup.add((index,), sourceWeight, 'REPLACE')
                    modifiedSuffixes.add(suffix)

        # Duplicate source data along the center
        centerData = tuple(filter(lambda x: abs(x[1].x) < MESH_UNFOLD_THRESHOLD, vertexData))
        centerData = tuple((index, groups) for index, _, groups in centerData)

        commitVertexData(centerData)

        # Copy source data to the target side
        sideData = tuple((v, coord.copy(), groups) for v, coord, groups in vertexData)
        sideData = tuple(filter(lambda x: abs(x[1].x) >= MESH_UNFOLD_THRESHOLD, sideData))
        sideData = tuple((v1, v2, c1, c2, g1, g2) for v1, c1, g1 in sideData for v2, c2, g2 in sideData if v1 != v2)
        sideData = tuple((v1, v2, c1, c2, g1, g2) if v1 < v2 else (v2, v1, c2, c1, g2, g1) for v1, v2, c1, c2, g1, g2 in sideData)
        sideData = set((v1, v2, c1.freeze(), c2.freeze(), g1, g2) for v1, v2, c1, c2, g1, g2 in sideData)
        sideData = tuple(filter(lambda x: vec3IsClose(x[2], Vector((-x[3].x, x[3].y, x[3].z)), MESH_UNFOLD_THRESHOLD), sideData))

        if leftHand:
            sideData = tuple(filter(lambda x: x[2].x >= MESH_UNFOLD_THRESHOLD, sideData))
            sideData = tuple((index, groups) for _, index, _, _, groups, _ in sideData)
        else:
            sideData = tuple(filter(lambda x: x[3].x <= -MESH_UNFOLD_THRESHOLD, sideData))
            sideData = tuple((index, groups) for index, _, _, _, _, groups in sideData)

        commitVertexData(sideData)

        if len(centerData) > 0 and len(sideData) > 0 and len(modifiedSuffixes) == 0:
            self.report({ 'WARNING' }, f"GZRS2: No relevant pairs detected. Verify your group names match the Realspace2 convention: 'Bip01 <L/R> <bonename> '.")
        else:
            self.report({ 'INFO' }, f"GZRS2: Successfully modified { len(modifiedSuffixes) } pairs of vertex groups.")

        return { 'FINISHED' }

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
        blObj = context.active_object

        if blObj is None or blObj.type != 'MESH':
            return False

        if blObj.mode != 'OBJECT':
            return False

        blMesh = blObj.data

        if blMesh is None or blMesh.gzrs2.meshType not in ('WORLD', 'PROP'):
            return False

        return blObj.active_material is not None

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, 'materialPreset')

    def execute(self, context):
        bpy.ops.ed.undo_push()

        blObj = context.active_object
        meshType = blObj.data.gzrs2.meshType

        blMat = blObj.active_material
        tree, links, nodes = getMatTreeLinksNodes(blMat)

        shader, output, info, transparent, mix, clip, add, lightmix = getRelevantShaderNodes(nodes)
        shaderValid, infoValid, transparentValid, mixValid, clipValid, addValid, lightmixValid = checkShaderNodeValidity(shader, output, info, transparent, mix, clip, add, lightmix, links)
        texture, emission, alpha, lightmap = getLinkedImageNodes(shader, shaderValid, links, clip, clipValid, lightmix, lightmixValid, validOnly = False)

        # Reuse existing image texture nodes
        texture     = texture   or emission or alpha    or getShaderNodeByID(nodes, 'ShaderNodeTexImage', blacklist = (lightmap,))
        emission    = emission  or texture  or alpha
        alpha       = alpha     or texture  or emission
        lightmap    = lightmap                          or getShaderNodeByID(nodes, 'ShaderNodeTexImage', blacklist = (texture, emission, alpha))

        twosided, additive, alphatest, usealphatest, useopacity = getMatFlagsRender(blMat, clip, addValid, clipValid, emission, alpha)

        # We avoid links.clear() to preserve the user's material as much as possible
        relevantNodes = [shader, output, info, transparent, mix, clip, add, lightmix]

        for link in links:
            if link.from_node in relevantNodes or link.to_node in relevantNodes:
                links.remove(link)

        if shaderValid and addValid:
            blMat.gzrs2.fakeEmission = shader.inputs[27].default_value # Emission Strength

        # We assume the setup functions modify valid inputs and only create what is missing
        blMat, tree, links, nodes, shader, output, info, transparent, mix = setupMatBase(blMat.name, blMat = blMat, shader = shader, output = output, info = info, transparent = transparent, mix = mix)

        if meshType == 'WORLD':
            _, _, lightmix, _ = setupMatNodesLightmap(blMat, tree, links, nodes, shader, lightmap = lightmap, lightmix = lightmix)

        if self.materialPreset == 'COLORED':
            return { 'FINISHED' }

        texture = texture or nodes.new('ShaderNodeTexImage')
        texture.location = (-440, 300)
        texture.select = False

        if meshType == 'WORLD':     links.new(texture.outputs[0], lightmix.inputs[0])
        else:                       links.new(texture.outputs[0], shader.inputs[0]) # Base Color

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

            source = lightmix if meshType == 'WORLD' else texture
            add = setupMatNodesAdditive(blMat, tree, links, nodes, additive, source, shader, transparent, mix, add = add)

        setMatFlagsTransparency(blMat, usealphatest or useopacity or additive, twosided = twosided)

        return { 'FINISHED' }

class GZRS2_OT_Toggle_Lightmap_Mix(Operator):
    bl_idname = 'gzrs2.toggle_lightmap_mix'
    bl_label = "Toggle Lightmap Mix"
    bl_options = { 'REGISTER', 'INTERNAL' }
    bl_description = "Toggle the shader node controlling the mixing of lightmaps"

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        group = ensureLmMixGroup()
        nodes = group.nodes

        for node in nodes:
            if node.type == 'MIX_RGB' and node.label.lower() == 'lightmap':
                if node.inputs[0].default_value > 0.5:  node.inputs[0].default_value = 0.0
                else:                                   node.inputs[0].default_value = 1.0

                return { 'FINISHED' }
        else:
            return { 'CANCELLED' }

class GZRS2_OT_Toggle_Lightmap_Mod4(Operator):
    bl_idname = 'gzrs2.toggle_lightmap_mod4'
    bl_label = "Toggle Lightmap Mod4"
    bl_options = { 'REGISTER', 'INTERNAL' }
    bl_description = "Toggle the shader node controlling the lightmap mod4 fix"

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        group = ensureLmMixGroup()
        nodes = group.nodes

        for node in nodes:
            if node.type == 'MIX_RGB' and node.label.lower() == 'mod4':
                if node.inputs[0].default_value > 0.5:  node.inputs[0].default_value = 0.0
                else:                                   node.inputs[0].default_value = 1.0

                return { 'FINISHED' }
        else:
            return { 'CANCELLED' }

class GZRS2_OT_Recalculate_Lights_Fog(Operator):
    bl_idname = 'gzrs2.recalculate_lights_fog'
    bl_label = "Recalculate Lights & Fog"
    bl_options = { 'REGISTER', 'INTERNAL' }
    bl_description = "Recalculate Blender lights and fog volume based on associated Realspace properties"

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        world = ensureWorld(context)
        worldProps = world.gzrs2
        fogColor = worldProps.fogColor

        tree = world.node_tree
        links = tree.links
        nodes = tree.nodes

        output = getShaderNodeByID(nodes, 'ShaderNodeOutputWorld')

        if sum(fogColor[:3]) / 3 > 0.5:
            shader = getShaderNodeByID(nodes, 'ShaderNodeVolumeScatter') or nodes.new('ShaderNodeVolumeScatter')
            shader.inputs[1].default_value = pow(worldProps.fogDensity, 2 / 3) * 0.001
        else:
            shader = getShaderNodeByID(nodes, 'ShaderNodeVolumeAbsorption') or nodes.new('ShaderNodeVolumeAbsorption')
            shader.inputs[1].default_value = pow(worldProps.fogDensity, 2 / 3) * 0.1

        shader.inputs[0].default_value = (fogColor.r, fogColor.g, fogColor.b, 1)

        for link in links:
            if link.to_node == output and link.to_socket == output.inputs[1]:
                links.remove(link)

        if worldProps.fogEnable:
            links.new(shader.outputs[0], output.inputs[1])

        blLights = tuple((blObj.data, blObj) for blObj in bpy.data.objects if blObj.type == 'LIGHT' and blObj.data.gzrs2.lightType != 'NONE')

        for blLight, blLightObj in blLights:
            props = blLight.gzrs2

            intensity = props.intensity
            attStart = props.attStart
            attEnd = clampLightAttEnd(props.attEnd, attStart)

            blLight.energy = calcLightEnergy(blLightObj, context)
            blLight.shadow_soft_size = calcLightSoftSize(blLightObj, context)

            # blLightObj.hide_render = calcLightRender(blLightObj, context)

        return { 'FINISHED' }

class GZRS2_OT_Prepare_Bake(Operator):
    bl_idname = 'gzrs2.prepare_bake'
    bl_label = "Prepare for Bake"
    bl_options = { 'REGISTER', 'INTERNAL' }
    bl_description = "Applies the current world lightmap to all world materials and sets it as the active bake target"

    @classmethod
    def poll(cls, context):
        blObj = context.active_object

        if blObj is None or blObj.type != 'MESH':
            return False

        if blObj.mode != 'OBJECT':
            return False

        blMesh = blObj.data

        if blMesh is None:
            return False

        return True

    def execute(self, context):
        worldProps = ensureWorld(context).gzrs2
        lightmapImage = worldProps.lightmapImage

        blBakeObj = context.active_object
        blBakeMesh = blBakeObj.data

        if len(blBakeMesh.uv_layers) < 2:
            self.report({ 'ERROR' }, f"GZRS2: Bake prep requires a second UV channel!")
            return { 'CANCELLED' }

        blBakeMesh.uv_layers.active_index = 1

        blBakeMats = set(matSlot.material for matSlot in blBakeObj.material_slots)

        if len(blBakeMats) == 0:
            self.report({ 'ERROR' }, f"GZRS2: Bake prep requires at least one material!")
            return { 'CANCELLED' }

        for blBakeMat in blBakeMats:
            tree, links, nodes = getMatTreeLinksNodes(blBakeMat)

            shader, output, info, transparent, mix, clip, add, lightmix = getRelevantShaderNodes(nodes)
            shaderValid, infoValid, transparentValid, mixValid, clipValid, addValid, lightmixValid = checkShaderNodeValidity(shader, output, info, transparent, mix, clip, add, lightmix, links)

            if any((not shaderValid,        not infoValid,
                    not transparentValid,   not mixValid)):
                self.report({ 'ERROR' }, f"GZRS2: Bake prep requires all bake materials conform to a preset! { blBakeMat.name }")
                return { 'CANCELLED' }

            nodes.active = None

            for node in nodes:
                node.select = False

            _, _, _, lightmap = getLinkedImageNodes(shader, shaderValid, links, clip, clipValid, lightmix, lightmixValid, validOnly = False)

            if lightmap is not None:
                tree.nodes.active = lightmap
                lightmap.image = lightmapImage
                lightmap.select = True

        group = ensureLmMixGroup()
        nodes = group.nodes

        for node in nodes:
            if node.type == 'MIX_RGB' and node.label.lower() == 'lightmap':
                node.inputs[0].default_value = 0.0

        if lightmapImage is not None:
            lightmapImage.use_fake_user = True

        return { 'FINISHED' }

class GZRS2Preferences(AddonPreferences):
    bl_idname = __package__

    rs2DataDir: StringProperty(
        name = 'RS2/.mrs',
        description = "Path to a folder containing extracted .mrs data",
        default = '',
        options = { 'OUTPUT_PATH' },
        subtype = 'DIR_PATH'
    )

    rs3DataDir: StringProperty(
        name = 'RS3/.mrf',
        description = "Path to a folder containing extracted .mrf data",
        default = '',
        options = { 'OUTPUT_PATH' },
        subtype = 'DIR_PATH'
    )

    serverProfile: EnumProperty(
        name = 'Server Profile',
        items = (('VANILLA',    'Vanilla',      ""),
                 ('DUELISTS',   'Duelists',     ""))
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

        box = layout.box()

        column = box.column()
        column.label(text = "Valid data subdirectories for .mrf include:")
        column.label(text = "\'Data\' and \'EngineRes\'")
        column.label(text = "Example: \'C:\\Users\\krunk\\Documents\\GunZ2\\z3ResEx\\datadump\\")

        row = column.row()
        row.label(text = self.rs3DataDir)
        row.operator(GZRS2_OT_Specify_Path_MRF.bl_idname, text = "Set .mrf (GunZ 2) data path...")

        column = layout.column()
        column.prop(self, 'serverProfile')


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
        default = False
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

    @classmethod
    def poll(cls, context):
        return context.active_object is None or context.active_object.mode == 'OBJECT'

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

    @classmethod
    def poll(cls, context):
        return context.active_object is None or context.active_object.mode == 'OBJECT'

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

    isMapProp: BoolProperty(
        name = 'Map Prop',
        description = "Reorients the prop to face forward",
        default = False
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

    @classmethod
    def poll(cls, context):
        return context.active_object is None or context.active_object.mode == 'OBJECT'

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
        layout.prop(operator, 'isMapProp')

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

    filterMode: EnumProperty(
        name = 'Filter Mode',
        items = (('ALL',        'All',          "Import considers all relevant objects. Only applies to VERTEX and TM type animations"),
                 ('SELECTED',   'Selected',     "Limit import to selected objects. Only applies to VERTEX and TM type animations"),
                 ('VISIBLE',    'Visible',      "Limit import to visible objects. Only applies to VERTEX and TM type animations"))
    )

    includeChildren: BoolProperty(
        name = 'Include Children',
        description = "Include children of selected objects. Only applies to VERTEX and TM type animations",
        default = True
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

    @classmethod
    def poll(cls, context):
        return context.active_object is None or context.active_object.mode == 'OBJECT'

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
        layout.prop(operator, 'filterMode')

        column = layout.column()
        column.prop(operator, 'includeChildren')
        column.enabled = operator.filterMode == 'SELECTED'

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

    doPlanes: BoolProperty(
        name = 'Planes (slow)',
        description = "Import cutting planes for debugging",
        default = False
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

    @classmethod
    def poll(cls, context):
        return context.active_object is None or context.active_object.mode == 'OBJECT'

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
        layout.prop(operator, 'doPlanes')

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

    @classmethod
    def poll(cls, context):
        return context.active_object is None or context.active_object.mode == 'OBJECT'

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

    panelLogging: BoolProperty(
        name = 'Logging',
        description = "Log details to the console",
        default = False
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

    @classmethod
    def poll(cls, context):
        return context.active_object is None or context.active_object.mode == 'OBJECT'

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

    def draw_header(self, context):
        self.layout.prop(context.space_data.active_operator, 'panelLogging', text = "")

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelLogging

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

    uncapLimits: BoolProperty(
        name = 'Uncap Limits',
        description = "Removes the check for a triangle count limit. (MAX_VERTEX)",
        default = False
    )

    filterMode: EnumProperty(
        name = 'Filter Mode',
        items = (('ALL',        'All',          "Exports all relevant objects"),
                 ('SELECTED',   'Selected',     "Limit export to selected objects"),
                 ('VISIBLE',    'Visible',      "Limit export to visible objects"))
    )

    includeChildren: BoolProperty(
        name = 'Include Children',
        description = "Include children of selected objects",
        default = True
    )

    isMapProp: BoolProperty(
        name = 'Map Prop',
        description = "Reorients the prop to face forward and verifies the user is exporting it with the correct filename",
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

    @classmethod
    def poll(cls, context):
        return context.active_object is None or context.active_object.mode == 'OBJECT'

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
        layout.prop(operator, 'uncapLimits')
        layout.prop(operator, 'filterMode')

        column = layout.column()
        column.prop(operator, 'includeChildren')
        column.enabled = operator.filterMode == 'SELECTED'

        layout.prop(operator, 'isMapProp')

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

class ExportGZRS2(Operator, ExportHelper):
    bl_idname = 'export_scene.gzrs2'
    bl_label = 'Export RS2'
    bl_options = { 'UNDO', 'PRESET' }
    bl_description = "Save an RS file"

    filename_ext = ".rs"
    filter_glob: StringProperty(
        default = "*.rs",
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

    filterMode: EnumProperty(
        name = 'Filter Mode',
        items = (('ALL',        'All',          "Exports all relevant objects"),
                 ('SELECTED',   'Selected',     "Limit export to selected objects"),
                 ('VISIBLE',    'Visible',      "Limit export to visible objects"))
    )

    includeChildren: BoolProperty(
        name = 'Include Children',
        description = "Include children of selected objects",
        default = True
    )

    purgeUnused: BoolProperty(
        name = 'Purge Unused',
        description = "Always checks for files to backup. Ensures map data a previous export does not conflict with the current one",
        default = True
    )

    lmVersion4: BoolProperty(
        name = 'Version 4',
        description = "Fixes bit depth issues and makes use of DXT1 compression, not compatible with vanilla GunZ",
        default = False
    )

    mod4Fix: BoolProperty(
        name = 'MOD4',
        description = "Compresses the color range to compensate for the D3DTOP_MODULATE4X flag.",
        default = True
    )

    logRs: BoolProperty(
        name = 'Rs',
        description = "Log Rs data",
        default = True
    )

    logBsp: BoolProperty(
        name = 'Bsp',
        description = "Log Bsp data",
        default = True
    )

    logCol: BoolProperty(
        name = 'Col',
        description = "Log Col data",
        default = True
    )

    logLm: BoolProperty(
        name = 'Lm',
        description = "Log Lm data",
        default = True
    )

    @classmethod
    def poll(cls, context):
        return context.active_object is None or context.active_object.mode == 'OBJECT'

    def draw(self, context):
        pass

    def execute(self, context):
        return export_gzrs2.exportRS2(self, context)

class GZRS2_PT_Export_Main(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'Main'
    bl_parent_id = 'FILE_PT_operator'

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == 'EXPORT_SCENE_OT_gzrs2'

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelMain

        layout.prop(operator, 'convertUnits')
        layout.prop(operator, 'filterMode')

        column = layout.column()
        column.prop(operator, 'includeChildren')
        column.enabled = operator.filterMode == 'SELECTED'

        layout.prop(operator, 'purgeUnused')

class GZRS2_PT_Export_Lightmap(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'Lightmap'
    bl_parent_id = 'FILE_PT_operator'

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == 'EXPORT_SCENE_OT_gzrs2'

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.prop(operator, 'lmVersion4')

        column = layout.column()
        column.prop(operator, 'mod4Fix')
        column.enabled = not operator.lmVersion4

class GZRS2_PT_Export_Logging(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = 'Logging'
    bl_parent_id = 'FILE_PT_operator'

    @classmethod
    def poll(cls, context):
        return context.space_data.active_operator.bl_idname == 'EXPORT_SCENE_OT_gzrs2'

    def draw_header(self, context):
        self.layout.prop(context.space_data.active_operator, 'panelLogging', text = "")

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.enabled = operator.panelLogging

        layout.prop(operator, "logRs")
        layout.prop(operator, "logBsp")
        layout.prop(operator, "logCol")
        layout.prop(operator, "logLm")

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

    @classmethod
    def poll(cls, context):
        return context.active_object is None or context.active_object.mode == 'OBJECT'

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
        description = "Export UV data, requires an active mesh object with valid UVs in channel 2 as well as a GunZ 1 .rs file for the same map in the same directory",
        default = True
    )

    lmVersion4: BoolProperty(
        name = 'Version 4',
        description = "Fixes bit depth issues and makes use of DXT1 compression, not compatible with vanilla GunZ",
        default = False
    )

    mod4Fix: BoolProperty(
        name = 'MOD4',
        description = "Compresses the color range to compensate for the D3DTOP_MODULATE4X flag.",
        default = True
    )

    logLmHeaders: BoolProperty(
        name = 'Lm Headers',
        description = "Log Lm header data",
        default = True
    )

    @classmethod
    def poll(cls, context):
        return context.active_object is None or context.active_object.mode == 'OBJECT'

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

class GZRS2WorldProperties(PropertyGroup):
    def onPollLightmapImage(self, object):
        return object.type in ('IMAGE', 'UV_TEST') and object.source in ('FILE', 'GENERATED') and not object.is_multiview

    lightmapImage: PointerProperty(
        type = bpy.types.Image,
        name = 'Image',
        poll = onPollLightmapImage
    )

    lightIntensity: FloatProperty(
        name = 'Light Intensity',
        default = 1.0,
        min = 0.0,
        max = 100.0,
        soft_min = 0.0,
        soft_max = 100.0,
        subtype = 'UNSIGNED'
    )

    sunIntensity: FloatProperty(
        name = 'Sun Intensity',
        default = 1.0,
        min = 0.0,
        max = 100.0,
        soft_min = 0.0,
        soft_max = 100.0,
        subtype = 'UNSIGNED'
    )

    lightSoftSize: FloatProperty(
        name = 'Light Soft Size',
        default = 1.0,
        min = 0.0,
        max = 100.0,
        soft_min = 0.0,
        soft_max = 100.0,
        subtype = 'UNSIGNED'
    )

    fogEnable: BoolProperty(
        name = 'Enable',
        default = False
    )

    fogColor: FloatVectorProperty(
        name = 'Color',
        default = (1.0, 1.0, 1.0),
        min = 0.0,
        max = 1.0,
        soft_min = 0.0,
        soft_max = 1.0,
        subtype = 'COLOR',
        size = 3
    )

    fogDensity: FloatProperty(
        name = 'Fog Density',
        default = 1.0,
        min = 0.0,
        max = 100.0,
        soft_min = 0.0,
        soft_max = 100.0,
        subtype = 'UNSIGNED'
    )

    fogMin: FloatProperty(
        name = 'Start',
        default = 10.0,
        min = 0.0,
        max = 3.402823e+38,
        soft_min = 0.0,
        soft_max = 3.402823e+38,
        subtype = 'UNSIGNED',
        unit = 'LENGTH'
    )

    fogMax: FloatProperty(
        name = 'End',
        default = 100.0,
        min = 0.0,
        max = 3.402823e+38,
        soft_min = 0.0,
        soft_max = 3.402823e+38,
        subtype = 'UNSIGNED',
        unit = 'LENGTH'
    )

    farClip: FloatProperty(
        name = 'Far Clip',
        default = 100.0,
        min = 0.0,
        max = 3.402823e+38,
        soft_min = 0.0,
        soft_max = 3.402823e+38,
        subtype = 'UNSIGNED',
        unit = 'LENGTH'
    )

    @classmethod
    def register(cls):
        bpy.types.World.gzrs2 = PointerProperty(type = cls)

    @classmethod
    def unregister(cls):
        del bpy.types.World.gzrs2

class GZRS2_PT_Realspace_World(Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_label = 'Realspace'
    bl_idname = 'WORLD_PT_realspace'
    bl_description = "Custom properties for Realspace engine maps."
    bl_context = 'world'

    @classmethod
    def poll(cls, context):
        return context.scene.world is not None

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        worldProps = ensureWorld(context).gzrs2
        lightmapImage = worldProps.lightmapImage

        box = layout.box()
        column = box.column()
        column.label(text = "Render")
        column.prop(worldProps, 'lightIntensity')
        column.prop(worldProps, 'sunIntensity')
        column.prop(worldProps, 'lightSoftSize')
        column.prop(worldProps, 'fogDensity')

        box = layout.box()
        column = box.column()
        column.label(text = "Fog")
        column.prop(worldProps, 'fogEnable')

        column = column.column()
        column.prop(worldProps, 'fogColor')
        column.prop(worldProps, 'fogMin')
        column.prop(worldProps, 'fogMax')
        column.enabled = worldProps.fogEnable

        box = layout.box()
        column = box.column()
        column.label(text = "Lightmap")
        column.prop(worldProps, 'lightmapImage')

        if lightmapImage is not None:
            imageWidth, imageHeight = lightmapImage.size
            mipCount = math.log2(imageWidth) if imageWidth != 0 else None

            if imageWidth < LM_MIN_SIZE or imageHeight < LM_MIN_SIZE or imageWidth != imageHeight or not mipCount.is_integer():
                if imageWidth < LM_MIN_SIZE or imageHeight < LM_MIN_SIZE:
                    row = column.row()
                    row.alert = True
                    row.label(text = f"Image side length must be greater than { LM_MIN_SIZE }!")

                if imageWidth != imageHeight or not mipCount.is_integer():
                    row = column.row()
                    row.alert = True
                    row.label(text = f"Image must be a square, power of two texture!")
            else:
                row = column.row()
                row.label(text = "Size:")
                row.label(text = str(imageWidth))
                row = column.row()
                row.label(text = "Mip Count:")
                row.label(text = str(int(mipCount)))
        else:
            row = column.row()
            row.label(text = "Size:")
            row.label(text = '')
            row = column.row()
            row.label(text = "Mip Count:")
            row.label(text = '')

        column = layout.column()
        row = column.row()
        row.operator(GZRS2_OT_Toggle_Lightmap_Mix.bl_idname, text = "Lightmap Mix")
        row.operator(GZRS2_OT_Toggle_Lightmap_Mod4.bl_idname, text = "Lightmap Mod4")
        column.operator(GZRS2_OT_Recalculate_Lights_Fog.bl_idname, text = "Recalculate Lights & Fog")
        column.operator(GZRS2_OT_Prepare_Bake.bl_idname, text = "Prepare for Bake")

        box = layout.box()
        column = box.column()
        column.label(text = "Other")
        column.prop(worldProps, 'farClip')

class GZRS2ObjectProperties(PropertyGroup):
    def ensureAll(self):
        if 'dummyType'          not in self: self['dummyType']          = 'NONE'
        if 'spawnType'          not in self: self['spawnType']          = 'SOLO'
        if 'spawnIndex'         not in self: self['spawnIndex']         = 1
        if 'spawnTeamID'        not in self: self['spawnTeamID']        = 1
        if 'spawnEnemyType'     not in self: self['spawnEnemyType']     = 'MELEE'
        if 'spawnBlitzType'     not in self: self['spawnBlitzType']     = 'BARRICADE'
        if 'soundFileName'      not in self: self['soundFileName']      = ''
        if 'soundSpace'         not in self: self['soundSpace']         = '3D'
        if 'soundShape'         not in self: self['soundShape']         = 'AABB'
        if 'itemGameID'         not in self: self['itemGameID']         = 'SOLO'
        if 'itemType'           not in self: self['itemType']           = 'HP'
        if 'itemID'             not in self: self['itemID']             = 1
        if 'itemTimer'          not in self: self['itemTimer']          = 30.0
        if 'smokeType'          not in self: self['smokeType']          = 'SS'
        if 'smokeDirection'     not in self: self['smokeDirection']     = 0
        if 'smokePower'         not in self: self['smokePower']         = 0.0
        if 'smokeDelay'         not in self: self['smokeDelay']         = 100
        if 'smokeSize'          not in self: self['smokeSize']          = 40.0
        if 'smokeLife'          not in self: self['smokeLife']          = 1.0
        if 'smokeToggleMinTime' not in self: self['smokeToggleMinTime'] = 2.0
        if 'occPriority'        not in self: self['occPriority']        = 1
        if 'occBsp'             not in self: self['occBsp']             = False
        if 'occOct'             not in self: self['occOct']             = False
        if 'occProp'            not in self: self['occProp']            = False

    def onUpdate(self, context):
        blObj = self.id_data

        if blObj is None or blObj.data is not None:
            return

        props = blObj.gzrs2
        dummyType = props.dummyType

        # TODO: Custom sprite gizmos
        if dummyType == 'SOUND':
            soundShape = props.soundShape

            if soundShape == 'AABB':        blObj.empty_display_type = 'CUBE'
            elif soundShape == 'SPHERE':    blObj.empty_display_type = 'SPHERE'
        elif dummyType == 'ITEM':           blObj.empty_display_type = 'SPHERE'
        elif dummyType == 'OCCLUSION':      blObj.empty_display_type = 'IMAGE'
        else:                               blObj.empty_display_type = 'ARROWS'

        if dummyType == 'SOUND':
            if soundShape == 'AABB':
                blObj.rotation_euler = Matrix.Identity(4).to_euler()
                blObj.empty_display_size = 1
            elif soundShape == 'SPHERE':
                blObj.rotation_euler = Matrix.Identity(4).to_euler()
                blObj.scale = (1, 1, 1)
                blObj.empty_display_size = int(blObj.empty_display_size * 100) / 100
        elif dummyType == 'OCCLUSION':
            if props.occOct:
                blObj.rotation_euler = eulerSnapped(blObj.rotation_euler)

            blObj.empty_image_side = 'FRONT'
            blObj.use_empty_image_alpha = True
            blObj.color[3] = 0.5
            # TODO: Custom image or sprite gizmo?
            # TODO: Duplicate the empty panel to appear for image data as well

    dummyTypeEnumItems = (
        ('NONE',        'None',         "Not a Realspace object. Will not be exported"),
        ('SPAWN',       'Spawn',        "Spawn location for characters"),
        ('FLARE',       'Flare',        "Lens flare location. Not an actual light source"),
        ('SOUND',       'Sound',        "Ambient sound, based on proximity to a sphere or axis-aligned bounding box center"),
        ('ITEM',        'Item',         "Health, armor, ammo etc"),
        ('SMOKE',       'Smoke',        "Smoke particle generator"),
        ('OCCLUSION',   'Occlusion',    "Occlusion plane, not visible, used to improve performance by skipping world and detail geometry"),
        ('ATTACHMENT',  'Attachment',   "Attachment point for weapon, equipment, particle effect, etc")
    )

    spawnTypeEnumItems = SPAWN_TYPE_DATA
    spawnEnemyTypeEnumItems = SPAWN_ENEMY_TYPE_DATA
    spawnBlitzTypeEnumItems = SPAWN_BLITZ_TYPE_DATA
    soundSpaceEnumItems = SOUND_SPACE_DATA
    soundShapeEnumItems = SOUND_SHAPE_DATA
    itemGameIDEnumItems = ITEM_GAME_ID_DATA
    itemTypeEnumItems = ITEM_TYPE_DATA
    smokeTypeEnumItems = SMOKE_TYPE_DATA

    def onGetDummyType(self):           self.ensureAll(); return enumTagToIndex(self, self['dummyType'],        self.dummyTypeEnumItems)
    def onGetSpawnType(self):           self.ensureAll(); return enumTagToIndex(self, self['spawnType'],        self.spawnTypeEnumItems)
    def onGetSpawnIndex(self):          self.ensureAll(); return self['spawnIndex']
    def onGetSpawnTeamID(self):         self.ensureAll(); return self['spawnTeamID']
    def onGetSpawnEnemyType(self):      self.ensureAll(); return enumTagToIndex(self, self['spawnEnemyType'],   self.spawnEnemyTypeEnumItems)
    def onGetSpawnBlitzType(self):      self.ensureAll(); return enumTagToIndex(self, self['spawnBlitzType'],   self.spawnBlitzTypeEnumItems)
    def onGetSoundFileName(self):       self.ensureAll(); return self['soundFileName']
    def onGetSoundSpace(self):          self.ensureAll(); return enumTagToIndex(self, self['soundSpace'],       self.soundSpaceEnumItems)
    def onGetSoundShape(self):          self.ensureAll(); return enumTagToIndex(self, self['soundShape'],       self.soundShapeEnumItems)
    def onGetItemGameID(self):          self.ensureAll(); return enumTagToIndex(self, self['itemGameID'],       self.itemGameIDEnumItems)
    def onGetItemType(self):            self.ensureAll(); return enumTagToIndex(self, self['itemType'],         self.itemTypeEnumItems)
    def onGetItemID(self):              self.ensureAll(); return self['itemID']
    def onGetItemTimer(self):           self.ensureAll(); return self['itemTimer']
    def onGetSmokeType(self):           self.ensureAll(); return enumTagToIndex(self, self['smokeType'],        self.smokeTypeEnumItems)
    def onGetSmokeDirection(self):      self.ensureAll(); return self['smokeDirection']
    def onGetSmokePower(self):          self.ensureAll(); return self['smokePower']
    def onGetSmokeDelay(self):          self.ensureAll(); return self['smokeDelay']
    def onGetSmokeSize(self):           self.ensureAll(); return self['smokeSize']
    def onGetSmokeLife(self):           self.ensureAll(); return self['smokeLife']
    def onGetSmokeToggleMinTime(self):  self.ensureAll(); return self['smokeToggleMinTime']
    def onGetOccPriority(self):         self.ensureAll(); return self['occPriority']
    def onGetOccBsp(self):              self.ensureAll(); return self['occBsp']
    def onGetOccOct(self):              self.ensureAll(); return self['occOct']
    def onGetOccProp(self):             self.ensureAll(); return self['occProp']

    def onSetDummyType(self, value):            self.ensureAll(); self['dummyType']             = enumIndexToTag(value, self.dummyTypeEnumItems)
    def onSetSpawnType(self, value):            self.ensureAll(); self['spawnType']             = enumIndexToTag(value, self.spawnTypeEnumItems)
    def onSetSpawnIndex(self, value):           self.ensureAll(); self['spawnIndex']            = value
    def onSetSpawnTeamID(self, value):          self.ensureAll(); self['spawnTeamID']           = value
    def onSetSpawnEnemyType(self, value):       self.ensureAll(); self['spawnEnemyType']        = enumIndexToTag(value, self.spawnEnemyTypeEnumItems)
    def onSetSpawnBlitzType(self, value):       self.ensureAll(); self['spawnBlitzType']        = enumIndexToTag(value, self.spawnBlitzTypeEnumItems)
    def onSetSoundFileName(self, value):        self.ensureAll(); self['soundFileName']         = value
    def onSetSoundSpace(self, value):           self.ensureAll(); self['soundSpace']            = enumIndexToTag(value, self.soundSpaceEnumItems)
    def onSetSoundShape(self, value):           self.ensureAll(); self['soundShape']            = enumIndexToTag(value, self.soundShapeEnumItems)
    def onSetItemGameID(self, value):           self.ensureAll(); self['itemGameID']            = enumIndexToTag(value, self.itemGameIDEnumItems)
    def onSetItemType(self, value):             self.ensureAll(); self['itemType']              = enumIndexToTag(value, self.itemTypeEnumItems)
    def onSetItemID(self, value):               self.ensureAll(); self['itemID']                = value
    def onSetItemTimer(self, value):            self.ensureAll(); self['itemTimer']             = value
    def onSetSmokeType(self, value):            self.ensureAll(); self['smokeType']             = enumIndexToTag(value, self.smokeTypeEnumItems)
    def onSetSmokeDirection(self, value):       self.ensureAll(); self['smokeDirection']        = value
    def onSetSmokePower(self, value):           self.ensureAll(); self['smokePower']            = value
    def onSetSmokeDelay(self, value):           self.ensureAll(); self['smokeDelay']            = value
    def onSetSmokeSize(self, value):            self.ensureAll(); self['smokeSize']             = value
    def onSetSmokeLife(self, value):            self.ensureAll(); self['smokeLife']             = value
    def onSetSmokeToggleMinTime(self, value):   self.ensureAll(); self['smokeToggleMinTime']    = value
    def onSetOccPriority(self, value):          self.ensureAll(); self['occPriority']           = value
    def onSetOccBsp(self, value):               self.ensureAll(); self['occBsp']                = value
    def onSetOccOct(self, value):               self.ensureAll(); self['occOct']                = value
    def onSetOccProp(self, value):              self.ensureAll(); self['occProp']               = value

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

    itemTimer: FloatProperty(
        name = 'Timer',
        default = 30.0,
        min = 0.0,
        max = 3.402823e+38,
        soft_min = 0.0,
        soft_max = 3.402823e+38,
        subtype = 'UNSIGNED',
        unit = 'TIME_ABSOLUTE',
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
        name = 'Accel. Direction',
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
        name = 'Accel. Power',
        default = 0.0,
        min = 0.0,
        max = 1000.0,
        soft_min = 0.0,
        soft_max = 1000.0,
        subtype = 'UNSIGNED',
        update = onUpdate,
        get = onGetSmokePower,
        set = onSetSmokePower
    )

    smokeDelay: IntProperty(
        name = 'Delay',
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
        name = 'Size',
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
        name = 'Lifetime',
        default = 1.0,
        min = 0.0,
        max = 100.0,
        soft_min = 0.0,
        soft_max = 100.0,
        subtype = 'UNSIGNED',
        update = onUpdate,
        get = onGetSmokeLife,
        set = onSetSmokeLife
    )

    smokeToggleMinTime: FloatProperty(
        name = 'Min. Toggle Time',
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

    occPriority: IntProperty(
        name = 'Priority',
        default = 1,
        min = 1,
        max = 999,
        soft_min = 1,
        soft_max = 999,
        subtype = 'UNSIGNED',
        update = onUpdate,
        get = onGetOccPriority,
        set = onSetOccPriority
    )

    occBsp: BoolProperty(
        name = 'Bsptree',
        default = True,
        update = onUpdate,
        get = onGetOccBsp,
        set = onSetOccBsp
    )

    occOct: BoolProperty(
        name = 'Octree',
        default = False,
        update = onUpdate,
        get = onGetOccOct,
        set = onSetOccOct
    )

    occProp: BoolProperty(
        name = 'Props',
        default = False,
        update = onUpdate,
        get = onGetOccProp,
        set = onSetOccProp
    )

    attachmentFilename: StringProperty(
        name = 'Filename',
        default = '',
        subtype = 'FILE_NAME'
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

            if props.spawnType == 'TEAM':       column.prop(props, 'spawnTeamID')
            elif props.spawnType == 'NPC':      column.prop(props, 'spawnEnemyType')
            elif props.spawnType == 'BLITZ':    column.prop(props, 'spawnBlitzType')
        elif props.dummyType == 'SOUND':
            column.prop(props, 'soundFileName')
            column.prop(props, 'soundSpace')
            column.prop(props, 'soundShape')
            soundShape = props.soundShape

            if      soundShape == 'AABB':       column.label(text = "Tip: Keep size at 1m, use scale instead.")
            elif    soundShape == 'SPHERE':     column.label(text = "Tip: Keep scale at (1, 1, 1), use size instead.")
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
            if props.smokeType == 'ST':
                column.prop(props, 'smokeToggleMinTime')
            else:
                column.label(text = "Tip: Smoke and Train Smoke always point up.")
            column.label(text = "Tip: Direction is an angle in world space.")
        elif props.dummyType == 'OCCLUSION':
            column.prop(props, 'occPriority')
            column.prop(props, 'occBsp')
            column.prop(props, 'occOct')
            column.prop(props, 'occProp')
            if props.occProp:
                column.label(text = "Tip: Keep size at 1m, use scale instead.")
        elif props.dummyType == 'ATTACHMENT':
            column.prop(props, 'attachmentFilename')

class GZRS2MeshProperties(PropertyGroup):
    def onUpdate(self, context):
        blSelfMesh = self.id_data

        if blSelfMesh is None:
            return

        blLinkedObjs = tuple(blObj for blObj in context.scene.objects if blObj.type == 'MESH' and blObj.data == blSelfMesh)

        for blLinkedObj in blLinkedObjs:
            if self.meshType == 'PROP' and self.propSubtype == 'SKY':
                blLinkedObj.visible_volume_scatter = False
                blLinkedObj.visible_transmission = False
                blLinkedObj.visible_shadow = False
            else:
                blLinkedObj.visible_volume_scatter = True
                blLinkedObj.visible_transmission = True
                blLinkedObj.visible_shadow = True

    # TODO: Custom sprite gizmos
    meshType: EnumProperty(
        name = 'Type',
        items = MESH_TYPE_DATA,
        update = onUpdate
    )

    worldCollision: BoolProperty(
        name = 'Collision',
        default = False
    )

    worldDetail: BoolProperty(
        name = 'Detail',
        default = False
    )

    propSubtype: EnumProperty(
        name = 'Subtype',
        items = PROP_SUBTYPE_DATA,
        update = onUpdate
    )

    propFilename: StringProperty(
        name = 'Filename',
        default = '',
        subtype = 'FILE_NAME'
    )

    flagDirection: IntProperty(
        name = 'Wind Direction',
        default = 0,
        min = 0,
        max = 359,
        soft_min = 0,
        soft_max = 359,
        subtype = 'ANGLE'
    )

    flagPower: FloatProperty(
        name = 'Wind Power',
        default = 0.0,
        min = 0.0,
        max = 1000.0,
        soft_min = 0.0,
        soft_max = 1000.0,
        subtype = 'UNSIGNED'
    )

    flagWindType: EnumProperty(
        name = 'Wind Type',
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

    flagUseLimit: BoolProperty(
        name = 'Limit',
        default = False
    )

    flagLimitAxis: EnumProperty(
        name = 'Limit Axis',
        items = FLAG_LIMIT_AXIS_DATA
    )

    flagLimitOffset: FloatProperty(
        name = 'Limit Offset',
        default = 0.0,
        min = -1000.0,
        max = 1000.0,
        soft_min = -1000.0,
        soft_max = 1000.0,
        unit = 'LENGTH'
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

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        blMeshObj = context.active_object
        meshName = blMeshObj.name

        props = blMeshObj.data.gzrs2

        column = layout.column()
        column.prop(props, 'meshType')

        if props.meshType == 'WORLD':
            column.prop(props, 'worldCollision')
            column.prop(props, 'worldDetail')
        elif props.meshType == 'PROP':
            column.prop(props, 'propSubtype')
            column.prop(props, 'propFilename')

            propFilename = props.propFilename

            if meshName in propFilename:    splitname = propFilename.split(meshName)
            else:                           splitname = ("N/A", "N/A")

            box = layout.box()
            column = box.column()
            row = column.row()
            row.label(text = "Is Child:")
            row.label(text = "True" if isChildProp(blMeshObj) else "False")
            row = column.row()
            row.label(text = "Prefix:")
            row.label(text = splitname[0])
            row = column.row()
            row.label(text = "Suffix:")
            row.label(text = splitname[1])

            column = layout.column()

            if props.propSubtype == 'NONE':
                column.operator(GZRS2_OT_Unfold_Vertex_Data.bl_idname, text = "Unfold Vertex Data")
            elif props.propSubtype == 'FLAG':
                column.prop(props, 'flagDirection')
                column.prop(props, 'flagPower')
                column.prop(props, 'flagWindType')
                column.prop(props, 'flagWindDelay')
                column.prop(props, 'flagUseLimit')

                column2 = column.column()
                column2.prop(props, 'flagLimitAxis')
                column2.prop(props, 'flagLimitOffset')
                column2.prop(props, 'flagLimitCompare')
                column2.enabled = props.flagUseLimit

        if props.meshType in ('WORLD', 'COLLISION', 'NAVIGATION'):
            column.operator(GZRS2_OT_Preprocess_Geometry.bl_idname, text = "Pre-process Geometry")

class GZRS2LightProperties(PropertyGroup):
    lightType: EnumProperty(
        name = 'Type',
        items = (('NONE',       'None',         "Not a Realspace light. Will not be exported"),
                 ('STATIC',     'Static',       "Lights world geometry during lightmap baking"),
                 ('DYNAMIC',    'Dynamic',      "Lights props at runtime. Does not contribute to lightmaps"))
    )

    lightSubtype: EnumProperty(
        name = 'Type',
        items = (('NONE',       'None',         "Light has no special properties"),
                 ('SUN',        'Sun',          "Light is assumed to be far away and high above the map"))
    )

    intensity: FloatProperty(
        name = 'Intensity',
        default = 1.0,
        min = 0.0,
        max = 3.402823e+38,
        soft_min = 0.0,
        soft_max = 3.402823e+38,
        subtype = 'UNSIGNED'
    )

    attStart: FloatProperty(
        name = 'Attenuation Start',
        default = 0.0,
        min = 0.0,
        max = 3.402823e+38,
        soft_min = 0.0,
        soft_max = 3.402823e+38,
        subtype = 'UNSIGNED',
        unit = 'LENGTH'
    )

    attEnd: FloatProperty(
        name = 'Attenuation End',
        default = 10.0,
        min = 0.0,
        max = 3.402823e+38,
        soft_min = 0.0,
        soft_max = 3.402823e+38,
        subtype = 'UNSIGNED',
        unit = 'LENGTH'
    )

    duelistsRange: FloatProperty(
        name = 'Range',
        default = 5.0,
        min = 0.0,
        max = 3.402823e+38,
        soft_min = 0.0,
        soft_max = 3.402823e+38,
        subtype = 'UNSIGNED',
        unit = 'LENGTH'
    )

    duelistsShadowBias: FloatProperty(
        name = 'Shadow Bias',
        default = 0.001,
        min = -3.402823e+38,
        max = 3.402823e+38,
        soft_min = -3.402823e+38,
        soft_max = 3.402823e+38
    )

    duelistsShadowResolution: IntProperty(
        name = 'Shadow Res.',
        default = 256,
        min = 256,
        max = 2**31 - 1,
        soft_min = 256,
        soft_max = 2**31 - 1,
        subtype = 'PIXEL'
    )

    @classmethod
    def register(cls):
        bpy.types.Light.gzrs2 = PointerProperty(type = cls)

    @classmethod
    def unregister(cls):
        del bpy.types.Light.gzrs2

class GZRS2_PT_Realspace_Light(Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_label = 'Realspace'
    bl_idname = 'LIGHT_PT_realspace'
    bl_description = "Custom properties for Realspace engine lights."
    bl_context = 'data'

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'LIGHT'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        serverProfile = context.preferences.addons[__package__].preferences.serverProfile

        blLight = context.active_object.data
        props = blLight.gzrs2

        attStart = props.attStart
        attEnd = clampLightAttEnd(props.attEnd, attStart)

        column = layout.column()

        column.prop(props, 'lightType')

        if props.lightType == 'NONE':
            return

        column.prop(props, 'lightSubtype')
        column.prop(props, 'intensity')
        column.prop(props, 'attStart')
        column.prop(props, 'attEnd')

        if serverProfile == 'DUELISTS':
            column.separator()
            column.prop(props, 'duelistsRange')
            column.prop(props, 'duelistsShadowBias')
            column.prop(props, 'duelistsShadowResolution')

        worldProps = ensureWorld(context).gzrs2

        box = layout.box()
        column = box.column()
        column.label(text = "Render")
        column.prop(worldProps, 'lightIntensity')
        column.prop(worldProps, 'sunIntensity')
        column.prop(worldProps, 'lightSoftSize')
        column.prop(worldProps, 'fogDensity')

        column = layout.column()
        row = column.row()
        row.operator(GZRS2_OT_Toggle_Lightmap_Mix.bl_idname, text = "Lightmap Mix")
        row.operator(GZRS2_OT_Toggle_Lightmap_Mod4.bl_idname, text = "Lightmap Mod4")
        column.operator(GZRS2_OT_Recalculate_Lights_Fog.bl_idname, text = "Recalculate Lights & Fog")
        column.operator(GZRS2_OT_Prepare_Bake.bl_idname, text = "Prepare for Bake")

class GZRS2CameraProperties(PropertyGroup):
    cameraIndex: IntProperty(
        name = 'Index',
        default = 1,
        min = 1,
        max = 999,
        soft_min = 1,
        soft_max = 999,
        subtype = 'UNSIGNED'
    )

    cameraType: EnumProperty(
        name = 'Type',
        items = CAMERA_TYPE_DATA
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

def getFilteredObjectLists(blObjs):
    # Gather data into lists
    blMeshObjs = tuple(blObj for blObj in blObjs if blObj.type == 'MESH')
    blWorldObjs = tuple(blMeshObj for blMeshObj in blMeshObjs if blMeshObj.data.gzrs2.meshType == 'WORLD')
    blPropObjs = tuple(blMeshObj for blMeshObj in blMeshObjs if blMeshObj.data.gzrs2.meshType == 'PROP' and not isChildProp(blMeshObj))

    # Sort lists
    def sortProp(x):
        return (
            PROP_SUBTYPE_TAGS.index(x.data.gzrs2.propSubtype),
            x.name
        )

    blWorldObjs     = tuple(sorted(blWorldObjs,     key = lambda x: x.name))
    blPropObjs      = tuple(sorted(blPropObjs,      key = sortProp))

    # Consolidate and freeze lists
    blPropObjsAll = []

    for blPropObj in blPropObjs:
        blPropObjsAll.append(blPropObj)
        blPropObjChildren = []

        for object in blPropObj.children_recursive:
            if      object.type != 'MESH':                  continue
            elif    object.data.gzrs2.meshType != 'PROP':   continue

            blPropObjChildren.append(object)

        blPropObjsAll += tuple(sorted(tuple(blPropObjChildren), key = sortProp))

    return blWorldObjs, tuple(blPropObjsAll)

class GZRS2MaterialProperties(PropertyGroup):
    def onPollParent(self, object):
        blSelfMat = self.id_data
        blTargetMat = object

        if blSelfMat == blTargetMat:
            return False

        # Prevent parent chains
        if blTargetMat.gzrs2.parent is not None:
            return False

        # We assume none of these contain empty slots
        blWorldObjs, blPropObjsAll = getFilteredObjectLists(bpy.context.scene.objects)

        blWorldMats     = set(matSlot.material for blWorldObj   in blWorldObjs      for matSlot in blWorldObj.material_slots)
        blPropMats      = set(matSlot.material for blPropObj    in blPropObjsAll    for matSlot in blPropObj.material_slots)
        blPropMats      |= set(blPropMat.gzrs2.parent for blPropMat in blPropMats) - { None }

        # TODO: Prevent collisions, if possible

        # Prevent parent forking
        blSelfObjs      = set(blPropObj for blPropObj in blPropObjsAll for matSlot in blPropObj.material_slots if matSlot.material == blSelfMat)
        blSiblingMats   = set(matSlot.material for blSelfObj in blSelfObjs for matSlot in blSelfObj.material_slots if matSlot.material != blSelfMat)
        blParentMats    = set(blSiblingMat.gzrs2.parent for blSiblingMat in blSiblingMats if blSiblingMat != blSelfMat) - { None }

        if len(blParentMats) > 0:
            if blTargetMat not in blParentMats:
                return False

        # Prevent parent chains
        blParentMats    = set(blPropMat.gzrs2.parent for blPropMat in blPropMats)

        if len(blParentMats) > 0:
            if blSelfMat in blParentMats:
                return False

        # Prevent type overlap
        if      blSelfMat in blWorldMats    and blTargetMat in blPropMats:      return False
        elif    blSelfMat in blPropMats     and blTargetMat in blWorldMats:     return False

        return True

    priority: IntProperty(
        name = 'Priority',
        default = 0,
        min = 0,
        max = 2**31 - 1,
        soft_min = 0,
        soft_max = 256,
        subtype = 'UNSIGNED'
    )

    parent: PointerProperty(
        type = bpy.types.Material,
        name = 'Parent',
        poll = onPollParent
    )

    ambient: FloatVectorProperty(
        name = 'Ambient',
        default = (0.5882353, 0.5882353, 0.5882353),
        min = 0.0,
        max = 1.0,
        soft_min = 0.0,
        soft_max = 1.0,
        subtype = 'COLOR',
        size = 3
    )

    diffuse: FloatVectorProperty(
        name = 'Diffuse',
        default = (0.5882353, 0.5882353, 0.5882353),
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

    overrideTexpath: BoolProperty(
        name = 'Override Texpath',
        default = False
    )

    writeDirectory: BoolProperty(
        name = 'Write Directory',
        default = False
    )

    texBase: StringProperty(
        name = 'Basename',
        default = '',
        subtype = 'FILE_NAME'
    )

    texDir: StringProperty(
        name = 'Directory',
        default = ''
    )

    sound: EnumProperty(
        name = 'Sound',
        items = MATERIAL_SOUND_DATA
    )

    fakeEmission: FloatProperty(
        name = 'Emission',
        default = 0.0,
        min = 0.0,
        max = 100.0,
        soft_min = 0.0,
        soft_max = 100.0,
        precision = 3,
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

    @classmethod
    def poll(cls, context):
        blObj = context.active_object

        if blObj is None or blObj.type != 'MESH':
            return False

        blMesh = blObj.data

        if blMesh is None:
            return False

        return blObj.active_material is not None

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        serverProfile = context.preferences.addons[__package__].preferences.serverProfile

        blObj = context.active_object
        blMesh = blObj.data
        blMat = blObj.active_material

        worldProps = ensureWorld(context).gzrs2
        meshProps = blMesh.gzrs2
        matProps = blMat.gzrs2

        meshType = meshProps.meshType

        if meshType not in ('WORLD', 'PROP'):
            column = layout.column()
            row = column.row()
            row.alert = True
            row.label(text = "Mesh type must be World or Prop!")
            column.prop(meshProps, 'meshType', text = "Mesh Type")
            return

        blWorldObjs, blPropObjsAll = getFilteredObjectLists(context.scene.objects)
        blExportObjs = blWorldObjs + blPropObjsAll

        def reportUI(column, needSeparator, names, errorText1, errorText2):
            if needSeparator:
                column.separator()

            row = column.row()
            row.alert = True
            row.label(text = errorText1)

            if errorText2 is not None:
                row = column.row()
                row.alert = True
                row.label(text = errorText2)

            for name in names:
                column.label(text = "\t\t\t\t\t\t\t\t" + name)

        # Check for and report error, early exit
        emptyNames, hasEmpty = checkMeshesEmptySlots(blExportObjs)

        if hasEmpty:
            column = layout.column(align = True)
            reportUI(column, False, emptyNames, "Mesh objects cannot have empty slots!", "Remove them before continuing!")
            return

        # Gather materials by type
        blWorldMats     = set(matSlot.material for blWorldObj   in blWorldObjs      for matSlot in blWorldObj.material_slots)
        blPropMats      = set(matSlot.material for blPropObj    in blPropObjsAll    for matSlot in blPropObj.material_slots)
        blPropMats      |= set(blPropMat.gzrs2.parent for blPropMat in blPropMats) - { None }

        # Check for errors
        overlapNames,       hasOverlaps     = checkMatTypeOverlaps(blWorldMats, blPropMats)
        forkedNames,        hasForked       = checkPropsParentForks(blPropObjsAll)
        chainedNames,       hasChained      = checkPropsParentChains(blPropObjsAll)

        # Generate material info
        blBaseMats, blSubMats, subIDsByMat, uniqueMatLists = divideMeshMats(blPropObjsAll)

        # Check for errors
        swizzledNames,      hasSwizzled     = checkSubMatsSwizzles(subIDsByMat)
        collidingNames,     hasColliding    = checkSubMatsCollisions(subIDsByMat)

        # Associate materials
        blPropMatGraph = generateMatGraph(blBaseMats, blSubMats, subIDsByMat, uniqueMatLists)

        # Report errors
        needSeparator = hasOverlaps or hasForked or hasChained or hasSwizzled or hasColliding

        if needSeparator:
            column = layout.column(align = True)

        if hasOverlaps:     reportUI(column, needSeparator,     overlapNames,       "Prop materials must be exclusive to props!",       "Rearrange materials or change mesh type!")
        if hasForked:       reportUI(column, needSeparator,     forkedNames,        "Parents must match for all materials in mesh!",    "Empty parent fields count too!")
        if hasChained:      reportUI(column, needSeparator,     chainedNames,       "Materials cannot form chains or loops!",           "Double check parent fields!")
        if hasSwizzled:     reportUI(column, needSeparator,     swizzledNames,      "Child materials cannot swizzle slots!",            "Check meshes and rearrange materials!")
        if hasColliding:    reportUI(column, needSeparator,     collidingNames,     "Materials of the same parent cannot collide!",     "Rearrange materials or duplicate the parent!")

        if hasOverlaps:
            return

        # Sort materials
        blWorldMats = tuple(sorted(blWorldMats, key = lambda x: (x.gzrs2.priority, x.name)))

        # Get relevant variables
        isBase = False
        childCount = 0

        for matID, (blBaseMat, subMats) in enumerate(blPropMatGraph):
            if blBaseMat is not None and blBaseMat == blMat:
                isBase = True
                childCount = len(subMats)
                break

            if blMat in subMats:
                isBase = False
                childCount = 0
                break

        # Begin layout
        column = layout.column()
        row = column.row()
        row.prop(matProps, 'priority')
        row.enabled = isBase

        if meshType == 'WORLD':
            row = column.row()
            split = row.split(factor = 0.4125)
            split.alignment = 'RIGHT'
            split.label(text = "Parent")
            split.alignment = 'LEFT'
            split.label(text = "N/A")

            row.label(text = "", icon = 'DECORATE')

            row = column.row()
            split = row.split(factor = 0.4125)
            split.alignment = 'RIGHT'
            split.label(text = "Material ID")

            row2 = split.row()
            row2.label(text = "Xml " + str(blWorldMats.index(blMat)))
            row2.label(text = "")
            row2.label(text = "")

            row.label(text = "", icon = 'DECORATE')
        elif meshType == 'PROP':
            if childCount > 0:
                row = column.row()
                split = row.split(factor = 0.4125)
                split.alignment = 'RIGHT'

                if childCount == 1:
                    split.label(text = "Child")
                    split.alignment = 'LEFT'
                    split.label(text = subMats[0].name)
                else:
                    split.label(text = "Children")
                    split.alignment = 'LEFT'
                    split.label(text = str(childCount))

                row.label(text = "", icon = 'DECORATE')
            else:
                column.prop(matProps, 'parent')

            row = column.row()
            split = row.split(factor = 0.4125)
            split.alignment = 'RIGHT'
            split.label(text = "Material ID")
            split.alignment = 'LEFT'

            if not (hasForked or hasChained or hasSwizzled or hasColliding):
                row2 = split.row()
                row2.label(text = "Xml " + str(matID + len(blWorldMats)))
                row2.label(text = "Elu " + str(matID))

                if blMat in blSubMats:  row2.label(text = "Slot " + str(subIDsByMat[blMat][0]))
                else:                   row2.label(text = "")
            else:
                split.label(text = "Error")

            row.label(text = "", icon = 'DECORATE')

        tree, links, nodes = getMatTreeLinksNodes(blMat)

        shader, output, info, transparent, mix, clip, add, lightmix = getRelevantShaderNodes(nodes)
        shaderValid, infoValid, transparentValid, mixValid, clipValid, addValid, lightmixValid = checkShaderNodeValidity(shader, output, info, transparent, mix, clip, add, lightmix, links)

        if shaderValid:
            texture, emission, alpha, _ = getLinkedImageNodes(shader, shaderValid, links, clip, clipValid, lightmix, lightmixValid)
            twosided, additive, alphatest, usealphatest, useopacity = getMatFlagsRender(blMat, clip, addValid, clipValid, emission, alpha)

            if      matProps.overrideTexpath:   texpath = os.path.join(matProps.texDir, matProps.texBase)
            elif    texture is None:            texpath = ''
            elif    matProps.writeDirectory:    texpath = makeRS2DataPath(texture.image.filepath)
            else:                               texpath = makePathExtSingle(bpy.path.basename(texture.image.filepath))

            if texpath == False:
                texBase = bpy.path.basename(texture.image.filepath)
                texDir = 'Invalid'
            else:
                texBase, texName, _, texDir = decomposePath(texpath)
                isAniTex = checkIsAniTex(texName)
                success, frameCount, frameSpeed, frameGap = processAniTexParameters(isAniTex, texName, silent = True)

        shaderLabel =       '' if shaderValid           is None else ('Invalid' if shaderValid ==           False else 'Valid')
        infoLabel =         '' if infoValid             is None else ('Invalid' if infoValid ==             False else 'Valid')
        transparentLabel =  '' if transparentValid      is None else ('Invalid' if transparentValid ==      False else 'Valid')
        mixLabel =          '' if mixValid              is None else ('Invalid' if mixValid ==              False else 'Valid')
        clipLabel =         '' if clipValid             is None else ('Invalid' if clipValid ==             False else 'Valid')
        addLabel =          '' if addValid              is None else ('Invalid' if addValid ==              False else 'Valid')
        lightmixLabel =     '' if lightmixValid         is None else ('Invalid' if lightmixValid ==         False else 'Valid')

        column = layout.column()

        row = column.row()
        row.prop(matProps, 'ambient')
        row.enabled = meshType == 'PROP' or serverProfile == 'DUELISTS'

        column.prop(matProps, 'diffuse')

        row = column.row()
        row.prop(matProps, 'specular')
        row.enabled = meshType == 'PROP' or serverProfile == 'DUELISTS'

        row = column.row()
        row.prop(matProps, 'exponent')
        row.enabled = meshType == 'PROP' or serverProfile == 'DUELISTS'

        row = column.row()
        if shaderValid and addValid:    row.prop(shader.inputs[27], 'default_value', text = "Emission") # Emission Strength
        else:                           row.prop(matProps, 'fakeEmission')
        row.enabled = bool(shaderValid and addValid)

        row = column.row()
        row.prop(matProps, 'sound')
        row.enabled = meshType == 'WORLD' and '_mt_' not in blMat.name

        row = column.row()
        row.operator(GZRS2_OT_Apply_Material_Preset.bl_idname, text = "Change Preset")

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
        row.label(text = clipLabel if meshType == 'PROP' else 'N/A')
        row.enabled = meshType == 'PROP'
        row = column.row()
        row.label(text = "Add Shader:")
        row.label(text = addLabel if meshType == 'PROP' else 'N/A')
        row.enabled = meshType == 'PROP'
        row = column.row()
        row.label(text = "Lightmap Mix:")
        row.label(text = lightmixLabel if meshType == 'WORLD' else 'N/A')
        row.enabled = meshType == 'WORLD'

        box = layout.box()
        column = box.column()

        row = column.row()
        row.use_property_split = False
        row.prop(matProps, 'overrideTexpath')
        row.prop(matProps, 'writeDirectory')

        if matProps.overrideTexpath:
            column.prop(matProps, 'texBase')
            column.prop(matProps, 'texDir')
            column.label(text = "Tip: Use \"..\\\" to go up one folder.")
        else:
            row = column.row()
            row.label(text = "Basename:")
            row.label(text = texBase if shaderValid else 'N/A')
            row = column.row()
            row.label(text = "Directory:")
            row.label(text = texDir if shaderValid else 'N/A')

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
        row.label(text = "Is Animated:")
        row.label(text = str(isAniTex) if shaderValid and texpath else 'N/A')
        row = column.row()
        row.label(text = "Frame Count:")
        row.label(text = str(frameCount) if shaderValid and texpath and success else 'N/A')
        row = column.row()
        row.label(text = "Frame Speed:")
        row.label(text = str(frameSpeed) if shaderValid and texpath and success else 'N/A')
        row = column.row()
        row.label(text = "Frame Gap:")
        row.label(text = str(frameGap) if shaderValid and texpath and success else 'N/A')

classes = (
    GZRS2_OT_Specify_Path_MRS,
    GZRS2_OT_Specify_Path_MRF,
    GZRS2_OT_Preprocess_Geometry,
    GZRS2_OT_Unfold_Vertex_Data,
    GZRS2_OT_Apply_Material_Preset,
    GZRS2_OT_Toggle_Lightmap_Mix,
    GZRS2_OT_Toggle_Lightmap_Mod4,
    GZRS2_OT_Recalculate_Lights_Fog,
    GZRS2_OT_Prepare_Bake,
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
    ExportGZRS2,
    GZRS2_PT_Export_Main,
    GZRS2_PT_Export_Lightmap,
    GZRS2_PT_Export_Logging,
    ExportRSELU,
    RSELU_PT_Export_Main,
    RSELU_PT_Export_Logging,
    ExportRSNAV,
    RSNAV_PT_Export_Main,
    RSNAV_PT_Export_Logging,
    ExportRSLM,
    RSLM_PT_Export_Main,
    RSLM_PT_Export_Logging,
    GZRS2WorldProperties,
    GZRS2_PT_Realspace_World,
    GZRS2ObjectProperties,
    GZRS2_PT_Realspace_Object,
    GZRS2MeshProperties,
    GZRS2_PT_Realspace_Mesh,
    GZRS2LightProperties,
    GZRS2_PT_Realspace_Light,
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
    self.layout.operator(ImportRSLM.bl_idname, text = 'GunZ LM Image (.lm)')

def menu_func_export(self, context):
    self.layout.operator(ExportGZRS2.bl_idname, text = 'GunZ RS2 (.rs) (Beta)')
    self.layout.operator(ExportRSELU.bl_idname, text = 'GunZ ELU (.elu)')
    self.layout.operator(ExportRSNAV.bl_idname, text = 'GunZ NAV (.nav)')
    self.layout.operator(ExportRSLM.bl_idname, text = 'GunZ LM Overwrite (.lm)')

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
