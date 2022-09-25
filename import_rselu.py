#####
# Most of the code is based on logic found in...
#
### GunZ 1
# - RTypes.h
# - RToken.h
# - RBspObject.h/.cpp
# - RMaterialList.h/.cpp
# - RMesh_Load.cpp
# - RMeshUtil.h
# - MZFile.cpp
# - R_Mtrl.cpp
# - EluLoader.h/cpp
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

import bpy, os, io, math, mathutils
import xml.dom.minidom as minidom
from mathutils import Vector, Matrix
from contextlib import redirect_stdout

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .parse_gzrs2 import *
from .readelu_gzrs2 import *
from .lib_gzrs2 import *

def importElu(self, context):
    state = GZRS2State()
    silence = io.StringIO()

    state.convertUnits = self.convertUnits
    state.doCleanup = self.doCleanup
    state.doBoneRolls = self.doBoneRolls
    state.doTwistConstraints = self.doTwistConstraints

    if self.panelLogging:
        print()
        print("=======================================================================")
        print("===========================  GZRS2 Import  ============================")
        print("=======================================================================")
        print(f"== { self.filepath }")
        print("=======================================================================")
        print()

        state.logEluHeaders = self.logEluHeaders
        state.logEluMats = self.logEluMats
        state.logEluMeshNodes = self.logEluMeshNodes
        state.logVerboseIndices = self.logVerboseIndices
        state.logVerboseWeights = self.logVerboseWeights
        state.logCleanup = self.logCleanup

    elupath = self.filepath
    directory = os.path.dirname(elupath)
    filename = os.path.splitext(os.path.basename(elupath))[0]

    xmlelupath = f"{ elupath }.xml"

    xmlElu = False
    xmlEluExists = pathExists(xmlelupath, directory)

    if xmlEluExists:
        xmlelupath = xmlEluExists
        xmlElu = minidom.parse(xmlelupath)
        state.xmlEluMats[0] = parseEluXML(self, xmlElu, state)
    else:
        xmlelupath = f"{ elupath }.XML"
        xmlEluExists = pathExists(xmlelupath, directory)

        if xmlEluExists:
            xmlelupath = xmlEluExists
            xmlElu = minidom.parse(xmlelupath)
            state.xmlEluMats[0] = parseEluXML(self, xmlElu, state)

    readElu(self, elupath, state)

    bpy.ops.ed.undo_push()
    collections = bpy.data.collections

    rootMesh = collections.new(filename)
    context.collection.children.link(rootMesh)

    for material in state.eluMats:
        name = material.texName or f"{ material.matID }[{ material.subMatID }]"
        blMat = bpy.data.materials.new(f"{ filename }_{ name }")
        blMat.use_nodes = True

        tree = blMat.node_tree
        nodes = tree.nodes

        shader = nodes.get('Principled BSDF')
        shader.location = (0, 300)
        shader.inputs[7].default_value = material.power / 100.0

        if material.texBase != '':
            texpath = textureSearch(self, directory, material.texBase, material.texDir)

            if texpath is not None:
                texture = nodes.new(type = 'ShaderNodeTexImage')
                texture.image = bpy.data.images.load(texpath)
                texture.location = (-280, 300)

                tree.links.new(texture.outputs[0], shader.inputs[0])

                blMat.use_backface_culling = not material.twosided

                if material.alphatest:
                    blMat.blend_method = 'CLIP'
                    blMat.shadow_method = 'CLIP'
                    blMat.show_transparent_back = True
                    blMat.use_backface_culling = False
                    blMat.alpha_threshold = 1.0 - (material.alphatest / 100.0)

                    tree.links.new(texture.outputs[1], shader.inputs[21])
                elif material.useopacity:
                    blMat.blend_method = 'HASHED'
                    blMat.shadow_method = 'HASHED'
                    blMat.show_transparent_back = True
                    blMat.use_backface_culling = False

                    tree.links.new(texture.outputs[1], shader.inputs[21])

                if material.additive:
                    blMat.blend_method = 'BLEND'
                    blMat.show_transparent_back = True
                    blMat.use_backface_culling = False

                    add = nodes.new(type = 'ShaderNodeAddShader')
                    add.location = (300, 140)

                    transparent = nodes.new(type = 'ShaderNodeBsdfTransparent')
                    transparent.location = (300, 20)

                    tree.links.new(texture.outputs[0], shader.inputs[19])
                    tree.links.new(shader.outputs[0], add.inputs[0])
                    tree.links.new(transparent.outputs[0], add.inputs[1])
                    tree.links.new(add.outputs[0], nodes.get('Material Output').inputs[0])
            else:
                self.report({ 'INFO' }, f"GZRS2: Texture not found for .elu material: { material.texPath }")

        if not material.matID in state.blEluMats:
            state.blEluMats[material.matID] = {}

        state.blEluMats[material.matID][material.subMatID] = blMat

    if xmlElu:
        state.blXmlEluMats[0] = []

        for m, material in enumerate(state.xmlEluMats[0]):
            blMat = bpy.data.materials.new(f"{ filename }_{ material['name'] }")
            blMat.use_nodes = True

            tree = blMat.node_tree
            nodes = tree.nodes

            shader = nodes.get('Principled BSDF')
            shader.location = (0, 300)
            shader.inputs[6].default_value = material['GLOSSINESS'] / 100.0 if 'GLOSSINESS' in material else 0.0
            shader.inputs[7].default_value = 0.0

            diffuse = None
            opacity = None

            for texture in material['textures']:
                textype = texture['type']
                texname = texture['name']

                if textype in ['DIFFUSEMAP', 'SPECULARMAP', 'SELFILLUMINATIONMAP', 'OPACITYMAP', 'NORMALMAP']:
                    if texname:
                        texpath = textureSearch(self, directory, texname, '')

                        if texpath is not None:
                            if textype == 'DIFFUSEMAP':
                                if opacity is None:
                                    texture = nodes.new(type = 'ShaderNodeTexImage')
                                    texture.image = bpy.data.images.load(texpath)
                                    texture.location = (-560, 300)
                                else:
                                    texture = opacity

                                tree.links.new(texture.outputs[0], shader.inputs[0])
                                diffuse = texture
                            elif textype == 'SPECULARMAP':
                                texture = nodes.new(type = 'ShaderNodeTexImage')
                                texture.image = bpy.data.images.load(texpath)
                                texture.location = (-560, 0)
                                tree.links.new(texture.outputs[0], shader.inputs[7])
                            elif textype == 'SELFILLUMINATIONMAP':
                                texture = nodes.new(type = 'ShaderNodeTexImage')
                                texture.image = bpy.data.images.load(texpath)
                                texture.location = (-560, -300)
                                tree.links.new(texture.outputs[0], shader.inputs[19])
                            elif textype == 'OPACITYMAP':
                                if diffuse is None:
                                    texture = nodes.new(type = 'ShaderNodeTexImage')
                                    texture.image = bpy.data.images.load(texpath)
                                    texture.location = (-560, 300)
                                else:
                                    texture = diffuse

                                tree.links.new(texture.outputs[1], shader.inputs[21])
                                opacity = texture

                                blMat.blend_method = 'CLIP'
                                blMat.shadow_method = 'CLIP'
                                blMat.alpha_threshold = material['ALPHATESTVALUE'] / 255.0 if 'ALPHATESTVALUE' in material else 0.5
                            elif textype == 'NORMALMAP':
                                texture = nodes.new(type = 'ShaderNodeTexImage')
                                normal = nodes.new(type = 'ShaderNodeNormalMap')
                                texture.image = bpy.data.images.load(texpath)
                                texture.image.colorspace_settings.name = 'Non-Color'
                                texture.location = (-560, -600)
                                normal.location = (-280, -600)
                                tree.links.new(texture.outputs[0], normal.inputs[1])
                                tree.links.new(normal.outputs[0], shader.inputs[22])
                        else:
                            self.report({ 'INFO' }, f"GZRS2: Texture not found for .elu.xml material: { textype }, { texname }")
                    else:
                        self.report({ 'INFO' }, f"GZRS2: .elu.xml material with empty texture name: { m }, { textype }")
                else:
                    self.report({ 'INFO' }, f"GZRS2: Unsupported texture type for .elu.xml material: { textype }, { texname }")

            state.blXmlEluMats[0].append(blMat)

    boneNames = set()

    if state.doCleanup and state.logCleanup:
        print()
        print("=== Elu Mesh Cleanup ===")
        print()

    for eluMesh in state.eluMeshes:
        name = f"{ filename }_{ eluMesh.meshName }"

        if eluMesh.meshName.startswith(("Bip01", "Bone")):
            boneNames.add(eluMesh.meshName)

        if eluMesh.isDummy:
            blDummyObj = bpy.data.objects.new(name, None)

            blDummyObj.empty_display_type = 'ARROWS'
            blDummyObj.empty_display_size = 0.1
            blDummyObj.matrix_local = eluMesh.transform

            rootMesh.objects.link(blDummyObj)

            state.blDummyObjs.append(blDummyObj)
            state.blObjPairs.append((eluMesh, blDummyObj))
        else:
            doNorms = len(eluMesh.normals) > 0
            doUV1 = len(eluMesh.uv1s) > 0
            doUV2 = len(eluMesh.uv2s) > 0
            doWeights = len(eluMesh.weights) > 0

            meshVerts = []
            meshFaces = []
            meshNorms = [] if doNorms else None
            meshUV1 = [] if doUV1 else None
            meshUV2 = [] if doUV2 else None
            groups = {} if doWeights else None
            index = 0

            blMesh = bpy.data.meshes.new(name)
            blMeshObj = bpy.data.objects.new(name, blMesh)

            for face in eluMesh.faces:
                degree = face.degree

                # Reverses the winding order for GunZ 1 elus
                for v in range(degree - 1, -1, -1) if eluMesh.version <= ELU_5007 else range(degree):
                    meshVerts.append(eluMesh.vertices[face.ipos[v]])
                    if doNorms: meshNorms.append(eluMesh.normals[face.inor[v]])
                    if doUV1: meshUV1.append(eluMesh.uv1s[face.iuv1[v]])
                    if doUV2: meshUV2.append(eluMesh.uv2s[face.iuv2[v]])

                meshFaces.append(tuple(range(index, index + degree)))
                index += degree

            blMesh.from_pydata(meshVerts, [], meshFaces)

            if doNorms:
                blMesh.use_auto_smooth = True
                blMesh.normals_split_custom_set_from_vertices(meshNorms)

            if doUV1:
                uvLayer1 = blMesh.uv_layers.new()
                for u, uv in enumerate(meshUV1): uvLayer1.data[u].uv = uv

            if doUV2:
                uvLayer2 = blMesh.uv_layers.new()
                for u, uv in enumerate(meshUV2): uvLayer2.data[u].uv = uv

            blMesh.validate()
            blMesh.update()

            if eluMesh.version <= ELU_5007:
                if eluMesh.matID in state.blEluMats:
                    blMesh.materials.append(state.blEluMats[eluMesh.matID][-1])
                else:
                    self.report({ 'INFO' }, f"GZRS2: Missing .elu material: { eluMesh.meshName }, { eluMesh.matID }")
            elif xmlElu:
                if state.blXmlEluMats[0][eluMesh.matID]:
                    blMesh.materials.append(state.blXmlEluMats[0][eluMesh.matID])
                else:
                    self.report({ 'INFO' }, f"GZRS2: Missing .elu.xml material: { eluMesh.meshName }, { eluMesh.matID }")
            else:
                self.report({ 'INFO' }, f"GZRS2: .elu.xml material requested where none was parsed, skipping: { eluMesh.meshName }, { eluMesh.matID }")

            blMeshObj.matrix_world = eluMesh.transform

            if doWeights:
                modifier = blMeshObj.modifiers.new("Armature", 'ARMATURE')
                modifier.use_deform_preserve_volume = True

                index = 0

                for face in eluMesh.faces:
                    degree = face.degree

                    # Reverses the winding order for GunZ 1 elus
                    for v in range(degree - 1, -1, -1) if eluMesh.version <= ELU_5007 else range(degree):
                        weight = eluMesh.weights[face.ipos[v]]

                        for d in range(weight.degree):
                            if eluMesh.version <= ELU_5007:
                                parentName = weight.meshName[d]
                                found = False

                                for p, parent in enumerate(state.eluMeshes):
                                    if parent.meshName == parentName:
                                        meshID = p
                                        found = True
                                        break

                                if not found:
                                    self.report({ 'ERROR' }, f"GZRS2: Named search failed to find mesh id for weight group: { eluMesh.meshName }, { parentName }")
                            else:
                                meshID = weight.meshID[d]

                            if not meshID in groups:
                                boneName = state.eluMeshes[meshID].meshName
                                boneNames.add(boneName)
                                groups[meshID] = blMeshObj.vertex_groups.new(name = boneName)

                            groups[meshID].add([index], weight.value[d], 'REPLACE')

                        index += 1

            rootMesh.objects.link(blMeshObj)

            for viewLayer in context.scene.view_layers:
                viewLayer.objects.active = blMeshObj

            if state.doCleanup:
                if state.logCleanup: print(eluMesh.meshName)

                bpy.ops.object.select_all(action = 'DESELECT')
                blMeshObj.select_set(True)
                bpy.ops.object.shade_smooth(use_auto_smooth = doNorms)
                bpy.ops.object.select_all(action = 'DESELECT')

                bpy.ops.object.mode_set(mode = 'EDIT')

                bpy.ops.mesh.select_mode(type = 'VERT')
                bpy.ops.mesh.select_all(action = 'SELECT')

                if state.logCleanup:
                    bpy.ops.mesh.delete_loose()
                else:
                    with redirect_stdout(silence):
                        bpy.ops.mesh.delete_loose()

                bpy.ops.mesh.select_all(action = 'SELECT')

                if state.logCleanup:
                    bpy.ops.mesh.remove_doubles(use_sharp_edge_from_normals = True)
                else:
                    with redirect_stdout(silence):
                        bpy.ops.mesh.remove_doubles(use_sharp_edge_from_normals = True)

                bpy.ops.mesh.select_all(action = 'DESELECT')

                if state.logCleanup: print()

            bpy.ops.object.mode_set(mode = 'OBJECT')

            state.blMeshes.append(blMesh)
            state.blMeshObjs.append(blMeshObj)

            state.blObjPairs.append((eluMesh, blMeshObj))

    for child, childObj in state.blObjPairs:
        if child.parentName == '':
            continue

        found = False

        for parent, parentObj in state.blObjPairs:
            if child != parent and child.parentName == parent.meshName:
                if child.version <= ELU_5007:
                    transform = childObj.matrix_world

                childObj.parent = parentObj

                if child.version <= ELU_5007:
                    childObj.matrix_world = transform

                found = True
                break

        if not found:
            self.report({ 'INFO' }, f"GZRS2: Parent not found for elu child mesh: { child.meshName }, { child.parentName }")

    if len(boneNames) > 0:
        state.blArmature = bpy.data.armatures.new("Armature")
        state.blArmatureObj = bpy.data.objects.new(f"{ filename }_Armature", state.blArmature)

        state.blArmatureObj.display_type = 'WIRE'
        state.blArmatureObj.show_in_front = True

        rootMesh.objects.link(state.blArmatureObj)

        for viewLayer in context.scene.view_layers:
            viewLayer.objects.active = state.blArmatureObj

        bpy.ops.object.mode_set(mode = 'EDIT')

        reorient = Matrix.Rotation(math.radians(-90.0), 4, 'Z') @ Matrix.Rotation(math.radians(-90.0), 4, 'Y')

        for eluMesh, blMeshOrDummyObj in state.blObjPairs:
            if not eluMesh.meshName in boneNames:
                continue

            blBone = state.blArmature.edit_bones.new(eluMesh.meshName)
            blBone.tail = (0, 0.1, 0)
            blBone.matrix = blMeshOrDummyObj.matrix_world @ reorient

            if eluMesh.isDummy:
                for collection in blMeshOrDummyObj.users_collection:
                    collection.objects.unlink(blMeshOrDummyObj)

            state.blBonePairs.append((eluMesh, blBone))

        for child, childBone in state.blBonePairs:
            if child.meshName == 'Bip01':
                continue

            found = False

            for parent, parentBone in state.blBonePairs:
                if child != parent and child.parentName == parent.meshName:
                    childBone.parent = parentBone
                    found = True

                    break

            if not found:
                self.report({ 'INFO' }, f"GZRS2: Parent not found for elu child bone: { child.meshName }, { child.parentName }")

        for eluMesh, blBone in state.blBonePairs:
            if blBone.name == 'Bip01':
                continue
            elif len(blBone.children) > 0:
                length = 0

                for child in blBone.children:
                    length = max(length, (child.head - blBone.head).length)

                blBone.length = length
            elif blBone.parent is not None:
                blBone.length = blBone.parent.length / 2

            if blBone.parent is not None and (Vector(blBone.parent.tail) - Vector(blBone.head)).length < 0.0001:
                blBone.use_connect = True

        if state.doBoneRolls:
            bpy.ops.armature.select_all(action = 'SELECT')
            bpy.ops.armature.calculate_roll(type = 'GLOBAL_POS_Z')
            bpy.ops.armature.select_all(action = 'DESELECT')

        bpy.ops.object.mode_set(mode = 'OBJECT')

        blPoseBones = state.blArmatureObj.pose.bones

        if state.doBoneRolls and state.doTwistConstraints:
            for parentBone in blPoseBones:
                if 'twist' in parentBone.name.lower():
                    for siblingBone in parentBone.parent.children:
                        if parentBone != siblingBone and len(siblingBone.children) > 0:
                            constraint = parentBone.constraints.new(type = 'TRACK_TO')
                            constraint.target = state.blArmatureObj
                            constraint.subtarget = siblingBone.children[0].name
                            constraint.track_axis = 'TRACK_Y'
                            constraint.up_axis = 'UP_Z'
                            constraint.use_target_z = True
                            constraint.target_space = 'POSE'
                            constraint.owner_space = 'POSE'

                            break

        for child, childObj in state.blObjPairs:
            isBone = child.meshName in boneNames

            if not child.parentName in boneNames or (isBone and child.isDummy):
                continue

            targetName = child.meshName if isBone else child.parentName
            found = False

            for parentBone in blPoseBones:
                if targetName == parentBone.name:
                    transform = childObj.matrix_world

                    childObj.parent = state.blArmatureObj
                    childObj.parent_bone = parentBone.name
                    childObj.parent_type = 'BONE'

                    childObj.matrix_world = transform

                    found = True
                    break

            if not found:
                self.report({ 'INFO' }, f"GZRS2: Bone parent not found: { child.meshName }, { child.parentName }, { child.isDummy }")

        for blMeshObj in state.blMeshObjs:
            modifier = blMeshObj.modifiers.get("Armature", None)

            if modifier:
                modifier.object = state.blArmatureObj

    bpy.ops.object.select_all(action = 'DESELECT')

    return { 'FINISHED' }
