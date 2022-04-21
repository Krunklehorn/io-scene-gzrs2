import os, math

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .io_gzrs2 import *

def readRs(self, path, state: GZRS2State):
    file = open(path, 'rb')

    id = readUInt(file)
    version = readUInt(file)
    matCount = readInt(file)
    for i in range(matCount): # skip material strings
        count = 0

        while count < 256:
            char = str(file.read(1), 'utf-8')
            if char == chr(0):
                break
            else:
                count = count + 1

    if id != RS_ID or version != RS_VERSION:
        self.report({ 'ERROR' }, f"RS header invalid! { id }, { version }")
        file.close()

        return
    elif matCount != len(state.xmlMats):
        self.report({ 'ERROR' }, f"RS material count did not match the XML parse! { matCount }, { len(state.xmlMats) }")
        file.close()

        return

    rsPolyCount = readInt(file)
    file.seek(4, 1) # skip total vertex count

    for _ in range(rsPolyCount):
        file.seek(4 + 4 + (4 * 4) + 4, 1) # skip material id, draw flags, plane and area data
        vertexCount = readInt(file)

        for _ in range(vertexCount): file.seek(4 * 3, 1) # skip vertex data
        for _ in range(vertexCount): file.seek(4 * 3, 1) # skip normal data

    file.seek(4 * 4, 1) # skip unused, unknown counts
    file.seek(4 * 2, 1) # skip leaf and polygon counts
    bspTotalVertices = readInt(file)
    file.seek(4, 1) # skip indices count

    firstVertex = 0

    def openBspNode():
        nonlocal firstVertex

        if self.doBspBounds:
            state.bspBounds.append(readBounds(file, self.convertUnits))
        else:
            file.seek(4 * 6, 1) # skip bounds data

        file.seek(4 * 4, 1) # skip plane data

        if readBool(file): openBspNode() # positive
        if readBool(file): openBspNode() # negative

        bspPolyCount = readInt(file)

        for _ in range(bspPolyCount):
            materialID = readInt(file)
            file.seek(4, 1) # skip polygon index
            drawFlags = readUInt(file)
            vertexCount = readInt(file)

            for j in range(vertexCount):
                pos = readCoordinate(file, self.convertUnits)
                nor = readCoordinate(file, False)
                uv = readUV(file)
                file.seek(4 * 2, 1) # skip bogus lightmap uv data

                state.bspVerts.append(BspVertex(pos, nor, uv))

            file.seek(4 * 3, 1) # skip plane normal

            if not (0 <= materialID < len(state.xmlMats)):
                self.report({ 'INFO' }, f"Material ID out of bounds, setting to 0 and continuing. { materialID }, { len(state.xmlMats) }")
                materialID = 0

            state.bspPolys.append(BspPolyData(materialID, drawFlags, vertexCount, firstVertex))
            firstVertex += vertexCount

    openBspNode()

    if len(state.bspVerts) != bspTotalVertices:
        self.report({ 'ERROR' }, f"Bsp vertex count did not match vertices written! { len(state.bspVerts) }, { bspTotalVertices }")

    file.close()

def readCol(self, path, state: GZRS2State):
    file = open(path, 'rb')

    id = readUInt(file)
    version = readUInt(file)

    if id != R_COL_ID or version != R_COL_VERSION:
        self.report({ 'ERROR' }, f"Col header invalid! { id }, { version }")
        file.close()

        return

    file.seek(4, 1) # skip node count
    colTotalPolys = readInt(file)

    colPolysWritten = 0

    def openColNode():
        nonlocal colPolysWritten

        file.seek(4 * 4 + 1, 1) # skip plane data and solidity bool

        if readBool(file): openColNode() # positive
        if readBool(file): openColNode() # negative

        colPolyCount = readInt(file)

        for _ in range(colPolyCount):
            state.colVerts.append(readCoordinate(file, self.convertUnits))
            state.colVerts.append(readCoordinate(file, self.convertUnits))
            state.colVerts.append(readCoordinate(file, self.convertUnits))
            file.seek(4 * 3, 1) # skip normal

        colPolysWritten += colPolyCount

    openColNode()

    if colPolysWritten != colTotalPolys:
        self.report({ 'ERROR' }, f"Col polygon count did not match polygons written! { colPolysWritten }, { colTotalPolys }")

    file.close()

