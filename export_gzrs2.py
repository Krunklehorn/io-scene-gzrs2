#####
# Most of the code is based on logic found in...
#
### GunZ 1
# - RBspObject.h/.cpp
# - LightmapGenerator.h/.cpp
# - RBspExporter.cpp
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

    state.purgeUnused       = self.purgeUnused
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

        state.logRs     = self.logRs
        state.logBsp    = self.logBsp
        state.logCol    = self.logCol
        state.logLm     = self.logLm

    rspath = self.filepath
    directory = os.path.dirname(rspath)
    basename = bpy.path.basename(rspath)
    splitname = basename.split(os.extsep)
    filename = splitname[0]

    rsxmlpath = f"{ rspath }{ os.extsep }xml"
    spawnxmlpath = os.path.join(directory, "spawn.xml")
    flagxmlpath = os.path.join(directory, "flag.xml")
    smokexmlpath = os.path.join(directory, "smoke.xml")
    bsppath = f"{ rspath }{ os.extsep }bsp"
    colpath = f"{ rspath }{ os.extsep }col"
    lmpath = f"{ rspath }{ os.extsep }lm"

    exportPaths = (rspath, rsxmlpath, spawnxmlpath, flagxmlpath, smokexmlpath, bsppath, colpath, lmpath)

    for exportPath in exportPaths:
        createBackupFile(exportPath, purgeUnused = state.purgeUnused)

    windowManager = context.window_manager

    objects = getFilteredObjects(context, state)

    # TODO: New material tags
    #   at_:    adds <ALPHATEST/>?
    #   hide_:  not rendered at runtime, useless?
    #   pass_:  rendered but ignored by collision, useless?
    #   passb_: bullets pass through
    #   passr_: bullets, rockets and grenades pass through

    # TODO: New mesh tags
    #   algn#_: 0 face camera, 1 face camera fixed z-axis
    #   water_: it's wet
    #   sea_:   it's wet

    # TODO: Verify blitzkrieg data
    # TODO: Verify flag data
    # TODO: Verify smoke data

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

    windowManager.progress_begin(0, len(objects))

    for o, object in enumerate(objects):
        windowManager.progress_update(o)

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

                if meshType == 'WORLD' and props.worldCollision:
                    blColObjs.append(object)
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

    def sortOcclusion(x):
        return (
            x.gzrs2.occBsp,
            x.gzrs2.occOct,
            x.gzrs2.occPriority,
            x.name
        )

    def sortCamera(x):
        return (
            CAMERA_TYPE_TAGS.index(x.data.gzrs2.cameraType),
            x.data.gzrs2.cameraIndex,
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

    blOccObjs           = tuple(sorted(blOccObjs,           key = sortOcclusion))

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
    for blPropObj           in blPropObjsAll:       blDummyObjs.append(blPropObj)
    for blCameraWaitObj     in blCameraWaitObjs:    blDummyObjs.append(blCameraWaitObj)
    for blCameraTrackObj    in blCameraTrackObjs:   blDummyObjs.append(blCameraTrackObj)

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

    blWorldMats     = set(matSlot.material for blWorldObj   in blWorldObjs      for matSlot in blWorldObj.material_slots)
    blPropMats      = set(matSlot.material for blPropObj    in blPropObjsAll    for matSlot in blPropObj.material_slots)
    blPropMats      |= set(blPropMat.gzrs2.parent for blPropMat in blPropMats) - { None }

    if len(blWorldMats) == 0:
        self.report({ 'ERROR' }, f"GZRS2: RS export requires at least one world material!")
        return { 'CANCELLED' }

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
    rsPropCount = len(blPropObjsAll)
    rsDummyCount = len(blDummyObjs)
    rsOccCount = len(blOccObjs)
    rsSoundCount = len(blSoundObjs)

    rsMatTexpaths = []
    reorientCamera = Matrix.Rotation(math.radians(-90.0), 4, 'X')

    propFilenames = set()

    for blPropObj in blPropObjsAll:
        propFilename = blPropObj.data.gzrs2.propFilename
        propFilename = propFilename.replace(os.extsep + 'elu', '')

        if propFilename == '':
            self.report({ 'ERROR' }, f"GZRS2: Prop with empty filename: { blPropObj.name }")
            return { 'CANCELLED' }

        propFilenames.add(propFilename)

    windowManager.progress_end()
    windowManager.progress_begin(0, rsMatCount + rsLightCount + rsPropCount + rsDummyCount + rsOccCount + rsSoundCount)
    progress = 0

    # Write .rs.xml
    with open(rsxmlpath, 'w') as file:
        file.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
        file.write("<XML>\n")

        if rsMatCount > 0:
            file.write("\t<MATERIALLIST>\n")

        for m, blWorldMat in enumerate(blWorldMats):
            progress += 1
            windowManager.progress_update(progress)

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
                    transparentValid    == False,   mixValid    == False)):
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
            progress += 1
            windowManager.progress_update(progress)

            loc = blLightObj.matrix_world.to_translation()

            blLight = blLightObj.data
            props = blLight.gzrs2

            lightType = props.lightType
            lightSubtype = props.lightSubtype
            intensity = props.intensity

            if lightSubtype == 'SUN':
                lightName = 'sun_omni'
            else:
                lightName = blLightObj.name

                lightName = lightName.replace('obj_', '')
                lightName = lightName.replace('_obj', '')
                lightName = lightName.replace('sun_', '')
                lightName = lightName.replace('_sun', '')
                lightName = lightName.replace('sun_omni_', '')
                lightName = lightName.replace('_sun_omni', '')

                if lightType == 'DYNAMIC':
                    lightName = 'obj_' + lightName

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

        for propFilename in propFilenames:
            progress += 1
            windowManager.progress_update(progress)

            file.write(f"\t\t<OBJECT name=\"{ propFilename }{ os.extsep }elu\"/>\n")

        if rsPropCount > 0:
            file.write("\t</OBJECTLIST>\n")

        if rsDummyCount > 0:
            file.write("\t<DUMMYLIST>\n")

        sm = 1

        for blDummyObj in blDummyObjs:
            progress += 1
            windowManager.progress_update(progress)

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

        bspPlanes   = []
        octPlanes   = []
        oc = 1

        for blOccObj in blOccObjs:
            if blOccObj.gzrs2.occOct:
                blOccObj.rotation_euler = eulerSnapped(blOccObj.rotation_euler)

        context.view_layer.update()

        for blOccObj in blOccObjs:
            progress += 1
            windowManager.progress_update(progress)

            props = blOccObj.gzrs2
            occPrefix = ''

            if props.occOct:    occPrefix = 'partition_' + occPrefix
            if props.occProp:   occPrefix = 'wall_' + occPrefix

            if occPrefix == '':
                occPrefix = 'plane_'

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

            normal = worldMatrix.to_quaternion() @ Vector((0, 0, 1))
            plane = normal.to_4d()
            plane.w = -normal.dot(worldMatrix.translation)

            if props.occBsp:    bspPlanes.append(plane)
            if props.occOct:    octPlanes.append(plane)

            file.write(f"\t\t<OCCLUSION name=\"{ occPrefix }{ str(oc).zfill(2) }\">\n")
            file.write("\t\t\t<POSITION>{:f} {:f} {:f}</POSITION>\n".format(*tokenizeVec3(v1, 'POSITION', state.convertUnits, True)))
            file.write("\t\t\t<POSITION>{:f} {:f} {:f}</POSITION>\n".format(*tokenizeVec3(v2, 'POSITION', state.convertUnits, True)))
            file.write("\t\t\t<POSITION>{:f} {:f} {:f}</POSITION>\n".format(*tokenizeVec3(v3, 'POSITION', state.convertUnits, True)))
            file.write("\t\t\t<POSITION>{:f} {:f} {:f}</POSITION>\n".format(*tokenizeVec3(v4, 'POSITION', state.convertUnits, True)))
            file.write("\t\t</OCCLUSION>\n")

            oc += 1

        if rsOccCount > 0:
            file.write("\t</OCCLUSIONLIST>\n")

        fogColor = worldProps.fogColor
        fogMin = tokenizeDistance(worldProps.fogMin, state.convertUnits)
        fogMax = tokenizeDistance(worldProps.fogMax, state.convertUnits)
        fogR = int(fogColor.r * 255)
        fogG = int(fogColor.g * 255)
        fogB = int(fogColor.b * 255)

        if worldProps.fogEnable:
            file.write(f"\t<FOG min=\"{ fogMin }\" max=\"{ fogMax }\">\n")
            file.write(f"\t<R>{ fogR }</R>\n")
            file.write(f"\t<G>{ fogG }</G>\n")
            file.write(f"\t<B>{ fogB }</B>\n")
            file.write("\t</FOG>\n")

        if rsSoundCount > 0:
            file.write("\t<AMBIENTSOUNDLIST>\n")

        identityQuat = Quaternion()

        for blSoundObj in blSoundObjs:
            progress += 1
            windowManager.progress_update(progress)

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
            file.write(f"\t\t<fog_min>{ fogMin }</fog_min>\n")
            file.write(f"\t\t<fog_max>{ fogMax }</fog_max>\n")
            file.write(f"\t\t<fog_color>{ fogR },{ fogG },{ fogB }</fog_color>\n")
        file.write(f"\t\t<far_z>{ tokenizeDistance(worldProps.farClip, state.convertUnits) }</far_z>\n")
        file.write("\t</GLOBAL>\n")
        file.write("</XML>\n")

    rsMatTexpaths = tuple(rsMatTexpaths)

    # Write spawn.xml
    itemSoloCount = len(blItemSoloObjs)
    itemTeamCount = len(blItemTeamObjs)

    if itemSoloCount > 0 or itemTeamCount > 0:
        with open(spawnxmlpath, 'w') as file:
            file.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
            file.write("<XML>\n")

            if itemSoloCount > 0:
                file.write("\t<GAMETYPE id=\"solo\">\n")
                for blItemSoloObj in blItemSoloObjs:
                    loc = blItemSoloObj.matrix_world.to_translation()

                    props = blItemSoloObj.gzrs2
                    itemIDString = str(props.itemID).zfill(2)

                    file.write(f"\t\t<SPAWN item=\"{ props.itemType.lower() }{ itemIDString }\" timesec=\"{ int(props.itemTimer * 1000) }\">\n")
                    file.write("\t\t\t<POSITION>{:f} {:f} {:f}</POSITION>\n".format(*tokenizeVec3(loc, 'POSITION', state.convertUnits, True)))
                    file.write(f"\t\t</SPAWN>\n")
                file.write("\t</GAMETYPE>\n")

            if itemTeamCount > 0:
                file.write("\t<GAMETYPE id=\"team\">\n")
                for blItemTeamObj in blItemTeamObjs:
                    loc = blItemTeamObj.matrix_world.to_translation()

                    props = blItemTeamObj.gzrs2
                    itemIDString = str(props.itemID).zfill(2)

                    file.write(f"\t\t<SPAWN item=\"{ props.itemType.lower() }{ itemIDString }\" timesec=\"{ int(props.itemTimer * 1000) }\">\n")
                    file.write("\t\t\t<POSITION>{:f} {:f} {:f}</POSITION>\n".format(*tokenizeVec3(loc, 'POSITION', state.convertUnits, True)))
                    file.write(f"\t\t</SPAWN>\n")
                file.write("\t</GAMETYPE>\n")

            file.write("</XML>\n")

    # Write flag.xml
    if len(blPropFlagObjs) > 0:
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

    windowManager.progress_end()
    windowManager.progress_begin(0, len(blWorldObjs))

    for w, blWorldObj in enumerate(blWorldObjs):
        windowManager.progress_update(w)

        blMesh = blWorldObj.data
        props = blMesh.gzrs2

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
            detail      = props.worldDetail

            worldPolygons.append(RsWorldPolygon(normal, len(positions), positions, normals, uv1s, uv2s, matID, drawFlags, area, detail))

        o += len(blMesh.vertices)

    worldVertices = tuple(worldVertices)
    worldPolygons = tuple(worldPolygons)

    worldBBMin, worldBBMax = calcCoordinateBounds(worldVertices)

    # Generate RS convex polygons
    rsConvexPolygons = []
    rsCVertexCount = 0

    windowManager.progress_end()
    windowManager.progress_begin(0, len(worldPolygons))

    for p, polygon in enumerate(worldPolygons):
        windowManager.progress_update(w)

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

    windowManager.progress_end()
    windowManager.progress_begin(0, len(worldPolygons))

    for convexID, polygon in enumerate(worldPolygons):
        windowManager.progress_update(convexID)

        vertexCount = polygon.vertexCount
        vertices = []

        for i in range(vertexCount):
            pos = polygon.positions[i].copy()
            nor = polygon.normals[i].normalized()
            uv1 = polygon.uv1s[i].copy()
            uv2 = polygon.uv2s[i].copy()

            vertices.append(Rs2TreeVertex(pos, nor, uv1, uv2))
        rsOctreePolygons.append(Rs2TreePolygonExport(polygon.matID, convexID, polygon.drawFlags, vertexCount, tuple(vertices), polygon.normal, polygon.detail))

    rsOctreePolygons = tuple(rsOctreePolygons)

    depthLimit = calcDepthLimit(worldBBMin, worldBBMax)

    windowManager.progress_end()
    windowManager.progress_begin(0, depthLimit)

    try:
        rsOctreeRoot = createOctreeNode(rsOctreePolygons, octPlanes, worldBBMin, worldBBMax, depthLimit, windowManager)
    except (GZRS2EdgePlaneIntersectionError, GZRS2DegeneratePolygonError) as error:
        self.report({ 'ERROR' }, error.message)
        return { 'CANCELLED' }

    rsONodeCount        = getTreeNodeCount(rsOctreeRoot)
    rsOPolygonCount     = getTreePolygonCount(rsOctreeRoot)
    rsOVertexCount      = getTreeVertexCount(rsOctreeRoot)
    rsOIndexCount       = getTreeIndicesCount(rsOctreeRoot)
    rsOTreeDepth        = getTreeDepth(rsOctreeRoot)

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

    windowManager.progress_end()
    windowManager.progress_begin(0, len(worldPolygons))

    for convexID, polygon in enumerate(worldPolygons):
        windowManager.progress_update(convexID)

        vertexCount = polygon.vertexCount
        vertices = []

        for i in range(vertexCount):
            pos = polygon.positions[i].copy()
            nor = polygon.normals[i].normalized()
            uv1 = polygon.uv1s[i].copy()
            uv2 = polygon.uv2s[i].copy()

            vertices.append(Rs2TreeVertex(pos, nor, uv1, uv2))

        rsBsptreePolygons.append(Rs2TreePolygonExport(polygon.matID, convexID, polygon.drawFlags, vertexCount, tuple(vertices), polygon.normal, polygon.detail))

    rsBsptreePolygons = tuple(rsBsptreePolygons)

    windowManager.progress_end()
    windowManager.progress_begin(0, 1)

    try:
        rsBsptreeRoot = createBsptreeNode(rsBsptreePolygons, bspPlanes, worldBBMin, worldBBMax, windowManager)
    except (GZRS2EdgePlaneIntersectionError, GZRS2DegeneratePolygonError) as error:
        self.report({ 'ERROR' }, error.message)
        return { 'CANCELLED' }

    rsBNodeCount        = getTreeNodeCount(rsBsptreeRoot)
    rsBPolygonCount     = getTreePolygonCount(rsBsptreeRoot)
    rsBVertexCount      = getTreeVertexCount(rsBsptreeRoot)
    rsBIndexCount       = getTreeIndicesCount(rsBsptreeRoot)
    rsBTreeDepth        = getTreeDepth(rsBsptreeRoot)

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
    id = RS2_ID
    version = RS2_VERSION

    if state.logRs:
        print("===================  Write Rs   ===================")
        print()
        print(f"Path:               { rspath }")
        print(f"ID:                 { hex(id) }")
        print(f"Version:            { hex(version) }")
        print()
        print(f"Material Count:     { rsMatCount }")
        print()
        print("Convex:")
        print(f"Polygon Count:      { rsCPolygonCount }")
        print(f"Vertex Count:       { rsCVertexCount }")
        print()
        print("Bsptree:")
        print(f"Node Count:         { rsBNodeCount }")
        print(f"Polygon Count:      { rsBPolygonCount }")
        print(f"Vertex Count:       { rsBVertexCount }")
        print(f"Index Count:        { rsBIndexCount }")
        print(f"Depth:              { rsBTreeDepth }")
        print()
        print("Octree:")
        print(f"Node Count:         { rsONodeCount }")
        print(f"Polygon Count:      { rsOPolygonCount }")
        print(f"Vertex Count:       { rsOVertexCount }")
        print(f"Index Count:        { rsOIndexCount }")
        print(f"Depth:              { rsOTreeDepth }")
        print()

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
    id = BSP_ID
    version = BSP_VERSION

    if state.logBsp:
        print("===================  Write Bsp  ===================")
        print()
        print(f"Path:               { bsppath }")
        print(f"ID:                 { hex(id) }")
        print(f"Version:            { hex(version) }")
        print()
        print(f"Node Count:         { bspNodeCount }")
        print(f"Polygon Count:      { bspPolygonCount }")
        print(f"Vertex Count:       { bspVertexCount }")
        print(f"Index Count:        { bspIndexCount }")
        print()

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

    windowManager.progress_end()
    windowManager.progress_begin(0, len(blColObjs))

    for c, blColObj in enumerate(blColObjs):
        windowManager.progress_update(c)

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

    windowManager.progress_end()
    windowManager.progress_begin(0, 1)

    try:
        col1Root = createColtreeNode(coltreePolygons, coltreeBoundsQuads, windowManager)
    except (GZRS2EdgePlaneIntersectionError, GZRS2DegeneratePolygonError) as error:
        self.report({ 'ERROR' }, error.message)
        return { 'CANCELLED' }

    colNodeCount        = getTreeNodeCount(col1Root)
    colTriangleCount    = getTreeTriangleCount(col1Root)
    colTreeDepth        = getTreeDepth(col1Root)

    # Write Col
    id = COL1_ID
    version = COL1_VERSION

    if state.logCol:
        print("===================  Write Col  ===================")
        print()
        print(f"Path:               { colpath }")
        print(f"ID:                 { hex(id) }")
        print(f"Version:            { hex(version) }")
        print()
        print(f"Node Count:         { colNodeCount }")
        print(f"Triangle Count:     { colTriangleCount }")
        print(f"Depth:              { colTreeDepth }")
        print()

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

    if lightmapImage:
        imageDatas, imageSizes = generateLightmapData(self, lightmapImage, numCells, state)

        if not imageDatas or not imageSizes:
            return { 'CANCELLED' }
    else:
        pixelCount = LM_MIN_SIZE ** 2
        floats = tuple(1.0 for _ in range(pixelCount * 4))
        imageData = packLmImageData(self, LM_MIN_SIZE, floats, state)

        imageDatas, imageSizes = (imageData,), (LM_MIN_SIZE,)

    imageCount = len(imageDatas)

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
    id = LM_ID
    version = LM_VERSION_EXT if state.lmVersion4 else LM_VERSION
    lmCPolygonCount = rsCPolygonCount # CONVEX polygon count!
    lmONodeCount = rsONodeCount # OCTREE node count!

    if state.logLm:
        print("===================  Write Lm   ===================")
        print()
        print(f"Path:               { lmpath }")
        print(f"ID:                 { hex(id) }")
        print(f"Version:            { hex(version) }")
        print()
        print(f"Image Count:        { imageCount }")
        print()

    with open(lmpath, 'wb') as file:
        writeUInt(file, id)
        writeUInt(file, version)

        writeUInt(file, lmCPolygonCount)
        writeUInt(file, lmONodeCount)
        writeUInt(file, imageCount)

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

    windowManager.progress_end()

    return { 'FINISHED' }
