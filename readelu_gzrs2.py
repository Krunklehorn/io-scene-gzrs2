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

import math, io

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .io_gzrs2 import *
from .lib_gzrs2 import *

def readElu(self, file, path, state):
    file.seek(0, os.SEEK_END)
    fileSize = file.tell()
    file.seek(0, os.SEEK_SET)

    if state.logEluHeaders or state.logEluMats or state.logEluMeshNodes:
        print("===================  Read Elu  ===================")
        print()

    id = readUInt(file)
    version = readUInt(file)
    matCount = readInt(file)
    meshCount = readInt(file)

    if state.logEluHeaders:
        print(f"Path:               { path }")
        print(f"ID:                 { hex(id) }")
        print(f"Version:            { hex(version) }")
        print(f"Mat Count:          { matCount }")
        print(f"Mesh Count:         { meshCount }")
        print()

    if id != ELU_ID or version not in ELU_VERSIONS:
        self.report({ 'ERROR' }, f"GZRS2: ELU header invalid! { hex(id) }, { hex(version) }")
        return { 'CANCELLED' }

    if version not in ELU_IMPORT_VERSIONS:
        self.report({ 'ERROR' }, f"GZRS2: Importing this ELU version is not supported yet! Model will not load properly! { path }, { hex(version) }")
        return { 'CANCELLED' }

    result = None

    if version <= ELU_5007: # GunZ 1 R_Mesh_Load.cpp
        if version == ELU_0:
            result = readEluRS2Meshes(self, path, file, version, meshCount, state)
            result = readEluRS2Materials(self, path, file, version, matCount, state)
        else:
            result = readEluRS2Materials(self, path, file, version, matCount, state)
            result = readEluRS2Meshes(self, path, file, version, meshCount, state)
    else: # GunZ 2 RMesh.cpp
        result = readEluRS3Meshes(self, path, file, version, meshCount, state)

    if state.logEluHeaders or state.logEluMats or state.logEluMeshNodes:
        bytesRemaining = fileSize - file.tell()

        if bytesRemaining > 0:
            self.report({ 'ERROR' }, f"GZRS2: ELU import finished with bytes remaining! { path }, { hex(id) }, { hex(version) }")

        print(f"Bytes Remaining:    { bytesRemaining }")
        print()

    return result

