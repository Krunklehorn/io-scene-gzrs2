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
# - RBspExporter.cpp
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

from contextlib import redirect_stdout
from mathutils import Vector, Matrix, Quaternion

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .parse_gzrs2 import *
from .io_gzrs2 import *
from .lib_gzrs2 import *

def exportRS2(self, context):
    state = GZRS2ExportState()

    state.convertUnits      = self.convertUnits
    state.filterMode        = self.filterMode
    state.includeChildren   = self.includeChildren and self.filterMode == 'SELECTED'

    state.lmVersion4        = self.lmVersion4
    state.mod4Fix           = self.mod4Fix and not self.lmVersion4

    if self.panelLogging:
        print()
        print("=======================================================================")
        print("===========================  GZRS2 Import  ============================")
        print("=======================================================================")
        print(f"== { self.filepath }")
        print("=======================================================================")
        print()

        # TODO: Switches

        state.logRsHeaders          = self.logRsHeaders # TODO
        state.logRsTrees            = self.logRsTrees # TODO
        state.logRsPolygons         = self.logRsPolygons # TODO
        state.logRsVerts            = self.logRsVerts # TODO
        state.logBspHeaders         = self.logBspHeaders # TODO
        state.logBspPolygons        = self.logBspPolygons # TODO
        state.logBspVerts           = self.logBspVerts # TODO
        state.logColHeaders         = self.logColHeaders # TODO
        state.logColNodes           = self.logColNodes # TODO
        state.logColTris            = self.logColTris # TODO
        state.logNavHeaders         = self.logNavHeaders # TODO
        state.logNavData            = self.logNavData # TODO
        state.logLmHeaders          = self.logLmHeaders # TODO
        state.logLmImages           = self.logLmImages # TODO
        state.logEluHeaders         = self.logEluHeaders # TODO
        state.logEluMats            = self.logEluMats # TODO
        state.logEluMeshNodes       = self.logEluMeshNodes # TODO
        state.logVerboseIndices     = self.logVerboseIndices    and self.logEluMeshNodes # TODO
        state.logVerboseWeights     = self.logVerboseWeights    and self.logEluMeshNodes # TODO

    rspath = self.filepath
    directory = os.path.dirname(rspath)
    basename = bpy.path.basename(rspath)
    splitname = basename.split(os.extsep)
    filename = splitname[0]

    objects = getFilteredObjects(context, state)

    # TODO: New material tags
    #   at_:    adds <ALPHATEST/>?
    #   hide_:  not rendered at runtime
    #   pass_:  rendered but ignored by collision
    #   passb_: bullets pass through
    #   passr_: bullets, rockets and grenades pass through

    # TODO: New mesh tags
    #   algn#_: 0 face camera, 1 face camera fixed z-axis
    #   water_: it's wet
    #   sea_:   it's wet

    # TODO: New empty type for "Partition" planes, cuts an octree at a specified depth without incrementing the counter

    # TODO: Verify blitzkrieg data

    # Gather data into lists
    blSpawnSoloObjs     = []
    blSpawnTeamObjs     = []
    blSpawnNpcObjs      = []
    blSpawnBlitzObjs    = []
    blFlareObjs         = []
    blSoundObjs         = []
    blSmokeObjs         = []
    blItemSoloObjs      = []
    blItemTeamObjs      = []
    blOccObjs           = []

    blWorldObjs         = []
    blPropNoneObjs      = []
    blPropSkyObjs       = []
    blPropFlagObjs      = []
    blColObjs           = []
    blNavObjs           = []

    blLightStaticObjs   = []
    blLightDynamicObjs  = []

    blCameraObjs        = []
    blCameraWaitObjs    = []
    blCameraTrackObjs   = []

    foundValid = False
    invalidCount = 0

    for object in objects:
        if object is None:
            continue

        objType = object.type

        if objType in ('EMPTY', 'MESH', 'LIGHT', 'CAMERA'):
            foundValid = True

            if objType == 'EMPTY':
                props = object.gzrs2
                dummyType = props.dummyType

                if      dummyType == 'SPAWN':
                    spawnType = props.spawnType

                    if      spawnType == 'SOLO':    blSpawnSoloObjs.append(object)
                    elif    spawnType == 'TEAM':    blSpawnTeamObjs.append(object)
                    elif    spawnType == 'NPC':     blSpawnNpcObjs.append(object)
                    elif    spawnType == 'BLITZ':   blSpawnBlitzObjs.append(object)
                elif    dummyType == 'FLARE':       blFlareObjs.append(object)
                elif    dummyType == 'SOUND':       blSoundObjs.append(object)
                elif    dummyType == 'SMOKE':       blSmokeObjs.append(object)
                elif    dummyType == 'ITEM':
                    itemGameID = props.itemGameID

                    if      itemGameID == 'SOLO':   blItemSoloObjs.append(object)
                    elif    itemGameID == 'TEAM':   blItemTeamObjs.append(object)
                elif    dummyType == 'OCCLUSION':   blOccObjs.append(object)
            elif objType == 'MESH':
                props = object.data.gzrs2
                meshType = props.meshType

                if      meshType == 'WORLD':        blWorldObjs.append(object)
                elif    meshType == 'PROP':
                    propSubtype = props.propSubtype

                    if isChildProp(object):
                        continue

                    if      propSubtype == 'NONE':  blPropNoneObjs.append(object)
                    elif    propSubtype == 'SKY':   blPropSkyObjs.append(object)
                    elif    propSubtype == 'FLAG':  blPropFlagObjs.append(object)
                elif    meshType == 'COLLISION':    blColObjs.append(object)
                elif    meshType == 'NAVIGATION':   blNavObjs.append(object)
            elif objType == 'LIGHT':
                props = object.data.gzrs2
                lightType =props.lightType

                if      lightType == 'STATIC':      blLightStaticObjs.append(object)
                elif    lightType == 'DYNAMIC':     blLightDynamicObjs.append(object)
            elif objType == 'CAMERA':
                props = object.data.gzrs2
                cameraType = props.cameraType

                blCameraObjs.append(object)

                if      cameraType == 'WAIT':       blCameraWaitObjs.append(object)
                elif    cameraType == 'TRACK':      blCameraTrackObjs.append(object)
        else:
            invalidCount += 1

    if not foundValid:
        self.report({ 'ERROR' }, "GZRS2: RS export requires objects of type EMPTY, MESH, LIGHT and/or CAMERA!")
        return { 'CANCELLED' }

    if invalidCount > 0:
        self.report({ 'WARNING' }, f"GZRS2: RS export skipped { invalidCount } invalid objects...")

    if len(blWorldObjs) == 0:
        self.report({ 'ERROR' }, f"GZRS2: RS export requires at least one world mesh!")
        return { 'CANCELLED' }

    if len(blColObjs) == 0:
        self.report({ 'ERROR' }, f"GZRS2: RS export requires at least one collision mesh!")
        return { 'CANCELLED' }

    # Sort lists
    def sortByName(x):
        return x.name

    def sortSound(x):
        return (
            SOUND_SPACE_TAGS.index(x.gzrs2.soundSpace),
            SOUND_SHAPE_TAGS.index(x.gzrs2.soundShape),
            x.gzrs2.soundFileName,
            x.name
        )

    def sortSmoke(x):
        return (
            SMOKE_TYPE_TAGS.index(x.gzrs2.smokeType),
            x.gzrs2.smokeDirection,
            x.gzrs2.smokePower,
            x.gzrs2.smokeDelay,
            x.gzrs2.smokeSize,
            x.gzrs2.smokeLife,
            x.gzrs2.smokeToggleMinTime,
            x.name
        )

    def sortItem(x):
        return (
            ITEM_GAME_ID_TAGS.index(x.gzrs2.itemGameID),
            ITEM_TYPE_TAGS.index(x.gzrs2.itemType),
            x.gzrs2.itemID,
            x.gzrs2.itemTimer,
            x.name
        )

    def sortCamera(x):
        return (
            CAMERA_TYPE_TAGS.index(x.data.gzrs2.gzrs2.cameraType),
            x.data.gzrs2.gzrs2.cameraIndex,
            x.name
        )

    blWorldObjs         = tuple(sorted(blWorldObjs,         key = sortByName))

    blPropNoneObjs      = tuple(sorted(blPropNoneObjs,      key = sortByName))
    blPropSkyObjs       = tuple(sorted(blPropSkyObjs,       key = sortByName))
    blPropFlagObjs      = tuple(sorted(blPropFlagObjs,      key = sortByName))

    blSpawnSoloObjs     = tuple(sorted(blSpawnSoloObjs,     key = lambda x: (                           x.gzrs2.spawnIndex,     x.name)))
    blSpawnTeamObjs     = tuple(sorted(blSpawnTeamObjs,     key = lambda x: (x.gzrs2.spawnTeamID,       x.gzrs2.spawnIndex,     x.name)))
    blSpawnNpcObjs      = tuple(sorted(blSpawnNpcObjs,      key = lambda x: (x.gzrs2.spawnEnemyType,    x.gzrs2.spawnIndex,     x.name)))
    blSpawnBlitzObjs    = tuple(sorted(blSpawnBlitzObjs,    key = lambda x: (x.gzrs2.spawnBlitzType,    x.gzrs2.spawnIndex,     x.name)))

    blFlareObjs         = tuple(sorted(blFlareObjs,         key = sortByName))
    blSoundObjs         = tuple(sorted(blSoundObjs,         key = sortSound))
    blSmokeObjs         = tuple(sorted(blSmokeObjs,         key = sortSmoke))

    blItemSoloObjs      = tuple(sorted(blItemSoloObjs,      key = sortItem))
    blItemTeamObjs      = tuple(sorted(blItemTeamObjs,      key = sortItem))

    blOccObjs           = tuple(sorted(blOccObjs,           key = sortByName))

    blCameraObjs        = tuple(sorted(blCameraObjs,        key = lambda x: sortCamera))
    blCameraWaitObjs    = tuple(sorted(blCameraWaitObjs,    key = lambda x: (x.data.gzrs2.cameraIndex,  x.name)))
    blCameraTrackObjs   = tuple(sorted(blCameraTrackObjs,   key = lambda x: (x.data.gzrs2.cameraIndex,  x.name)))

    # Consolidate and freeze lists
    blPropObjs      = []
    blPropObjsAll   = []
    blLightObjs     = []
    blDummyObjs     = []

    for blPropNoneObj       in blPropNoneObjs:      blPropObjs.append(blPropNoneObj)
    for blPropSkyObj        in blPropSkyObjs:       blPropObjs.append(blPropSkyObj)
    for blPropFlagObj       in blPropFlagObjs:      blPropObjs.append(blPropFlagObj)

    for blPropObj in blPropObjs:
        blPropObjsAll.append(blPropObj)
        blPropObjChildren = tuple(object for object in blPropObj.children_recursive if object.type == 'MESH' and object.data.gzrs2.meshType == 'PROP')
        blPropObjsAll += tuple(sorted(blPropObjChildren, key = sortByName))

    for blLightStaticObj    in blLightStaticObjs:   blLightObjs.append(blLightStaticObj)
    for blLightDynamicObj   in blLightDynamicObjs:  blLightObjs.append(blLightDynamicObj)

    for blSpawnSoloObj      in blSpawnSoloObjs:     blDummyObjs.append(blSpawnSoloObj)
    for blSpawnTeamObj      in blSpawnTeamObjs:     blDummyObjs.append(blSpawnTeamObj)
    for blSpawnNpcObj       in blSpawnNpcObjs:      blDummyObjs.append(blSpawnNpcObj)
    for blSpawnBlitzObj     in blSpawnBlitzObjs:    blDummyObjs.append(blSpawnBlitzObj)
    for blFlareObj          in blFlareObjs:         blDummyObjs.append(blFlareObj)
    for blSoundObj          in blSoundObjs:         blDummyObjs.append(blSoundObj)
    for blSmokeObj          in blSmokeObjs:         blDummyObjs.append(blSmokeObj)
    for blItemSoloObj       in blItemSoloObjs:      blDummyObjs.append(blItemSoloObj)
    for blItemTeamObj       in blItemTeamObjs:      blDummyObjs.append(blItemTeamObj)
    for blPropObj           in blPropObjs:          blDummyObjs.append(blPropObj)
    for blCameraWaitObj     in blCameraWaitObjs:    blDummyObjs.append(blCameraWaitObj)
    for blCameraTrackObj    in blCameraTrackObjs:   blDummyObjs.append(blCameraTrackObj)

    blPropObjs      = tuple(blPropObjs)
    blPropObjsAll   = tuple(blPropObjsAll)
    blLightObjs     = tuple(blLightObjs)
    blDummyObjs     = tuple(blDummyObjs)

    blExportObjs    = blWorldObjs + blPropObjsAll

    # Gather materials
    world = ensureWorld(context)
    worldProps = world.gzrs2

    if checkMeshesEmptySlots(blExportObjs, self):       return { 'CANCELLED' }
    if checkPropsParentForks(blPropObjsAll, self):      return { 'CANCELLED' }
    if checkPropsParentChains(blPropObjsAll, self):     return { 'CANCELLED' }

    blWorldMats     = set(getOrNone(blWorldObj.material_slots, 0)   for blWorldObj  in blWorldObjs)
    blPropMats      = set(getOrNone(blPropObj.material_slots, 0)    for blPropObj   in blPropObjsAll)

    blWorldMats     = set(blWorldMat.material       for blWorldMat  in blWorldMats)
    blPropMats      = set(blPropMat.material        for blPropMat   in blPropMats)
    blPropMats      |= set(blPropMat.gzrs2.parent   for blPropMat   in blPropMats)

    blWorldMats     -= { None }
    blPropMats      -= { None }

    for blWorldMat in blWorldMats:
        if blWorldMat in blPropMats:
            self.report({ 'ERROR' }, f"GZRS2: RS export requires all materials be linked to mesh objects of type 'World' or 'Prop', but not both: { blWorldMat.name }")
            return { 'CANCELLED' }

    # Sort materials
    blWorldMats     = tuple(sorted(blWorldMats,     key = lambda x: (x.gzrs2.priority, x.name)))
    # blPropMats      = tuple(sorted(blPropMats,      key = lambda x: (x.gzrs2.priority, x.name)))

    # TODO: Do we need to include base prop materials?

    rsMatCount = len(blWorldMats)
    rsLightCount = len(blLightObjs)
    rsPropCount = len(blPropObjs)
    rsDummyCount = len(blDummyObjs)
    rsOccCount = len(blOccObjs)
    rsSoundCount = len(blSoundObjs)

    rsMatTexpaths = []

    reorientCamera = Matrix.Rotation(math.radians(-90.0), 4, 'X')

    # Write .rs.xml
    rsxmlpath = f"{ rspath }{ os.extsep }xml"

    createBackupFile(rsxmlpath)

    with open(rsxmlpath, 'w') as file:
        file.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
        file.write("<XML>\n")

        if rsMatCount > 0:
            file.write("\t<MATERIALLIST>\n")

        for m, blWorldMat in enumerate(blWorldMats):

            props = blWorldMat.gzrs2
            exportName = blWorldMat.name
            exportNameLower = exportName.lower()

            # TODO: Regex this instead, '_mt_AAA'
            if props.sound != 'NONE' and '_mt_' not in exportNameLower:
                exportName += '_mt_'
                exportName += props.sound.lower()

            _, links, nodes = getMatTreeLinksNodes(blWorldMat)

            shader, output, info, transparent, mix, clip, add, lightmix = getRelevantShaderNodes(nodes)
            shaderValid, infoValid, transparentValid, mixValid, clipValid, addValid, lightmixValid = checkShaderNodeValidity(shader, output, info, transparent, mix, clip, add, lightmix, links)

            if any((shaderValid         == False,   infoValid   == False,
                    transparentValid    == False,   mixValid    == False,
                    clipValid           == False,   addValid    == False,
                    lightmixValid       == False)):
                self.report({ 'ERROR' }, f"GZRS2: RS export requires all materials conform to a preset! { exportName }")
                return { 'CANCELLED' }

            texture, emission, alpha, lightmap = getLinkedImageNodes(shader, shaderValid, links, clip, clipValid, lightmix, lightmixValid)
            twosided, additive, _, usealphatest, useopacity = getMatFlagsRender(blWorldMat, clip, addValid, clipValid, emission, alpha)

            if props.overrideTexpath:   texpath = os.path.join(props.texDir, props.texBase)
            elif texture is None:       texpath = ''
            elif props.writeDirectory:  texpath = makeRS2DataPath(texture.image.filepath)
            else:                       texpath = makePathExtSingle(bpy.path.basename(texture.image.filepath))

            if texpath == False:
                self.report({ 'ERROR' }, f"GZRS2: Directory requested but image filepath does not contain a valid data subdirectory! { m }, { exportName }, { texture.image.filepath }")

            if len(texpath) >= RS_PATH_LENGTH:
                self.report({ 'ERROR' }, f"GZRS2: RS texture path has too many characters! Max length is { RS_PATH_LENGTH }! { m }, { exportName }, { texpath }")
                return { 'CANCELLED' }

            rsMatTexpaths.append(texpath)

            file.write(f"\t\t<MATERIAL name=\"{ exportName.lower() }\">\n")
            file.write("\t\t\t<DIFFUSE>{:f} {:f} {:f}</DIFFUSE>\n".format(*props.diffuse[:3]))
            file.write("\t\t\t<AMBIENT>{:f} {:f} {:f}</AMBIENT>\n".format(*props.ambient[:3]))
            file.write("\t\t\t<SPECULAR>{:f} {:f} {:f}</SPECULAR>\n".format(*props.specular[:3]))
            file.write(f"\t\t\t<DIFFUSEMAP>{ texpath }</DIFFUSEMAP>\n")
            if twosided:      file.write(f"\t\t\t<TWOSIDED/>\n")
            if additive:      file.write(f"\t\t\t<ADDITIVE/>\n")
            if usealphatest:  file.write(f"\t\t\t<USEALPHATEST/>\n")
            if useopacity:    file.write(f"\t\t\t<USEOPACITY/>\n")
            file.write("\t\t</MATERIAL>\n")

        if rsMatCount > 0:      file.write("\t</MATERIALLIST>\n")
        if rsLightCount > 0:    file.write("\t<LIGHTLIST>\n")

        for blLightObj in blLightObjs:
            loc = blLightObj.matrix_world.to_translation()

            blLight = blLightObj.data
            props = blLight.gzrs2

            lightType = props.lightType
            lightSubtype = props.lightSubtype
            intensity = props.intensity

            lightName = blLightObj.name
            lightNameLower = lightName.lower()

            lightName = lightName.replace('obj_', '')
            lightName = lightName.replace('_obj', '')
            lightName = lightName.replace('sun_', '')
            lightName = lightName.replace('_sun', '')

            if lightSubtype == 'SUN':   lightName = 'sun_' + lightName # Ruin & Lost Shrine
            if lightType == 'DYNAMIC':  lightName = 'obj_' + lightName

            file.write(f"\t\t<LIGHT name=\"{ lightName.lower() }\">\n")
            file.write("\t\t\t<POSITION>{:f} {:f} {:f}</POSITION>\n".format(*tokenizeVec3(loc, 'POSITION', state.convertUnits, True)))
            file.write("\t\t\t<COLOR>{:f} {:f} {:f}</COLOR>\n".format(*blLight.color))
            file.write("\t\t\t<INTENSITY>{:f}</INTENSITY>\n".format(intensity))
            file.write("\t\t\t<ATTENUATIONSTART>{:f}</ATTENUATIONSTART>\n".format(tokenizeDistance(props.attStart, state.convertUnits)))
            file.write("\t\t\t<ATTENUATIONEND>{:f}</ATTENUATIONEND>\n".format(tokenizeDistance(props.attEnd, state.convertUnits)))
            if blLight.use_shadow:  file.write(f"\t\t\t<CASTSHADOW/>\n")
            file.write("\t\t</LIGHT>\n")

        if rsLightCount > 0:    file.write("\t</LIGHTLIST>\n")
        if rsPropCount > 0:     file.write("\t<OBJECTLIST>\n")

        for blPropObj in blPropObjs:
            propFilename = blPropObj.data.gzrs2.propFilename
            propFilename = propFilename.replace(os.extsep + 'elu', '')

            file.write(f"\t\t<OBJECT name=\"{ propFilename }{ os.extsep }elu\"/>\n")

        if rsPropCount > 0:
            file.write("\t</OBJECTLIST>\n")

        if rsDummyCount > 0:
            file.write("\t<DUMMYLIST>\n")

        sm = 1

        for blDummyObj in blDummyObjs:
            objType = blDummyObj.type

            if objType == 'EMPTY':
                dummyName = blDummyObj.name
                dummyNameLower = dummyName.lower()

                props = blDummyObj.gzrs2
                dummyType = props.dummyType

                if dummyType == 'SPAWN':
                    spawnType = props.spawnType
                    exportName = f"spawn_{ props.spawnType }"

                    if      spawnType == 'SOLO':    exportName += f"_{ props.spawnIndex + 100 }"
                    elif    spawnType == 'TEAM':    exportName += f"{ props.spawnTeamID }_{ props.spawnIndex + 100 }"
                    elif    spawnType == 'NPC':     exportName += f"_{ props.spawnEnemyType }_{ str(props.spawnIndex).zfill(2) }"
                    elif    spawnType == 'BLITZ':
                        spawnBlitzType = props.spawnBlitzType
                        # TODO: Support for custom teamIDs, wait, but blitz spawns use letters now? OH GOD
                        spawnTeamAlpha = 'r' if props.spawnTeamID == 1 else 'b'

                        exportName = f"_{ props.spawnBlitzType }"

                        if      spawnBlitzType == 'BARRICADE':  exportName += f"_{ spawnTeamAlpha }"
                        elif    spawnBlitzType == 'RADAR':      exportName += f"_{ spawnTeamAlpha }"

                        exportName += f"_{ str(props.spawnIndex).zfill(2) }"
                elif dummyType == 'FLARE':
                    exportName = "sun_dummy"
                elif dummyType == 'SOUND':
                    exportName = f"snd_amb_{ blDummyObj.name }"
                elif dummyType == 'SMOKE':
                    exportName = f"smk_{ props.smokeType.lower() }"
                    exportName += f"_{ str(sm).zfill(2) }"
                    sm += 1
                elif dummyType == 'ITEM':
                    exportName = f"spawn_item_{ blDummyObj.name }"
            elif objType == 'MESH':
                exportName = blDummyObj.name
            elif objType == 'CAMERA':
                props = blDummyObj.data.gzrs2
                cameraType = props.cameraType

                if      cameraType == 'WAIT':   exportName = f"wait_pos_{ str(props.cameraIndex).zfill(2) }"
                elif    cameraType == 'TRACK':  exportName = f"camera_pos { str(props.cameraIndex).zfill(2) }"

            worldMatrix = blDummyObj.matrix_world.copy()

            if blDummyObj in blCameraObjs:
                worldMatrix = worldMatrix @ reorientCamera

            loc = worldMatrix.to_translation()
            rot = worldMatrix.to_quaternion() @ Vector((0, 1, 0))

            file.write(f"\t\t<DUMMY name=\"{ exportName.lower() }\">\n")
            file.write("\t\t\t<POSITION>{:f} {:f} {:f}</POSITION>\n".format(*tokenizeVec3(loc, 'POSITION', state.convertUnits, True)))
            file.write("\t\t\t<DIRECTION>{:f} {:f} {:f}</DIRECTION>\n".format(*tokenizeVec3(rot, 'DIRECTION', state.convertUnits, True)))
            file.write("\t\t</DUMMY>\n")

        if rsDummyCount > 0:
            file.write("\t</DUMMYLIST>\n")

        if rsOccCount > 0:
            file.write("\t<OCCLUSIONLIST>\n")

        oc = 1

        for blOccObj in blOccObjs:
            occName = blOccObj.name

            worldMatrix = blOccObj.matrix_world.copy()

            # Reorientation is baked into the vertices
            v1 = Vector(( 0.5,  0.5, 0.0))
            v2 = Vector((-0.5,  0.5, 0.0))
            v3 = Vector((-0.5, -0.5, 0.0))
            v4 = Vector(( 0.5, -0.5, 0.0))

            v1 = worldMatrix @ v1
            v2 = worldMatrix @ v2
            v3 = worldMatrix @ v3
            v4 = worldMatrix @ v4

            # TODO: 'wall_' vs 'wall_partition_'?
            file.write(f"\t\t<OCCLUSION name=\"wall_{ str(oc).zfill(2) }\">\n")
            file.write("\t\t\t<POSITION>{:f} {:f} {:f}</POSITION>\n".format(*tokenizeVec3(v1, 'POSITION', state.convertUnits, True)))
            file.write("\t\t\t<POSITION>{:f} {:f} {:f}</POSITION>\n".format(*tokenizeVec3(v2, 'POSITION', state.convertUnits, True)))
            file.write("\t\t\t<POSITION>{:f} {:f} {:f}</POSITION>\n".format(*tokenizeVec3(v3, 'POSITION', state.convertUnits, True)))
            file.write("\t\t\t<POSITION>{:f} {:f} {:f}</POSITION>\n".format(*tokenizeVec3(v4, 'POSITION', state.convertUnits, True)))
            file.write("\t\t</OCCLUSION>\n")

            oc += 1

        if rsOccCount > 0:
            file.write("\t</OCCLUSIONLIST>\n")

        fogColor = worldProps.fogColor
        fogR = int(fogColor.r * 255)
        fogG = int(fogColor.g * 255)
        fogB = int(fogColor.b * 255)

        if worldProps.fogEnable:
            file.write(f"\t<FOG min=\"{ worldProps.fogMin }\" max=\"{ worldProps.fogMax }\">\n")
            file.write(f"\t<R>{ fogR }</R>\n")
            file.write(f"\t<G>{ fogG }</G>\n")
            file.write(f"\t<B>{ fogB }</B>\n")
            file.write("\t</FOG>\n")

        if rsSoundCount > 0:
            file.write("\t<AMBIENTSOUNDLIST>\n")

        identityQuat = Quaternion()

        for blSoundObj in blSoundObjs:
            props = blSoundObj.gzrs2

            soundFileName = props.soundFileName

            soundSpace = props.soundSpace
            soundShape = props.soundShape
            typecode = ('a' if soundSpace == '2D' else 'b') + ('0' if soundShape == 'AABB' else '1')

            file.write(f"\t\t<AMBIENTSOUND ObjName=\"{ blSoundObj.name.lower() }\" type=\"{ typecode }\" filename=\"{ soundFileName }\">\n")

            worldMatrix = blSoundObj.matrix_world.copy()
            loc, rot, sca = worldMatrix.decompose()

            if soundShape == 'AABB':
                if rot != identityQuat:
                    self.report({ 'WARNING' }, f"GZRS2: RS export found sound of type 'AABB' with rotation data! AABB orientation will not correct until you reset it!")

                loc.y = -loc.y

                p1 = loc - sca
                p2 = loc + sca

                file.write("\t\t\t<MIN_POSITION>{:f} {:f} {:f}</MIN_POSITION>\n".format(*tokenizeVec3(p1, 'MIN_POSITION', state.convertUnits, True)))
                file.write("\t\t\t<MAX_POSITION>{:f} {:f} {:f}</MAX_POSITION>\n".format(*tokenizeVec3(p2, 'MAX_POSITION', state.convertUnits, True)))
            elif soundShape == 'SPHERE':
                radius = blSoundObj.empty_display_size * sca.x

                if sca.x != sca.y or sca.x != sca.z:
                    self.report({ 'WARNING' }, f"GZRS2: RS export found sound of type 'SPHERE' with non-uniform scale! Only the x-component will be considered!")

                file.write("\t\t\t<CENTER>{:f} {:f} {:f}</CENTER>\n".format(*tokenizeVec3(loc, 'POSITION', state.convertUnits, True)))
                file.write("\t\t\t<RADIUS>{:d}</RADIUS>\n".format(int(tokenizeDistance(radius, state.convertUnits))))
            file.write("\t\t</AMBIENTSOUND>\n")

        if rsSoundCount > 0:
            file.write("\t</AMBIENTSOUNDLIST>\n")

        file.write("\t<GLOBAL>\n")
        if worldProps.fogEnable:
            file.write(f"\t\t<fog_enable>{ str(worldProps.fogEnable).upper() }</fog_enable>\n")
            file.write(f"\t\t<fog_min>{ worldProps.fogMin }</fog_min>\n")
            file.write(f"\t\t<fog_max>{ worldProps.fogMax }</fog_max>\n")
            file.write(f"\t\t<fog_color>{ fogR },{ fogG },{ fogB }</fog_color>\n")
        file.write(f"\t\t<far_z>{ worldProps.farClip }</far_z>\n")
        file.write("\t</GLOBAL>\n")
        file.write("</XML>\n")

    rsMatTexpaths = tuple(rsMatTexpaths)

    # Write spawn.xml
    itemSoloCount = len(blItemSoloObjs)
    itemTeamCount = len(blItemSoloObjs)

    if itemSoloCount > 0 or itemTeamCount > 0:
        spawnxmlpath = os.path.join(directory, "spawn.xml")

        createBackupFile(spawnxmlpath)

        with open(spawnxmlpath, 'w') as file:
            file.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
            file.write("<XML>\n")

            if itemSoloCount > 0:
                file.write("\t<GAMETYPE id=\"solo\">\n")
                for blItemSoloObj in blItemSoloObjs:
                    loc = blItemSoloObj.matrix_world.to_translation()

                    props = blItemSoloObj.gzrs2
                    itemIDString = str(props.itemID).zfill(2)

                    file.write(f"\t\t<SPAWN item=\"{ props.itemType.lower() }{ itemIDString }\" timesec=\"{ props.itemTimer }\">\n")
                    file.write("\t\t\t<POSITION>{:f} {:f} {:f}</POSITION>\n".format(*tokenizeVec3(loc, 'POSITION', state.convertUnits, True)))
                    file.write(f"\t\t</SPAWN>\n")
                file.write("\t</GAMETYPE>\n")

            if itemTeamCount > 0:
                file.write("\t<GAMETYPE id=\"team\">\n")
                for blItemTeamObj in blItemTeamObjs:
                    loc = blItemTeamObj.matrix_world.to_translation()

                    props = blItemTeamObj.gzrs2
                    itemIDString = str(props.itemID).zfill(2)

                    file.write(f"\t\t<SPAWN item=\"{ props.itemType.lower() }{ itemIDString }\" timesec=\"{ props.itemTimer }\">\n")
                    file.write("\t\t\t<POSITION>{:f} {:f} {:f}</POSITION>\n".format(*tokenizeVec3(loc, 'POSITION', state.convertUnits, True)))
                    file.write(f"\t\t</SPAWN>\n")
                file.write("\t</GAMETYPE>\n")

            file.write("</XML>\n")

    # Write flag.xml
    if len(blPropFlagObjs) > 0:
        flagxmlpath = os.path.join(directory, "flag.xml")

        createBackupFile(flagxmlpath)

        with open(flagxmlpath, 'w') as file:
            file.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
            file.write("<XML>\n")

            for blPropFlagObj in blPropFlagObjs:
                props = blPropFlagObj.data.gzrs2
                windType = FLAG_WINDTYPE_TAGS.index(props.flagWindType)

                # TODO: Reorient

                file.write(f"\t<FLAG NAME=\"{ blPropFlagObj.name.lower() }{ os.extsep }elu\" DIRECTION=\"{ props.flagDirection }\" POWER=\"{ props.flagPower }\">\n")
                # TODO: Multiple windtype data
                file.write(f"\t\t<WINDTYPE TYPE=\"{ windType }\" DELAY=\"{ props.flagWindDelay }\"/>\n")

                # TODO: Multiple limit data
                if props.flagUseLimit:
                    file.write(f"\t\t<RESTRICTION AXIS=\"{ limitAxis }\" POSITION=\"{ props.flagLimitOffset }\" COMPARE=\"{ limitCompare }\" />\n")
                    limitAxis = FLAG_LIMIT_AXIS_TAGS.index(props.flagLimitAxis)
                    limitCompare = FLAG_LIMIT_COMPARE_TAGS.index(props.flagLimitCompare)

                file.write("\t</FLAG>\n")

            file.write("</XML>\n")

    # Write smoke.xml
    if len(blSmokeObjs) > 0:
        smokexmlpath = os.path.join(directory, "smoke.xml")

        createBackupFile(smokexmlpath)

        with open(smokexmlpath, 'w') as file:
            file.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
            file.write("<XML>\n")

            sm = 1

            for blSmokeObj in blSmokeObjs:
                props = blSmokeObj.gzrs2

                exportName = f"smk_{ props.smokeType.lower() }"
                exportName += f"_{ str(sm).zfill(2) }"
                sm += 1

                # TODO: Reorient

                file.write("\t<SMOKE ")
                file.write(f"NAME=\"{           exportName                  }{ os.extsep }elu\" ")
                file.write(f"DIRECTION=\"{      props.smokeDirection        }\" ")
                file.write(f"POWER=\"{          props.smokePower            }\" ")
                file.write(f"DELAY=\"{          props.smokeDelay            }\" ")
                file.write(f"SIZE=\"{           props.smokeSize             }\" ")
                file.write(f"LIFE=\"{           props.smokeLife             }\" ")
                file.write(f"TOGGLEMINTIME=\"{  props.smokeToggleMinTime    }\"/>\n")

            file.write("</XML>\n")

    # Gather vertex & face data
    worldVertices = []
    worldPolygons = []
    o = 0

    for blWorldObj in blWorldObjs:
        blMesh = blWorldObj.data
        uvLayer1 = getOrNone(blMesh.uv_layers, 0)
        uvLayer2 = getOrNone(blMesh.uv_layers, 1)

        hasUV1s = uvLayer1 is not None
        hasUV2s = uvLayer2 is not None
        hasCustomNormals = blMesh.has_custom_normals

        matSlots = blWorldObj.material_slots
        hasMatIDs = len(matSlots) > 0

        worldMatrix = blWorldObj.matrix_world
        worldVertices += tuple(worldMatrix @ vertex.co for vertex in blMesh.vertices)

        for polygon in blMesh.polygons:
            loopRange = range(polygon.loop_start, polygon.loop_start + polygon.loop_total)

            normal      = polygon.normal
            positions   = tuple(worldVertices[o + i] for i in polygon.vertices)
            uv1s        = tuple(uvLayer1.uv[i].vector   for i in loopRange)             if hasUV1s              else tuple(Vector((0, 0)) for _ in loopRange)
            uv2s        = tuple(uvLayer2.uv[i].vector   for i in loopRange)             if hasUV2s              else tuple(Vector((0, 0)) for _ in loopRange)
            normals     = tuple(blMesh.loops[i].normal  for i in loopRange)             if hasCustomNormals     else tuple(normal for _ in loopRange)
            matID       = blWorldMats.index(matSlots[polygon.material_index].material)  if hasMatIDs            else -1
            drawFlags   = 0 # TODO
            area        = polygon.area

            worldPolygons.append(RsWorldPolygon(normal, len(positions), positions, normals, uv1s, uv2s, matID, drawFlags, area))

        o += len(blMesh.vertices)

    worldVertices = tuple(worldVertices)
    worldPolygons = tuple(worldPolygons)

    worldBBMin, worldBBMax = calcCoordinateBounds(worldVertices)

    # Generate RS convex polygons
    rsConvexPolygons = []
    rsCVertexCount = 0

    for polygon in worldPolygons:
        normal = polygon.normal.normalized()
        plane = normal.to_4d()
        plane.w = -normal.dot(polygon.positions[0])
        vertexCount = polygon.vertexCount
        positions = tuple(polygon.positions)
        normals = tuple(normal.normalized() for normal in polygon.normals)

        rsConvexPolygons.append(RsConvexPolygonExport(polygon.matID, polygon.drawFlags, plane, polygon.area, vertexCount, positions, normals))
        rsCVertexCount += vertexCount

    rsConvexPolygons = tuple(rsConvexPolygons)
    rsCPolygonCount = len(rsConvexPolygons)

    # Generate Rs octree nodes
    rsOctreePolygons = []

    for convexID, polygon in enumerate(worldPolygons):
        vertexCount = polygon.vertexCount
        vertices = []

        for i in range(vertexCount):
            pos = polygon.positions[i].copy()
            nor = polygon.normals[i].normalized()
            uv1 = polygon.uv1s[i].copy()
            uv2 = polygon.uv2s[i].copy()

            vertices.append(Rs2TreeVertex(pos, nor, uv1, uv2))
        rsOctreePolygons.append(Rs2TreePolygonExport(polygon.matID, convexID, polygon.drawFlags, vertexCount, tuple(vertices), polygon.normal, False))

    rsOctreePolygons = tuple(rsOctreePolygons)

    rsOctreeRoot = createOctreeNode(rsOctreePolygons, worldBBMin, worldBBMax, calcDepthLimit(worldBBMin, worldBBMax))

    rsONodeCount        = getTreeNodeCount(rsOctreeRoot)
    rsOPolygonCount     = getTreePolygonCount(rsOctreeRoot)
    rsOVertexCount      = getTreeVertexCount(rsOctreeRoot)
    rsOIndexCount       = getTreeIndicesCount(rsOctreeRoot)

    def getOctreeLmUVs(node, *, data = []):
        if node.positive: getOctreeLmUVs(node.positive, data = data)
        if node.negative: getOctreeLmUVs(node.negative, data = data)

        for polygon in node.polygons:
            for vertex in polygon.vertices:
                data.append(vertex.uv2.copy())

        return data

    rsOctreeLmUVs = tuple(getOctreeLmUVs(rsOctreeRoot))

    # Generate Bsp nodes
    rsBsptreePolygons = []

    for convexID, polygon in enumerate(worldPolygons):
        vertexCount = polygon.vertexCount
        vertices = []

        for i in range(vertexCount):
            pos = polygon.positions[i].copy()
            nor = polygon.normals[i].normalized()
            uv1 = polygon.uv1s[i].copy()
            uv2 = polygon.uv2s[i].copy()

            vertices.append(Rs2TreeVertex(pos, nor, uv1, uv2))

        rsBsptreePolygons.append(Rs2TreePolygonExport(polygon.matID, convexID, polygon.drawFlags, vertexCount, tuple(vertices), polygon.normal, False))

    rsBsptreePolygons = tuple(rsBsptreePolygons)

    rsBsptreeRoot = createBsptreeNode(rsBsptreePolygons, worldBBMin, worldBBMax)

    rsBNodeCount        = getTreeNodeCount(rsBsptreeRoot)
    rsBPolygonCount     = getTreePolygonCount(rsBsptreeRoot)
    rsBVertexCount      = getTreeVertexCount(rsBsptreeRoot)
    rsBIndexCount       = getTreeIndicesCount(rsBsptreeRoot)

    bspNodeCount        = rsBNodeCount
    bspPolygonCount     = rsBPolygonCount
    bspVertexCount      = rsBVertexCount
    bspIndexCount       = rsBIndexCount

    def writeTreeNode(node):
        writeBounds(file, node.bbmin, node.bbmax, state.convertUnits)
        writePlane(file, node.plane, state.convertUnits, True)

        writeBool(file, node.positive is not None)
        if node.positive is not None:
            writeTreeNode(node.positive)

        writeBool(file, node.negative is not None)
        if node.negative is not None:
            writeTreeNode(node.negative)

        writeUInt(file, len(node.polygons))

        for polygon in node.polygons:
            writeInt(file, polygon.matID)
            writeUInt(file, polygon.convexID)
            writeUInt(file, polygon.drawFlags)
            writeUInt(file, polygon.vertexCount)

            for vertex in polygon.vertices:
                writeCoordinate(file, vertex.pos, state.convertUnits, True)
                writeDirection(file, vertex.nor, True)
                writeUV2(file, vertex.uv1)
                writeUV2(file, vertex.uv2)

            writeDirection(file, polygon.normal, True)

    # Write Rs
    if state.logRsHeaders or state.logRsTrees or state.logRsPolygons or state.logRsVerts:
        print("===================  Write Rs   ===================")
        print()

    id = RS2_ID
    version = RS2_VERSION

    if state.logRsHeaders:
        print(f"Path:               { rspath }")
        print(f"ID:                 { hex(id) }")
        print(f"Version:            { hex(version) }")
        print()

    createBackupFile(rspath)

    with open(rspath, 'wb') as file:
        writeUInt(file, id)
        writeUInt(file, version)

        writeInt(file, rsMatCount)

        for texpath in rsMatTexpaths:
            writeStringPacked(file, texpath)

        writeUInt(file, rsCPolygonCount)
        writeUInt(file, rsCVertexCount)

        for polygon in rsConvexPolygons:
            writeInt(file, polygon.matID)
            writeUInt(file, polygon.drawFlags)
            writePlane(file, polygon.plane, state.convertUnits, True)
            writeFloat(file, polygon.area)
            writeUInt(file, polygon.vertexCount)

            writeCoordinateArray(file, polygon.positions, state.convertUnits, True)
            writeDirectionArray(file, polygon.normals, True)

        writeUInt(file, rsBNodeCount)
        writeUInt(file, rsBPolygonCount)
        writeUInt(file, rsBVertexCount)
        writeUInt(file, rsBIndexCount)

        writeUInt(file, rsONodeCount)
        writeUInt(file, rsOPolygonCount)
        writeUInt(file, rsOVertexCount)
        writeUInt(file, rsOIndexCount)

        writeTreeNode(rsOctreeRoot)

    # Write Bsp
    if state.logBspHeaders or state.logBspPolygons or state.logBspVerts:
        print("===================  Write Bsp  ===================")
        print()

    id = BSP_ID
    version = BSP_VERSION

    bsppath = f"{ rspath }{ os.extsep }bsp"

    if state.logBspHeaders:
        print(f"Path:               { bsppath }")
        print(f"ID:                 { hex(id) }")
        print(f"Version:            { hex(version) }")
        print()

    createBackupFile(bsppath)

    with open(bsppath, 'wb') as file:
        writeUInt(file, id)
        writeUInt(file, version)

        writeUInt(file, bspNodeCount)
        writeUInt(file, bspPolygonCount)
        writeUInt(file, bspVertexCount)
        writeUInt(file, bspIndexCount)

        writeTreeNode(rsBsptreeRoot)

    # Generate Col nodes
    coltreeVertices = []
    coltreePolygons = []
    o = 0

    for blColObj in blColObjs:
        blMesh = blColObj.data

        worldMatrix = blColObj.matrix_world
        coltreeVertices += tuple(worldMatrix @ vertex.co for vertex in blMesh.vertices)

        for polygon in blMesh.polygons:
            positions = tuple(coltreeVertices[o + i] for i in polygon.vertices)
            normal = polygon.normal.normalized()

            coltreePolygons.append(Col1HullPolygon(len(positions), positions, normal, False))

        o += len(blMesh.vertices)

    coltreeVertices = tuple(coltreeVertices)
    coltreePolygons = tuple(coltreePolygons)

    colBBMin, colBBMax = calcCoordinateBounds(coltreeVertices)
    coltreeBoundsQuads = tuple(createBoundsQuad(colBBMin, colBBMax, s) for s in range(6))

    col1Root = createColtreeNode(coltreePolygons, coltreeBoundsQuads)

    colNodeCount        = getTreeNodeCount(col1Root)
    colTriangleCount    = getTreeTriangleCount(col1Root)

    # Write Col
    if state.logColHeaders or state.logColNodes or state.logColTris:
        print("===================  Write Col  ===================")
        print()

    id = COL1_ID
    version = COL1_VERSION

    colpath = f"{ rspath }{ os.extsep }col"

    if state.logColHeaders:
        print(f"Path:               { colpath }")
        print(f"ID:                 { hex(id) }")
        print(f"Version:            { hex(version) }")
        print()

    createBackupFile(colpath)

    with open(colpath, 'wb') as file:
        writeUInt(file, id)
        writeUInt(file, version)

        writeUInt(file, colNodeCount)
        writeUInt(file, colTriangleCount)

        def writeCol1Node(node):
            writePlane(file, node.plane, state.convertUnits, True)
            writeBool(file, node.solid)

            writeBool(file, node.positive is not None)
            if node.positive is not None:
                writeCol1Node(node.positive)

            writeBool(file, node.negative is not None)
            if node.negative is not None:
                writeCol1Node(node.negative)

            writeUInt(file, len(node.triangles))

            for triangle in node.triangles:
                writeCoordinateArray(file, triangle.vertices, state.convertUnits, True)
                writeDirection(file, triangle.normal, True)

        writeCol1Node(col1Root)

    # Gather lightmap data
    lightmapImage = worldProps.lightmapImage
    # Never atlas, we increase the lightmap resolution instead
    # numCells = worldProps.lightmapNumCells
    numCells = 1

    imageDatas, imageSizes = generateLightmapData(self, lightmapImage, numCells, state)
    imageCount = len(imageDatas)

    if not imageDatas or not imageSizes:
        return { 'CANCELLED' }

    polygonOrder = bytearray(rsOPolygonCount * 4)
    lightmapIDs = bytearray(rsOPolygonCount * 4)
    lightmapUVs = bytearray(rsOVertexCount * 2 * 4)

    polygonOrderInts = memoryview(polygonOrder).cast('I')
    lightmapIDsInts = memoryview(lightmapIDs).cast('I')
    lightmapUVsFloats = memoryview(lightmapUVs).cast('f')

    # Never atlas, we increase the lightmap resolution instead
    for p in range(rsOPolygonCount):
        polygonOrderInts[p] = p
        lightmapIDsInts[p] = 0

    for v in range(rsOVertexCount):
        uv2 = rsOctreeLmUVs[v]

        lightmapUVsFloats[v * 2 + 0] = uv2.x
        lightmapUVsFloats[v * 2 + 1] = 1 - uv2.y

    polygonOrderInts.release()
    lightmapIDsInts.release()
    lightmapUVsFloats.release()

    # Write LM
    if state.logLmHeaders or state.logLmImages:
        print("===================  Write Lm   ===================")
        print()

    id = LM_ID
    version = LM_VERSION_EXT if state.lmVersion4 else LM_VERSION
    lmCPolygonCount = rsCPolygonCount # CONVEX polygon count!
    lmONodeCount = rsONodeCount # OCTREE node count!

    lmpath = f"{ rspath }{ os.extsep }lm"

    if state.logLmHeaders:
        print(f"Path:               { lmpath }")
        print(f"ID:                 { hex(id) }")
        print(f"Version:            { hex(version) }")
        print(f"Image Count:        { imageCount }")
        print()

    createBackupFile(lmpath)

    with open(lmpath, 'wb') as file:
        writeUInt(file, id)
        writeUInt(file, version)

        writeUInt(file, lmCPolygonCount)
        writeUInt(file, lmONodeCount)
        writeUInt(file, len(imageDatas))

        for i in range(imageCount):
            imageData = imageDatas[i]
            imageSize = imageSizes[i]

            pixelCount = imageSize ** 2

            if state.lmVersion4:
                ddsSize = 76 + 32 + 20 + pixelCount // 2
                writeUInt(file, ddsSize)
                writeDDSHeader(file, imageSize, pixelCount, ddsSize)
            else:
                bmpSize = 14 + 40 + pixelCount * 3
                writeUInt(file, bmpSize)
                writeBMPHeader(file, imageSize, bmpSize)

            file.write(imageData)

        file.write(polygonOrder)
        file.write(lightmapIDs)
        file.write(lightmapUVs)

        file.truncate()

    # Dump Images
    dumpImageData(imageDatas, imageSizes, imageCount, directory, filename, state)

    return { 'FINISHED' }
