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

import math, io

from mathutils import Vector, Quaternion, Matrix

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .io_gzrs2 import *
from .lib_gzrs2 import *

def readVisData(file, version, state):
    visKeyCount = 0
    visValues = ()
    visTicks = ()

    if version > ANI_0012:
        visKeyCount = readUInt(file) # m_vis_cnt

        if visKeyCount > 0:
            visValues = [0.0 for _ in range(visKeyCount)]
            visTicks = [0 for _ in range(visKeyCount)]

            for k in range(visKeyCount):
                visValues[k] = readFloat(file)
                visTicks[k] = readInt(file)

            visValues = tuple(visValues)
            visTicks = tuple(visTicks)
            state.aniMaxVisTick = max(state.aniMaxVisTick, visTicks[-1])

    if state.logAniNodes:
        output = "Vis Keyframes:      {:<6d}".format(visKeyCount)

        if visKeyCount > 0:
            output += "      Value Range: ({:>5.02f}, {:>5.02f})".format(min(visValues), max(visValues))
            output += "\n                                Tick Range:  ({:>6d}, {:>6d})".format(min(visTicks), max(visTicks))

        print(output)

    return visKeyCount, visValues, visTicks

def readAni(self, file, path, state):
    file.seek(0, os.SEEK_END)
    fileSize = file.tell()
    file.seek(0, os.SEEK_SET)

    if state.logAniHeaders or state.logAniNodes:
        print("===================  Read Ani  ===================")
        print()

    id = readUInt(file)
    version = readUInt(file)
    maxKeyIndex = readInt(file)
    nodeCount = readInt(file)
    aniType = readInt(file)

    if state.logAniHeaders:
        print(f"Path:               { path }")
        print(f"ID:                 { hex(id) }")
        print(f"Version:            { hex(version) }")
        print(f"Max Key Index:      { maxKeyIndex }")
        print(f"Node Count:         { nodeCount }")
        print(f"Animation Type:     { ANI_TYPES_PRETTY.get(aniType, aniType) }")
        print()

    error = False

    if id != ANI_ID or version not in ANI_VERSIONS:
        self.report({ 'ERROR' }, f"GZRS2: ANI header invalid! { hex(id) }, { hex(version) }")
        error = True

    if nodeCount == 0:                      self.report({ 'ERROR' }, f"GZRS2: ANI file with no nodes! { hex(version) }"); error = True
    if aniType not in ANI_IMPORT_TYPES:     self.report({ 'ERROR' }, f"GZRS2: ANI file with unsupported type! { hex(version) }, { ANI_TYPES_PRETTY.get(aniType, aniType) }"); error = True

    if nodeCount < 0:               self.report({ 'ERROR' }, f"GZRS2: ANI file with negative node count! { hex(version) }, { nodeCount }"); error = True
    if maxKeyIndex < 0:             self.report({ 'ERROR' }, f"GZRS2: ANI file with negative max key index! { hex(version) }, { maxKeyIndex }"); error = True
    if aniType < 0:                 self.report({ 'ERROR' }, f"GZRS2: ANI file with negative type! { hex(version) }, { aniType }"); error = True

    if error:
        return { 'CANCELLED' }

    maxKeyCount = 0

    if aniType == ANI_TYPE_VERTEX:
        for n in range(nodeCount):
            meshName = readStringAlt(file, ELU_NAME_LENGTH) # t_mesh_name
            vertexKeyCount = readInt(file) # m_vertex_cnt
            vertexCount = readInt(file) # m_vertex_vcnt

            if state.logAniNodes:
                print(f"===== Node { n } =====")
                print(f"Mesh Name:          { meshName }")
                print(f"Keyframe Count:     { vertexKeyCount }")
                print(f"Vertex Count:       { vertexCount }")
                print()

            vertexTicks = readUIntArray(file, vertexKeyCount) # m_vertex_frame
            vertexPositions = readCoordinateArray(file, vertexKeyCount * vertexCount, state.convertUnits, False, swizzle = True)

            if state.logAniNodes:
                output = "Ticks:              {:<6d}".format(vertexKeyCount)
                output += "      Min & Max: ({:>6d}, {:>6d})".format(min(vertexTicks), max(vertexTicks)) if vertexKeyCount > 0 else ''
                print(output)
                output = "Positions:          {:<6d}".format(len(vertexPositions))
                output += "      Min: ({:>6.03f}, {:>6.03f}, {:>6.03f})     Max: ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*vecArrayMinMax(vertexPositions, 3)) if len(vertexPositions) > 0 else ''
                print(output)

            visKeyCount, visValues, visTicks = readVisData(file, version, state)

            state.aniNodes.append(AniNodeVertex(meshName, vertexKeyCount, vertexCount, vertexTicks, vertexPositions, visKeyCount, visValues, visTicks))

            maxKeyCount = max(maxKeyCount, vertexKeyCount)

            if state.logAniNodes:
                print()

        for node in state.aniNodes:
            if node.vertexKeyCount > 0:
                state.aniMaxTick = max(state.aniMaxTick, node.vertexTicks[-1])
                break # Why prioritize the first found? Shouldn't we consider all nodes?
    elif aniType == ANI_TYPE_TM:
        for n in range(nodeCount):
            meshName = readStringAlt(file, ELU_NAME_LENGTH)
            tmKeyCount = readInt(file) # m_mat_cnt

            if state.logAniNodes:
                print(f"===== Node { n } =====")
                print(f"Mesh Name:          { meshName }")
                print(f"Frame Count:        { tmKeyCount }")

            tmMats = [Matrix() for _ in range(tmKeyCount)]
            tmTicks = [0 for _ in range(tmKeyCount)]

            for k in range(tmKeyCount):
                tmMats[k] = readTransform(file, state.convertUnits, swizzle = True)
                tmTicks[k] = readInt(file)

            tmMats = tuple(tmMats)
            tmTicks = tuple(tmTicks)

            firstMat = tmMats[0]
            state.aniMaxTick = max(state.aniMaxTick, tmTicks[-1])

            if state.logAniNodes:
                print("First Matrix:       ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*firstMat[0]))
                print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*firstMat[1]))
                print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*firstMat[2]))
                print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*firstMat[3]))
                print()

            if state.logAniNodes:
                output = "Transform Keyframes:{:<6d}".format(tmKeyCount)
                if tmKeyCount > 0:
                    output += "      Matrix Range: N/A"
                    output += "\n                                Tick Range:  ({:>6d}, {:>6d})".format(min(tmTicks), max(tmTicks))
                print(output)

            visKeyCount, visValues, visTicks = readVisData(file, version, state)

            state.aniNodes.append(AniNodeTM(meshName, firstMat, tmKeyCount, tmMats, tmTicks, visKeyCount, visValues, visTicks))

            maxKeyCount = max(maxKeyCount, tmKeyCount)

            if state.logAniNodes:
                print()
    else:
        for n in range(nodeCount):
            meshName = readStringAlt(file, ELU_NAME_LENGTH) # t_mesh_name
            baseMat = readTransform(file, state.convertUnits, swizzle = True)

            if state.logAniNodes:
                print(f"===== Node { n } =====")
                print(f"Mesh Name:          { meshName }")
                print("Base Matrix:        ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*baseMat[0]))
                print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*baseMat[1]))
                print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*baseMat[2]))
                print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*baseMat[3]))
                print()

            posKeyCount = readInt(file) # pos_key_num, m_pos_cnt

            if posKeyCount > 0:
                posVectors = [Vector((0.0, 0.0, 0.0)) for _ in range(posKeyCount)]
                posTicks = [0 for _ in range(posKeyCount)]

                for k in range(posKeyCount):
                    posVectors[k] = readCoordinate(file, state.convertUnits, False, swizzle = True)
                    posTicks[k] = readInt(file)

                posVectors = tuple(posVectors)
                posTicks = tuple(posTicks)

                state.aniMaxTick = max(state.aniMaxTick, posTicks[-1])
            else:
                posVectors = ()
                posTicks = ()

            if state.logAniNodes:
                output = "Position Keyframes: {:<6d}".format(posKeyCount)
                if posKeyCount > 0:
                    output += "      Vector Range: (({:>6.03f}, {:>6.03f}, {:>6.03f}), ({:>6.03f}, {:>6.03f}, {:>6.03f}))".format(*vecArrayMinMax(posVectors, 3))
                    output += "\n                                Tick Range:  ({:>6d}, {:>6d})".format(min(posTicks), max(posTicks))
                print(output)

            rotKeyCount = readInt(file) # rot_key_num, m_rot_cnt

            if rotKeyCount > 0:
                rotQuats = [Quaternion() for _ in range(rotKeyCount)]
                rotTicks = [0 for _ in range(rotKeyCount)]

                if version > ANI_1002:
                    for k in range(rotKeyCount):
                        x = readFloat(file)
                        y = readFloat(file)
                        z = readFloat(file)
                        w = readFloat(file)

                        # Swizzle and reverse
                        rotQuats[k] = Quaternion((-w, x, z, y))
                        rotTicks[k] = readInt(file)
                else:
                    for k in range(rotKeyCount):
                        x = readFloat(file)
                        y = readFloat(file)
                        z = readFloat(file)
                        angle = readFloat(file)

                        # Swizzle and reverse
                        rotQuats[k] = Quaternion((x, z, y), -angle)
                        rotTicks[k] = readInt(file)

                rotQuats = tuple(rotQuats)
                rotTicks = tuple(rotTicks)

                state.aniMaxTick = max(state.aniMaxTick, rotTicks[-1])
            else:
                rotQuats = ()
                rotTicks = ()

            if state.logAniNodes:
                output = "Rotation Keyframes: {:<6d}".format(rotKeyCount)
                if rotKeyCount > 0:
                    output += "      Quaternion Range: (({:>5.02f}, {:>5.02f}, {:>5.02f}, {:>5.02f}), ({:>5.02f}, {:>5.02f}, {:>5.02f}, {:>5.02f}))".format(*vecArrayMinMax(rotQuats, 4))
                    output += "\n                                Tick Range:  ({:>6d}, {:>6d})".format(min(rotTicks), max(rotTicks))
                print(output)

            visKeyCount, visValues, visTicks = readVisData(file, version, state)

            if aniType == ANI_TYPE_TRANSFORM:
                state.aniNodes.append(AniNodeTransform(meshName, baseMat, posKeyCount, posVectors, posTicks, rotKeyCount, rotQuats, rotTicks, visKeyCount, visValues, visTicks))
                maxKeyCount = max(maxKeyCount, posKeyCount)
                maxKeyCount = max(maxKeyCount, rotKeyCount)
            else:
                state.aniNodes.append(AniNodeBone(meshName, baseMat, posKeyCount, posVectors, posTicks, rotKeyCount, rotQuats, rotTicks, visKeyCount, visValues, visTicks))
                maxKeyCount = max(maxKeyCount, posKeyCount)
                maxKeyCount = max(maxKeyCount, rotKeyCount)

            if state.logAniNodes:
                print()

    state.aniMaxTick = max(state.aniMaxTick, state.aniMaxVisTick)

    if state.logAniNodes:
        print(f"Max Tick:           { state.aniMaxTick }")

    if maxKeyCount > 0 and maxKeyCount - 1 != maxKeyIndex:
        self.report({ 'ERROR' }, f"GZRS2: ANI import finished but maximum keyframe did not match recorded value! { maxKeyCount - 1 }, { maxKeyIndex }")

    if aniType == ANI_TYPE_TRANSFORM or aniType == ANI_TYPE_BONE:
        warnPosNoZero = True
        warnPosDuplicate = True
        warnPosOutOfOrder = True
        warnRotNoZero = True
        warnRotDuplicate = True
        warnRotOutOfOrder = True

        for node in state.aniNodes:
            if node.posKeyCount > 0:
                tickList = node.posTicks
                tickSet = set(tickList)

                if warnPosNoZero and 0 not in tickList:
                    self.report({ 'WARNING' }, f"GZRS2: ANI with position keyframes but no zero tick! Please submit to Krunk#6051 for testing!")
                    warnPosNoZero = False

                if warnPosDuplicate and len(tickList) != len(tickSet):
                    self.report({ 'WARNING' }, f"GZRS2: ANI with duplicate position keyframes! Please submit to Krunk#6051 for testing!")
                    warnPosDuplicate = False

                if warnPosOutOfOrder:
                    for k in range(node.posKeyCount - 1):
                        if tickList[k] > tickList[k + 1]:
                            self.report({ 'WARNING' }, f"GZRS2: ANI with position keyframes out of order! Please submit to Krunk#6051 for testing!")
                            warnPosOutOfOrder = False
                            break

            if node.rotKeyCount > 0:
                tickList = node.rotTicks
                tickSet = set(tickList)

                if warnRotNoZero and 0 not in tickList:
                    self.report({ 'WARNING' }, f"GZRS2: ANI with rotation keyframes but no zero tick! Please submit to Krunk#6051 for testing!")
                    warnRotNoZero = False

                if warnRotDuplicate and len(tickList) != len(tickSet):
                    self.report({ 'WARNING' }, f"GZRS2: ANI with duplicate rotation keyframes! Please submit to Krunk#6051 for testing!")
                    warnRotDuplicate = False

                if warnRotOutOfOrder:
                    for k in range(node.rotKeyCount - 1):
                        if tickList[k] > tickList[k + 1]:
                            self.report({ 'WARNING' }, f"GZRS2: ANI with rotation keyframes out of order! Please submit to Krunk#6051 for testing!")
                            warnRotOutOfOrder = False
                            break

    if state.logAniHeaders or state.logAniNodes:
        bytesRemaining = fileSize - file.tell()

        if bytesRemaining > 0:
            self.report({ 'ERROR' }, f"GZRS2: ANI import finished with bytes remaining! { path }, { hex(id) }, { hex(version) }")

        print(f"Bytes Remaining:    { bytesRemaining }")
        print()