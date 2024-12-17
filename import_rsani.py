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

    context.scene.frame_set(0)

    aniType = type(state.aniNodes[0]) # We assume the entire list is homogeneous
    aniTypeEnum = ANI_TYPES_ENUM.get(aniType, aniType)
    aniTypePretty = ANI_TYPES_PRETTY.get(aniTypeEnum, aniTypeEnum)

    if aniType is not AniNodeTM:
        action = None
        actionName = state.filename

        if state.overwriteAction:   action = bpy.data.actions.get(actionName) or bpy.data.actions.new(actionName)
        else:                       action = bpy.data.actions.new(actionName)

        action.frame_end = state.aniMaxTick / ANI_TICKS_PER_FRAME
        action.use_cyclic = True
        action.use_frame_range = True
        action.fcurves.clear()

    if aniType is AniNodeVertex:
        nodeMeshNames = tuple(node.meshName for node in state.aniNodes)
        blValidObjs = { object.name: object for object in getFilteredObjects(context, state) if object.name in nodeMeshNames and object.type == 'MESH'}

        bpy.ops.object.mode_set(mode = 'OBJECT')

        for node in state.aniNodes:
            if node.vertexKeyCount == 0:
                continue

            meshName = node.meshName
            blObj = blValidObjs.get(meshName)

            if blObj is None:
                if node.vertexKeyCount == 0:
                    continue

                self.report({ 'INFO' }, f"GZRS2: ANI import of type { aniTypePretty } failed to find a matching mesh, skipping: { meshName }")
                continue

            blObjAnimData = blObj.animation_data or blObj.animation_data_create()
            blObjAnimData.action = action

            context.view_layer.update()
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

        bpy.ops.object.mode_set(mode = 'OBJECT')

        blValidObjs = {}

        for node in state.aniNodes:
            meshName = node.meshName
            blObj = blObjs.get(meshName)

            if blObj is None:
                if node.tmKeyCount == 0 and node.visKeyCount == 0:
                    continue

                self.report({ 'INFO' }, f"GZRS2: ANI import of type { aniTypePretty } failed to find a matching object, skipping: { meshName }")
                continue

            blValidObjs[meshName] = blObj

        reorientWorld = Matrix.Rotation(math.radians(-90.0), 4, 'X')

        for node in state.aniNodes:
            meshName = node.meshName
            blObj = blValidObjs.get(meshName)
            blObj.rotation_mode = 'QUATERNION'

            if node.tmKeyCount == 0 and node.visKeyCount == 0:
                continue

            if blObj is None:
                self.report({ 'INFO' }, f"GZRS2: ANI import of type { aniTypePretty } failed to find a matching object, skipping: { meshName }")
                continue

            actionName = f"{ state.filename }_{ meshName }"

            if state.overwriteAction:   action = bpy.data.actions.get(actionName) or bpy.data.actions.new(actionName)
            else:                       action = bpy.data.actions.new(actionName)

            action.frame_end = state.aniMaxTick / ANI_TICKS_PER_FRAME
            action.use_cyclic = True
            action.use_frame_range = True
            action.fcurves.clear()

            blObjAnimData = blObj.animation_data or blObj.animation_data_create()
            blObjAnimData.action = action

            if node.tmKeyCount > 0:
                locCurves = tuple(action.fcurves.new('location',              index = i) for i in range(3))
                rotCurves = tuple(action.fcurves.new('rotation_quaternion',   index = i) for i in range(4))
                scaCurves = tuple(action.fcurves.new('scale',                 index = i) for i in range(3))

                for i in range(3): locCurves[i].keyframe_points.add(node.tmKeyCount)
                for i in range(4): rotCurves[i].keyframe_points.add(node.tmKeyCount)
                for i in range(3): scaCurves[i].keyframe_points.add(node.tmKeyCount)

                for k in range(node.tmKeyCount):
                    frame = int(round(node.tmTicks[k] / ANI_TICKS_PER_FRAME))
                    worldMat = node.tmMats[k] @ reorientWorld
                    loc, rot, sca = worldMat.decompose()

                    print(rot)

                    for i in range(3): locCurves[i].keyframe_points[k].co = Vector((frame + 1, loc[i]))
                    for i in range(4): rotCurves[i].keyframe_points[k].co = Vector((frame + 1, rot[i]))
                    for i in range(3): scaCurves[i].keyframe_points[k].co = Vector((frame + 1, sca[i]))

                for i in range(3): locCurves[i].update()
                for i in range(4): rotCurves[i].update()
                for i in range(3): scaCurves[i].update()

                blObj.matrix_world = node.firstMat @ reorientWorld

            if node.visKeyCount > 0:
                visCurve = blObjAnimData.action.fcurves.new('color', index = 3)
                visCurve.keyframe_points.add(node.visKeyCount)

                for k in range(node.visKeyCount):
                    frame = int(round(node.visTicks[k] / ANI_TICKS_PER_FRAME))
                    visValue = node.visValues[k]

                    visCurve.keyframe_points[k].co = Vector((frame + 1, visValue))

                visCurve.update()
    else:
        blObjs = { object.name: object for object in context.scene.objects }

        blArmatureObj = context.active_object if context.active_object in context.selected_objects else None

        if blArmatureObj is None or blArmatureObj.type != 'ARMATURE':
            self.report({ 'ERROR' }, f"GZRS2: ANI import of type { aniTypePretty } requires a selected armature as a reference!")
            return { 'CANCELLED' }

        blArmatureObjAnimData = blArmatureObj.animation_data or blArmatureObj.animation_data_create()
        blArmatureObjAnimData.action = action

        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.mode_set(mode = 'POSE')

        blPoseBones = blArmatureObj.pose.bones

        for blPoseBone in blPoseBones:
            if blPoseBone.parent is not None:
                break
        else:
            self.report({ 'WARNING' }, f"GZRS2: ANI import of type { aniTypePretty } performed on an armature with no parent-child hierarchy!")

        for blPoseBone in blPoseBones:
            blPoseBone.matrix_basis.identity()

        bpy.ops.object.mode_set(mode = 'OBJECT')

        context.view_layer.update()
        blArmatureObj.update_from_editmode()

        bpy.ops.object.mode_set(mode = 'EDIT')

        for blEditBone in blArmatureObj.data.edit_bones:
            blEditBone.use_connect = False

        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.mode_set(mode = 'POSE')

        blValidObjs = {}

        for node in state.aniNodes:
            meshName = node.meshName
            blObj = blObjs.get(meshName)

            if blObj is None:
                if node.posKeyCount == 0 and node.rotKeyCount == 0:
                    continue

                self.report({ 'INFO' }, f"GZRS2: ANI import of type { aniTypePretty } failed to find a matching object, skipping: { meshName }")
                continue

            blValidObjs[meshName] = blObj

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
                nonlocal blArmatureObj, meshName, blPoseBone, locPath, rotPath

                blPoseBone.matrix = poseMat @ reorientPose
                context.view_layer.update()

                blArmatureObj.keyframe_insert(data_path = locPath, frame = frame, group = meshName)
                blArmatureObj.keyframe_insert(data_path = rotPath, frame = frame, group = meshName)

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

    if aniType is not AniNodeTM:
        for node in state.aniNodes:
            meshName = node.meshName
            blObj = blValidObjs.get(meshName)

            if node.visKeyCount == 0:
                continue

            if blObj is None:
                self.report({ 'INFO' }, f"GZRS2: ANI import of type { aniTypePretty } failed to find a matching object, skipping: { meshName }")
                continue

            blObjAnimData = blObj.animation_data or blObj.animation_data_create()
            blObjAnimData.action = blObjAnimData.action or bpy.data.actions.new(f"{ state.filename }_{ meshName }")
            blObjAnimData.action.fcurves.clear()

            visCurve = blObjAnimData.action.fcurves.new('color', index = 3)
            visCurve.keyframe_points.add(node.visKeyCount)

            for k in range(node.visKeyCount):
                frame = int(round(node.visTicks[k] / ANI_TICKS_PER_FRAME))
                visValue = node.visValues[k]

                visCurve.keyframe_points[k].co = Vector((frame + 1, visValue))

            visCurve.update()

    return { 'FINISHED' }
