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

from contextlib import redirect_stdout
from mathutils import Vector, Matrix

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .parse_gzrs2 import *
from .readrs_gzrs2 import *
from .readbsp_gzrs2 import *
from .readcol_gzrs2 import *
from .readnav_gzrs2 import *
from .readlm_gzrs2 import *
from .readelu_gzrs2 import *
from .lib_gzrs2 import *

def importRS2(self, context):
    state = GZRS2State()

    rs2DataDir = os.path.dirname(context.preferences.addons[__package__].preferences.rs2DataDir)

    if self.texSearchMode == 'PATH':
        if not rs2DataDir:
            self.report({ 'ERROR' }, f"GZRS2: Must specify a path to search for or select a different texture mode! Verify your path in the plugin's preferences!")
            return { 'CANCELLED' }

        if not matchRSDataDirectory(self, rs2DataDir, os.path.basename(rs2DataDir), False, state):
            self.report({ 'ERROR' }, f"GZRS2: Search path must point to a folder containing a valid data subdirectory! Verify your path in the plugin's preferences!")
            return { 'CANCELLED' }

    state.convertUnits      = self.convertUnits
    state.meshMode          = self.meshMode
    state.texSearchMode     = self.texSearchMode
    state.doBsptree         = self.doBsptree        and self.meshMode != 'BAKE'
    state.doCollision       = self.doCollision      and self.meshMode != 'BAKE'
    state.doNavigation      = self.doNavigation     and self.meshMode != 'BAKE'
    state.doLightmap        = self.doLightmap
    state.doLights          = self.doLights
    state.tweakLights       = self.tweakLights      and self.doLights
    state.doProps           = self.doProps
    state.doDummies         = self.doDummies        and self.meshMode != 'BAKE'
    state.doOcclusion       = self.doOcclusion      and self.meshMode != 'BAKE'
    state.doFog             = self.doFog
    state.doSounds          = self.doSounds         and self.meshMode != 'BAKE'
    state.doItems           = self.doItems          and self.meshMode != 'BAKE'
    state.doBounds          = self.doBounds         and self.meshMode != 'BAKE'
    state.doLightDrivers    = self.doLightDrivers
    state.doFogDriver       = self.doFogDriver
    state.doCleanup         = self.doCleanup

    if self.panelLogging:
        print()
        print("=======================================================================")
        print("===========================  GZRS2 Import  ============================")
        print("=======================================================================")
        print(f"== { self.filepath }")
        print("=======================================================================")
        print()

        state.logRsHeaders          = self.logRsHeaders
        state.logRsPortals          = self.logRsPortals
        state.logRsCells            = self.logRsCells
        state.logRsGeometry         = self.logRsGeometry
        state.logRsTrees            = self.logRsTrees
        state.logRsPolygons         = self.logRsPolygons
        state.logRsVerts            = self.logRsVerts
        state.logBspHeaders         = self.logBspHeaders
        state.logBspPolygons        = self.logBspPolygons
        state.logBspVerts           = self.logBspVerts
        state.logColHeaders         = self.logColHeaders
        state.logColNodes           = self.logColNodes
        state.logColTris            = self.logColTris
        state.logNavHeaders         = self.logNavHeaders
        state.logNavData            = self.logNavData
        state.logLmHeaders          = self.logLmHeaders
        state.logLmImages           = self.logLmImages
        state.logEluHeaders         = self.logEluHeaders
        state.logEluMats            = self.logEluMats
        state.logEluMeshNodes       = self.logEluMeshNodes
        state.logVerboseIndices     = self.logVerboseIndices    and self.logEluMeshNodes
        state.logVerboseWeights     = self.logVerboseWeights    and self.logEluMeshNodes
        state.logCleanup            = self.logCleanup

    rspath = self.filepath
    state.directory = os.path.dirname(rspath)
    state.filename = os.path.basename(rspath).split(os.extsep)[0]

    xmlRs = False
    for ext in XML_EXTENSIONS:
        rsxmlpath = pathExists(f"{ rspath }.{ ext }")

        if rsxmlpath:
            with open(rsxmlpath, encoding = 'utf-8') as file:
                xmlRs = minidom.parseString(file.read())
            break

    if not rsxmlpath:
        state.doLights = False
        state.doProps = False
        state.doDummies = False
        state.doOcclusion = False
        state.doFog = False
        state.doSounds = False
        self.report({ 'ERROR' }, "GZRS2: Map xml not found, no materials or objects to generate!")

    xmlSpawn = False
    spawnxmlpath = os.path.join(state.directory, "spawn.xml")

    if state.doItems:
        for ext in XML_EXTENSIONS:
            spawnxmlpath = pathExists(os.path.join(state.directory, f"spawn.{ ext }"))

            if spawnxmlpath:
                with open(spawnxmlpath, encoding = 'utf-8') as file:
                    xmlSpawn = minidom.parseString(file.read())
                break

        if not spawnxmlpath: self.report({ 'INFO' }, "GZRS2: Items requested but spawn.xml not found, no items to generate.")

    if xmlRs:
        state.xmlRsMats = parseRsXML(self, xmlRs, 'MATERIAL', state)
        if state.doLights:      state.xmlLits = parseRsXML(self, xmlRs, 'LIGHT', state)
        if state.doProps:       state.xmlObjs = parseRsXML(self, xmlRs, 'OBJECT', state)
        if state.doDummies:     state.xmlDums = parseRsXML(self, xmlRs, 'DUMMY', state)
        if state.doOcclusion:   state.xmlOccs = parseRsXML(self, xmlRs, 'OCCLUSION', state)
        if state.doFog:         state.xmlFogs = parseRsXML(self, xmlRs, 'FOG', state)
        if state.doSounds:      state.xmlAmbs = parseRsXML(self, xmlRs, 'AMBIENTSOUND', state)

    if xmlSpawn:
        if state.doItems:       state.xmlItms = parseSpawnXML(self, xmlSpawn, state)

    state.doLights =        state.doLights and      len(state.xmlLits) != 0
    state.doProps =         state.doProps and       len(state.xmlObjs) != 0
    state.doDummies =       state.doDummies and     len(state.xmlDums) != 0
    state.doOcclusion =     state.doOcclusion and   len(state.xmlOccs) != 0
    state.doFog =           state.doFog and         len(state.xmlFogs) != 0
    state.doSounds =        state.doSounds and      len(state.xmlAmbs) != 0
    state.doItems =         state.doItems and       len(state.xmlItms) != 0

    readRs(self, rspath, state)

    if state.doBsptree:
        for ext in BSP_EXTENSIONS:
            bsppath = pathExists(f"{ rspath }.{ ext }")

            if bsppath:
                if readBsp(self, bsppath, state):
                    return { 'CANCELLED' }
                break

        if not bsppath:
            state.doBsptree = False
            self.report({ 'INFO' }, "GZRS2: Bsp mesh requested but .bsp file not found, no bsp mesh to generate.")

    if state.doCollision:
        for ext in COL_EXTENSIONS:
            colpath = pathExists(f"{ rspath }.{ ext }")

            if colpath:
                if readCol(self, colpath, state):
                    return { 'CANCELLED' }
                break

        if not colpath:
            state.doCollision = False
            self.report({ 'INFO' }, "GZRS2: Collision mesh requested but .col/.cl2 file not found, no collision mesh to generate.")

    if state.doNavigation:
        for ext in NAV_EXTENSIONS:
            navpath = pathExists(f"{ rspath }.{ ext }")

            if navpath:
                if readNav(self, navpath, state):
                    return { 'CANCELLED' }
                break

        if not navpath:
            state.doNavigation = False
            self.report({ 'INFO' }, "GZRS2: Navigation mesh requested but .nav file not found, no navigation mesh to generate.")

    if state.doLightmap:
        for ext in LM_EXTENSIONS:
            lmpath = pathExists(f"{ rspath }.{ ext }")

            if lmpath:
                if readLm(self, lmpath, state):
                    return { 'CANCELLED' }
                break

        if not lmpath:
            state.doLightmap = False
            self.report({ 'INFO' }, "GZRS2: Lightmaps requested but .lm file not found, no lightmaps to generate.")
        else:
            unpackLmImages(state)
            setupLmMixGroup(state)

    if state.doProps:
        for p, prop in enumerate(state.xmlObjs):
            elupath = os.path.join(state.directory, prop['name'])

            for ext in XML_EXTENSIONS:
                eluxmlpath = pathExists(f"{ elupath }.{ ext }")

                if eluxmlpath:
                    with open(eluxmlpath, encoding = 'utf-8') as file:
                        state.xmlEluMats[p] = minidom.parseString(file.read())
                    break

            readElu(self, elupath, state)

    if state.doFog and not state.doLights:
        state.doFog = False
        self.report({ 'INFO' }, "GZRS2: Fog data but no lights, fog volume will not be generated.")

    state.doLightDrivers =   state.doLightDrivers and state.doLights
    state.doFogDriver =      state.doFogDriver and state.doFog
    doDrivers =             self.panelDrivers and (state.doLightDrivers or state.doFogDriver)
    doExtras =              state.doCollision or state.doNavigation or state.doOcclusion or state.doFog or state.doBounds or doDrivers

    bpy.ops.ed.undo_push()
    collections = bpy.data.collections

    rootMap =                   collections.new(state.filename)
    rootMeshesBsp =             collections.new(f"{ state.filename }_Meshes_Bsptree")           if state.doBsptree else False
    rootMeshesOct =             collections.new(f"{ state.filename }_Meshes_Octree")
    rootMeshesUni =             collections.new(f"{ state.filename }_Meshes_Unified")           if self.meshMode == 'BAKE' else False

    rootLightsMain =            collections.new(f"{ state.filename }_Lights_Main")              if state.doLights else False
    rootLightsSoft =            collections.new(f"{ state.filename }_Lights_Soft")              if state.doLights else False
    rootLightsHard =            collections.new(f"{ state.filename }_Lights_Hard")              if state.doLights else False
    rootLightsSoftAmbient =     collections.new(f"{ state.filename }_Lights_SoftAmbient")       if state.doLights else False
    rootLightsSoftCasters =     collections.new(f"{ state.filename }_Lights_SoftCasters")       if state.doLights else False
    rootLightsHardAmbient =     collections.new(f"{ state.filename }_Lights_HardAmbient")       if state.doLights else False
    rootLightsHardCasters =     collections.new(f"{ state.filename }_Lights_HardCasters")       if state.doLights else False

    rootProps =                 collections.new(f"{ state.filename }_Props")                    if state.doProps else False
    rootDummies =               collections.new(f"{ state.filename }_Dummies")                  if state.doDummies else False
    rootSounds =                collections.new(f"{ state.filename }_Sounds")                   if state.doSounds else False
    rootItems =                 collections.new(f"{ state.filename }_Items")                    if state.doItems else False
    rootExtras =                collections.new(f"{ state.filename }_Extras")                   if doExtras else False
    rootBoundsBsp =             collections.new(f"{ state.filename }_Bounds_Bsptree")           if state.doBounds and state.doBsptree else False
    rootBoundsOct =             collections.new(f"{ state.filename }_Bounds_Octree")            if state.doBounds else False

    context.collection.children.link(rootMap)

    if state.doBsptree:
        rootMap.children.link(rootMeshesBsp)

    rootMap.children.link(rootMeshesOct)

    if self.meshMode == 'BAKE':
        rootMap.children.link(rootMeshesUni)

    if state.doLights:
        rootMap.children.link(rootLightsMain)
        rootMap.children.link(rootLightsSoft)
        rootMap.children.link(rootLightsHard)
        rootLightsSoft.children.link(rootLightsSoftAmbient)
        rootLightsSoft.children.link(rootLightsSoftCasters)
        rootLightsHard.children.link(rootLightsHardAmbient)
        rootLightsHard.children.link(rootLightsHardCasters)

    if state.doProps:       rootMap.children.link(rootProps)
    if state.doDummies:     rootMap.children.link(rootDummies)
    if state.doSounds:      rootMap.children.link(rootSounds)
    if state.doItems:       rootMap.children.link(rootItems)
    if doExtras:            rootMap.children.link(rootExtras)
    if state.doBounds:
        if state.doBsptree:
            rootExtras.children.link(rootBoundsBsp)
        rootExtras.children.link(rootBoundsOct)

        for viewLayer in context.scene.view_layers:
            lcRoot = lcFindRoot(viewLayer.layer_collection, rootMap)

            if lcRoot is None:
                self.report({ 'WARNING' }, f"GZRS2: Unable to find root collection in view layer: { viewLayer }")
                continue

            for lcExtras in lcRoot.children:
                if lcExtras.collection is rootExtras:
                    for lcBounds in lcExtras.children:
                        if any((lcBounds.collection is rootBoundsBsp and state.doBsptree,
                                lcBounds.collection is rootBoundsOct)):
                            lcBounds.hide_viewport = True

    for m, xmlRsMat in enumerate(state.xmlRsMats):
        xmlRsMatName = xmlRsMat.get('name', f"Material_{ m }")
        blMat, tree, links, nodes, shader, _, _, transparent, mix = setupMatBase(xmlRsMatName)

        shader.inputs[12].default_value = 0.0 # Specular IOR Level

        blMat.gzrs2.matID = m

        processRS2Texlayer(self, blMat, xmlRsMat, tree, links, nodes, shader, transparent, mix, state)

        state.blXmlRsMats.append(blMat)

        if state.meshMode == 'STANDARD':
            if state.doBsptree:
                bspMeshName = f"Bsp_{ xmlRsMatName }"

                blBspMesh = bpy.data.meshes.new(bspMeshName)
                blBspMeshObj = bpy.data.objects.new(bspMeshName, blBspMesh)

                state.blBspMeshes.append(blBspMesh)
                state.blBspMeshObjs.append(blBspMeshObj)

            octMeshName = f"Oct_{ xmlRsMatName }"

            blOctMesh = bpy.data.meshes.new(octMeshName)
            blOctMeshObj = bpy.data.objects.new(octMeshName, blOctMesh)

            state.blOctMeshes.append(blOctMesh)
            state.blOctMeshObjs.append(blOctMeshObj)

    if state.doCleanup and state.logCleanup:
        print()
        print("=== RS Mesh Cleanup ===")
        print()

    def cleanupFunc(blObj):
        bpy.ops.object.select_all(action = 'DESELECT')
        blObj.select_set(True)
        bpy.ops.object.shade_smooth()
        bpy.ops.object.select_all(action = 'DESELECT')

        bpy.ops.object.mode_set(mode = 'EDIT')

        bpy.ops.mesh.select_mode(type = 'VERT')
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.delete_loose()
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.remove_doubles(use_sharp_edge_from_normals = True)
        bpy.ops.mesh.select_all(action = 'DESELECT')

        bpy.ops.object.mode_set(mode = 'OBJECT')

        deleteInfoReports(11, context) # TODO: 5? 9? Not working?

    def setupUnifiedMesh(name, setupFunc, isBakeMesh = False):
        blMesh = bpy.data.meshes.new(name)
        blObj = bpy.data.objects.new(name, blMesh)

        meshMatIDs = setupFunc(self, -1, blMesh, state)

        for blXmlRsMat in state.blXmlRsMats:
            blMesh.materials.append(blXmlRsMat)

        for p, polygon in blMesh.polygons.items():
            polygon.material_index = meshMatIDs[p]

        rootMeshesUni.objects.link(blObj)

        for viewLayer in context.scene.view_layers:
            viewLayer.objects.active = blObj

        if state.doCleanup and not isBakeMesh:
            if state.logCleanup:
                print(blMesh.name)
                cleanupFunc(blObj)
                print()
            else:
                with redirect_stdout(state.silentIO):
                    cleanupFunc(blObj)

        return blMesh, blObj

    # TODO: Improve performance of convex id matching
    # blConvexMesh, blConvexObj = setupUnifiedMesh(f"{ state.filename }_Convex", setupRsConvexMesh)

    if state.meshMode == 'STANDARD':
        def setupStandardMeshes(blMeshes, blMeshObjs, treePolygons, treeVerts, rootMeshes, *, allowLightmapUVs = True):
            for m, blMesh in enumerate(blMeshes):
                if not setupRsTreeMesh(self, m, blMesh, treePolygons, treeVerts, state, allowLightmapUVs = allowLightmapUVs):
                    continue

                blMeshObj = blMeshObjs[m]

                blMesh.materials.append(state.blXmlRsMats[m])

                rootMeshes.objects.link(blMeshObj)

                for viewLayer in context.scene.view_layers:
                    viewLayer.objects.active = blMeshObj

                if state.doCleanup:
                    if state.logCleanup:
                        print(blMesh.name)
                        cleanupFunc(blMeshObj)
                        print()
                    else:
                        with redirect_stdout(state.silentIO):
                            cleanupFunc(blMeshObj)

        setupStandardMeshes(state.blBspMeshes, state.blBspMeshObjs, state.bspTreePolygons, state.bspTreeVerts, rootMeshesBsp, allowLightmapUVs = False) # TODO: Improve performance of convex id matching
        setupStandardMeshes(state.blOctMeshes, state.blOctMeshObjs, state.rsOctreePolygons, state.rsOctreeVerts, rootMeshesOct)
    elif state.meshMode == 'BAKE':
        blBakeMesh, blBakeObj = setupUnifiedMesh(f"{ state.filename }_Bake", setupRsTreeMesh, state.rsOctreePolygons, state.rsOctreeVerts, isBakeMesh = True)

    if state.doLights:
        for light in state.xmlLits:
            lightName = light['name']
            attEnd = light['ATTENUATIONEND']
            attStart = light['ATTENUATIONSTART']
            softness = (attEnd - attStart) / attEnd
            hardness = 0.001 / (1 - min(softness, 0.9999))
            castshadow = light['CASTSHADOW']

            blLight = bpy.data.lights.new(lightName, 'POINT')
            blLight.color = light['COLOR']
            blLight.energy = light['INTENSITY'] * pow(attEnd, 2) * 2
            blLight.shadow_soft_size = hardness * attEnd
            blLight.cycles.cast_shadow = castshadow

            # Some simple tweaks to help with contrast and shadow sharpness. The numbers were
            # tuned for outdoor maps with sunlight like Battle Arena, Castle and Factory, but
            # should be a decent starting point for other maps too.
            if self.tweakLights and softness <= 0.1:
                if castshadow:
                    if state.doFog:
                        blLight.energy *= 100
                        blLight.shadow_soft_size = 0
                    else:
                        blLight.energy *= 10
                else:
                    blLight.energy /= 100

            blLightObj = bpy.data.objects.new(lightName, blLight)
            blLightObj.location = light['POSITION']

            state.blLights.append(blLight)
            state.blLightObjs.append(blLightObj)

            if lightName.lower().startswith(('main_omni', 'sun_omni', 'omni_main', 'omni_sun', 'omni_def', 'omni_shadow')):
                rootLightsMain.objects.link(blLightObj)
            elif softness <= 0.1:
                if castshadow: rootLightsHardCasters.objects.link(blLightObj)
                else: rootLightsHardAmbient.objects.link(blLightObj)
            else:
                if castshadow: rootLightsSoftCasters.objects.link(blLightObj)
                else: rootLightsSoftAmbient.objects.link(blLightObj)

            if lightName.lower().startswith('obj_'):
                for viewLayer in context.scene.view_layers:
                    blLightObj.hide_set(True, view_layer = viewLayer)

    if state.doDummies:
        propDums = []

    if state.doProps:
        if state.doDummies:
            for prop in state.xmlObjs:
                propName = prop['name'].split('_', 1)[1].rsplit('.', 1)[0]

                for d, dummy in enumerate(state.xmlDums):
                    if dummy['name'] == propName:
                        propDums.append(d)

        for m, eluMat in enumerate(state.eluMats):
            setupEluMat(self, m, eluMat, state)

        if state.xmlEluMats:
            for elupath, materials in state.xmlEluMats.items():
                for xmlEluMat in materials:
                    setupXmlEluMat(self, elupath, xmlEluMat, state)

        if state.doCleanup and state.logCleanup:
            print()
            print("=== Elu Mesh Cleanup ===")
            print()

        for eluMesh in state.eluMeshes:
            if eluMesh.meshName.startswith(('Bip01', 'Bone', 'Dummy')):
                state.gzrsValidBones.add(eluMesh.meshName)

            if eluMesh.isDummy:
                self.report({ 'INFO' }, f"GZRS2: Skipping dummy prop: { eluMesh.meshName }")
                continue

            setupElu(self, eluMesh, True, rootProps, context, state)

    processEluIsEffect(state)
    processEluHeirarchy(self, state)

    if len(state.gzrsValidBones) > 0:
        self.report({ 'INFO' }, f"GZRS2: Valid bones were found in some props: { len(state.gzrsValidBones) }")

    if state.doDummies:
        i = 0

        for d, dummy in enumerate(state.xmlDums):
            if d in propDums:
                continue

            name = dummy['name']
            nameLower = name.lower()

            if nameLower.startswith(('spawn_item', 'snd_amb')):
                continue

            dir = dummy['DIRECTION']
            up = Vector((0, 0, 1))
            right = dir.cross(up)
            up = right.cross(dir)
            rot = Matrix((right, dir, up)).to_euler()

            RS_DUMMY_NAME_SPLIT_DATA = (
                ((  'spawn_solo', 'spawn_team'  ), '_', 3),
                ((  'spawn_npc', 'spawn_blitz'  ), '_', 4), # spawn_npc_melee_01, spawn_npc_melee_02, TODO: verify blitz data
                ((  'camera_pos',               ), ' ', 2), # camera_pos 01, camera_pos 01
                ((  'wait_pos',                 ), '_', 3), # wait_pos_01
            )

            RS_DUMMY_NAME_SPLIT_SUBSTRINGS = tuple(substring for substrings, _, _ in RS_DUMMY_NAME_SPLIT_DATA for substring in substrings)

            if nameLower.startswith(RS_DUMMY_NAME_SPLIT_SUBSTRINGS):
                for substrings, token, expectedCount in RS_DUMMY_NAME_SPLIT_DATA:
                    if nameLower.startswith(substrings):
                        nameSplits = nameLower.split(token)
                        splitCount = len(splits)
                        splitCountError = splitCount != expectedCount
                        break

                if splitCountError:
                    self.report({ 'WARNING' }, f"GZRS2: Dummy name with incorrect formatting, incorrect placement of separators, skipping: { d }, { name }")
                    continue

                nameSuffix = nameSplits[-1]

                if not nameSuffix.isnumeric():
                    self.report({ 'WARNING' }, f"GZRS2: Dummy name with incorrect formatting, unable to detect spawn index, skipping: { d }, { name }")
                    continue

                nameIndex = int(nameSuffix)

            if nameLower.startswith((   'spawn_solo',   'spawn_team',
                                        'spawn_npc',    'spawn_blitz')):    objName = f"{ state.filename }_Spawn{ i }"
            elif nameLower.startswith(( 'camera_pos',   'wait_pos')):       objName = f"{ state.filename }_Camera{ i }"
            else:                                                           objName = f"{ state.filename }_Dummy_{ name }"

            if nameLower.startswith(('camera_pos', 'wait_pos')):
                blObj = bpy.data.objects.new(objName, 'CAMERA')
                props = blObj.data.gzrs2
            else:
                blObj = bpy.data.objects.new(objName, None)
                blObj.empty_display_type = 'ARROWS'
                props = blObj.gzrs2

            blObj.location = dummy['POSITION']
            blObj.rotation_euler = rot

            if nameLower.startswith('spawn_solo'):
                props.dummyType = 'SPAWN'
                props.spawnType = 'SOLO'
                props.spawnIndex = nameIndex
            elif nameLower.startswith('spawn_team'):
                props.dummyType = 'SPAWN'
                props.spawnType = 'TEAM'
                props.spawnIndex = nameIndex

                # We assume that 'spawn_team' always prefixes a single digit number starting at 1
                props.spawnTeamID = int(nameLower.split('spawn_team')[1][0])
            elif nameLower.startswith('spawn_npc'):
                props.dummyType = 'SPAWN'
                props.spawnType = 'NPC'
                props.spawnIndex = nameIndex

                # TODO: Custom value support for npc types
                if      nameLower.startswith('spawn_npc_melee'):    props.spawnEnemyType = 'MELEE'
                elif    nameLower.startswith('spawn_npc_ranged'):   props.spawnEnemyType = 'RANGED'
                elif    nameLower.startswith('spawn_npc_boss'):     props.spawnEnemyType = 'BOSS'
            elif nameLower.startswith('spawn_blitz'):
                props.dummyType = 'SPAWN'
                props.spawnType = 'BLITZ'
                props.spawnIndex = nameIndex

                # TODO: Custom value support for blitzkrieg types
                if      nameLower.startswith('spawn_blitz_barricade'):  props.spawnBlitzType = 'BARRICADE'
                elif    nameLower.startswith('spawn_blitz_guardian'):   props.spawnBlitzType = 'GUARDIAN'
                elif    nameLower.startswith('spawn_blitz_radar'):      props.spawnBlitzType = 'RADAR'
                elif    nameLower.startswith('spawn_blitz_honoritem'):  props.spawnBlitzType = 'TREASURE'
            elif nameLower.startswith('wait_pos'):
                props.cameraIndex = nameIndex
                props.cameraType = 'WAIT'
            elif nameLower.startswith('camera_pos'):
                props.cameraIndex = nameIndex
                props.cameraType = 'TRACK'
            elif nameLower.startswith('sun_'):
                props.dummyType = 'SUN'

            state.blDummyObjs.append(blObj)
            rootDummies.objects.link(blObj)

            i += 1

    skippedSounds = []

    if state.doSounds:
        for s, sound in enumerate(state.xmlAmbs):
            if not all(tuple(key in sound for key in ['ObjName', 'type', 'filename'])):
                skippedSounds.append(s)
                continue

            soundObjName = sound['ObjName']
            soundFileName = sound['filename']
            typecode = sound['type']
            space = '2D' if typecode[0] == 'a' else '3D'
            shape = 'AABB' if typecode[1] == '0' else 'SPHERE'

            if (shape == 'AABB' and not ('MIN_POSITION' in sound and 'MAX_POSITION' in sound)) or (shape == 'SPHERE' and 'CENTER' not in sound):
                skippedSounds.append(s)
                continue

            blSoundObj = bpy.data.objects.new(f"{ state.filename }_Sound_{ soundObjName }", None)
            props = blSoundObj.gzrs2

            props.dummyType = 'SOUND'
            props.soundFileName = soundFileName
            props.soundSpace = space
            props.soundShape = shape

            if shape == 'AABB':
                p1 = sound['MIN_POSITION']
                p2 = sound['MAX_POSITION']
                hdims = (p2 - p1) / 2
                center = p1 + hdims

                blSoundObj.empty_display_type = 'CUBE'
                blSoundObj.location = center
                blSoundObj.scale = hdims
            elif shape == 'SPHERE':
                blSoundObj.empty_display_type = 'SPHERE'
                blSoundObj.location = sound['CENTER']
                blSoundObj.empty_display_size = sound['RADIUS']

            blSoundObj.location.y = -blSoundObj.location.y

            state.blSoundObjs.append(blSoundObj)
            rootSounds.objects.link(blSoundObj)

    if len(skippedSounds) > 0:
        self.report({ 'WARNING' }, f"GZRS2: Skipped sounds with missing attributes: { skippedSounds }")

    if state.doItems:
        i = 0

        for gametype in state.xmlItms:
            gameID = gametype['id'].upper()

            # TODO: Custom value support for game IDs
            if gameID not in ['SOLO', 'TEAM']:
                self.report({ 'WARNING' }, f"GZRS2: Skipped game id of unsupported type: { s }, { gameID }")
                continue

            for s, spawn in enumerate(gametype['spawns']):
                item = spawn['item']

                # TODO: Custom value support for item types
                if len(item) >= 4:
                    itemType = item[:-2].upper()
                    itemID = item[-2:]

                if len(item) < 4 or not itemType.isalpha() or not itemID.isnumeric():
                    self.report({ 'WARNING' }, f"GZRS2: Skipped item of unsupported type: { s }, { gameID }, { item }")
                    continue

                blItemObj = bpy.data.objects.new(f"{ state.filename }_Item{ i }", None)
                blItemObj.empty_display_type = 'SPHERE'
                blItemObj.location = spawn['POSITION']

                blItemObj.gzrs2.dummyType = 'ITEM'
                blItemObj.gzrs2.itemGameID = gameID
                blItemObj.gzrs2.itemType = itemType
                blItemObj.gzrs2.itemID = int(itemID)
                blItemObj.gzrs2.itemTimer = spawn['timesec']

                state.blItemObjs.append(blItemObj)
                rootItems.objects.link(blItemObj)

                i += 1

    if doExtras:
        if state.doCollision:
            colName = f"{ state.filename }_Collision"
            blColObj = setupColMesh(colName, state)
            rootExtras.objects.link(blColObj)

            for viewLayer in context.scene.view_layers:
                blColObj.hide_set(True, view_layer = viewLayer)

        if state.doNavigation:
            blNavFacesObj, blNavLinksObj = setupNavMesh(state)
            rootExtras.objects.link(blNavFacesObj)
            rootExtras.objects.link(blNavLinksObj)

            for viewLayer in context.scene.view_layers:
                blNavFacesObj.hide_set(True, view_layer = viewLayer)
                blNavLinksObj.hide_set(True, view_layer = viewLayer)

        if state.doOcclusion:
            occName = f"{ state.filename }_Occlusion"
            blOccMat = setupDebugMat(occName, (0.0, 1.0, 1.0, 0.25))

            occVerts = []
            occFaces = []
            index = 0

            for o, occlusion in enumerate(state.xmlOccs):
                points = occlusion['POSITION']
                occVertexCount = len(points)

                for point in points:
                    occVerts.append(point)

                occFaces.append(tuple(range(index, index + occVertexCount)))
                index += occVertexCount

            blOccMesh = bpy.data.meshes.new(occName)
            blOccObj = bpy.data.objects.new(occName, blOccMesh)

            blOccMesh.from_pydata(occVerts, (), occFaces)
            blOccMesh.validate()
            blOccMesh.update()

            setObjFlagsDebug(blOccObj)

            state.blOccMat = blOccMat
            state.blOccMesh = blOccMesh
            state.blOccObj = blOccObj

            blOccObj.data.materials.append(blOccMat)
            rootExtras.objects.link(blOccObj)

            for viewLayer in context.scene.view_layers:
                blOccObj.hide_set(True, view_layer = viewLayer)

        if state.doBounds:
            def createBBoxEmpty(name, blBBoxObjs, rootBounds):
                p1, p2 = bounds
                hdims = (p2 - p1) / 2
                center = p1 + hdims

                blBBoxObj = bpy.data.objects.new(name, None)
                blBBoxObj.empty_display_type = 'CUBE'
                blBBoxObj.location = center
                blBBoxObj.scale = hdims

                blBBoxObjs.append(blBBoxObj)
                rootBounds.objects.link(blBBoxObj)

                return blBBoxObj

            if state.doBsptree:
                for b, bounds in enumerate(state.bspTreeBounds):
                    createBBoxEmpty(f"{ state.filename }_BspBBox{ b }", state.blBspBBoxObjs, rootBoundsBsp)

            for b, bounds in enumerate(state.rsOctreeBounds):
                createBBoxEmpty(f"{ state.filename }_OctBBox{ b }", state.blOctBBoxObjs, rootBoundsOct)

        if state.doFog:
            fog = state.xmlFogs[0]

            color = (fog['R'] / 255.0, fog['G'] / 255.0, fog['B'] / 255.0, 1.0)
            p1 = Vector((math.inf, math.inf, math.inf))
            p2 = Vector((-math.inf, -math.inf, -math.inf))

            for blLightObj in state.blLightObjs:
                p1.x = min(p1.x, blLightObj.location.x)
                p1.y = min(p1.y, blLightObj.location.y)
                p1.z = min(p1.z, blLightObj.location.z)
                p2.x = max(p2.x, blLightObj.location.x)
                p2.y = max(p2.y, blLightObj.location.y)
                p2.z = max(p2.z, blLightObj.location.z)

            hdims = (p2 - p1) / 2
            center = p1 + hdims

            fogName = f"{ state.filename }_Fog"

            blFogMat = bpy.data.materials.new(fogName)
            blFogMat.use_nodes = True

            tree, links, nodes = getMatTreeLinksNodes(blFogMat)

            nodes.remove(getShaderNodeByID(nodes, 'ShaderNodeBsdfPrincipled'))
            output = getShaderNodeByID(nodes, 'ShaderNodeOutputMaterial')
            output.select = False

            if min(color[:3]) > 0.5:
                shader = nodes.new('ShaderNodeVolumeScatter')
                shader.inputs[0].default_value = color
                shader.inputs[1].default_value = 0.0001
            else:
                shader = nodes.new('ShaderNodeVolumeAbsorption')
                shader.inputs[0].default_value = color
                shader.inputs[1].default_value = 0.1

            shader.location = (120, 300)
            shader.select = False

            links.new(shader.outputs[0], output.inputs[1])

            bpy.ops.mesh.primitive_cube_add(location = center, scale = hdims)
            deleteInfoReports(1, context)

            blFogObj = context.active_object
            blFogMesh = blFogObj.data
            blFogObj.name = blFogMesh.name = fogName
            blFogObj.display_type = 'WIRE'

            state.blFogMat = blFogMat
            state.blFogShader = shader
            state.blFogMesh = blFogMesh
            state.blFogObj = blFogObj

            blFogObj.data.materials.append(blFogMat)

            for collection in blFogObj.users_collection:
                collection.objects.unlink(blFogObj)
            rootExtras.objects.link(blFogObj)

        if doDrivers:
            driverObj = bpy.data.objects.new(f"{ state.filename }_Drivers", None)
            driverObj.empty_display_type = 'CUBE'

            if state.doLightDrivers:
                for g, group in enumerate(groupLights(state.blLights)):
                    property = f"GZRS2 Lightgroup { g }"
                    colorProp = f"{ property } Color"
                    energyProp = f"{ property } Energy"
                    softnessProp = f"{ property } Softness"

                    for light in group:
                        driverObj[colorProp] = light.color
                        driverObj[energyProp] = light.energy
                        driverObj[softnessProp] = light.shadow_soft_size

                        state.blDrivers.append((createArrayDriver(driverObj, f"[\"{ colorProp }\"]", light, 'color'),
                                                createDriver(driverObj, f"[\"{ energyProp }\"]", light, 'energy'),
                                                createDriver(driverObj, f"[\"{ softnessProp }\"]", light, 'shadow_soft_size')))

                    driverObj.id_properties_ui(colorProp).update(subtype = 'COLOR', min = 0.0, max = 1.0, soft_min = 0.0, soft_max = 1.0, precision = 3, step = 1.0)
                    driverObj.id_properties_ui(energyProp).update(subtype = 'POWER', min = 0.0, max = math.inf, soft_min = 0.0, soft_max = math.inf, precision = 1, step = 100)
                    driverObj.id_properties_ui(softnessProp).update(subtype = 'DISTANCE', min = 0.0, max = math.inf, soft_min = 0.0, soft_max = math.inf, precision = 2, step = 3)

            if state.doFogDriver:
                shader = state.blFogShader
                colorProp = 'GZRS2 Fog Color'
                densityProp = 'GZRS2 Fog Density'

                driverObj[colorProp] = shader.inputs[0].default_value
                driverObj[densityProp] = shader.inputs[1].default_value

                state.blDrivers.append(createArrayDriver(driverObj, f"[\"{ colorProp }\"]", shader.inputs[0], 'default_value'))
                state.blDrivers.append(createDriver(driverObj, f"[\"{ densityProp }\"]", shader.inputs[1], 'default_value'))

                driverObj.id_properties_ui(colorProp).update(subtype = 'COLOR', min = 0.0, max = 1.0, soft_min = 0.0, soft_max = 1.0, precision = 3, step = 1.0)
                driverObj.id_properties_ui(densityProp).update(subtype = 'NONE', min = 0.000001, max = 1.0, soft_min = 0.000001, soft_max = 1.0, precision = 5, step = 0.001)

            state.blDriverObj = driverObj
            rootExtras.objects.link(driverObj)

    bpy.ops.object.select_all(action = 'DESELECT')
    deleteInfoReports(1, context)

    return { 'FINISHED' }