def readElu(self, path, state: GZRS2State):
    file = open(path, 'rb')

    id = readUInt(file)
    version = readUInt(file)
    matCount = readUInt(file)
    meshCount = readUInt(file)

    if self.logEluHeaders or self.logEluMats or self.logEluMeshNodes:
        print("===================  Read Elu   ===================")
        print()

    if self.logEluHeaders:
        print(f"Path:           { path }")
        print(f"ID:             { hex(id) }")
        print(f"Version:        { hex(version) }")
        print(f"Mat Count:      { matCount }")
        print(f"Mesh Count:     { meshCount }")
        print()

    if id != ELU_ID or not version in ELU_VERSIONS:
        self.report({ 'ERROR' }, f"ELU header invalid! { id }, { hex(version) }")
        file.close()

        return

    if not version in ELU_SUPPORTED_VERSIONS:
        self.report({ 'INFO' }, f"ELU version support unconfirmed! Model may not load properly! Please submit to Krunk#6051 for testing! { path }, { hex(version) }")
        file.close()

        return

    if version < ELU_5012:
        # R_Mesh_Load.cpp
        fileBase = os.path.basename(path.rsplit('.', 1)[0])

        if fileBase.startswith("ef_"):
            effectSort = True
            litVertexModel = True
            matListObjTexture = False
        else:
            effectSort = False
            litVertexModel = False
            matListObjTexture = True

        if self.logEluMats and matCount > 0:
            print()
            print("=========  Elu Materials  =========")
            print()

        for _ in range(matCount):
            matID = readUInt(file)
            subMatID = readInt(file)

            ambient = readVec4(file)
            diffuse = readVec4(file)
            specular = readVec4(file)
            power = readUInt(file)

            if version <= ELU_5002:
                if power == 20:
                    power = 0
            else:
                power = power * 100

            subMatCount = readUInt(file)

            if version <= ELU_5005:
                texPath = readStringStripped(file, ELU_NAME_LENGTH)
                alphaPath = readStringStripped(file, ELU_NAME_LENGTH)
            else:
                texPath = readStringStripped(file, ELU_PATH_LENGTH)
                alphaPath = readStringStripped(file, ELU_PATH_LENGTH)

            twosided, additive, alphatest = False, False, False

            if version >= ELU_5002: twosided = readBool32(file)
            if version >= ELU_5004: additive = readBool32(file)
            if version >= ELU_5007: alphatest = readUInt(file)

            if alphatest > 0:
                isAlphaMap = False
                isDiffuseMap = False
            elif texPath:
                if alphaPath:
                    isAlphaMap = True
                    isDiffuseMap = False
                else:
                    isAlphaMap = False
                    isDiffuseMap = texPath.endswith(".tga")

            frameCount, frameSpeed, frameGap = 0, 0, 0.0

            # RMtrl::CheckAniTexture
            if texPath:
                texDir = os.path.dirname(texPath)
                texBase = os.path.basename(texPath)
                texName, texExt = texBase.rsplit('.', 1)
                isAniTex = texBase.startswith("txa")
                aniTexFrames = [] if isAniTex else None

                if isAniTex:
                    texName = texName[:len(texName) - 2]
                    texParams = texName.replace('_', ' ').split(' ')

                    if len(texParams) < 4:
                        self.report({ 'ERROR' }, f"Unable to split animated texture name! { texName }, { texParams } ")
                        file.close()

                        return

                    try:
                        frameCount, frameSpeed = int(texParams[1]), int(texParams[2])
                    except ValueError:
                        self.report({ 'ERROR' }, f"Animated texture name must use integers for frame count and speed! { texName } ")
                        file.close()

                        return
                    else:
                        frameGap = frameSpeed / frameCount

            if self.logEluMats:
                print(f"Mat ID:         { matID }")
                print(f"Sub Mat ID:     { subMatID }")
                print()
                print("Ambient:  ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*ambient))
                print("Diffuse:  ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*diffuse))
                print("Specular: ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.03f})".format(*specular))
                print(f"Power: { power }")
                print()
                print(f"Sub Mat Count:      { subMatCount }")
                print(f"Texture Path:       { texPath }")
                print(f"Alpha Path:         { alphaPath }")
                print(f"Two-sided:          { twosided }")
                print(f"Additive:           { additive }")
                print(f"Alpha Test:         { alphatest }")
                print(f"Is Alpha Map:       { isAlphaMap }")
                print(f"Is Diffuse Map:     { isDiffuseMap }")

                if texPath:
                    print()
                    print(f"Texture Name:   { texName }")
                    print(f"Texture Base:   { texBase }")
                    print(f"Extension:      { texExt }")
                    print(f"Directory:      { texDir }")
                    print(f"Is Animated:    { isAniTex }")
                    if isAniTex:
                        print(f"Frame Count: { frameCount }")
                        print(f"Frame Speed: { frameSpeed }")
                        print(f"Frame Gap: { frameGap }")
                    print()

            state.eluMats.append(EluMaterial(matID, subMatID,
                                             ambient, diffuse, specular, power,
                                             subMatCount,
                                             texPath, alphaPath,
                                             twosided, additive, alphatest,
                                             isAlphaMap, isDiffuseMap,
                                             texName, texBase, texExt, texDir,
                                             isAniTex, frameCount, frameSpeed, frameGap))

        EluMeshRoot = None

        if self.logEluMeshNodes and meshCount > 0:
            print()
            print("=========  Elu Mesh Nodes  ========")
            print()

        for _ in range(meshCount):
            meshID = 0
            parentMesh = EluMeshRoot
            baseMesh = EluMeshRoot

            meshName = readStringStripped(file, ELU_NAME_LENGTH)
            parentName = readStringStripped(file, ELU_NAME_LENGTH)

            baseMatrix = readTransform(file, self.convertUnits)

            if version >= ELU_5001:
                apScale = readVec3(file)

            if version >= ELU_5003:
                rotAxis = readCoordinate(file, False)
                rotAngle = readFloat(file)
                scaleAxis = readCoordinate(file, False)
                scaleAngle = readFloat(file)
                etcMatrix = readTransform(file, self.convertUnits)

            # CheckNameToType
            isDummy = False
            isDummyMesh = False
            isWeaponMesh = False
            isCollisionMesh = False

            partsType = None            # "eq_parts_etc"
            partsPosInfoType = None     # "eq_parts_pos_info_etc"
            cutParts = None             # "cut_parts_upper_body"
            lookAtParts = None          # "lookat_parts_etc"
            weaponDummyType = None      # "weapon_dummy_etc"
            alphaSortValue = 0.0

            if meshName.startswith("Bip"):
                isDummyMesh = True
            elif meshName.startswith("Bone"):
                isDummyMesh = True
            elif meshName.startswith("Dummy"):
                isDummy = True
                isDummyMesh = True
            elif meshName.startswith("eq_wd") or meshName.startswith("eq_wl") or meshName.startswith("eq_wr"):
                meshNameToWeaponPart = {
                    "eq_wd_katana":    "eq_parts_right_katana",
                    "eq_wl_pistol":    "eq_parts_left_pistol",
                    "eq_wr_pistol":    "eq_parts_right_pistol",
                    "eq_wd_pistol":    "eq_parts_right_pistol",
                    "eq_wl_smg":       "eq_parts_left_smg",
                    "eq_wr_smg":       "eq_parts_right_smg",
                    "eq_wd_smg":       "eq_parts_right_smg",
                    "eq_wd_shotgun":   "eq_parts_right_shotgun",
                    "eq_wd_rifle":     "eq_parts_right_rifle",
                    "eq_wd_grenade":   "eq_parts_right_grenade",
                    "eq_wd_item":      "eq_parts_right_item",
                    "eq_wl_dagger":    "eq_parts_left_dagger",
                    "eq_wr_dagger":    "eq_parts_right_dagger",
                    "eq_wd_medikit":   "eq_parts_right_item",
                    "eq_wd_rl":        "eq_parts_right_rlauncher",
                    "eq_wd_sword":     "eq_parts_right_sword",
                    "eq_wr_blade":     "eq_parts_right_blade",
                    "eq_wl_blade":     "eq_parts_left_blade"
                }

                if meshName in meshNameToWeaponPart:
                    isWeaponMesh = True
                    partsType = meshNameToWeaponPart[meshName]
            elif meshName.startswith("eq_"):
                meshNameToBodyPart = {
                    "eq_head": ("eq_parts_head", 1.0),
                    "eq_face": ("eq_parts_face", 2.0),
                    "eq_chest": ("eq_parts_chest", 3.0),
                    "eq_hands": ("eq_parts_hands", 4.0),
                    "eq_legs": ("eq_parts_legs", 5.0),
                    "eq_feet": ("eq_parts_feet", 6.0),
                    "eq_sunglass": ("eq_parts_sunglass", 0.5)
                }

                if meshName in meshNameToBodyPart:
                    partsType = meshNameToBodyPart[meshName][0]
                    alphaSortValue = meshNameToBodyPart[meshName][1]
            elif meshName.startswith("collision_"):
                isCollisionMesh = True
                isDummyMesh = True

            if meshName.startswith("lastmodel"):
                isLastModel = True

            if meshName.startswith("deffect"):
                isDummyMesh = True
                partsPosInfoType = "eq_parts_pos_info_Effect"

            if meshName.startswith("Bip"):
                if meshName.startswith("Bip01 L"):
                    if meshName.startswith("Bip01 L Calf"):
                        partsPosInfoType = "eq_parts_pos_info_LCalf"
                        cutParts = "cut_parts_lower_body"
                    elif meshName.startswith("Bip01 L Clavile"):
                        partsPosInfoType = "eq_parts_pos_info_LClavicle"
                    elif meshName.startswith("Bip01 L Finger0"):
                        partsPosInfoType = "eq_parts_pos_info_LFinger0"
                    elif meshName.startswith("Bip01 L FingerNub"):
                        partsPosInfoType = "eq_parts_pos_info_LFingerNub"
                    elif meshName.startswith("Bip01 L Foot"):
                        partsPosInfoType = "eq_parts_pos_info_LFoot"
                        cutParts = "cut_parts_lower_body"
                    elif meshName.startswith("Bip01 L ForeArm"):
                        partsPosInfoType = "eq_parts_pos_info_LForeArm"
                    elif meshName.startswith("Bip01 L Hand"):
                        partsPosInfoType = "eq_parts_pos_info_LHand"
                    elif meshName.startswith("Bip01 L Thigh"):
                        partsPosInfoType = "eq_parts_pos_info_LThigh"
                        cutParts = "cut_parts_lower_body"
                    elif meshName.startswith("Bip01 L Toe0Nub"):
                        partsPosInfoType = "eq_parts_pos_info_LToe0Nub"
                    elif meshName.startswith("Bip01 L Toe0"):
                        partsPosInfoType = "eq_parts_pos_info_LToe0"
                        cutParts = "cut_parts_lower_body"
                    elif meshName.startswith("Bip01 L UpperArm"):
                        partsPosInfoType = "eq_parts_pos_info_LUpperArm"
                elif meshName.startswith("Bip01 R"):
                    if meshName.startswith("Bip01 R Calf"):
                        partsPosInfoType = "eq_parts_pos_info_RCalf"
                        cutParts = "cut_parts_lower_body"
                    elif meshName.startswith("Bip01 R Clavile"):
                        partsPosInfoType = "eq_parts_pos_info_RClavicle"
                    elif meshName.startswith("Bip01 R Finger0"):
                        partsPosInfoType = "eq_parts_pos_info_RFinger0"
                    elif meshName.startswith("Bip01 R FingerNub"):
                        partsPosInfoType = "eq_parts_pos_info_RFingerNub"
                    elif meshName.startswith("Bip01 R Foot"):
                        partsPosInfoType = "eq_parts_pos_info_RFoot"
                        cutParts = "cut_parts_lower_body"
                    elif meshName.startswith("Bip01 R ForeArm"):
                        partsPosInfoType = "eq_parts_pos_info_RForeArm"
                    elif meshName.startswith("Bip01 R Hand"):
                        partsPosInfoType = "eq_parts_pos_info_RHand"
                    elif meshName.startswith("Bip01 R Thigh"):
                        partsPosInfoType = "eq_parts_pos_info_RThigh"
                        cutParts = "cut_parts_lower_body"
                    elif meshName.startswith("Bip01 R Toe0Nub"):
                        partsPosInfoType = "eq_parts_pos_info_RToe0Nub"
                    elif meshName.startswith("Bip01 R Toe0"):
                        partsPosInfoType = "eq_parts_pos_info_RToe0"
                        cutParts = "cut_parts_lower_body"
                    elif meshName.startswith("Bip01 R UpperArm"):
                        partsPosInfoType = "eq_parts_pos_info_RUpperArm"
                else:
                    if meshName == "Bip01":
                        partsPosInfoType = "eq_parts_pos_info_Root"
                        cutParts = "cut_parts_lower_body"
                    elif meshName == "Bip01 Head":
                        partsPosInfoType = "eq_parts_pos_info_Head"
                        lookAtParts = "lookat_parts_head"
                    elif meshName == "Bip01 HeadNub":
                        partsPosInfoType = "eq_parts_pos_info_HeadNub"
                    elif meshName == "Bip01 Neck":
                        partsPosInfoType = "eq_parts_pos_info_Neck"
                    elif meshName == "Bip01 Pelvis":
                        partsPosInfoType = "eq_parts_pos_info_Pelvis"
                    elif meshName == "Bip01 Spine":
                        partsPosInfoType = "eq_parts_pos_info_Spine"
                        cutParts = "cut_parts_lower_body"
                        lookAtParts = "lookat_parts_spine"
                    elif meshName == "Bip01 Spine1":
                        partsPosInfoType = "eq_parts_pos_info_Spine1"
                        lookAtParts = "lookat_parts_spine1"
                    elif meshName == "Bip01 Spine2":
                        partsPosInfoType = "eq_parts_pos_info_Spine2"
                        lookAtParts = "lookat_parts_spine2"

            if meshName.startswith("Bone") or meshName.startswith("Dummy"):
                cutParts = "cut_parts_lower_body"
            elif meshName.startswith("muzzle_flash"):
                weaponDummyType = "weapon_dummy_muzzle_flash"
            elif meshName.startswith("empty_cartridge01"):
                weaponDummyType = "weapon_dummy_cartridge01"
            elif meshName.startswith("empty_cartridge02"):
                weaponDummyType = "weapon_dummy_cartridge02"

            align = 0
            meshNameLength = len(meshName)

            # CheckEfAlign & checkEf
            if meshName:
                if "ef_algn" in meshName:
                    align = int(meshName.split("ef_algn")[1][0]) + 1
                elif "algn" in meshName:
                    align = int(meshName.split("algn")[1][0]) + 1

            if "_ef" in meshName:
                effectSort = True
                litVertexModel = True

            vertexCount = readUInt(file)

            if vertexCount > 0:
                vertices = readCoordinateArray(file, vertexCount, self.convertUnits)
                minVertex = Vector(( math.inf,  math.inf,  math.inf))
                maxVertex = Vector((-math.inf, -math.inf, -math.inf))

                for vertex in vertices:
                    minVertex.x = min(minVertex.x, vertex.x)
                    minVertex.y = min(minVertex.y, vertex.y)
                    minVertex.z = min(minVertex.z, vertex.z)

                    maxVertex.x = max(maxVertex.x, vertex.x)
                    maxVertex.y = max(maxVertex.y, vertex.y)
                    maxVertex.z = max(maxVertex.z, vertex.z)
            else:
                vertices = None
                minVertex = Vector((0, 0, 0))
                maxVertex = Vector((0, 0, 0))

            faceCount = readUInt(file)

            faces = None
            normals = None

            if faceCount > 0:
                faces = []
                normals = [Vector((0, 0, 0)) for _ in range(vertexCount)]

                for f in range(faceCount):
                    index = readUIntArray(file, 3)
                    uv1 = readUV(file)
                    skipBytes(file, 4) # skip unused z-coordinate
                    uv2 = readUV(file)
                    skipBytes(file, 4) # skip unused z-coordinate
                    uv3 = readUV(file)
                    skipBytes(file, 4) # skip unused z-coordinate
                    uv = (uv1, uv2, uv3)
                    matID = readInt(file)
                    sigID = readInt(file) if version >= ELU_5002 else -1

                    faces.append(EluFace(index, uv, matID, sigID))

                if version >= ELU_5005:
                    for face in faces:
                        face.normal = readCoordinate(file, False)
                        normals[face.index[0]] = readCoordinate(file, False)
                        normals[face.index[1]] = readCoordinate(file, False)
                        normals[face.index[2]] = readCoordinate(file, False)
                else:
                    for face in faces:
                        e1 = vertices[face.index[1]] - vertices[face.index[0]]
                        e2 = vertices[face.index[2]] - vertices[face.index[0]]

                        cross = e2.cross(e1)
                        cross.normalize()

                        face.normal = cross

                        for v in range(3):
                            normals[face.index[v]] += cross

                    for normal in normals:
                        normal.normalize()

            if vertexCount == 0 and faceCount == 0:
                isDummyMesh = True

            if version >= ELU_5005:
                vertexColorCount = readUInt(file)
                vertexColors = None

                if vertexColorCount > 0:
                    vertexColors = readVec3Array(file, vertexColorCount)
            else:
                vertexColorCount = 0
                vertexColors = None

            matID = readUInt(file)
            physCount = readUInt(file)

            if physCount > 0:
                isPhysMesh = True
                physInfos = []

                for _ in range(physCount):
                    parentName = tuple(readStringStripped(file, ELU_NAME_LENGTH) for _ in range(ELU_PHYS_KEYS))
                    weight = tuple(readFloat(file) for _ in range(ELU_PHYS_KEYS))
                    parentID = tuple(readUInt(file) for _ in range(ELU_PHYS_KEYS))
                    num = readUInt(file)
                    offset = tuple(readCoordinate(file, self.convertUnits) for _ in range(ELU_PHYS_KEYS))
                    physInfos.append(EluPhysInfo(parentName, weight, parentID, offset, num))
            else:
                isPhysMesh = False
                physInfos = None

            isClothMesh = vertexColorCount > 0 and partsType == "eq_parts_chest"

            if self.logEluMeshNodes:
                print(f"Mesh ID:        { meshID }")
                print(f"Parent Mesh:    { parentMesh }")
                print(f"Base Mesh:      { baseMesh }")
                print(f"Mesh Name:      { meshName }")
                print(f"Parent Name:    { parentName }")
                print("Base Matrix: ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.02f})".format(*baseMatrix[0]))
                print("             ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.02f})".format(*baseMatrix[1]))
                print("             ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.02f})".format(*baseMatrix[2]))
                print("             ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.02f})".format(*baseMatrix[3]))
                if version >= ELU_5001:
                    print("AP Scale:    ({:>5.02f}, {:>5.02f}, {:>5.02f})".format(*apScale))
                if version >= ELU_5003:
                    print("Rotation Axis & Angle: ({:>6.03f}, {:>6.03f}, {:>6.03f}), {:>5.02f}°".format(*rotAxis, math.degrees(rotAngle)))
                    print("Scale Axis & Angle:    ({:>6.03f}, {:>6.03f}, {:>6.03f}), {:>5.02f}°".format(*scaleAxis, math.degrees(scaleAngle)))
                    print("Etc Matrix: ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.02f})".format(*etcMatrix[0]))
                    print("            ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.02f})".format(*etcMatrix[1]))
                    print("            ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.02f})".format(*etcMatrix[2]))
                    print("            ({:>6.03f}, {:>6.03f}, {:>6.03f}, {:>6.02f})".format(*etcMatrix[3]))
                print()
                print(f"Is Dummy:               { isDummy }")
                print(f"Is Dummy Mesh:          { isDummyMesh }")
                print(f"Is Weapon Mesh:         { isWeaponMesh }")
                print(f"Is Collision Mesh:      { isCollisionMesh }")
                print(f"Parts Type:             { partsType }")
                print(f"Parts Pos Info Type:    { partsPosInfoType }")
                print(f"Cut Parts:              { cutParts }")
                print(f"Look At Parts:          { lookAtParts }")
                print(f"Weapon Dummy Type:      { weaponDummyType }")
                print(f"Alpha Sort Value:       { alphaSortValue }")
                print()
                print(f"Vertices: { vertexCount }")
                '''
                if vertices is not None:
                    for vertex in vertices:
                        print("            ({:>9.02f}, {:>9.02f}, {:>9.02f})".format(*vertex))
                    print("Min Vertex: ({:>9.02f}, {:>9.02f}, {:>9.02f})".format(*minVertex))
                    print("Max Vertex: ({:>9.02f}, {:>9.02f}, {:>9.02f})".format(*maxVertex))
                    print()
                '''
                print(f"Faces: { faceCount }")
                '''
                if faces is not None:
                    for face in faces:
                        print(f"Mat ID, Sig ID: { face.matID }, { face.sigID }")
                        print("Vertex Indices:  {:>2}, {:>2}, {:>2}".format(*face.index))
                        print("Face Normal:    ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*face.normal))
                        print("Vertex Normals: ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*normals[face.index[0]]))
                        print("                ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*normals[face.index[1]]))
                        print("                ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*normals[face.index[2]]))
                        print("Vertex UVs:     ({:>6.03f}, {:>6.03f})".format(*face.uv[0]))
                        print("                ({:>6.03f}, {:>6.03f})".format(*face.uv[1]))
                        print("                ({:>6.03f}, {:>6.03f})".format(*face.uv[2]))
                        print()
                    print()
                '''
                '''
                print(f"Vertex Colors: { vertexColorCount }")
                if vertexColors is not None:
                    for vertexColor in vertexColors:
                        print("Vertex Color: ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*vertexColor))
                    print()
                '''
                print(f"Mat ID: { matID }")
                print(f"Is Physics Mesh: { isPhysMesh }")
                print(f"Is Cloth Mesh: { isClothMesh }")
                print(f"Physics Info: { physCount }")
                '''
                if physInfos is not None:
                    for physInfo in physInfos:
                        print("Parent Name: {}".format(physInfo.parentName[0]))
                        print("             {}".format(physInfo.parentName[1]))
                        print("             {}".format(physInfo.parentName[2]))
                        print("             {}".format(physInfo.parentName[3]))
                        print("Parent ID:   {}".format(physInfo.parentID[0]))
                        print("             {}".format(physInfo.parentID[1]))
                        print("             {}".format(physInfo.parentID[2]))
                        print("             {}".format(physInfo.parentID[3]))
                        print("Weight:      {}".format(physInfo.weight[0]))
                        print("             {}".format(physInfo.weight[1]))
                        print("             {}".format(physInfo.weight[2]))
                        print("             {}".format(physInfo.weight[3]))
                        print("Offset:      {}".format(physInfo.offset[0]))
                        print("             {}".format(physInfo.offset[1]))
                        print("             {}".format(physInfo.offset[2]))
                        print("             {}".format(physInfo.offset[3]))
                        print("Num:         {}".format(physInfo.num))
                        print()
                    print()
                '''
                print()

            state.eluMeshNodes.append(EluMeshNode(meshID, matID,
                                                  parentMesh, baseMesh,
                                                  meshName, parentName,
                                                  baseMatrix, etcMatrix, apScale,
                                                  rotAxis, scaleAxis, rotAngle, scaleAngle,
                                                  partsType, partsPosInfoType, cutParts,
                                                  lookAtParts, weaponDummyType, alphaSortValue,
                                                  vertices, minVertex, maxVertex, faces, normals, vertexColors, physInfos,
                                                  isDummy, isDummyMesh, isWeaponMesh, isCollisionMesh, isPhysMesh, isClothMesh))

        # TODO: handle isCharacterMesh?

        file.close()

        # TODO: ConnectMatrix and everything past it?
    else:
        self.report({ 'ERROR' }, f"ELU versions 5012 and 5013 are not supported yet! Please submit to Krunk#6051 for testing! { path }, { hex(version) }")
        file.close()