def readEluRS2Materials(self, path, file, version, matCount, state):
    if version == ELU_0:
        matCount = readUShort(file)

    if state.logEluMats and matCount > 0:
        print()
        print("=========  Elu Materials  =========")
        print()
        if version == ELU_0:
            print(f"Mat Count:          { matCount }")
            print()

    eluMats = []

    for m in range(matCount):
        matID = readUInt(file)
        subMatID = readInt(file)

        if state.logEluMats:
            print(f"===== Material { m } =====")
            print(f"Mat ID:             { matID }")
            print(f"Sub Mat ID:         { subMatID }")
            print()

        ambient = readVec4(file)
        diffuse = readVec4(file)
        specular = readVec4(file)
        exponent = readFloat(file)

        if version <= ELU_5002:
            if exponent == 20.0:
                exponent = 0.0

        if state.logEluMats:
            print("Ambient:            ({:>5.03f}, {:>5.03f}, {:>5.03f}, {:>5.03f})".format(*ambient))
            print("Diffuse:            ({:>5.03f}, {:>5.03f}, {:>5.03f}, {:>5.03f})".format(*diffuse))
            print("Specular:           ({:>5.03f}, {:>5.03f}, {:>5.03f}, {:>5.03f})".format(*specular))
            print(f"Exponent:           { exponent }")
            print()

        subMatCount = readUInt(file)

        if version == ELU_0:
            texpath = readPath(file, readUShort(file))
            alphapath = readPath(file, readUShort(file))

            twosided = readCharBool(file)
            additive = readCharBool(file)
            alphatest = readUInt(file)
            skipBytes(file, 1) # skip diffuse? char
            useopacity = readCharBool(file)
        else:
            if version <= ELU_5005:
                texpath = readPath(file, ELU_NAME_LENGTH)
                alphapath = readPath(file, ELU_NAME_LENGTH)
            else:
                texpath = readPath(file, ELU_PATH_LENGTH)
                alphapath = readPath(file, ELU_PATH_LENGTH)

            twosided, additive, alphatest = False, False, 0

            if version >= ELU_5002: twosided = readBool32(file)
            if version >= ELU_5004: additive = readBool32(file)
            if version == ELU_5007: alphatest = readUInt(file)

            texpath = texpath.replace(os.extsep + 'dds' + os.extsep + 'dds', os.extsep + 'dds')
            alphapath = alphapath.replace(os.extsep + 'dds' + os.extsep + 'dds', os.extsep + 'dds')

            useopacity = alphapath != '' and alphapath.lower().endswith('.tga') or alphapath.lower().endswith('.tga.dds')

        if state.logEluMats:
            print(f"Sub Mat Count:      { subMatCount }")
            print(f"Texture path:       { texpath }")
            print(f"Alpha path:         { alphapath }")
            print()
            print(f"Two-sided:          { twosided }")
            print(f"Additive:           { additive }")
            print(f"Alpha Test:         { alphatest }")
            print(f"Use Opacity:        { useopacity }")
            print()

        texBase, texName, texExt, texDir = decomposePath(texpath)
        isAniTex = checkIsAniTex(texName)
        success, frameCount, frameSpeed, frameGap = processAniTexParameters(isAniTex, texName)

        if not success:
            return { 'CANCELLED' }

        if state.logEluMats:
            if texpath:
                print(f"Texture Base:       { texBase }")
                print(f"Name:               { texName }")
                print(f"Extension:          { texExt }")
                print(f"Directory:          { texDir }")
                print(f"Is Animated:        { isAniTex }")
                print()

                if isAniTex:
                    print(f"Frame Count:        { frameCount }")
                    print(f"Frame Speed:        { frameSpeed }")
                    print(f"Frame Gap:          { frameGap }")
                    print()

        eluMat = EluMaterial(path, matID, subMatID,
                             ambient, diffuse, specular, exponent,
                             subMatCount, texpath, alphapath,
                             twosided, additive, alphatest, useopacity,
                             texBase, texName, texExt, texDir,
                             isAniTex, frameCount, frameSpeed, frameGap)

        eluMats.append(eluMat)
        state.eluMats.append(eluMat)

    # Check for duplicate material id pairs
    dupePairs = set()

    for m1, eluMat1 in enumerate(eluMats):
        pair1 = (eluMat1.matID, eluMat1.subMatID)

        if pair1 in dupePairs:
            continue

        for m2, eluMat2 in enumerate(eluMats):
            if m2 == m1:
                continue

            pair2 = (eluMat2.matID, eluMat2.subMatID)

            if pair2 in dupePairs:
                continue

            if pair1 == pair2:
                self.report({ 'ERROR' }, f"GZRS2: Found .elu with duplicate material ids: { state.filename }, { hex(version) }, { pair1 }, { eluMat1.texpath }, { eluMat2.texpath }")
                dupePairs.add(pair1)

    # Check for sub-materials with an invalid base or sub-material counts of their own
    for m1, eluMat1 in enumerate(eluMats):
        if eluMat1.subMatID == -1:
            continue

        valid = False

        for m2, eluMat2 in enumerate(eluMats):
            if m2 == m1:
                continue

            if eluMat2.matID == eluMat1.matID and eluMat2.subMatID == -1:
                valid = True
                break

        if not valid:
            self.report({ 'ERROR' }, f"GZRS2: Found .elu sub-material with no valid base: { state.filename }, { hex(version) }, { eluMat1.matID }, { eluMat1.subMatID }")

        if eluMat1.subMatCount > 0:
            self.report({ 'ERROR' }, f"GZRS2: Found .elu sub-material with a sub-material count of it's own: { state.filename }, { hex(version) }, { eluMat1.matID }, { eluMat1.subMatID }, { eluMat1.subMatCount }")

