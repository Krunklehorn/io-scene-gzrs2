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

import os, io, shutil

from mathutils import Vector, Matrix

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .io_gzrs2 import *
from .lib_gzrs2 import *

def exportElu(self, context):
    state = RSELUExportState()

    state.convertUnits = self.convertUnits
    state.selectedOnly = self.selectedOnly
    state.includeChildren = self.includeChildren and self.selectedOnly
    state.visibleOnly = self.visibleOnly

    if self.panelLogging:
        print()
        print("=======================================================================")
        print("===========================  RSELU Export  ============================")
        print("=======================================================================")
        print(f"== { self.filepath }")
        print("=======================================================================")
        print()

        state.logEluHeaders = self.logEluHeaders
        state.logEluMats = self.logEluMats
        state.logEluMeshNodes = self.logEluMeshNodes
        state.logVerboseIndices = self.logVerboseIndices and self.logEluMeshNodes
        state.logVerboseWeights = self.logVerboseWeights and self.logEluMeshNodes

    elupath = self.filepath
    directory = os.path.dirname(elupath)
    basename = os.path.basename(elupath)
    splitname = basename.split(os.extsep)
    filename = splitname[0]

    id = ELU_ID
    version = ELU_5007

    if state.selectedOnly:
        if state.includeChildren:
            objects = set()

            for object in context.selected_objects:
                objects.add(object)

                for child in object.children_recursive:
                    objects.add(child)
        else:
            objects = context.selected_objects
    else:
        objects = context.scene.objects

    objects = tuple(object for object in objects if object.visible_get()) if state.visibleOnly else tuple(objects)

    blObjs = []
    blArmatureObjs = []
    blValidBones = {}

    foundValid = False
    invalidCount = 0

    reorientLocal = Matrix.Rotation(math.radians(90.0), 4, 'Y') @ Matrix.Rotation(math.radians(90.0), 4, 'Z')
    reorientWorld = Matrix.Rotation(math.radians(90.0), 4, 'X')

    for object in objects:
        if object is None:
            continue

        if object.type in ['MESH', 'EMPTY']:
            foundValid = True

            if object.type == 'MESH':
                object.update_from_editmode()

                blArmatureObj, blArmature = getValidArmature(self, object, state)

                if blArmatureObj not in blArmatureObjs and blArmature is not None:
                    blArmatureObj.update_from_editmode()
                    blArmatureObjs.append(blArmatureObj)

                    for blBone in blArmature.bones:
                        blBoneName = blBone.name

                        if not blBoneName.startswith(("Bip01", "Bone")):
                            continue

                        if blBoneName not in blValidBones:
                            blValidBones[blBoneName] = blBone
                        else:
                            self.report({ 'ERROR' }, "GZRS2: ELU export requires unique names for all bones across all connected armatures!")
                            return { 'CANCELLED' }

            blObjs.append(object)
        elif object.type != 'ARMATURE':
            invalidCount += 1

    if not foundValid:
        self.report({ 'ERROR' }, "GZRS2: ELU export requires objects of type MESH or EMPTY!")
        return { 'CANCELLED' }

    if invalidCount > 0:
        self.report({ 'WARNING' }, f"GZRS2: ELU export skipped { invalidCount } invalid objects...")

    if len(blArmatureObjs) > 1:
        self.report({ 'WARNING' }, f"GZRS2: ELU export detected multiple armatures! This scenerio is untested and may not be successful!")

    blObjs = tuple(blObjs)
    blArmatureObjs = tuple(blArmatureObjs)

    eluObjByName = {}

    eluMeshObjs = []
    eluEmptyBones = []

    eluMatrices = []
    eluInvMatrices = []

    eluBoneIDs = {}

    m = 0

    # Non-bone meshes first
    for blObj in blObjs:
        meshName = blObj.name

        if meshName in blValidBones:
            continue

        eluObjByName[meshName] = blObj

        eluMeshObjs.append(blObj)

        matrixWorld = blObj.matrix_world.copy()
        eluMatrices.append(matrixWorld)
        eluInvMatrices.append(matrixWorld.inverted())

        m += 1

    # Bone meshes second
    for blObj in blObjs:
        meshName = blObj.name

        if not meshName in blValidBones:
            continue

        eluObjByName[meshName] = blObj

        eluMeshObjs.append(blObj)

        matrixWorld = blObj.matrix_world.copy()
        eluMatrices.append(matrixWorld)
        eluInvMatrices.append(matrixWorld.inverted())

        eluBoneIDs[meshName] = m

        m += 1

    # Remaining bones last
    for blArmatureObj in blArmatureObjs:
        for blBone in blArmatureObj.data.bones:
            boneName = blBone.name

            if not boneName in blValidBones:
                continue

            if boneName in eluBoneIDs:
                continue

            eluObjByName[boneName] = blBone

            eluEmptyBones.append(blBone)

            matrixWorld = blArmatureObj.matrix_world @ blBone.matrix_local @ reorientLocal
            eluMatrices.append(matrixWorld)
            eluInvMatrices.append(matrixWorld.inverted())

            eluBoneIDs[boneName] = m

            m += 1

    meshCount = m

    blMats = set()
    matSets = {}

    for eluMeshObj in eluMeshObjs:
        if eluMeshObj.type != 'EMPTY':
            for blMatSlot in eluMeshObj.material_slots:
                blMat = blMatSlot.material

                if blMat is not None:
                    blMats.add(blMat)
                    matSets.setdefault(blMat.gzrs2.matID, set()).add(blMat.gzrs2.subMatID)

    blMats = list(blMats)

    # Ensure all sub-materials have a base
    for matID, subMatIDs in matSets.items():
        if -1 not in subMatIDs:
            blMats.append({
                'isPlaceholder': None,
                'gzrs2': {
                    'matID': matID,
                    'isBase': True,
                    'subMatID': -1,
                    'subMatCount': max(subMatIDs) + 1 }})
            self.report({ 'WARNING' }, f"GZRS2: ELU export found sub-materials with no base! A placeholder will be included for id: { matID }")

    blMats = tuple(sorted(blMats, key = lambda x: (x['gzrs2']['matID'], x['gzrs2']['subMatID'])))

    matCount = len(blMats)

    if state.logEluMats and matCount > 0:
        print()
        print("=========  Elu Materials  =========")
        print()

    eluMats = []

    maxPathLength = ELU_NAME_LENGTH if version <= ELU_5005 else ELU_PATH_LENGTH

    for m, blMat in enumerate(blMats):
        matID = blMat['gzrs2']['matID']
        isBase = blMat['gzrs2']['isBase']
        subMatID = blMat['gzrs2']['subMatID']
        subMatCount = blMat['gzrs2']['subMatCount']

        ambient = (0.588235, 0.588235, 0.588235, 1.0)
        diffuse = (0.588235, 0.588235, 0.588235, 1.0)
        specular = (0.9, 0.9, 0.9, 1.0)
        power = 0.0

        texpath = ''
        alphapath = ''

        twosided = False
        additive = False
        alphatest = 0
        useopacity = False

        if 'isPlaceholder' not in blMat:
            matName = blMat.name
            tree = blMat.node_tree
            links = tree.links.values()
            nodes = tree.nodes

            ambient = (blMat.gzrs2.ambient[0], blMat.gzrs2.ambient[1], blMat.gzrs2.ambient[2], 1.0)
            diffuse = (blMat.gzrs2.diffuse[0], blMat.gzrs2.diffuse[1], blMat.gzrs2.diffuse[2], 1.0)
            specular = (blMat.gzrs2.specular[0], blMat.gzrs2.specular[1], blMat.gzrs2.specular[2], 1.0)

            output          = getShaderNodeByID(self, nodes, 'ShaderNodeOutputMaterial')
            shader          = getShaderNodeByID(self, nodes, 'ShaderNodeBsdfPrincipled')
            add             = getShaderNodeByID(self, nodes, 'ShaderNodeAddShader')
            transparent     = getShaderNodeByID(self, nodes, 'ShaderNodeBsdfTransparent')
            clip            = getShaderNodeByID(self, nodes, 'ShaderNodeMath')

            shaderValid         = False if shader       is not None     else None
            addValid            = False if add          is not None     else None
            transparentValid    = False if transparent  is not None     else None
            clipValid           = False if clip         is not None     else None

            for link in links:
                if link.is_hidden or not link.is_valid:
                    continue

                if      shaderValid         == False    and link.from_socket == shader.outputs[0]       and link.to_socket == output.inputs[0]:     shaderValid         = True
                elif    addValid            == False    and link.from_socket == add.outputs[0]          and link.to_socket == output.inputs[0]:     addValid            = True
                elif    transparentValid    == False    and link.from_socket == transparent.outputs[0]  and link.to_socket == add.inputs[1]:        transparentValid    = True
                elif    clipValid           == False    and link.from_socket == clip.outputs[0]         and link.to_socket == shader.inputs[4]:     clipValid           = True

            for link in links:
                if link.is_hidden or not link.is_valid:
                    continue

                if addValid and transparentValid        and link.from_socket == shader.outputs[0]       and link.to_socket == add.inputs[0]:        shaderValid = True

            if clipValid and clip.operation != 'GREATER_THAN':
                clipValid = False

            if not shaderValid:
                self.report({ 'ERROR' }, f"GZRS2: Invalid shader node in ELU material! Check the GitHub page for what makes a valid ELU material! { matID }, { matName }")
                return { 'CANCELLED' }

            bsdfPower = (1 - shader.inputs[2].default_value) * 100 # Roughness
            if version <= ELU_5002:
                power = 20 if bsdfPower == 0 else bsdfPower
            else:
                power = bsdfPower / 100

            texture = None
            emission = None
            alpha = None

            for link in links:
                if link.is_hidden or not link.is_valid:
                    continue

                node = link.from_node

                if link.to_node == shader and isValidEluImageNode(node, link.is_muted):
                    if link.from_socket == node.outputs[0] and link.to_socket == shader.inputs[0]:      texture     = node
                    if link.from_socket == node.outputs[0] and link.to_socket == shader.inputs[26]:     emission    = node
                    if link.from_socket == node.outputs[1] and link.to_socket == shader.inputs[4]:      alpha       = node

            if texture is not None:
                if texture.label == '':
                    texpath = makePathExtSingle(os.path.basename(texture.image.filepath))
                else:
                    texpath = makeRS2DataPath(texture.label)

                    if texpath == False:
                        self.report({ 'ERROR' }, f"GZRS2: Unable to determine data path for texture in ELU material! Check the GitHub page for a list of valid data subdirectories! { matID }, { matName }, { texture.label }")
                        return { 'CANCELLED' }

                if len(texpath) >= maxPathLength:
                    self.report({ 'ERROR' }, f"GZRS2: Data path for texture has too many characters! Max length is 40 for versions <= ELU_5005 and 256 for everything above! { matID }, { matName }, { texpath }")
                    return { 'CANCELLED' }
            else: texpath = ''

            if alpha is not None:
                if alpha.label == '':
                    alphapath = makePathExtSingle(os.path.basename(alpha.image.filepath))
                else:
                    alphapath = makeRS2DataPath(alpha.label)

                    if alphapath == False:
                        self.report({ 'ERROR' }, f"GZRS2: Unable to determine data path for texture in ELU material! Check the GitHub page for a list of valid data subdirectories! { matID }, { matName }, { texture.label }")
                        return { 'CANCELLED' }

                if len(alphapath) > maxPathLength:
                    self.report({ 'ERROR' }, f"GZRS2: Data path for texture has too many characters! Max length is 40 for versions <= ELU_5005 and 256 for everything above! { matID }, { matName }, { alphapath }")
                    return { 'CANCELLED' }
            else: alphapath = ''

            alphatest = int(min(max(0, clip.inputs[1].default_value), 1) * 255) if clipValid else 0
            useopacity = alpha is not None
            additive = blMat.surface_render_method == 'BLENDED' and addValid and transparentValid and emission is not None
            twosided = not blMat.use_backface_culling

        if state.logEluMats:
            print(f"===== Material { m } =====")
            print(f"Mat ID:             { matID }")
            print(f"Sub Mat ID:         { subMatID }")
            print()
            print("Ambient:            ({:>5.03f}, {:>5.03f}, {:>5.03f}, {:>5.03f})".format(*ambient))
            print("Diffuse:            ({:>5.03f}, {:>5.03f}, {:>5.03f}, {:>5.03f})".format(*diffuse))
            print("Specular:           ({:>5.03f}, {:>5.03f}, {:>5.03f}, {:>5.03f})".format(*specular))
            print(f"Power:              { bsdfPower }")
            print()
            print(f"Sub Mat Count:      { subMatCount }")
            print(f"Texture path:       { texpath }")
            print(f"Alpha path:         { alphapath }")
            print()
            print(f"Two-sided:          { twosided }")
            print(f"Additive:           { additive }")
            print(f"Alpha Test:         { alphatest }")
            print(f"Use Opacity:        { useopacity }")
            print()

        eluMats.append(EluMaterialExport(matID, subMatID,
                                         ambient, diffuse, specular, power,
                                         subMatCount, texpath, alphapath,
                                         twosided, additive, alphatest))

    eluMats = tuple(eluMats)
    usesDummies = False
    totalSlotIDs = set()
    matIDs = set()
    weightIDs = set()
    weightNames = set()

    if state.logEluMeshNodes and meshCount > 0:
        print()
        print("=========  Elu Mesh Nodes  ========")
        print()

    eluMatrices = tuple(eluMatrices)
    eluInvMatrices = tuple(eluInvMatrices)

    eluMeshes = []

    m = 0

    for eluMeshObj in eluMeshObjs:
        meshName = eluMeshObj.name
        parentName = ''

        valid = True

        if eluMeshObj.parent is not None:
            if (eluMeshObj.parent_type == 'OBJECT' and
                eluMeshObj.parent.name in eluObjByName):
                    parentName = eluMeshObj.parent.name
            elif (eluMeshObj.parent_type == 'BONE' and
                  eluMeshObj.parent in blArmatureObjs and
                  eluMeshObj.parent_bone in blValidBones):
                    eluBone = blValidBones[eluMeshObj.parent_bone]

                    if eluBone.parent is not None:
                        parentName = eluBone.parent.name

                        if not parentName in blValidBones:
                            valid = False
            else:
                valid = False

        if not valid:
            self.report({ 'ERROR' }, f"GZRS2: Mesh object with an invalid parent! { meshName }, { parentName }")
            return { 'CANCELLED' }

        if meshName == parentName:
            self.report({ 'ERROR' }, f"GZRS2: Tried to parent a mesh object to itself! { meshName }")
            return { 'CANCELLED' }

        worldMatrix = eluMatrices[m]
        transform = reorientWorld @ worldMatrix
        apScale, rotAA, scaleAA, etcMatrix = calcEtcData(version, transform) # TODO

        if eluMeshObj.type == 'MESH':
            blMesh = eluMeshObj.data
            uvLayer1 = blMesh.uv_layers[0] if len(blMesh.uv_layers) > 0 else None
            color1 = blMesh.color_attributes[0] if len(blMesh.color_attributes) > 0 else None
            vertexGroups = eluMeshObj.vertex_groups if len(eluMeshObj.vertex_groups) > 0 else None
            blArmatureObj, blArmature = getValidArmature(self, eluMeshObj, state)

            hasUV1s = uvLayer1 is not None
            hasColors = color1 is not None
            hasVGroups = vertexGroups is not None and blArmatureObj in blArmatureObjs and blArmature is not None

            if hasColors and (color1.data_type != 'FLOAT_COLOR' or color1.domain != 'POINT'):
                self.report({ 'ERROR' }, f"GZRS2: Mesh with invalid color attribute! Colors must be stored as per-vertex float data! { meshName }")
                return { 'CANCELLED' }

            vertexCount = len(blMesh.vertices)
            vertices = tuple(vertex.co.copy() for vertex in blMesh.vertices)
            faceCount = len(blMesh.loop_triangles)
            faces = []
            slotIDs = set()

            useCustomNormals = blMesh.has_custom_normals

            for triangle in blMesh.loop_triangles:
                indices = tuple(reversed(triangle.vertices))
                uv1s = tuple(reversed(tuple(uvLayer1.uv[triangle.loops[i]].vector.copy() for i in range(3)))) if hasUV1s else (Vector((0, 0)), Vector((0, 0)), Vector((0, 0)))
                slotID = triangle.material_index
                slotIDs.add(slotID)

                if state.logEluMeshNodes:
                    totalSlotIDs.add(slotID)

                if version >= ELU_5005:
                    normal = triangle.normal.copy()
                    normals = tuple(reversed(tuple(blMesh.loops[triangle.loops[i]].normal.copy() for i in range(3)))) if useCustomNormals else (normal.copy(), normal.copy(), normal.copy())
                else:
                    normal = None
                    normals = None

                faces.append(EluFaceExport(indices, uv1s, slotID, normal, normals))

            faces = tuple(faces)
            slotIDs = tuple(sorted(slotIDs))

            if state.logEluMeshNodes and vertexCount == 0 or faceCount == 0:
                usesDummies = True

            if version >= ELU_5005 and hasColors:
                colorCount = vertexCount
                colors = tuple(color1.data[v].color[:3] for v in range(vertexCount))
            else:
                colorCount = 0
                colors = ()

            matID = None

            for blMatSlot in eluMeshObj.material_slots:
                if blMatSlot.material is None:
                    continue

                if matID == None:
                    matID = blMatSlot.material.gzrs2.matID
                elif matID != blMatSlot.material.gzrs2.matID:
                    self.report({ 'ERROR' }, f"GZRS2: Mesh with two different material IDs! { meshName }")
                    return { 'CANCELLED' }

            if matID == None:
                matID = 0

            if state.logEluMeshNodes:
                matIDs.add(matID)

            if hasVGroups:
                vgroupLookup = tuple(v.groups for v in blMesh.vertices)
                weightCount = len(vgroupLookup)
                weights = []

                skippedBoneNames = set()

                for v, vgroupInfos in enumerate(vgroupLookup):
                    pairs = []
                    vertexWorld = worldMatrix @ vertices[v]

                    for vgroupInfo in vgroupInfos:
                        boneName = vertexGroups[vgroupInfo.group].name

                        if not boneName in blValidBones:
                            skippedBoneNames.add(boneName)
                            continue

                        pairs.append((vgroupInfo.weight, boneName))

                    degree = len(pairs)
                    for _ in range(ELU_PHYS_KEYS - degree): pairs.append((0.0, ''))

                    pairs = sorted(pairs, reverse = True)[:ELU_PHYS_KEYS]
                    total = sum(pair[0] for pair in pairs)

                    boneNames = tuple(pair[1] for pair in pairs)
                    values = tuple(pair[0] / total for pair in pairs) if total != 0.0 else tuple(pair[0] for pair in pairs)
                    meshIDs = tuple(eluBoneIDs[boneName] if boneName != '' else 0 for boneName in boneNames)
                    offsets = tuple(eluInvMatrices[meshID] @ vertexWorld if meshID != 0 else Vector((0, 0, 0)) for meshID in meshIDs)
                    degree = min(ELU_PHYS_KEYS, degree)

                    weights.append(EluWeightExport(boneNames, values, meshIDs, degree, offsets))

                for boneName in skippedBoneNames:
                    self.report({ 'WARNING' }, f"GZRS2: ELU export skipping a vertex group with no corresponding bone: { meshName }, { boneName }")

                weights = tuple(weights)
            else:
                weightCount = 0
                weights = ()
        else:
            if state.logEluMeshNodes:
                usesDummies = True

            vertexCount = 0
            vertices = ()
            faceCount = 0
            faces = ()
            slotIDs = ()
            colorCount = 0
            colors = ()
            matID = 0
            weightCount = 0
            weights = ()

        m += 1
        eluMeshes.append(EluMeshNodeExport(meshName, parentName, transform,
                                           apScale, rotAA, scaleAA, etcMatrix,
                                           vertexCount, vertices, faceCount, faces,
                                           colorCount, colors, matID,
                                           weightCount, weights, slotIDs))

    for eluBone in eluEmptyBones:
        boneName = eluBone.name
        parentName = ''

        if eluBone.parent is not None:
            parentName = eluBone.parent.name

            if not parentName in blValidBones:
                self.report({ 'ERROR' }, f"GZRS2: ELU export found a bone with an invalid parent! { boneName }, { parentName }")
                return { 'CANCELLED' }

        if boneName == parentName:
            self.report({ 'ERROR' }, f"GZRS2: ELU export tried to parent a bone to itself! { boneName }")
            return { 'CANCELLED' }

        transform = reorientWorld @ eluMatrices[m]
        apScale, rotAA, scaleAA, etcMatrix = calcEtcData(version, transform) # TODO

        m += 1
        eluMeshes.append(EluMeshNodeExport(boneName, parentName, transform,
                                            apScale, rotAA, scaleAA, etcMatrix,
                                            0, (), 0, (), 0, (), 0, 0, ()))

    if m != meshCount:
        self.report({ 'ERROR' }, f"GZRS2: ELU export mesh count did not match after second pass! { m }, { meshCount }")
        return { 'CANCELLED' }

    eluMeshes = tuple(eluMeshes)

    if state.logEluMeshNodes:
        for m, eluMesh in enumerate(eluMeshes):
            print(f"===== Mesh { m } =====")
            print(f"Mesh Name:          { eluMesh.meshName }")
            print(f"Parent Name:        { eluMesh.parentName }")
            print("World Matrix:       ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*eluMatrices[m][0]))
            print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*eluMatrices[m][1]))
            print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*eluMatrices[m][2]))
            print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*eluMatrices[m][3]))
            print()

            output = "Vertices:           {:<6d}".format(eluMesh.vertexCount)
            output += "      Min: ({:>5.02f}, {:>5.02f}, {:>5.02f})     Max: ({:>5.02f}, {:>5.02f}, {:>5.02f})".format(*vecArrayMinMax(eluMesh.vertices, 3)) if eluMesh.vertexCount > 0 else ''
            print(output)
            if state.logVerboseIndices and eluMesh.vertexCount > 0:
                print()
                for pos in eluMesh.vertices:
                    print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*pos))
                print()

            print(f"Faces:              { eluMesh.faceCount }")
            if state.logVerboseIndices and eluMesh.faceCount > 0:
                print()
                for face in eluMesh.faces:
                    print("                     {:>4}, {:>4}, {:>4}".format(*face.indices))
                print()
            print("Slot IDs:           {{{}}}".format(', '.join(map(str, eluMesh.slotIDs))))

            uv1s = tuple(face.uv1s[i] for face in eluMesh.faces for i in range(3))
            output = "UV1s:               {:<6d}".format(eluMesh.faceCount * 3)
            output += "      Min: ({:>5.02f}, {:>5.02f})            Max: ({:>5.02f}, {:>5.02f})".format(*vecArrayMinMax(uv1s, 2)) if eluMesh.faceCount * 3 > 0 else ''
            print(output)

            if version >= ELU_5005:
                normals = tuple(face.normals[i] for face in eluMesh.faces for i in range(3))
                output = "Normals:            {:<6d}".format(eluMesh.faceCount * 3)
                output += "      Min: ({:>5.02f}, {:>5.02f}, {:>5.02f})     Max: ({:>5.02f}, {:>5.02f}, {:>5.02f})".format(*vecArrayMinMax(normals, 3)) if eluMesh.faceCount * 3 > 0 else ''
                print(output)

            print(f"Is Dummy:           { eluMesh.vertexCount == 0 or eluMesh.faceCount == 0 }")
            print()

            output = "Colors:             {:<6d}".format(eluMesh.colorCount)
            output += "      Min: ({:>5.02f}, {:>5.02f}, {:>5.02f})     Max: ({:>5.02f}, {:>5.02f}, {:>5.02f})".format(*vecArrayMinMax(eluMesh.colors, 3)) if eluMesh.colorCount > 0 else ''
            print(output)

            print(f"Material ID:        { eluMesh.matID }")

            if eluMesh.weightCount > 0:
                minWeightValue = float('inf')
                maxWeightValue = float('-inf')
                minWeightID = -1
                maxWeightID = -1
                minWeightName = 'ERROR'
                maxWeightName = 'ERROR'

                if state.logVerboseWeights:
                    print()

                for weight in eluMesh.weights:
                    degree = weight.degree
                    values = weight.values
                    meshIDs = weight.meshIDs
                    offsets = weight.offsets
                    boneNames = weight.meshNames

                    for d in range(degree):
                        weightValue = values[d]
                        weightID = meshIDs[d]
                        weightOffset = offsets[d] * (100 if state.convertUnits else 1)
                        weightName = boneNames[d]

                        if weightName == '':
                            continue

                        weightIDs.add(weightID)
                        weightNames.add(weightName)

                        if weightValue < minWeightValue:
                            minWeightValue = weightValue
                            minWeightID = weightID
                            minWeightName = weightName

                        if weightValue > maxWeightValue:
                            maxWeightValue = weightValue
                            maxWeightID = weightID
                            maxWeightName = weightName

                        if state.logVerboseWeights:
                            print("Weight:             {:>1d}, {:>6.03f}, {:>2d}, {:<16s}    ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(degree, weightValue, weightID, weightName, *weightOffset))

                if state.logVerboseWeights:
                    print()

            output = "Weights:            {:<6d}".format(eluMesh.weightCount)
            output += "      Min:  {:>5.02f}, {:>2d}, {:<10s}    Max:  {:>5.02f}, {:>2d}, {:<10s}".format(minWeightValue, minWeightID, minWeightName, maxWeightValue, maxWeightID, maxWeightName) if eluMesh.weightCount > 0 else ''
            print(output)
            print()

        print("===== Mesh Summary =====")
        print()

        print(f"Uses Dummies:       { usesDummies }")
        print(f"Slot IDs:           { totalSlotIDs }")
        print(f"Material IDs:       { matIDs }")
        print(f"Weight IDs:         { weightIDs }")
        print(f"Weight Names:       { weightNames }")
        print()

    if state.logEluHeaders or state.logEluMats or state.logEluMeshNodes:
        print("===================  Write Elu  ===================")
        print()

    if state.logEluHeaders:
        print(f"Path:               { elupath }")
        print(f"ID:                 { hex(id) }")
        print(f"Version:            { hex(version) }")
        print(f"Mat Count:          { matCount }")
        print(f"Mesh Count:         { meshCount }")
        print()

    if id != ELU_ID or version not in ELU_VERSIONS:
        self.report({ 'ERROR' }, f"GZRS2: ELU header invalid! { hex(id) }, { hex(version) }")
        return { 'CANCELLED' }

    if version not in ELU_EXPORT_VERSIONS:
        self.report({ 'ERROR' }, f"GZRS2: Exporting this ELU version is not supported yet! { elupath }, { hex(version) }")
        return { 'CANCELLED' }

    if os.path.isfile(elupath):
        shutil.copy2(elupath, os.path.join(directory, filename + "_backup") + '.' + splitname[1])

    file = io.open(elupath, 'wb')

    writeUInt(file, id)
    writeUInt(file, version)
    writeInt(file, matCount)
    writeInt(file, meshCount)

    for eluMat in eluMats:
        writeInt(file, eluMat.matID)
        writeInt(file, eluMat.subMatID)

        writeVec4(file, eluMat.ambient)
        writeVec4(file, eluMat.diffuse)
        writeVec4(file, eluMat.specular)
        writeFloat(file, eluMat.power)

        writeUInt(file, eluMat.subMatCount)

        if version <= ELU_5005:
            writeString(file, eluMat.texpath, ELU_NAME_LENGTH)
            writeString(file, eluMat.alphapath, ELU_NAME_LENGTH)
        else:
            writeString(file, eluMat.texpath, ELU_PATH_LENGTH)
            writeString(file, eluMat.alphapath, ELU_PATH_LENGTH)

        if version >= ELU_5002: writeBool32(file, eluMat.twosided)
        if version >= ELU_5004: writeBool32(file, eluMat.additive)
        if version == ELU_5007: writeUInt(file, eluMat.alphatest)

    for eluMesh in eluMeshes:
        writeString(file, eluMesh.meshName, ELU_NAME_LENGTH)
        writeString(file, eluMesh.parentName, ELU_NAME_LENGTH)

        writeTransform(file, eluMesh.transform, state.convertUnits, True)

        if version >= ELU_5001:
            writeVec3(file, eluMesh.apScale)

        if version >= ELU_5003:
            writeVec4(file, eluMesh.rotAA) # TODO: coordinates or directions?
            writeVec4(file, eluMesh.scaleAA) # TODO: coordinates or directions?
            writeTransform(file, eluMesh.etcMatrix, state.convertUnits, True)

        writeUInt(file, eluMesh.vertexCount)
        writeCoordinateArray(file, eluMesh.vertices, state.convertUnits, True)
        writeUInt(file, eluMesh.faceCount)

        if eluMesh.faceCount > 0:
            for face in eluMesh.faces:
                writeUIntArray(file, face.indices)

                # zero-fills unused z-coordinates
                writeUV3(file, face.uv1s[0])
                writeUV3(file, face.uv1s[1])
                writeUV3(file, face.uv1s[2])

                writeInt(file, face.slotID)

                if version >= ELU_5002:
                    writeInt(file, 0) # unused id

            if version >= ELU_5005:
                for face in eluMesh.faces:
                    writeDirection(file, face.normal, True)
                    writeDirectionArray(file, face.normals, True)

        if version >= ELU_5005:
            writeUInt(file, eluMesh.colorCount)
            writeVec3Array(file, eluMesh.colors)

        writeInt(file, eluMesh.matID)
        writeUInt(file, eluMesh.weightCount)

        for weight in eluMesh.weights:
            for k in range(ELU_PHYS_KEYS):
                writeString(file, weight.meshNames[k], ELU_NAME_LENGTH)

            writeFloatArray(file, weight.values)

            writeUIntArray(file, weight.meshIDs)
            writeUInt(file, weight.degree)
            writeCoordinateArray(file, weight.offsets, state.convertUnits, True)

    file.close()

    return { 'FINISHED' }
