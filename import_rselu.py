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

import bpy, os, math
import xml.dom.minidom as minidom
import re as regex

from contextlib import redirect_stdout
from mathutils import Vector, Matrix

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .parse_gzrs2 import *
from .readelu_gzrs2 import *
from .lib_gzrs2 import *

def importElu(self, context):
    state = GZRS2State()

    if self.texSearchMode == 'PATH':
        if not self.rs2DataDir:
            self.report({ 'ERROR' }, f"GZRS2: Must specify a path to search for or select a different texture mode!")
            return { 'CANCELLED' }

        if not matchRSDataDirectory(self, self.rs2DataDir, os.path.basename(self.rs2DataDir), False, state):
            self.report({ 'ERROR' }, f"GZRS2: Search path must point to a folder containing a valid data subdirectory: { self.rs2DataDir }")
            return { 'CANCELLED' }

    state.convertUnits = self.convertUnits
    state.texSearchMode = self.texSearchMode
    state.doBoneRolls = self.doBoneRolls
    state.doTwistConstraints = self.doTwistConstraints
    state.doCleanup = self.doCleanup

    if self.panelLogging:
        print()
        print("=======================================================================")
        print("===========================  RSELU Import  ============================")
        print("=======================================================================")
        print(f"== { self.filepath }")
        print("=======================================================================")
        print()

        state.logEluHeaders = self.logEluHeaders
        state.logEluMats = self.logEluMats
        state.logEluMeshNodes = self.logEluMeshNodes
        state.logVerboseIndices = self.logVerboseIndices and self.logEluMeshNodes
        state.logVerboseWeights = self.logVerboseWeights and self.logEluMeshNodes
        state.logCleanup = self.logCleanup

    elupath = self.filepath
    state.directory = os.path.dirname(elupath)
    state.filename = os.path.basename(elupath).split(os.extsep)[0]

    for ext in XML_EXTENSIONS:
        eluxmlpath = pathExists(f"{ elupath }.{ ext }")

        if eluxmlpath:
            with open(eluxmlpath, encoding = 'utf8') as file:
                eluxmlstring = file.read()
                eluxmlstring = regex.sub(r"(<Umbra Synchronization[^>]+\/>)", '', eluxmlstring)
                eluxmlstring = eluxmlstring.replace("\"unreducible=true\"", "\" unreducible=true\"")

            state.xmlEluMats[elupath] = parseEluXML(self, minidom.parseString(eluxmlstring), state)
            break

    if readElu(self, elupath, state):
        return { 'CANCELLED' }

    bpy.ops.ed.undo_push()
    collections = bpy.data.collections

    rootMesh = collections.new(state.filename)
    context.collection.children.link(rootMesh)

    setupErrorMat(state)

    for m, eluMat in enumerate(state.eluMats):
        setupEluMat(self, m, eluMat, state)

    if eluxmlpath:
        for xmlEluMat in state.xmlEluMats[elupath]:
            setupXmlEluMat(self, elupath, xmlEluMat, state)

    if state.doCleanup and state.logCleanup:
        print()
        print("=== Elu Mesh Cleanup ===")
        print()

    for eluMesh in state.eluMeshes:
        meshName = eluMesh.meshName

        if meshName.startswith(("Bip01", "Bone")):
            state.gzrsValidBones.add(meshName)

        if eluMesh.isDummy:
            blDummyObj = bpy.data.objects.new(meshName, None)

            blDummyObj.empty_display_type = 'ARROWS'
            blDummyObj.empty_display_size = 0.1
            blDummyObj.matrix_world = eluMesh.transform

            rootMesh.objects.link(blDummyObj)

            state.blDummyObjs.append(blDummyObj)
            state.blObjPairs.append((eluMesh, blDummyObj))
        else:
            setupElu(self, eluMesh, False, rootMesh, context, state)

    processEluHeirarchy(self, state)

    if len(state.gzrsValidBones) > 0:
        state.blArmature = bpy.data.armatures.new("Armature")
        state.blArmatureObj = bpy.data.objects.new("Armature", state.blArmature)

        state.blArmatureObj.display_type = 'WIRE'
        state.blArmatureObj.show_in_front = True

        rootMesh.objects.link(state.blArmatureObj)

        for viewLayer in context.scene.view_layers:
            viewLayer.objects.active = state.blArmatureObj

        bpy.ops.object.mode_set(mode = 'EDIT')

        reorientLocal = Matrix.Rotation(math.radians(-90.0), 4, 'Z') @ Matrix.Rotation(math.radians(-90.0), 4, 'Y')

        for eluMesh, blMeshOrDummyObj in state.blObjPairs:
            if eluMesh.meshName not in state.gzrsValidBones:
                continue

            editBone = state.blArmature.edit_bones.new(eluMesh.meshName)
            editBone.tail = (0, 0.1, 0)
            editBone.matrix = blMeshOrDummyObj.matrix_world @ reorientLocal

            if eluMesh.isDummy and 'Nub' in eluMesh.meshName:
                for collection in blMeshOrDummyObj.users_collection:
                    collection.objects.unlink(blMeshOrDummyObj)

            state.blBonePairs.append((eluMesh, editBone))

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
                self.report({ 'WARNING' }, f"GZRS2: Parent not found for .elu child bone: { child.meshName }, { child.parentName }")

        for eluMesh, editBone in state.blBonePairs:
            if editBone.name == 'Bip01':
                continue
            elif len(editBone.children) > 0:
                length = 0

                for child in editBone.children:
                    length = max(length, (child.head - editBone.head).length)

                editBone.length = length
            elif editBone.parent is not None:
                editBone.length = editBone.parent.length / 2

            if editBone.parent is not None and (Vector(editBone.parent.tail) - Vector(editBone.head)).length < 0.001:
                editBone.use_connect = True

        if state.doBoneRolls:
            with redirect_stdout(state.silentIO):
                bpy.ops.armature.select_all(action = 'SELECT')
                bpy.ops.armature.calculate_roll(type = 'GLOBAL_POS_Z')
                bpy.ops.armature.select_all(action = 'DESELECT')
            deleteInfoReports(3, context)

        bpy.ops.object.mode_set(mode = 'OBJECT')
        deleteInfoReports(1, context)

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
            isBone = child.meshName in state.gzrsValidBones
            noParentBone = child.parentName not in state.gzrsValidBones
            isNubDummy = isBone and child.isDummy and 'Nub' in child.meshName
            isNotRoot = child.meshName != 'Bip01'

            if isNubDummy or noParentBone and isNotRoot:
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
                self.report({ 'ERROR' }, f"GZRS2: Bone parent not found for .elu child mesh or dummy: { child.meshName }, { child.parentName }, { child.isDummy }")

        for blMeshObj in state.blMeshObjs:
            modifier = getModifierByType(self, blMeshObj.modifiers, 'ARMATURE')

            if modifier:
                modifier.object = state.blArmatureObj

    bpy.ops.object.select_all(action = 'DESELECT')
    deleteInfoReports(1, context)

    return { 'FINISHED' }
