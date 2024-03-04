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

def readElu(self, path, state):
    file = io.open(path, 'rb')
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
        file.close()

        return { 'CANCELLED' }

    if version not in ELU_IMPORT_VERSIONS:
        self.report({ 'ERROR' }, f"GZRS2: Importing this ELU version is not supported yet! Model will not load properly! { path }, { hex(version) }")
        file.close()

        return { 'CANCELLED' }

    if version <= ELU_5007: # GunZ 1 R_Mesh_Load.cpp
        if version == ELU_0:
            readEluRS2Meshes(self, path, file, version, meshCount, state)
            readEluRS2Materials(self, path, file, version, matCount, state)
        else:
            readEluRS2Materials(self, path, file, version, matCount, state)
            readEluRS2Meshes(self, path, file, version, meshCount, state)
    else: # GunZ 2 RMesh.cpp
        readEluRS3Meshes(self, path, file, version, meshCount, state)

    if state.logEluHeaders or state.logEluMats or state.logEluMeshNodes:
        bytesRemaining = fileSize - file.tell()

        if bytesRemaining > 0:
            self.report({ 'INFO' }, f"GZRS2: ELU import finished with bytes remaining! { path }, { hex(id) }, { hex(version) }")

        print(f"Bytes Remaining:    { bytesRemaining }")
        print()

    file.close()

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

    for m in range(matCount):
        matID = readInt(file)
        subMatID = readInt(file)

        if state.logEluMats:
            print(f"===== Material { m + 1 } =====")
            print(f"Mat ID:             { matID }")
            print(f"Sub Mat ID:         { subMatID }")
            print()

        ambient = readVec4(file)
        diffuse = readVec4(file)
        specular = readVec4(file)
        power = readFloat(file)

        if version <= ELU_5002:
            if power == 20:
                power = 0
        else:
            power *= 100

        if state.logEluMats:
            print("Ambient:            ({:>5.03f}, {:>5.03f}, {:>5.03f}, {:>5.03f})".format(*ambient))
            print("Diffuse:            ({:>5.03f}, {:>5.03f}, {:>5.03f}, {:>5.03f})".format(*diffuse))
            print("Specular:           ({:>5.03f}, {:>5.03f}, {:>5.03f}, {:>5.03f})".format(*specular))
            print(f"Power:              { power }")
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

        frameCount, frameSpeed, frameGap = 0, 0, 0.0

        if texpath:
            texDir = os.path.dirname(texpath)
            texBase = os.path.basename(texpath)
            texName, texExt = os.path.splitext(texBase)
            isAniTex = texBase.startswith("txa")

            if state.logEluMats:
                print(f"Texture Base:       { texBase }")
                print(f"Name:               { texName }")
                print(f"Extension:          { texExt }")
                print(f"Directory:          { texDir }")
                print(f"Is Animated:        { isAniTex }")
                print()

            if isAniTex:
                texName = texName[:len(texName) - 2]
                texParams = texName.replace('_', ' ').split(' ')

                if len(texParams) < 4:
                    self.report({ 'ERROR' }, f"GZRS2: Unable to split animated texture name! { texName }, { texParams } ")
                    file.close()

                    return { 'CANCELLED' }

                try:
                    frameCount, frameSpeed = int(texParams[1]), int(texParams[2])
                except ValueError:
                    self.report({ 'ERROR' }, f"GZRS2: Animated texture name must use integers for frame count and speed! { texName } ")
                    file.close()

                    return { 'CANCELLED' }
                else:
                    frameGap = frameSpeed / frameCount

                if state.logEluMats:
                    print(f"Frame Count:        { frameCount }")
                    print(f"Frame Speed:        { frameSpeed }")
                    print(f"Frame Gap:          { frameGap }")
                    print()

        state.eluMats.append(EluMaterial(path, matID, subMatID,
                                         ambient, diffuse, specular, power,
                                         subMatCount, texpath, alphapath,
                                         twosided, additive, alphatest, useopacity,
                                         texBase, texName, texExt, texDir,
                                         isAniTex, frameCount, frameSpeed, frameGap))

