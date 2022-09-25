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

import math

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .io_gzrs2 import *

def readElu(self, path, state: GZRS2State):
    file = open(path, 'rb')

    id = readUInt(file)
    version = readUInt(file)
    matCount = readInt(file)
    meshCount = readInt(file)

    if state.logEluHeaders or state.logEluMats or state.logEluMeshNodes:
        print("===================  Read Elu  ===================")
        print()

    if state.logEluHeaders:
        print(f"Path:           { path }")
        print(f"ID:             { hex(id) }")
        print(f"Version:        { hex(version) }")
        print(f"Mat Count:      { matCount }")
        print(f"Mesh Count:     { meshCount }")

    if state.logEluHeaders or state.logEluMats or state.logEluMeshNodes:
        print()

    if id != ELU_ID or not version in ELU_VERSIONS:
        self.report({ 'ERROR' }, f"GZRS2: ELU header invalid! { id }, { hex(version) }")
        file.close()

        return

    if not version in ELU_SUPPORTED_VERSIONS:
        self.report({ 'ERROR' }, f"GZRS2: ELU version is not supported yet! Model will not load properly! { path }, { hex(version) }")
        file.close()

        return

    if version == ELU_0: # GunZ 1 Alpha?
        matCount = 0 # always -1
        meshCount = 1 # always -1

        skipBytes(file, 2) # skip unknown short
        skipBytes(file, readUShort(file)) # skip unknown string
        skipBytes(file, 2) # skip unknown short

        # TODO: finish ELU_0 import!
    elif version <= ELU_5007: # GunZ 1 R_Mesh_Load.cpp
        if state.logEluMats and matCount > 0:
            print()
            print("=========  Elu Materials  =========")
            print()

        for m in range(matCount):
            if state.logEluMats: print(f"===== Material { m + 1 } =====")

            matID = readUInt(file)
            subMatID = readInt(file)

            if state.logEluMats:
                print(f"Mat ID:           { matID }")
                print(f"Sub Mat ID:       { subMatID }")
                print()

            ambient = readVec4(file)
            diffuse = readVec4(file)
            specular = readVec4(file)
            power = readFloat(file)

            if version <= ELU_5002:
                if power == 20:
                    power = 0
            else:
                power = power * 100

            if state.logEluMats:
                print("Ambient:         ({:>5.03f}, {:>5.03f}, {:>5.03f}, {:>5.03f})".format(*ambient))
                print("Diffuse:         ({:>5.03f}, {:>5.03f}, {:>5.03f}, {:>5.03f})".format(*diffuse))
                print("Specular:        ({:>5.03f}, {:>5.03f}, {:>5.03f}, {:>5.03f})".format(*specular))
                print(f"Power:            { power }")
                print()

            subMatCount = readUInt(file)

            if version <= ELU_5005:
                texPath = readPath(file, ELU_NAME_LENGTH)
                alphaPath = readPath(file, ELU_NAME_LENGTH)
            else:
                texPath = readPath(file, ELU_PATH_LENGTH)
                alphaPath = readPath(file, ELU_PATH_LENGTH)

            if state.logEluMats:
                print(f"Sub Mat Count:    { subMatCount }")
                print(f"Texture Path:     { texPath }")
                print(f"Alpha Path:       { alphaPath }")
                print()

            twosided, additive, alphatest = False, False, None

            if version >= ELU_5002: twosided = readBool32(file)
            if version >= ELU_5004: additive = readBool32(file)
            if version >= ELU_5007: alphatest = readUInt(file)

            if alphatest is not None and alphatest > 0:
                useopacity = False
            else:
                useopacity = alphaPath != '' and texPath.endswith(".tga")

            if state.logEluMats:
                print(f"Two-sided:        { twosided }")
                print(f"Additive:         { additive }")
                print(f"Alpha Test:       { alphatest }")
                print(f"Use Opacity:      { useopacity }")
                print()

            frameCount, frameSpeed, frameGap = 0, 0, 0.0

            # RMtrl::CheckAniTexture
            if texPath:
                texDir = os.path.dirname(texPath)
                texBase = os.path.basename(texPath)
                texName, texExt = os.path.splitext(texBase)
                isAniTex = texBase.startswith("txa")
                aniTexFrames = [] if isAniTex else None

                if state.logEluMats:
                    print(f"Texture Base:     { texBase }")
                    print(f"Name:             { texName }")
                    print(f"Extension:        { texExt }")
                    print(f"Directory:        { texDir }")
                    print(f"Is Animated:      { isAniTex }")
                    print()

                if isAniTex:
                    texName = texName[:len(texName) - 2]
                    texParams = texName.replace('_', ' ').split(' ')

                    if len(texParams) < 4:
                        self.report({ 'ERROR' }, f"GZRS2: Unable to split animated texture name! { texName }, { texParams } ")
                        file.close()

                        return

                    try:
                        frameCount, frameSpeed = int(texParams[1]), int(texParams[2])
                    except ValueError:
                        self.report({ 'ERROR' }, f"GZRS2: Animated texture name must use integers for frame count and speed! { texName } ")
                        file.close()

                        return
                    else:
                        frameGap = frameSpeed / frameCount

                    if state.logEluMats:
                        print(f"Frame Count:      { frameCount }")
                        print(f"Frame Speed:      { frameSpeed }")
                        print(f"Frame Gap:        { frameGap }")

            state.eluMats.append(EluMaterial(matID, subMatID,
                                             ambient, diffuse, specular, power,
                                             subMatCount, texPath, alphaPath,
                                             twosided, additive, alphatest, useopacity,
                                             texBase, texName, texExt, texDir,
                                             isAniTex, frameCount, frameSpeed, frameGap))

        EluMeshRoot = None

        if state.logEluMeshNodes and meshCount > 0:
            print()
            print("=========  Elu Mesh Nodes  ========")
            print()

        for m in range(meshCount):
            if state.logEluMeshNodes: print(f"===== Mesh { m + 1 } =====")

            meshName = readString(file, ELU_NAME_LENGTH)
            if state.logEluMeshNodes: print(f"Mesh Name:        { meshName }")

            parentName = readString(file, ELU_NAME_LENGTH)
            if state.logEluMeshNodes: print(f"Parent Name:      { parentName }")

            worldMatrix = readTransform(file, state.convertUnits, True)
            worldMatrix = Matrix.Rotation(math.radians(-90.0), 4, 'X') @ worldMatrix

            if state.logEluMeshNodes:
                print("World Matrix:    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.02f})".format(*worldMatrix[0]))
                print("                 ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.02f})".format(*worldMatrix[1]))
                print("                 ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.02f})".format(*worldMatrix[2]))
                print("                 ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.02f})".format(*worldMatrix[3]))

            if version >= ELU_5001: skipBytes(file, 4 * 3) # skip ap scale
            if version >= ELU_5003: skipBytes(file, 4 * 4 + 4 * 4 + 4 * 4 * 4) # skip rotation aa, scale aa and etc matrix

            if state.logEluMeshNodes: print()

            vertices = readCoordinateArray(file, readUInt(file), state.convertUnits, True)
            if state.logEluMeshNodes:
                print(f"Vertices:         { len(vertices) }")
                '''for pos in vertices:
                    print("                 ({:>9.02f}, {:>9.02f}, {:>9.02f})".format(*pos))
                print()'''

            faceCount = readUInt(file)
            faces = []
            normals = []
            uv1s = [Vector((0, 0)) for _ in range(faceCount * 3)]
            if state.logEluMeshNodes: print(f"Faces:            { faceCount }")

            if faceCount > 0:
                for f in range(faceCount):
                    indices = readUIntArray(file, 3)
                    if state.logEluMeshNodes and state.logVerboseIndices:
                        print("                  {:>4}, {:>4}, {:>4}".format(*indices))

                    # skips unused z-coordinates
                    uv1s[f * 3 + 0] = readUV3(file)
                    uv1s[f * 3 + 1] = readUV3(file)
                    uv1s[f * 3 + 2] = readUV3(file)

                    subMatID = readInt(file)
                    if version >= ELU_5002: skipBytes(file, 4) # skip signature ID

                    faces.append(EluFace(3, indices, None, [i for i in range(f * 3, f * 3 + 3)], [], subMatID))

                if version >= ELU_5005:
                    normals = [Vector((0, 0, 0)) for _ in range(faceCount * 3)]

                    for f, face in enumerate(faces):
                        skipBytes(file, 4 * 3) # skip face normal
                        normals[f * 3 + 0] = readDirection(file, True)
                        normals[f * 3 + 1] = readDirection(file, True)
                        normals[f * 3 + 2] = readDirection(file, True)

                        face.inor = [i for i in range(f * 3, f * 3 + 3)]

            if state.logEluMeshNodes:
                print(f"UV1s:             { len(uv1s) }")
                '''for uv1 in uv1s:
                    print("                 ({:>6.03f}, {:>6.03f})".format(*uv1))
                    print("                 ({:>6.03f}, {:>6.03f})".format(*uv1))
                    print("                 ({:>6.03f}, {:>6.03f})".format(*uv1))
                    print()
                print()'''

                print(f"Normals:          { len(normals) }")
                '''for nor in normals:
                    print("                 ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*nor))
                    print("                 ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*nor))
                    print("                 ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*nor))
                    print()
                print()'''

            isDummy = len(vertices) == 0 or len(faces) == 0
            if state.logEluMeshNodes:
                print(f"Is Dummy:         { isDummy }")
                print()

            colors = readVec3Array(file, readUInt(file)) if version >= ELU_5005 else []
            if state.logEluMeshNodes:
                print(f"Colors:           { len(colors) }")
                '''for color in colors:
                    print("                 ({:>5.03f}, {:>5.03f}, {:>5.03f})".format(*color))
                print()'''

            matID = readUInt(file)
            if state.logEluMeshNodes: print(f"Material ID:      { matID }")

            weights = []
            weightCount = readUInt(file)
            if state.logEluMeshNodes: print(f"Weights:          { weightCount }")

            for _ in range(weightCount):
                meshNames = tuple(readString(file, ELU_NAME_LENGTH) for _ in range(ELU_PHYS_KEYS))
                values = readFloatArray(file, ELU_PHYS_KEYS)

                skipBytes(file, 4 * ELU_PHYS_KEYS) # skip unknown ids
                degree = readUInt(file)
                skipBytes(file, 4 * 3 * ELU_PHYS_KEYS) # skip offsets

                if state.logEluMeshNodes and state.logVerboseWeights:
                    print(f"Degree:           { degree }")
                    for d in range(degree):
                        print("                 {:>6.03f}, {:<40s}".format(values[d], meshNames[d]))

                weights.append(EluWeight(degree, meshNames, None, values))

            if state.logEluMeshNodes: print()

            state.eluMeshes.append(EluMeshNode(version, meshName, parentName, worldMatrix,
                                               vertices, normals, uv1s, [],
                                               colors, faces, weights,
                                               isDummy, matID))
    else: # GunZ 2 RMesh.cpp
        if state.logEluMeshNodes and meshCount > 0:
            print()
            print("=========  Elu Mesh Nodes  ========")
            print()

        for m in range(meshCount):
            if state.logEluMeshNodes: print(f"===== Mesh { m + 1 } =====")

            meshName = readString(file, readUInt(file))
            if state.logEluMeshNodes: print(f"Mesh Name:        { meshName }")

            parentName = readString(file, readUInt(file))
            if state.logEluMeshNodes: print(f"Parent Name:      { parentName }")

            # meshID = readInt(file)
            # if state.logEluMeshNodes: print(f"Mesh ID:        { meshID }")
            skipBytes(file, 4) # skip unused mesh ID


            # RMeshNodeLoadImpl.cpp
            # LoadInfo()
            '''drawFlags = readUInt(file)
            print(f"Draw Flags:       { drawFlags }")
            meshAlign = RMESH_ALIGN[readUInt(file)]
            print(f"Mesh Align:       { meshAlign }")'''
            skipBytes(file, 4 + 4) # skip draw flags & mesh align

            if version < ELU_500A:
                skipBytes(file, 4 * 3) # skip unused bodypart info

            localMatrix = readTransform(file, state.convertUnits, False)

            if state.logEluMeshNodes:
                print("Local Matrix:    ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.02f})".format(*localMatrix[0]))
                print("                 ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.02f})".format(*localMatrix[1]))
                print("                 ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.02f})".format(*localMatrix[2]))
                print("                 ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.02f})".format(*localMatrix[3]))

            # visibility = readFloat(file) if version >= ELU_500A else None
            # lightmapID = -1
            skipBytes(file, 4) # skip visibility

            # LoadVertex()
            if version < ELU_5011:
                if version >= ELU_500D: skipBytes(file, 4) # skip FVF flags
                # if version >= ELU_500E: lightmapID = readInt(file)
                if version >= ELU_500E: skipBytes(file, 4) # skip lightmap ID

            '''if state.logEluMeshNodes:
                print(f"Visibility:       { visibility }")
                print(f"Lightmap ID:      { lightmapID }")
                print()'''

            vertices = readCoordinateArray(file, readUInt(file), state.convertUnits, False)
            if state.logEluMeshNodes:
                print(f"Vertices:         { len(vertices) }")
                '''for pos in vertices:
                    print("                 ({:>9.02f}, {:>9.02f}, {:>9.02f})".format(*pos))
                print()'''

            normals = readDirectionArray(file, readUInt(file), False)
            if state.logEluMeshNodes:
                print(f"Normals:          { len(normals) }")
                '''for nor in normals:
                    print("                 ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*nor))
                    print("                 ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*nor))
                    print("                 ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*nor))
                    print()
                print()'''

            if version < ELU_500F: skipBytes(file, 4 * 3 * readUInt(file)) # skip tangents
            else: skipBytes(file, 4 * 4 * readUInt(file)) # skip tangents

            skipBytes(file, 4 * 3 * readUInt(file)) # skip bitangents

            uv1s = readUV3Array(file, readUInt(file)) # skips invalid z-coordinate
            if state.logEluMeshNodes:
                print(f"UV1s:             { len(uv1s) }")
                '''for uv1 in uv1s:
                    print("                 ({:>6.03f}, {:>6.03f})".format(*uv1))
                    print("                 ({:>6.03f}, {:>6.03f})".format(*uv1))
                    print("                 ({:>6.03f}, {:>6.03f})".format(*uv1))
                    print()
                print()'''

            uv2s = []

            if version == ELU_500E or version == ELU_500F: skipBytes(file, 4 * 3 * readUInt(file)) # skip lightmap uvs
            elif version >= ELU_5011: uv2s = readUV3Array(file, readUInt(file)) # skips invalid z-coordinate
            if state.logEluMeshNodes:
                print(f"UV2s:             { len(uv2s) }")
                '''for uv2 in uv2s:
                    print("                 ({:>6.03f}, {:>6.03f})".format(*uv2))
                    print("                 ({:>6.03f}, {:>6.03f})".format(*uv2))
                    print("                 ({:>6.03f}, {:>6.03f})".format(*uv2))
                    print()'''

            # LoadFace()
            faceCount = readUInt(file)
            faces = []
            if state.logEluMeshNodes: print(f"Faces:            { faceCount }")

            if faceCount > 0:
                if version < ELU_500B:
                    totalDegree = faceCount * 3
                    totalTris = faceCount
                else:
                    totalDegree = readUInt(file)
                    totalTris = readUInt(file)

                if state.logEluMeshNodes:
                    print(f"Total Deg:        { totalDegree }")
                    print(f"Total Tris:       { totalTris }")

                for f in range(faceCount):
                    if version < ELU_500B: degree = 3
                    else: degree = readUInt(file)

                    if state.logEluMeshNodes and state.logVerboseIndices:
                        print(f"Degree:           { degree }")

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

                        if len(vertices) > 0 and pos >= len(vertices): self.report({ 'ERROR' }, f"GZRS2: Vertex index out of bounds! { pos } { len(vertices) }"); file.close(); return
                        if len(normals) > 0 and nor >= len(normals): self.report({ 'ERROR' }, f"GZRS2: Normal index out of bounds! { nor } { len(normals) }"); file.close(); return
                        if len(uv1s) > 0 and uv1 >= len(uv1s): self.report({ 'ERROR' }, f"GZRS2: UV1 index out of bounds! { uv1 } { len(uv1s) }"); file.close(); return
                        if version >= ELU_5011 and len(uv2s) > 0 and uv2 >= len(uv2s): self.report({ 'ERROR' }, f"GZRS2: UV2 index out of bounds! { uv2 } { len(uv2s) }"); file.close(); return

                        vindices[d] = pos
                        nindices[d] = nor
                        uv1indices[d] = uv1
                        uv2indices[d] = uv2

                        if state.logEluMeshNodes and state.logVerboseIndices:
                            print("                  {:>4}, {:>4}, {:>4}, {:>4}".format(pos, nor, uv1, uv2))

                    subMatID = readShort(file)

                    faces.append(EluFace(degree, vindices, nindices, uv1indices, uv2indices, subMatID))

            #LoadVertexInfo
            colors = readVec3Array(file, readUInt(file))
            if state.logEluMeshNodes:
                print(f"Colors:           { len(colors) }")
                '''for color in colors:
                    print("                 ({:>5.03f}, {:>5.03f}, {:>5.03f})".format(*color))
                print()'''

            isDummy = len(vertices) == 0 or len(faces) == 0
            if state.logEluMeshNodes:
                print(f"Is Dummy:         { isDummy }")
                print()

            matID = readInt(file)
            if state.logEluMeshNodes: print(f"Material ID:      { matID }")

            weights = []
            weightCount = readUInt(file)
            if state.logEluMeshNodes: print(f"Weights:          { weightCount }")

            for _ in range(weightCount):
                degree = readUInt(file)
                if state.logEluMeshNodes and state.logVerboseWeights:
                    print(f"Degree:           { degree }")

                meshIDs = [0 for _ in range(degree)]
                values = [0 for _ in range(degree)]

                for d in range(degree):
                    skipBytes(file, 2) # skip unused id
                    meshIDs[d] = readShort(file)
                    values[d] = readFloat(file)

                    if state.logEluMeshNodes and state.logVerboseWeights:
                        print("                  {:>6.03f}, {:>4}".format(values[d], meshIDs[d]))

                weights.append(EluWeight(degree, None, meshIDs, values))

            #LoadEtc
            for _ in range(readUInt(file)): skipBytes(file, 4 * 4 * 4 + 2) # skip bone etc matrices and indices

            '''
            indexCount = readUInt(file)
            if state.logEluMeshNodes: print(f"Indices:          { indexCount }")

            indices = []

            for i in range(indexCount):
                pos = readUShort(file)
                nor = readUShort(file)
                uv1 = readUShort(file)
                uv2 = readUShort(file) if version >= ELU_500E else -1 # stored, but not valid until ELU_5011
                skipBytes(file, 2 + 2) # skip bitangent and tangent indices

                if len(vertices) > 0 and pos >= len(vertices): self.report({ 'ERROR' }, f"GZRS2: Vertex index out of bounds! { pos } { len(vertices) }"); file.close(); return
                if len(normals) > 0 and nor >= len(normals): self.report({ 'ERROR' }, f"GZRS2: Normal index out of bounds! { nor } { len(normals) }"); file.close(); return
                if len(uv1s) > 0 and uv1 >= len(uv1s): self.report({ 'ERROR' }, f"GZRS2: UV1 index out of bounds! { uv1 } { len(uv1s) }"); file.close(); return
                if version >= ELU_500E and len(uv2s) > 0 and uv2 >= len(uv2s): self.report({ 'ERROR' }, f"GZRS2: UV2 index out of bounds! { uv2 } { len(uv2s) }"); file.close(); return

                if state.logEluMeshNodes and state.logVerboseIndices:
                    print("                   {:>4}, {:>4}, {:>4}, {:>4}".format(pos, nor, uv1, uv2))

                indices.append(EluIndex(pos, nor, uv1, uv2))
            '''

            skipBytes(file, 2 * 6 * readUInt(file)) # skip secondary vertex indices

            if version < ELU_500B:
                triangleIndexCount = faceCount * 3
            else:
                skipBytes(file, 4) # skip primitive type
                triangleIndexCount = readUInt(file)

            '''if state.logEluMeshNodes: print(f"Tri Indices:      { triangleIndexCount }")
            triangleIndices = readUShortArray(file, triangleIndexCount)
            '''

            skipBytes(file, 2 * triangleIndexCount) # skip triangle indices

            # skip material table data
            matTableCount = readUInt(file)
            if state.logEluMeshNodes: print(f"Mat Tables:       { matTableCount }")

            for _ in range(matTableCount):
                matID = readInt(file)
                offset = readUShort(file)
                count = readUShort(file)
                maskID = readUInt(file) if version >= ELU_5008 else -1

                if state.logEluMeshNodes:
                    print("                  {:>4}, {:>4}, {:>4}, {:>4}".format(matID, offset, count, maskID))

            if version >= ELU_500C: skipBytes(file, 4 * 6) # skip bounding box

            if state.logEluMeshNodes: print()

            state.eluMeshes.append(EluMeshNode(version, meshName, parentName, localMatrix,
                                               vertices, normals, uv1s, uv2s,
                                               colors, faces, weights,
                                               isDummy, matID))
    file.close()