def readEluRS2Meshes(self, path, file, version, meshCount, state):
    if version == ELU_0:
        meshCount = readUShort(file)

    usesDummies = False
    usesEffects = False
    totalSlotIDs = set()
    matIDs = set()
    weightIDs = set()
    weightNames = set()

    if state.logEluMeshNodes and meshCount > 0:
        print()
        print("=========  Elu Mesh Nodes  ========")
        print()
        if version == ELU_0:
            print(f"Mesh Count:         { meshCount }")
            print()

    for m in range(meshCount):
        if version == ELU_0:
            meshName = readString(file, readUShort(file))
            parentName = readString(file, readUShort(file))
            skipBytes(file, 4 * 3 + 4 * 4 * 4 * 3 + 4) # skip precalculated transform information
            worldMatrix = readTransform(file, state.convertUnits, swizzle = True)
            skipBytes(file, 4 * 4 * 4 + 4 * 3 + 4 + 4 * 4 * 4 * 3 + 4 * 3 + 4 * 4 * 4) # skip precalculated transform information
        else:
            meshName = readString(file, ELU_NAME_LENGTH)
            parentName = readString(file, ELU_NAME_LENGTH)
            worldMatrix = readTransform(file, state.convertUnits, swizzle = True)

            if version >= ELU_5001: skipBytes(file, 4 * 3) # skip ap scale
            if version >= ELU_5003: skipBytes(file, 4 * 4 + 4 * 4 + 4 * 4 * 4) # skip rotation aa, scale aa and etc matrix

        if state.logEluMeshNodes:
            print(f"===== Mesh { m } =====")
            print(f"Mesh Name:          { meshName }")
            print(f"Parent Name:        { parentName }")
            print("World Matrix:       ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*worldMatrix[0]))
            print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*worldMatrix[1]))
            print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*worldMatrix[2]))
            print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*worldMatrix[3]))
            print()

        vertices = readCoordinateArray(file, readUInt(file), state.convertUnits, False, swizzle = True)
        if state.logEluMeshNodes:
            output = "Vertices:           {:<6d}".format(len(vertices))
            output += "      Min: ({:>5.02f}, {:>5.02f}, {:>5.02f})     Max: ({:>5.02f}, {:>5.02f}, {:>5.02f})".format(*vecArrayMinMax(vertices, 3)) if len(vertices) > 0 else ''
            print(output)
            if state.logVerboseIndices:
                print()
                for pos in vertices:
                    print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*pos))
                print()

        faceCount = readUInt(file)
        faces = []
        normals = ()
        uv1s = [Vector((0, 0)) for _ in range(faceCount * 3)]
        slotIDs = set()
        if state.logEluMeshNodes:
            print(f"Faces:              { faceCount }")

            if state.logVerboseIndices:
                print()

        if faceCount > 0:
            for f in range(faceCount):
                indices = readUIntArray(file, 3)

                # ignores unused z-coordinates
                uv1s[f * 3 + 0] = readUV3(file)
                uv1s[f * 3 + 1] = readUV3(file)
                uv1s[f * 3 + 2] = readUV3(file)

                slotID = readInt(file)
                slotIDs.add(slotID)

                if state.logEluMeshNodes:
                    totalSlotIDs.add(slotID)

                if version == ELU_0 or version >= ELU_5002:
                    skipBytes(file, 4) # skip signature ID

                faces.append(EluFace(3, indices, None, tuple(i for i in range(f * 3, f * 3 + 3)), (), slotID))

                if state.logEluMeshNodes and state.logVerboseIndices:
                    print("                     {:>4}, {:>4}, {:>4}".format(*indices))

            if version == ELU_0 or version >= ELU_5005:
                normals = [Vector((0, 0, 0)) for _ in range(faceCount * 3)]

                for f, face in enumerate(faces):
                    skipBytes(file, 4 * 3) # skip face normal
                    normals[f * 3 + 0] = readDirection(file, False, swizzle = True)
                    normals[f * 3 + 1] = readDirection(file, False, swizzle = True)
                    normals[f * 3 + 2] = readDirection(file, False, swizzle = True)

                    face.inor = tuple(i for i in range(f * 3, f * 3 + 3))

        if state.logEluMeshNodes and state.logVerboseIndices:
            print()

        slotIDs = tuple(sorted(slotIDs))
        if state.logEluMeshNodes:
            print("Slot IDs:           {{{}}}".format(', '.join(map(str, slotIDs))))
            output = "UV1s:               {:<6d}".format(len(uv1s))
            output += "      Min: ({:>5.02f}, {:>5.02f})            Max: ({:>5.02f}, {:>5.02f})".format(*vecArrayMinMax(uv1s, 2)) if len(uv1s) > 0 else ''
            print(output)

            output = "Normals:            {:<6d}".format(len(normals))
            output += "      Min: ({:>5.02f}, {:>5.02f}, {:>5.02f})     Max: ({:>5.02f}, {:>5.02f}, {:>5.02f})".format(*vecArrayMinMax(normals, 3)) if len(normals) > 0 else ''
            print(output)

        isDummy = len(vertices) == 0 or len(faces) == 0

        if state.logEluMeshNodes:
            if isDummy: usesDummies = True
            print(f"Is Dummy:           { isDummy }")
            print()

        colors = readVec3Array(file, readUInt(file)) if version == ELU_0 or version >= ELU_5005 else ()
        if state.logEluMeshNodes:
            output = "Colors:             {:<6d}".format(len(colors))
            output += "      Min: ({:>5.02f}, {:>5.02f}, {:>5.02f})     Max: ({:>5.02f}, {:>5.02f}, {:>5.02f})".format(*vecArrayMinMax(colors, 3)) if len(colors) > 0 else ''
            print(output)

        matID = readUInt(file)
        if state.logEluMeshNodes:
            matIDs.add(matID)
            print(f"Material ID:        { matID }")

        weights = []
        weightCount = readUInt(file)

        if state.logEluMeshNodes and weightCount > 0:
            minWeightValue = float('inf')
            maxWeightValue = float('-inf')
            minWeightID = -1
            maxWeightID = -1
            minWeightName = 'ERROR'
            maxWeightName = 'ERROR'

            if state.logVerboseWeights:
                print()

        for _ in range(weightCount):
            if version == ELU_0:
                degree = min(ELU_PHYS_KEYS, readUChar(file))
                meshIDs = [0 for d in range(degree)]
                values = [0.0 for d in range(degree)]
                offsets = [Vector((0.0, 0.0, 0.0)) for d in range(degree)]
                meshNames = ['' for d in range(degree)]

                for d in range(degree):
                    meshIDs[d] = readUInt(file)
                    values[d] = readFloat(file)
                    offsets[d] = readVec3(file)
                    meshNames[d] = readStringAlt(file, readUShort(file))

                meshIDs = tuple(meshIDs)
                values = tuple(values)
                offsets = tuple(offsets)
                meshNames = tuple(meshNames)
            else:
                meshNames = tuple(readStringAlt(file, ELU_NAME_LENGTH) for _ in range(ELU_PHYS_KEYS))
                values = readFloatArray(file, ELU_PHYS_KEYS)
                meshIDs = readUIntArray(file, ELU_PHYS_KEYS)
                degree = min(ELU_PHYS_KEYS, readUInt(file))
                offsets = readVec3Array(file, ELU_PHYS_KEYS)

            if state.logEluMeshNodes:
                for d in range(degree):
                    weightValue = values[d]
                    weightID = meshIDs[d]
                    weightOffset = offsets[d]
                    weightName = meshNames[d]

                    weightIDs.add(weightID)
                    weightNames.add(weightName)

                    if weightName == '':
                        continue

                    if weightValue < minWeightValue:
                        minWeightValue = weightValue
                        minWeightID = weightID
                        minWeightName = weightName

                    if weightValue > maxWeightValue:
                        maxWeightValue = weightValue
                        maxWeightID = weightID
                        maxWeightName = weightName

                    if state.logVerboseWeights:
                        print("Weight:             {:>1d}/{:>1d}, {:>6.03f}, {:>2d}, {:<16s}    ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(d + 1, degree, weightValue, weightID, weightName, *weightOffset))

            weights.append(EluWeight(degree, meshNames, meshIDs, values, offsets))

        if state.logEluMeshNodes:
            if state.logVerboseWeights:
                print()

            output = "Weights:            {:<6d}".format(weightCount)
            output += "      Min:  {:>5.02f}, {:>2d}, {:<10s}    Max:  {:>5.02f}, {:>2d}, {:<10s}".format(minWeightValue, minWeightID, minWeightName, maxWeightValue, maxWeightID, maxWeightName) if weightCount > 0 else ''
            print(output)
            print()

        state.eluMeshes.append(EluMeshNode(path, version, meshName, parentName, 0, worldMatrix,
                                           vertices, tuple(normals), tuple(uv1s), (),
                                           colors, tuple(faces), tuple(weights), (),
                                           slotIDs, isDummy, matID))

    if state.logEluMeshNodes:
        print("===== Mesh Summary =====")
        print()

        print(f"Uses Dummies:       { usesDummies }")
        print(f"Uses Effects:       { usesEffects }")
        print(f"Slot IDs:           { totalSlotIDs }")
        print(f"Material IDs:       { matIDs }")
        print(f"Weight IDs:         { weightIDs }")
        print(f"Weight Names:       { weightNames }")
        print()

def readEluRS3UVs(file, version):
    uv1s, uv2s = (), ()

    if version <= ELU_5013:
        uv1s = readUV3Array(file, readUInt(file)) # skips invalid z-coordinate
    else:
        uv1Stride = readShort(file)
        uv1Count = readUInt(file)

        if   uv1Stride == 2:    uv1s = readUV2Array(file, uv1Count)
        elif uv1Stride == 3:    uv1s = readUV3Array(file, uv1Count)
        elif uv1Stride == 4:    uv1s = readUV4Array(file, uv1Count)
        else:
            self.report({ 'ERROR' }, f"GZRS2: Unsupported uv stride length! { uv1Stride }")
            return { 'CANCELLED' }

    if version == ELU_500E or version == ELU_500F:  skipBytes(file, 4 * 3 * readUInt(file)) # skip invalid lightmap uvs
    elif version >= ELU_5011:                       uv2s = readUV3Array(file, readUInt(file)) # skips invalid z-coordinate

    return uv1s, uv2s

def readEluRS3Meshes(self, path, file, version, meshCount, state):
    usesDummies = False
    totalSlotIDs = set()
    matIDs = set()
    weightIDs = set()

    if state.logEluMeshNodes and meshCount > 0:
        print()
        print("=========  Elu Mesh Nodes  ========")
        print()

    for m in range(meshCount):
        meshName = readString(file, readUInt(file))

        if version <= ELU_5012:
            parentName = readString(file, readUInt(file))
            meshID = readInt(file)
        else:
            meshID = readInt(file)
            parentName = readString(file, readUInt(file))

        if state.logEluMeshNodes:
            print(f"===== Mesh { m } =====")
            print(f"Mesh Name:          { meshName }")
            print(f"Parent Name:        { parentName }")
            print(f"Mesh ID:            { meshID }")


        # RMeshNodeLoadImpl.cpp -> LoadInfo()

        if version <= ELU_5012:
            drawFlags = readUInt(file)
            skipBytes(file, 4) # skip mesh align

            if version <= ELU_5009:
                skipBytes(file, 4 * 3) # skip unused bodypart info

            localMatrix = readTransform(file, state.convertUnits)

            if version >= ELU_500A:
                skipBytes(file, 4) # skip visibility

            if version == ELU_5012:
                skipBytes(file, 4) # skip unknown, always zero
        else:
            localMatrix = readTransform(file, state.convertUnits)
            skipBytes(file, 4) # skip visibility
            drawFlags = readUInt(file)
            skipBytes(file, 4 + 4) # skip mesh align and unknown index, thought to be for LOD projection

        if state.logEluMeshNodes:
            print(f"Draw Flags:         { drawFlags }")
            print("Local Matrix:       ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*localMatrix[0]))
            print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*localMatrix[1]))
            print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*localMatrix[2]))
            print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*localMatrix[3]))

        if state.logEluMeshNodes:
            print()


        # RMeshNodeLoadImpl.cpp -> LoadVertex()
        if version <= ELU_5010:
            if version >= ELU_500D:
                skipBytes(file, 4) # skip FVF flags

            if version >= ELU_500E:
                # lightmapID = readInt(file) # unused, -1 otherwise
                skipBytes(file, 4) # skip lightmap ID

        vertices = readCoordinateArray(file, readUInt(file), state.convertUnits, False)

        if state.logEluMeshNodes:
            output = "Vertices:           {:<6d}".format(len(vertices))
            output += "      Min: ({:>5.02f}, {:>5.02f}, {:>5.02f})     Max: ({:>5.02f}, {:>5.02f}, {:>5.02f})".format(*vecArrayMinMax(vertices, 3)) if len(vertices) > 0 else ''
            print(output)

        uv1s, uv2s = (), ()

        if version >= ELU_5013:
            uv1s, uv2s = readEluRS3UVs(file, version)

        normals = readDirectionArray(file, readUInt(file), False)

        if state.logEluMeshNodes:
            output = "Normals:            {:<6d}".format(len(normals))
            output += "      Min: ({:>5.02f}, {:>5.02f}, {:>5.02f})     Max: ({:>5.02f}, {:>5.02f}, {:>5.02f})".format(*vecArrayMinMax(normals, 3)) if len(normals) > 0 else ''
            print(output)

        if   version <= ELU_500E or version == ELU_5014:    skipBytes(file, 4 * 3 * readUInt(file)) # skip tangents
        else:                                               skipBytes(file, 4 * 4 * readUInt(file)) # skip tangents

        if version <= ELU_5013:  skipBytes(file, 4 * 3 * readUInt(file)) # skip bitangents

        if version == ELU_5014:
            skipBytes(file, 4 * 4 * readUInt(file)) # x/y/z are normalized, w is either -1.0 or 1.0
            skipBytes(file, 4) # skip unknown data, may be the start of the 7th buffer

        if version <= ELU_5012:
            uv1s, uv2s = readEluRS3UVs(file, version)

        if state.logEluMeshNodes:
                output = "UV1s:               {:<6d}".format(len(uv1s))
                output += "      Min: ({:>5.02f}, {:>5.02f})            Max: ({:>5.02f}, {:>5.02f})".format(*vecArrayMinMax(uv1s, 2)) if len(uv1s) > 0 else ''
                print(output)

                output = "UV2s:               {:<6d}".format(len(uv2s))
                output += "      Min: ({:>5.02f}, {:>5.02f})            Max: ({:>5.02f}, {:>5.02f})".format(*vecArrayMinMax(uv2s, 2)) if len(uv2s) > 0 else ''
                print(output)


        # RMeshNodeLoadImpl.cpp -> LoadFace()

        faces = []
        slotIDs = set()
        faceCount = readUInt(file)
        if state.logEluMeshNodes:
            print(f"Faces:              { faceCount }")

        if faceCount > 0:
            if version <= ELU_500A:
                totalDegree = faceCount * 3
                totalTris = faceCount
            else:
                totalDegree = readUInt(file)
                totalTris = readUInt(file)

            if state.logEluMeshNodes:
                print(f"Total Deg:          { totalDegree }")
                print(f"Total Tris:         { totalTris }")

            for f in range(faceCount):
                if version <= ELU_500A: degree = 3
                else: degree = readUInt(file)

                if state.logEluMeshNodes and state.logVerboseIndices:
                    print(f"Degree:             { degree }")
                    print()

                vindices = [0 for _ in range(degree)]
                nindices = [0 for _ in range(degree)]
                uv1indices = [0 for _ in range(degree)]
                uv2indices = [0 for _ in range(degree)]

                for d in range(degree): # why the uv and normal channels are stored swapped is beyond me, I was lucky to figure it out by mistake!
                    pos = readShort(file)
                    uv1 = readShort(file)
                    uv2 = readShort(file) if version >= ELU_500E else -1 # stored, but not valid until ELU_5011
                    nor = readShort(file)
                    skipBytes(file, 2 * 2) # skip bitangent and tangent indices

                    if version == ELU_5014:
                        skipBytes(file, 2) # skip unknown index, can be negative

                    if len(vertices) > 0    and pos >= len(vertices):   self.report({ 'ERROR' }, f"GZRS2: Vertex index out of bounds! { pos } { len(vertices) }");  #return { 'CANCELLED' }
                    if len(normals) > 0     and nor >= len(normals):    self.report({ 'ERROR' }, f"GZRS2: Normal index out of bounds! { nor } { len(normals) }");   #return { 'CANCELLED' }
                    if len(uv1s) > 0        and uv1 >= len(uv1s):       self.report({ 'ERROR' }, f"GZRS2: UV1 index out of bounds! { uv1 } { len(uv1s) }");         #return { 'CANCELLED' }
                    if len(uv2s) > 0        and uv2 >= len(uv2s):       self.report({ 'ERROR' }, f"GZRS2: UV2 index out of bounds! { uv2 } { len(uv2s) }");         #return { 'CANCELLED' }

                    vindices[d] = pos
                    nindices[d] = nor
                    uv1indices[d] = uv1
                    uv2indices[d] = uv2

                    if state.logEluMeshNodes and state.logVerboseIndices:
                        print("            {:>4}, {:>4}, {:>4}, {:>4}".format(pos, nor, uv1, uv2))

                slotID = readShort(file)
                slotIDs.add(slotID)

                if state.logEluMeshNodes:
                    totalSlotIDs.add(slotID)

                faces.append(EluFace(degree, tuple(vindices), tuple(nindices), tuple(uv1indices), tuple(uv2indices), slotID))

            if state.logEluMeshNodes and state.logVerboseIndices:
                print()

        slotIDs = tuple(sorted(slotIDs))
        if state.logEluMeshNodes:
            print("Slot IDs:           {{{}}}".format(', '.join(map(str, slotIDs))))

        isDummy = len(vertices) == 0 or len(faces) == 0
        if state.logEluMeshNodes:
            if isDummy: usesDummies = True
            print(f"Is Dummy:           { isDummy }")
            print()


        # RMeshNodeLoadImpl.cpp -> LoadVertexInfo()

        colors = readVec3Array(file, readInt(file))
        if state.logEluMeshNodes:
            output = "Colors:             {:<6d}".format(len(colors))
            output += "      Min: ({:>5.02f}, {:>5.02f}, {:>5.02f})     Max: ({:>5.02f}, {:>5.02f}, {:>5.02f})".format(*vecArrayMinMax(colors, 3)) if len(colors) > 0 else ''
            print(output)

        matID = readInt(file)
        if state.logEluMeshNodes:
            matIDs.add(matID)
            print(f"Material ID:        { matID }")

        weights = []
        weightCount = readUInt(file)

        if state.logEluMeshNodes and weightCount > 0:
            if weightCount > 0:
                minWeightValue = float('inf')
                maxWeightValue = float('-inf')
                minWeightID = -1
                maxWeightID = -1

                if state.logVerboseWeights:
                    print()

        for _ in range(weightCount):
            degree = readUInt(file)
            meshIDs = [0 for _ in range(degree)]
            values = [0 for _ in range(degree)]

            for d in range(degree):
                skipBytes(file, 2) # skip unused id
                meshIDs[d] = readShort(file)
                values[d] = readFloat(file)

            meshIDs = tuple(meshIDs)
            values = tuple(values)

            if state.logEluMeshNodes:
                for d in range(degree):
                    weightValue = values[d]
                    weightID = meshIDs[d]

                    weightIDs.add(weightID)

                    if state.logEluMeshNodes:
                        if weightValue < minWeightValue:
                            minWeightValue = weightValue
                            minWeightID = weightID

                        if weightValue > maxWeightValue:
                            maxWeightValue = weightValue
                            maxWeightID = weightID

                        if state.logVerboseWeights:
                            print("Weight:             {:>1d}/{:>1d}, {:>6.03f}, {:>2d}".format(d + 1, degree, weightValue, weightID))

            weights.append(EluWeight(degree, None, meshIDs, values, None))

        if state.logEluMeshNodes:
            if state.logVerboseWeights:
                print()

            output = "Weights:            {:<6d}".format(weightCount)
            output += "      Min:  {:>5.02f}  {:<14d}    Max:  {:>5.02f}  {:<14d}".format(minWeightValue, minWeightID, maxWeightValue, maxWeightID) if weightCount > 0 else ''
            print(output)


        # RMeshNodeLoadImpl.cpp -> LoadEtc()

        if version <= ELU_5012:
            boneIndexCount = readUInt(file)
            if state.logEluMeshNodes:
                print(f"Bone Indices:       { boneIndexCount }")

            skipBytes(file, (4 * 4 * 4 + 2) * boneIndexCount) # skip bone etc matrices and indices

            '''
            boneIndexCount = readUInt(file)
            if state.logEluMeshNodes:
                print(f"Bone Indices:       { boneIndexCount }")

                if state.logVerboseIndices:
                    print()

            boneIndices = []

            for i in range(boneIndexCount):
                pos = readUShort(file)
                nor = readUShort(file)
                uv1 = readUShort(file)
                uv2 = readUShort(file) if version >= ELU_500E else -1 # stored, but not valid until ELU_5011
                skipBytes(file, 2 + 2) # skip bitangent and tangent indices

                if len(vertices) > 0 and pos >= len(vertices): self.report({ 'ERROR' }, f"GZRS2: Vertex index out of bounds! { pos } { len(vertices) }"); return { 'CANCELLED' }
                if len(normals) > 0 and nor >= len(normals): self.report({ 'ERROR' }, f"GZRS2: Normal index out of bounds! { nor } { len(normals) }"); return { 'CANCELLED' }
                if len(uv1s) > 0 and uv1 >= len(uv1s): self.report({ 'ERROR' }, f"GZRS2: UV1 index out of bounds! { uv1 } { len(uv1s) }"); return { 'CANCELLED' }
                if version >= ELU_500E and len(uv2s) > 0 and uv2 >= len(uv2s): self.report({ 'ERROR' }, f"GZRS2: UV2 index out of bounds! { uv2 } { len(uv2s) }"); return { 'CANCELLED' }

                if state.logEluMeshNodes and state.logVerboseIndices:
                    print("                     {:>4}, {:>4}, {:>4}, {:>4}".format(pos, nor, uv1, uv2))

                boneIndices.append(EluIndex(pos, nor, uv1, uv2))

            if state.logEluMeshNodes and state.logVerboseIndices:
                print()

            boneIndices = tuple(boneIndices)
            '''
        else:
            skipBytes(file, 4) # skip primitive type

        vertIndexCount = readUInt(file)
        if state.logEluMeshNodes:
            print(f"Etc Vert Indices:   { vertIndexCount }")

        # skip secondary vertex indices
        if   version <= ELU_500D:   skipBytes(file, 2 * 5 * vertIndexCount)
        elif version <  ELU_5014:   skipBytes(file, 2 * 6 * vertIndexCount)
        else:                       skipBytes(file, 2 * 7 * vertIndexCount)

        if version <= ELU_5012:
            if version <= ELU_500A:
                faceIndexCount = faceCount * 3
            else:
                skipBytes(file, 4) # skip primitive type
                faceIndexCount = readUInt(file)

            if state.logEluMeshNodes:
                print(f"Etc Face Indices:   { faceIndexCount }")

            skipBytes(file, 2 * faceIndexCount) # skip secondary face indices

        if version >= ELU_5013:
            skipBytes(file, (4 * 4 * 4 + 2) * readUInt(file)) # skip bone etc matrices and indices

        slots = []
        slotCount = readUInt(file)

        if state.logEluMeshNodes:
            print(f"Material Slots:     { slotCount }")

        for _ in range(slotCount):
            slotID = readInt(file)
            indexOffset = readUShort(file)
            faceCount = readUShort(file)
            maskID = readInt(file)

            if state.logEluMeshNodes:
                print("                     {:>4}, {:>4}, {:>4}, {:>4}".format(slotID, indexOffset, faceCount, maskID))

            slots.append(EluSlot(slotID, indexOffset, faceCount, maskID))

        if version >= ELU_5013:
            skipBytes(file, 2 * readUInt(file)) # skip secondary face indices

        if version >= ELU_500C:
            skipBytes(file, 4 * 3 * 2) # skip bounding box

        if state.logEluMeshNodes:
            print()

        state.eluMeshes.append(EluMeshNode(path, version, meshName, parentName, drawFlags, localMatrix,
                                           vertices, normals, uv1s, uv2s,
                                           colors, tuple(faces), tuple(weights), tuple(slots),
                                           slotIDs, isDummy, matID))

    if state.logEluMeshNodes:
        print("===== Mesh Summary =====")
        print()

        print(f"Uses Dummies:       { usesDummies }")
        print(f"Slot IDs:           { totalSlotIDs }")
        print(f"Material IDs:       { matIDs }")
        print(f"Weight IDs:         { weightIDs }")
        print()