def readEluRS2Meshes(self, path, file, version, meshCount, state):
    if version == ELU_0:
        meshCount = readUShort(file)

    if state.logEluMeshNodes and meshCount > 0:
        print()
        print("=========  Elu Mesh Nodes  ========")
        print()
        if version == ELU_0:
            print(f"Mesh Count:         { meshCount }")
            print()

        usesDummies = False
        matIDs = set()
        weightIDs = set()
        weightNames = set()

    reorientWorld = Matrix.Rotation(math.radians(-90.0), 4, 'X')

    for m in range(meshCount):
        if version == ELU_0:
            meshName = readString(file, readUShort(file))
            parentName = readString(file, readUShort(file))
            skipBytes(file, 4 * 3 + 4 * 4 * 4 * 3 + 4) # skip precalculated transform information
            worldMatrix = reorientWorld @ readTransform(file, state.convertUnits, True)
            skipBytes(file, 4 * 4 * 4 + 4 * 3 + 4 + 4 * 4 * 4 * 3 + 4 * 3 + 4 * 4 * 4) # skip precalculated transform information
        else:
            meshName = readString(file, ELU_NAME_LENGTH)
            parentName = readString(file, ELU_NAME_LENGTH)
            worldMatrix = reorientWorld @ readTransform(file, state.convertUnits, True)

            if version >= ELU_5001: skipBytes(file, 4 * 3) # skip ap scale
            if version >= ELU_5003: skipBytes(file, 4 * 4 + 4 * 4 + 4 * 4 * 4) # skip rotation aa, scale aa and etc matrix

        if state.logEluMeshNodes:
            print(f"===== Mesh { m + 1 } =====")
            print(f"Mesh Name:          { meshName }")
            print(f"Parent Name:        { parentName }")
            print("World Matrix:       ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*worldMatrix[0]))
            print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*worldMatrix[1]))
            print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*worldMatrix[2]))
            print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*worldMatrix[3]))
            print()

        vertices = readCoordinateArray(file, readUInt(file), state.convertUnits, True)
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

                if version == ELU_0 or version >= ELU_5002: skipBytes(file, 4) # skip signature ID

                faces.append(EluFace(3, indices, None, tuple(i for i in range(f * 3, f * 3 + 3)), (), slotID))

                if state.logEluMeshNodes and state.logVerboseIndices:
                    print("                     {:>4}, {:>4}, {:>4}".format(*indices))

            if version == ELU_0 or version >= ELU_5005:
                normals = [Vector((0, 0, 0)) for _ in range(faceCount * 3)]

                for f, face in enumerate(faces):
                    skipBytes(file, 4 * 3) # skip face normal
                    normals[f * 3 + 0] = readDirection(file, True)
                    normals[f * 3 + 1] = readDirection(file, True)
                    normals[f * 3 + 2] = readDirection(file, True)

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

        eluMatID = readInt(file)
        if state.logEluMeshNodes:
            matIDs.add(eluMatID)
            print(f"Material ID:        { eluMatID }")

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
                degree = readUChar(file)
                meshIDs = [0 for d in range(degree)]
                values = [0.0 for d in range(degree)]
                offsets = [Vector((0.0, 0.0, 0.0)) for d in range(degree)]
                meshNames = ['' for d in range(degree)]

                for d in range(degree):
                    meshIDs[d] = readUInt(file)
                    values[d] = readFloat(file)
                    offsets[d] = readVec3(file)
                    meshNames[d] = readString(file, readUShort(file))

                meshIDs = tuple(meshIDs)
                values = tuple(values)
                offsets = tuple(offsets)
                meshNames = tuple(meshNames)
            else:
                meshNames = tuple(readString(file, ELU_NAME_LENGTH) for _ in range(ELU_PHYS_KEYS))
                values = readFloatArray(file, ELU_PHYS_KEYS)
                meshIDs = readUIntArray(file, ELU_PHYS_KEYS)
                degree = readUInt(file)
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
                        print("Weight:             {:>1d}, {:>6.03f}, {:>2d}, {:<16s}    ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(degree, weightValue, weightID, weightName, *weightOffset))

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
                                           slotIDs, isDummy, eluMatID))

    if state.logEluMeshNodes:
        print(f"Uses Dummies:       { usesDummies }")
        print(f"Material IDs:       { matIDs }")
        print(f"Weight IDs:         { weightIDs }")
        print(f"Weight Names:       { weightNames }")
        print()

