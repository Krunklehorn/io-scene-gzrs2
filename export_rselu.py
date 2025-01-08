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

import os, io

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
    version, maxPathLength = getEluExportConstants()

    if id != ELU_ID or version not in ELU_VERSIONS:
        self.report({ 'ERROR' }, f"GZRS2: ELU header invalid! { hex(id) }, { hex(version) }")
        return { 'CANCELLED' }

    if version not in ELU_EXPORT_VERSIONS:
        self.report({ 'ERROR' }, f"GZRS2: Exporting this ELU version is not supported yet! { elupath }, { hex(version) }")
        return { 'CANCELLED' }

    objects = getFilteredObjects(context, state)

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

        if object.type in ('EMPTY', 'MESH'):
            foundValid = True

            if object.type == 'MESH':
                object.update_from_editmode()

                blArmatureObj, blArmature = getValidArmature(self, object, state)

                if blArmatureObj not in blArmatureObjs and blArmature is not None:
                    blArmatureObj.update_from_editmode()
                    blArmatureObjs.append(blArmatureObj)

                    for blBone in blArmature.bones:
                        blBoneName = blBone.name

                        if not blBoneName.startswith(('Bip', 'Bone', 'Dummy')):
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
        self.report({ 'ERROR' }, "GZRS2: ELU export requires objects of type EMPTY or MESH!")
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

    worldMatrices = []
    worldInvMatrices = []
    worldMatrixByName = {}

    eluBoneIDs = {}

    m = 0

    # Non-bone meshes first
    for blObj in blObjs:
        objName = blObj.name

        if objName in blValidBones:
            continue

        eluObjByName[objName] = blObj

        eluMeshObjs.append(blObj)

        matrixWorld = blObj.matrix_world
        worldMatrices.append(matrixWorld)
        worldInvMatrices.append(matrixWorld.inverted())
        worldMatrixByName[objName] = matrixWorld

        m += 1

    # Bone meshes second
    for blObj in blObjs:
        objName = blObj.name

        if objName not in blValidBones:
            continue

        eluObjByName[objName] = blObj

        eluMeshObjs.append(blObj)

        matrixWorld = blObj.matrix_world
        worldMatrices.append(matrixWorld)
        worldInvMatrices.append(matrixWorld.inverted())
        worldMatrixByName[objName] = matrixWorld

        eluBoneIDs[objName] = m

        m += 1

    # Remaining bones last
    for blArmatureObj in blArmatureObjs:
        for blBone in blArmatureObj.data.bones:
            boneName = blBone.name

            if boneName not in blValidBones:
                continue

            if boneName in eluBoneIDs:
                continue

            eluObjByName[boneName] = blBone

            eluEmptyBones.append(blBone)

            matrixWorld = blArmatureObj.matrix_world @ blBone.matrix_local @ reorientLocal
            worldMatrices.append(matrixWorld)
            worldInvMatrices.append(matrixWorld.inverted())
            worldMatrixByName[boneName] = matrixWorld

            eluBoneIDs[boneName] = m

            m += 1

    meshCount = m

    eluMeshObjs = tuple(eluMeshObjs)
    eluEmptyBones = tuple(eluEmptyBones)

    worldMatrices = tuple(worldMatrices)
    worldInvMatrices = tuple(worldInvMatrices)

    blMats = getStrictMaterials(self, eluMeshObjs)
    matCount = len(blMats)

    if state.logEluMats and matCount > 0:
        print()
        print("=========  Elu Materials  =========")
        print()

    eluMats = []

    for m, blMat in enumerate(blMats):
        matID = blMat.gzrs2.matID
        isBase = blMat.gzrs2.isBase
        subMatID = blMat.gzrs2.subMatID
        subMatCount = blMat.gzrs2.subMatCount

        ambient = (0.588235, 0.588235, 0.588235, 1.0)
        diffuse = (0.588235, 0.588235, 0.588235, 1.0)
        specular = (0.9, 0.9, 0.9, 1.0)
        exponent = 0.0

        texpath = ''
        alphapath = ''

        twosided = False
        additive = False
        alphatest = 0
        useopacity = False

        if not isinstance(blMat, RSELUExportMaterialPlaceholder):
            matName = blMat.name
            tree, links, nodes = getMatTreeLinksNodes(blMat)

            shader, output, info, transparent, mix, clip, add, lightmix = getRelevantShaderNodes(nodes)
            shaderValid, _, transparentValid, _, clipValid, addValid, lightmixValid = checkShaderNodeValidity(shader, output, info, transparent, mix, clip, add, lightmix, links)

            if not shaderValid:
                self.report({ 'ERROR' }, f"GZRS2: Invalid shader node in ELU material! Check the GitHub page for what makes a valid ELU material! { matID }, { matName }")
                return { 'CANCELLED' }

            ambient = (blMat.gzrs2.ambient[0], blMat.gzrs2.ambient[1], blMat.gzrs2.ambient[2], 1.0)
            diffuse = (blMat.gzrs2.diffuse[0], blMat.gzrs2.diffuse[1], blMat.gzrs2.diffuse[2], 1.0)
            specular = (blMat.gzrs2.specular[0], blMat.gzrs2.specular[1], blMat.gzrs2.specular[2], 1.0)
            exponent = blMat.gzrs2.exponent

            texture, emission, alpha = getLinkedImageNodes(shader, shaderValid, links, clip, clipValid, lightmix, lightmixValid)
            texpath = getValidImageNodePath(self, texture, maxPathLength, matID, matName)
            alphapath = getValidImageNodePath(self, alpha, maxPathLength, matID, matName)

            if texpath is None or alphapath is None:
                return { 'CANCELLED' }

            twosided, additive, alphatest, usealphatest, useopacity = getMatFlagsRender(blMat, clip, addValid, clipValid, emission, alpha)

            texBase, texName, texExt, texDir = decomposePath(texpath)
            isAniTex = checkIsAniTex(texBase)
            success, frameCount, frameSpeed, frameGap = processAniTexParameters(isAniTex, texName)

            if not success:
                return { 'CANCELLED' }

        if state.logEluMats:
            print(f"===== Material { m } =====")
            print(f"Mat ID:             { matID }")
            print(f"Sub Mat ID:         { subMatID }")
            print()
            print("Ambient:            ({:>5.03f}, {:>5.03f}, {:>5.03f}, {:>5.03f})".format(*ambient))
            print("Diffuse:            ({:>5.03f}, {:>5.03f}, {:>5.03f}, {:>5.03f})".format(*diffuse))
            print("Specular:           ({:>5.03f}, {:>5.03f}, {:>5.03f}, {:>5.03f})".format(*specular))
            print(f"Exponent:           { exponent }")
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

            if texpath:
                print(f"Texture Base:       { texBase }")
                print(f"Name:               { texName }")
                print(f"Extension:          { texExt }")
                print(f"Directory:          { texDir }")
                print()
                print(f"Is Animated:        { isAniTex }")

                if isAniTex:
                    print(f"Frame Count:        { frameCount }")
                    print(f"Frame Speed:        { frameSpeed }")
                    print(f"Frame Gap:          { frameGap }")

                print()

        eluMats.append(EluMaterialExport(matID, subMatID,
                                         ambient, diffuse, specular, exponent,
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
                    parentName = eluMeshObj.parent_bone

                    if meshName == parentName:
                        parentBone = blValidBones[parentName]

                        if parentBone in eluEmptyBones:
                            self.report({ 'ERROR' }, f"GZRS2: ELU export found a mesh object with a corresponding empty bone that didn't get skipped! { meshName }")
                            return { 'CANCELLED' }

                        parentParent = parentBone.parent
                        parentName = parentParent.name if parentParent is not None else ''
            else:
                valid = False

        if not valid:
            self.report({ 'ERROR' }, f"GZRS2: ELU export found a mesh object with an invalid parent! { meshName }, { parentName }")
            return { 'CANCELLED' }

        if meshName == parentName:
                self.report({ 'ERROR' }, f"GZRS2: ELU export tried to parent a mesh object to itself! { meshName }")
                return { 'CANCELLED' }

        worldMatrix = reorientWorld @ worldMatrices[m]
        parentWorld = worldMatrixByName.get(parentName) or Matrix.Identity(4)
        apScale, rotAA, stretchAA, etcMatrix = calcEtcData(worldMatrix, parentWorld)

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
            vertices = tuple(vertex.co for vertex in blMesh.vertices)
            faceCount = len(blMesh.loop_triangles)
            faces = []
            slotIDs = set()

            if vertexCount >= ELU_MAX_VERTEX or faceCount * 3 >= ELU_MAX_VERTEX:
                self.report({ 'ERROR' }, f"GZRS2: Mesh with too many vertices, maximum is { ELU_MAX_VERTEX }, must split mesh before continuing: { meshName }")
                return { 'CANCELLED' }

            useCustomNormals = blMesh.has_custom_normals

            for triangle in blMesh.loop_triangles:
                indices = tuple(reversed(triangle.vertices))
                uv1s = tuple(reversed(tuple(uvLayer1.uv[triangle.loops[i]].vector for i in range(3)))) if hasUV1s else (Vector((0, 0)), Vector((0, 0)), Vector((0, 0)))
                slotID = triangle.material_index
                slotIDs.add(slotID)

                if state.logEluMeshNodes:
                    totalSlotIDs.add(slotID)

                if version >= ELU_5005:
                    normal = triangle.normal
                    normals = tuple(reversed(tuple(blMesh.loops[triangle.loops[i]].normal for i in range(3)))) if useCustomNormals else (normal, normal, normal)
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
                colors = []

                for v in range(vertexCount):
                    color = color1.data[v].color
                    color = [color[0], color[1], color[2]]

                    for c in range(3):
                        if color[c] > 0.99: color[c] = 1.0
                        if color[c] < 0.01: color[c] = 0.0

                    colors.append(tuple(color))

                colors = tuple(colors)
            else:
                colorCount = 0
                colors = ()

            matID = None

            for blMatSlot in eluMeshObj.material_slots:
                if blMatSlot.material is None:
                    self.report({ 'ERROR' }, f"GZRS2: Mesh with empty material slot! { meshName }")
                    return { 'CANCELLED' }

                if matID is None:
                    matID = blMatSlot.material.gzrs2.matID
                elif matID != blMatSlot.material.gzrs2.matID:
                    self.report({ 'ERROR' }, f"GZRS2: Mesh with two different material IDs! { meshName }")
                    return { 'CANCELLED' }

            if matID is None:
                matID = 0

            if state.logEluMeshNodes:
                matIDs.add(matID)

            if hasVGroups:
                vgroupLookup = tuple(vertex.groups for vertex in blMesh.vertices)
                weightCount = len(vgroupLookup)
                weights = []

                skippedBoneNames = set()

                for v, vgroupInfos in enumerate(vgroupLookup):
                    pairs = []
                    vertexWorld = worldMatrix @ vertices[v]

                    for vgroupInfo in vgroupInfos:
                        boneName = vertexGroups[vgroupInfo.group].name

                        if boneName not in blValidBones:
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
                    offsets = tuple(worldInvMatrices[meshID] @ vertexWorld if meshID != 0 else Vector((0, 0, 0)) for meshID in meshIDs)
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
        eluMeshes.append(EluMeshNodeExport(meshName, parentName, worldMatrix,
                                           apScale, rotAA, stretchAA, etcMatrix,
                                           vertexCount, vertices, faceCount, faces,
                                           colorCount, colors, matID,
                                           weightCount, weights, slotIDs))

    for eluBone in eluEmptyBones:
        boneName = eluBone.name
        parentName = ''

        if eluBone.parent is not None:
            parentName = eluBone.parent.name

            if parentName not in blValidBones:
                self.report({ 'ERROR' }, f"GZRS2: ELU export found a bone with an invalid parent! { boneName }, { parentName }")
                return { 'CANCELLED' }

        if boneName == parentName:
            self.report({ 'ERROR' }, f"GZRS2: ELU export tried to parent a bone to itself! { boneName }")
            return { 'CANCELLED' }

        worldMatrix = reorientWorld @ worldMatrices[m]
        parentWorld = worldMatrixByName.get(parentName) or Matrix.Identity(4)
        apScale, rotAA, stretchAA, etcMatrix = calcEtcData(worldMatrix, parentWorld)

        m += 1
        eluMeshes.append(EluMeshNodeExport(boneName, parentName, worldMatrix,
                                           apScale, rotAA, stretchAA, etcMatrix,
                                           0, (), 0, (), 0, (), 0, 0, (), ()))

    if m != meshCount:
        self.report({ 'ERROR' }, f"GZRS2: ELU export mesh count did not match after second pass! { m }, { meshCount }")
        return { 'CANCELLED' }

    eluMeshes = tuple(eluMeshes)

    if state.logEluMeshNodes:
        for m, eluMesh in enumerate(eluMeshes):
            print(f"===== Mesh { m } =====")
            print(f"Mesh Name:          { eluMesh.meshName }")
            print(f"Parent Name:        { eluMesh.parentName }")
            print("World Matrix:       ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*eluMesh.transform[0]))
            print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*eluMesh.transform[1]))
            print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*eluMesh.transform[2]))
            print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*eluMesh.transform[3]))
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

    # Write ELU
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

    createBackupFile(elupath)

    with open(elupath, 'wb') as file:
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
            writeFloat(file, eluMat.exponent)

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

            writeTransform(file, eluMesh.transform, state.convertUnits, True) # TODO: swizzle

            if version >= ELU_5001:
                writeVec3(file, eluMesh.apScale) # TODO: swizzle

            if version >= ELU_5003:
                writeVec4(file, eluMesh.rotAA) # TODO: swizzle
                writeVec4(file, eluMesh.stretchAA) # TODO: swizzle
                writeTransform(file, eluMesh.etcMatrix, state.convertUnits, True) # TODO: swizzle

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

    return { 'FINISHED' }
