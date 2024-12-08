#####
# Most of the code is based on logic found in...
#
### GunZ 1
# - RAnimationFile.cpp
# - RAnimationDef.h
# - RAnimationNode.h
# - RMeshUtil.h/.cpp
# - RMeshFrame.cpp
# - MUtil.h
# - MCPlug2_Ani.cpp
# - el_mesh.cpp
#
# Please report maps and models with unsupported features to me on Discord: Krunk#6051
#####

import bpy, os, math

from contextlib import redirect_stdout
from mathutils import Vector, Matrix
from mathutils.kdtree import KDTree

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .readani_gzrs2 import *
from .lib_gzrs2 import *

def importAni(self, context):
    state = GZRS2State()

    state.convertUnits = self.convertUnits
    state.overwriteAction = self.overwriteAction
    state.selectedOnly = self.selectedOnly
    state.includeChildren = self.includeChildren and self.selectedOnly
    state.visibleOnly = self.visibleOnly

    if self.panelLogging:
        print()
        print("=======================================================================")
        print("===========================  RSANI Import  ============================")
        print("=======================================================================")
        print(f"== { self.filepath }")
        print("=======================================================================")
        print()

        state.logAniHeaders = self.logAniHeaders
        state.logAniNodes = self.logAniNodes

    anipath = self.filepath
    state.directory = os.path.dirname(anipath)
    state.filename = os.path.basename(anipath).split(os.extsep)[0]

    if readAni(self, anipath, state):
        return { 'CANCELLED' }

    bpy.ops.ed.undo_push()

    action = None
    actionName = state.filename

    if state.overwriteAction:   action = bpy.data.actions.get(actionName) or bpy.data.actions.new(actionName)
    else:                       action = bpy.data.actions.new(actionName)

    action.frame_end = state.aniMaxTick / ANI_TICKS_PER_FRAME
    action.use_cyclic = True
    action.use_frame_range = True

    bpy.context.scene.frame_set(0)

    aniType = type(state.aniNodes[0]) # We assume the entire list is homogeneous
    aniTypeEnum = ANI_TYPES_ENUM.get(aniType, aniType)
    aniTypePretty = ANI_TYPES_PRETTY.get(aniTypeEnum, aniTypeEnum)

    if state.overwriteAction:
        action.fcurves.clear()

    if aniType is AniNodeVertex:
        nodeMeshNames = tuple(node.meshName for node in state.aniNodes)
        blObjs = { object.name: object for object in getFilteredObjects(context, state) if object.name in nodeMeshNames and object.type == 'MESH'}

        bpy.ops.object.mode_set(mode = 'OBJECT')

        for node in state.aniNodes:
            if node.vertexKeyCount == 0:
                continue

            meshName = node.meshName
            blObj = blObjs.get(meshName)

            if blObj is None:
                if node.vertexKeyCount == 0:
                    continue

                self.report({ 'INFO' }, f"GZRS2: ANI import of type { aniTypePretty } failed to find a matching mesh, skipping: { meshName }")
                continue

            blObjAnimData = blObj.animation_data or blObj.animation_data_create()
            blObjAnimData.action = action

            bpy.context.view_layer.update()
            worldMatrixInv = blObj.matrix_world.inverted()

            worldPositions = [worldMatrixInv @ localPos for localPos in node.vertexPositions]

            blMesh = blObj.data
            blKeys = blMesh.shape_keys

            if blKeys is None:
                basisShape = blObj.shape_key_add(name = 'Basis', from_mix = False)
                blKeys = blMesh.shape_keys
            else:
                basisShape = blKeys.reference_key or blObj.shape_key_add(name = 'Basis', from_mix = False)

            blKeys.use_relative = False

            nodeVertexCount = node.vertexCount
            meshVertexCount = len(blMesh.vertices)

            if meshVertexCount != nodeVertexCount:
                self.report({ 'WARNING' }, f"GZRS2: ANI import of type { aniTypePretty } found a mesh whose vertex count did not match, the smaller count will be used, corruption may occur: { meshName }, { meshVertexCount }, { nodeVertexCount }")
                continue

            vertexCount = min(meshVertexCount, nodeVertexCount)
            vertexRange = []

            kZero = IndexOrNone(node.vertexTicks, 0) * vertexCount

            kdTree = KDTree(vertexCount)

            for v in range(vertexCount):
                kdTree.insert(blMesh.vertices[v].co, v)

            kdTree.balance()

            warnDuplicateIndex = False
            warnDistanceThreshold = False
            maxDist = 0.0

            for v in range(vertexCount):
                _, i, d = kdTree.find(worldPositions[kZero + v])

                if i in vertexRange:            warnDuplicateIndex = True
                elif d > ANI_VERTEX_THRESHOLD:  warnDistanceThreshold = True

                vertexRange.append((v, i))
                maxDist = max(maxDist, d)

            if warnDuplicateIndex:
                self.report({ 'WARNING' }, f"GZRS2: ANI import of type { aniTypePretty } indexed the same point more than once, corruption may occur: { meshName }")

            if warnDistanceThreshold:
                self.report({ 'WARNING' }, f"GZRS2: ANI import of type { aniTypePretty } indexed a point beyond the threshold, corruption may occur: { meshName }, { maxDist }")

            vertexRange = tuple(vertexRange)

            for k in range(node.vertexKeyCount):
                frame = int(round(node.vertexTicks[k] / ANI_TICKS_PER_FRAME))

                currShape = blObj.shape_key_add(name = f'ani{ frame }', from_mix = False)
                shapePoints = currShape.points

                for v, i in vertexRange:
                    shapePoints[i].co = worldPositions[k * vertexCount + v].copy()

                blKeys.eval_time = frame * 10
                blKeys.keyframe_insert(data_path = 'eval_time', frame = frame, group = meshName)

        print()
    elif aniType is AniNodeTM:
        blObjs = { object.name: object for object in getFilteredObjects(context, state) }

        # Ignore filter since objects have unique names anyways
        blArmatureObj = bpy.context.scene.objects.get(ANI_TM_ARMATURE_NAME)

        if blArmatureObj is not None:
            if blArmatureObj.type != 'ARMATURE':
                blArmatureObj.name = f'{ blArmatureObj.name }.001'
                blArmatureObj = None

        if blArmatureObj is None:
            blArmature = bpy.data.armatures.new(ANI_TM_ARMATURE_NAME)
            blArmatureObj = bpy.data.objects.new(ANI_TM_ARMATURE_NAME, blArmature)

            blArmatureObj.display_type = 'WIRE'
            blArmatureObj.show_in_front = True

            context.collection.objects.link(blArmatureObj)

            for viewLayer in context.scene.view_layers:
                viewLayer.objects.active = blArmatureObj

        blArmature = blArmatureObj.data

        reorientBone = Matrix.Rotation(math.radians(-90.0), 4, 'X')
        reorientWorld = Matrix.Rotation(math.radians(180.0), 4, 'X')

        bpy.context.view_layer.objects.active = blArmatureObj

        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.mode_set(mode = 'POSE')

        blPoseBones = blArmatureObj.pose.bones

        for blPoseBone in blPoseBones:
            blPoseBone.matrix_basis.identity()

        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.mode_set(mode = 'EDIT')

        blEditBones = blArmature.edit_bones

        blValidObjs = []

        for node in state.aniNodes:
            meshName = node.meshName
            blObj = blObjs.get(meshName)

            if blObj is None:
                if node.tmKeyCount == 0:
                    continue

                self.report({ 'INFO' }, f"GZRS2: ANI import of type { aniTypePretty } failed to find a matching object, skipping: { meshName }")
                continue

            blEditBone = blEditBones.get(meshName) or blArmature.edit_bones.new(meshName)
            blEditBone.matrix = Matrix.Identity(4)
            bpy.context.view_layer.update()

            blEditBone.tail = (0.0, 0.0, 0.1)
            blEditBone.matrix = blObj.matrix_world @ reorientBone

            blValidObjs.append(blObj)

        bpy.ops.object.mode_set(mode = 'OBJECT')

        for blObj in blValidObjs:
            transform = blObj.matrix_world

            blObj.parent = blArmatureObj
            blObj.parent_bone = blObj.name
            blObj.parent_type = 'BONE'

            blObj.matrix_world = transform

        blObj = blArmatureObj

        blObjAnimData = blObj.animation_data or blObj.animation_data_create()
        blObjAnimData.action = action

        bpy.ops.object.mode_set(mode = 'POSE')

        for node in state.aniNodes:
            meshName = node.meshName
            blPoseBone = blPoseBones.get(meshName)

            if blPoseBone is None:
                if node.tmKeyCount == 0:
                    continue

                self.report({ 'INFO' }, f"GZRS2: ANI import of type { aniTypePretty } failed to find a matching bone, skipping: { meshName }")
                continue

            blPoseBone.matrix_basis.identity()
            bpy.context.view_layer.update()

            firstMat = node.firstMat

            pathPrefix = f'pose.bones[\"{ meshName }\"].'
            locPath = pathPrefix + 'location'
            rotPath = pathPrefix + 'rotation_quaternion'
            scaPath = pathPrefix + 'scale'

            def applyWorldMat(frame, worldMat):
                nonlocal blPoseBone, meshName

                blPoseBone.matrix = worldMat @ reorientWorld
                bpy.context.view_layer.update()

                blObj.keyframe_insert(data_path = locPath, frame = frame, group = meshName)
                blObj.keyframe_insert(data_path = rotPath, frame = frame, group = meshName)
                blObj.keyframe_insert(data_path = scaPath, frame = frame, group = meshName)

            for k in range(node.tmKeyCount):
                frame = int(round(node.tmTicks[k] / ANI_TICKS_PER_FRAME))
                worldMat = node.tmMats[k]

                applyWorldMat(frame + 1, worldMat)

            blPoseBone.matrix = firstMat @ reorientWorld
            bpy.context.view_layer.update()

        bpy.ops.object.mode_set(mode = 'OBJECT')
    else:
        blObj = bpy.context.active_object

        if blObj is None or blObj.type != 'ARMATURE':
            self.report({ 'ERROR' }, f"GZRS2: ANI import of type { aniTypePretty } requires a selected armature as a reference!")
            return { 'CANCELLED' }

        blObjAnimData = blObj.animation_data or blObj.animation_data_create()
        blObjAnimData.action = action

        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.mode_set(mode = 'POSE')

        blPoseBones = blObj.pose.bones

        for blPoseBone in blPoseBones:
            if blPoseBone.parent is not None:
                break
        else:
            self.report({ 'WARNING' }, f"GZRS2: ANI import of type { aniTypePretty } performed on an armature with no parent-child hierarchy!")

        for blPoseBone in blPoseBones:
            blPoseBone.matrix_basis.identity()

        bpy.ops.object.mode_set(mode = 'OBJECT')

        bpy.context.view_layer.update()
        blObj.update_from_editmode()

        bpy.ops.object.mode_set(mode = 'EDIT')

        for blEditBone in blObj.data.edit_bones:
            blEditBone.use_connect = False

        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.mode_set(mode = 'POSE')

        reorientPose = Matrix.Rotation(math.radians(180.0), 4, 'Y') @ Matrix.Rotation(math.radians(90.0), 4, 'Z')

        poseMats = {}

        for node in state.aniNodes:
            meshName = node.meshName
            blPoseBone = blPoseBones.get(meshName)

            if blPoseBone is None:
                if node.posKeyCount == 0 and node.rotKeyCount == 0:
                        continue

                self.report({ 'INFO' }, f"GZRS2: ANI import of type { aniTypePretty } failed to find a matching bone, skipping: { meshName }")
                continue

            baseMat = node.baseMat
            poseMats[meshName] = baseMat
            parentWorld = poseMats[blPoseBone.parent.name] if blPoseBone.parent is not None else Matrix.Identity(4)

            pathPrefix = f'pose.bones[\"{ meshName }\"].'
            locPath = pathPrefix + 'location'
            rotPath = pathPrefix + 'rotation_quaternion'

            def applyPoseMat(frame, poseMat):
                nonlocal blObj, meshName, blPoseBone, locPath, rotPath

                blPoseBone.matrix = poseMat @ reorientPose
                bpy.context.view_layer.update()

                blObj.keyframe_insert(data_path = locPath, frame = frame, group = meshName)
                blObj.keyframe_insert(data_path = rotPath, frame = frame, group = meshName)

            if node.posKeyCount > 0 or node.rotKeyCount > 0:
                keyframeMats = {}

                for k in range(node.posKeyCount):
                    frame = int(round(node.posTicks[k] / ANI_TICKS_PER_FRAME))
                    keyframeMats[frame] = Matrix.Translation(node.posVectors[k])

                for k in range(node.rotKeyCount):
                    frame = int(round(node.rotTicks[k] / ANI_TICKS_PER_FRAME))
                    rotMat = node.rotQuats[k].to_matrix().to_4x4()

                    if frame in keyframeMats:
                        keyframeMats[frame] = keyframeMats[frame] @ rotMat
                    else:
                        parentLocalBaseMat = parentWorld.inverted() @ baseMat
                        parentLocalBaseTranslation = Matrix.Translation(parentLocalBaseMat.to_translation())
                        keyframeMats[frame] = parentLocalBaseTranslation @ rotMat

                for frame, worldMat in keyframeMats.items():
                    poseMat = parentWorld @ worldMat

                    # We assume that a 0 frame exists
                    if frame == 0:
                        poseMats[meshName] = poseMat

                    applyPoseMat(frame + 1, poseMat)
            applyPoseMat(0, baseMat)

        bpy.ops.object.mode_set(mode = 'OBJECT')

    return { 'FINISHED' }