def readEluRS3Meshes(self, path, file, version, meshCount, state):
    if state.logEluMeshNodes and meshCount > 0:
        print()
        print("=========  Elu Mesh Nodes  ========")
        print()

    for m in range(meshCount):
        meshName = readString(file, readUInt(file))
        parentName = readString(file, readUInt(file))

        if state.logEluMeshNodes:
            print(f"===== Mesh { m + 1 } =====")
            print(f"Mesh Name:          { meshName }")
            print(f"Parent Name:        { parentName }")

        # meshID = readInt(file)
        # if state.logEluMeshNodes: print(f"Mesh ID:        { meshID }")
        skipBytes(file, 4) # skip unused mesh ID

        # RMeshNodeLoadImpl.cpp -> LoadInfo()
        drawFlags = readUInt(file)
        if state.logEluMeshNodes: print(f"Draw Flags:         { drawFlags }")

        # meshAlign = RMESH_ALIGN[readUInt(file)]
        # if state.logEluMeshNodes: print(f"Mesh Align:         { meshAlign }")
        skipBytes(file, 4) # skip mesh align

        if version < ELU_500A:
            skipBytes(file, 4 * 3) # skip unused bodypart info

        localMatrix = readTransform(file, state.convertUnits, False)

        if state.logEluMeshNodes:
            print("Local Matrix:       ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*localMatrix[0]))
            print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*localMatrix[1]))
            print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*localMatrix[2]))
            print("                    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*localMatrix[3]))

        # visibility = readFloat(file) if version >= ELU_500A else None
        skipBytes(file, 4) # skip visibility

        # lightmapID = -1

        # RMeshNodeLoadImpl.cpp -> LoadVertex()
        if version < ELU_5011:
            if version >= ELU_500D: skipBytes(file, 4) # skip FVF flags
            if version >= ELU_500E:
                # lightmapID = readInt(file)
                skipBytes(file, 4) # skip lightmap ID

        if state.logEluMeshNodes:
            # print(f"Visibility:         { visibility }")
            # print(f"Lightmap ID:        { lightmapID }")
            print()

        vertexCount = readUInt(file)
        vertices = readCoordinateArray(file, vertexCount, state.convertUnits, False)
        if state.logEluMeshNodes:
            output = "Vertices:           {:<6d}".format(vertexCount)
            output += "      Min: ({:>5.02f}, {:>5.02f}, {:>5.02f})     Max: ({:>5.02f}, {:>5.02f}, {:>5.02f})".format(*vecArrayMinMax(vertices, 3)) if vertexCount > 0 else ''
            print(output)

        normalCount = readUInt(file)
        normals = readDirectionArray(file, normalCount, False)
        if state.logEluMeshNodes:
            output = "Normals:            {:<6d}".format(normalCount)
            output += "      Min: ({:>5.02f}, {:>5.02f}, {:>5.02f})     Max: ({:>5.02f}, {:>5.02f}, {:>5.02f})".format(*vecArrayMinMax(normals, 3)) if normalCount > 0 else ''
            print(output)

        if version < ELU_500F: skipBytes(file, 4 * 3 * readUInt(file)) # skip tangents
        else: skipBytes(file, 4 * 4 * readUInt(file)) # skip tangents

        skipBytes(file, 4 * 3 * readUInt(file)) # skip bitangents

        uv1s = readUV3Array(file, readUInt(file)) # skips invalid z-coordinate
        if state.logEluMeshNodes:
            output = "UV1s:               {:<6d}".format(len(uv1s))
            output += "      Min: ({:>5.02f}, {:>5.02f})            Max: ({:>5.02f}, {:>5.02f})".format(*vecArrayMinMax(uv1s, 2)) if len(uv1s) > 0 else ''
            print(output)

        uv2s = ()

        if version == ELU_500E or version == ELU_500F: skipBytes(file, 4 * 3 * readUInt(file)) # skip lightmap uvs
        elif version >= ELU_5011: uv2s = readUV3Array(file, readUInt(file)) # skips invalid z-coordinate
        if state.logEluMeshNodes:
            output = "UV2s:               {:<6d}".format(len(uv2s))
            output += "      Min: ({:>5.02f}, {:>5.02f})            Max: ({:>5.02f}, {:>5.02f})".format(*vecArrayMinMax(uv2s, 2)) if len(uv2s) > 0 else ''
            print(output)

        # LoadFace()
        faceCount = readUInt(file)
        faces = []
        slotIDs = set()
        if state.logEluMeshNodes:
            print(f"Faces:              { faceCount }")

        if faceCount > 0:
            if version < ELU_500B:
                totalDegree = faceCount * 3
                totalTris = faceCount
            else:
                totalDegree = readUInt(file)
                totalTris = readUInt(file)

            if state.logEluMeshNodes:
                print(f"Total Deg:          { totalDegree }")
                print(f"Total Tris:         { totalTris }")

            for f in range(faceCount):
                if version < ELU_500B: degree = 3
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

                    if len(vertices) > 0 and    pos >= len(vertices):   self.report({ 'ERROR' }, f"GZRS2: Vertex index out of bounds! { pos } { len(vertices) }");  file.close(); return { 'CANCELLED' }
                    if len(normals) > 0 and     nor >= len(normals):    self.report({ 'ERROR' }, f"GZRS2: Normal index out of bounds! { nor } { len(normals) }");   file.close(); return { 'CANCELLED' }
                    if len(uv1s) > 0 and        uv1 >= len(uv1s):       self.report({ 'ERROR' }, f"GZRS2: UV1 index out of bounds! { uv1 } { len(uv1s) }");         file.close(); return { 'CANCELLED' }
                    if version >= ELU_5011:
                        if len(uv2s) > 0 and    uv2 >= len(uv2s):       self.report({ 'ERROR' }, f"GZRS2: UV2 index out of bounds! { uv2 } { len(uv2s) }");         file.close(); return { 'CANCELLED' }

                    vindices[d] = pos
                    nindices[d] = nor
                    uv1indices[d] = uv1
                    uv2indices[d] = uv2

                    if state.logEluMeshNodes and state.logVerboseIndices:
                        print("            {:>4}, {:>4}, {:>4}, {:>4}".format(pos, nor, uv1, uv2))

                slotID = readShort(file)
                slotIDs.add(slotID)

                faces.append(EluFace(degree, tuple(vindices), tuple(nindices), tuple(uv1indices), tuple(uv2indices), slotID))

            if state.logEluMeshNodes and state.logVerboseIndices:
                print()

        slotIDs = tuple(sorted(slotIDs))
        if state.logEluMeshNodes:
            print("Slot IDs:           {{{}}}".format(', '.join(map(str, slotIDs))))

        # LoadVertexInfo
        colors = readVec3Array(file, readUInt(file))
        if state.logEluMeshNodes:
            output = "Colors:             {:<6d}".format(len(colors))
            output += "      Min: ({:>5.02f}, {:>5.02f}, {:>5.02f})     Max: ({:>5.02f}, {:>5.02f}, {:>5.02f})".format(*vecArrayMinMax(colors, 3)) if len(colors) > 0 else ''
            print(output)

        isDummy = len(vertices) == 0 or len(faces) == 0
        if state.logEluMeshNodes:
            print(f"Is Dummy:           { isDummy }")
            print()

        eluMatID = readInt(file)
        if state.logEluMeshNodes: print(f"Material ID:        { eluMatID }")

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
                meshID = readShort(file)
                value = readFloat(file)

                values[d] = value
                meshIDs[d] = meshID

                if state.logEluMeshNodes:
                    if value < minWeightValue:
                        minWeightValue = value
                        minWeightID = meshID

                    if value > maxWeightValue:
                        maxWeightValue = value
                        maxWeightID = meshID
                    
                    if state.logVerboseWeights:
                        print("Weight:             {:>1d}, {:>6.03f}, {:>2d}".format(degree, values[d], meshIDs[d]))

            weights.append(EluWeight(degree, None, tuple(meshIDs), tuple(values), None))

        weights = tuple(weights)
        if state.logEluMeshNodes:
            if state.logVerboseWeights:
                print()

            output = "Weights:            {:<6d}".format(weightCount)
            output += "      Min:  {:>5.02f}  {:<14d}    Max:  {:>5.02f}  {:<14d}".format(minWeightValue, minWeightID, maxWeightValue, maxWeightID) if weightCount > 0 else ''
            print(output)

        # LoadEtc
        for _ in range(readUInt(file)): skipBytes(file, 4 * 4 * 4 + 2) # skip bone etc matrices and indices

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

            if len(vertices) > 0 and pos >= len(vertices): self.report({ 'ERROR' }, f"GZRS2: Vertex index out of bounds! { pos } { len(vertices) }"); file.close(); return { 'CANCELLED' }
            if len(normals) > 0 and nor >= len(normals): self.report({ 'ERROR' }, f"GZRS2: Normal index out of bounds! { nor } { len(normals) }"); file.close(); return { 'CANCELLED' }
            if len(uv1s) > 0 and uv1 >= len(uv1s): self.report({ 'ERROR' }, f"GZRS2: UV1 index out of bounds! { uv1 } { len(uv1s) }"); file.close(); return { 'CANCELLED' }
            if version >= ELU_500E and len(uv2s) > 0 and uv2 >= len(uv2s): self.report({ 'ERROR' }, f"GZRS2: UV2 index out of bounds! { uv2 } { len(uv2s) }"); file.close(); return { 'CANCELLED' }

            if state.logEluMeshNodes and state.logVerboseIndices:
                print("                     {:>4}, {:>4}, {:>4}, {:>4}".format(pos, nor, uv1, uv2))

            boneIndices.append(EluIndex(pos, nor, uv1, uv2))

        if state.logEluMeshNodes and state.logVerboseIndices:
            print()

        boneIndices = tuple(boneIndices)
        '''

        skipBytes(file, 2 * 6 * readUInt(file)) # skip secondary vertex indices

        if version < ELU_500B:
            triangleIndexCount = faceCount * 3
        else:
            skipBytes(file, 4) # skip primitive type
            triangleIndexCount = readUInt(file)

        '''
        if state.logEluMeshNodes: print(f"Tri Indices:        { triangleIndexCount }")
        triangleIndices = readUShortArray(file, triangleIndexCount)
        '''

        skipBytes(file, 2 * triangleIndexCount) # skip triangle indices

        slotCount = readUInt(file)
        slots = []
        if state.logEluMeshNodes: print(f"Material Slots:     { slotCount }")

        for _ in range(slotCount):
            slotID = readInt(file)
            indexOffset = readUShort(file)
            faceCount = readUShort(file)
            maskID = readInt(file)

            if state.logEluMeshNodes:
                print("                     {:>4}, {:>4}, {:>4}, {:>4}".format(slotID, indexOffset, faceCount, maskID))

            slots.append(EluSlot(slotID, indexOffset, faceCount, maskID))

        if version >= ELU_500C: skipBytes(file, 4 * 3 * 2) # skip bounding box

        if state.logEluMeshNodes: print()

        state.eluMeshes.append(EluMeshNode(path, version, meshName, parentName, drawFlags, localMatrix,
                                           vertices, normals, uv1s, uv2s,
                                           colors, tuple(faces), tuple(weights), tuple(slots),
                                           slotIDs, isDummy, eluMatID))