'''
class testSelf:
    convertUnits = False

    def report(self, t, s):
        print(s)

testPaths = {
    'ELU_0': "..\\..\\GunZ\\clean\\Model\\weapon\\blade\\blade_2011_4lv.elu.xml"
    'ELU_5004': "..\\..\\GunZ\\clean\\Model\\weapon\\rocketlauncher\\rocket.elu.xml"
    'ELU_5005': "..\\..\\GunZ\\clean\\Model\\weapon\\dagger\\dagger04.elu.xml"
    'ELU_5006': "..\\..\\GunZ\\clean\\Model\\weapon\\katana\\katana10.elu.xml"
    'ELU_5007': "..\\..\\GunZ\\clean\\Model\\weapon\\blade\\blade07.elu.xml"

    'ELU_5008': "..\\..\\Gunz2\\Trinityent\\Gunz2\\Develop\\Gunz2\\Runtime\\Data\\Model\\Sky\\sky_daytime_cloudy.elu.xml",
    'ELU_5009': "..\\..\\Gunz2\\Trinityent\\Gunz2\\Develop\\Gunz2\\Runtime\\Data\\Model\\Sky\\sky_night_nebula.elu.xml",
    'ELU_500A': "..\\..\\Gunz2\\Trinityent\\Gunz2\\Develop\\Gunz2\\Runtime\\Data\\Model\\Sky\\weather_rainy.elu.xml",
    'ELU_500B': "..\\..\\Gunz2\\Trinityent\\Gunz2\\Develop\\Gunz2\\Runtime\\Data\\Model\\Sky\\weather_heavy_rainy.elu.xml",
    'ELU_500C': "..\\..\\Gunz2\\Trinityent\\Gunz2\\Develop\\mdk\\RealSpace3\\Runtime\\TestRS3\\Data\\Model\\MapObject\\login_water_p_01.elu.xml",
    'ELU_500D': "..\\..\\Gunz2\\Trinityent\\Gunz2\\Develop\\mdk\\RealSpace3\\Runtime\\Mesh\\goblin_commander\\goblin_commander.elu.xml",
    'ELU_500E': "..\\..\\Gunz2\\Trinityent\\Gunz2\\Develop\\Gunz2\\Runtime\\Data\\Model\\colony_machinegun01.elu.xml",
    'ELU_500F': "..\\..\\Gunz2\\Trinityent\\Gunz2\\Develop\\Gunz2\\Runtime\\Data\\Model\\healcross.elu.xml",
    'ELU_5010': "..\\..\\Gunz2\\Trinityent\\Gunz2\\Develop\\Gunz2\\Runtime\\Data\\Model\\weapon\\eq_ws_smg_06.elu.xml",

    'ELU_5011': "..\\..\\Gunz2\\Trinityent\\Gunz2\\Develop\\Gunz2\\Runtime\\Data\\Model\\Assassin\Male\\Assassin_Male_01.elu.xml",
    'ELU_5012': "..\\..\\Gunz2\\z3ResEx\\datadump\\Data\\Model\\MapObject\\Props\\Box\\Wood_Box\\prop_box_wood_01a.elu.xml",
    'ELU_5013': "..\\..\\Gunz2\\z3ResEx\\datadump\\Data\\Model\\weapon\\character_weapon\\Knife\\Wpn_knife_0001.elu.xml",
    'ELU_5014': "..\\..\\Gunz2\\z3ResEx\\datadump\\Data\\Model\\weapon\\character_weapon\\Katana\\Wpn_katana_0002.elu.xml"
}

for version, path in testPaths.items():
    print(f"{ version } { path }")

    readElu(testSelf(), path, GZRS2State(logEluHeaders = True, logEluMats = True, logEluMeshNodes = True))
'''
