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

        if not matchRSDataDirectory(self, rs2DataDir, bpy.path.basename(rs2DataDir), False, state):
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
    state.doProps           = self.doProps
    state.doDummies         = self.doDummies        and self.meshMode != 'BAKE'
    state.doOcclusion       = self.doOcclusion      and self.meshMode != 'BAKE'
    state.doFog             = self.doFog
    state.doSounds          = self.doSounds         and self.meshMode != 'BAKE'
    state.doMisc            = self.doMisc           and self.meshMode != 'BAKE'
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
    state.filename = bpy.path.basename(rspath).split(os.extsep)[0]

    xmlRs = False
    for ext in XML_EXTENSIONS:
        rsxmlpath = pathExists(f"{ rspath }{ os.extsep }{ ext }")

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
        self.report({ 'WARNING' }, "GZRS2: Map xml not found, no materials or objects to generate!")

    xmlSpawn = False
    xmlFlag = False
    xmlSmoke = False

    if state.doMisc:
        spawnxmlpath = os.path.join(state.directory, "spawn.xml")
        flagxmlpath = os.path.join(state.directory, "flag.xml")
        smokexmlpath = os.path.join(state.directory, "smoke.xml")

        for ext in XML_EXTENSIONS:
            spawnxmlpath = pathExists(os.path.join(state.directory, f"spawn.{ ext }"))

            if spawnxmlpath:
                with open(spawnxmlpath, encoding = 'utf-8') as file:
                    xmlSpawn = minidom.parseString(file.read())
                break

        for ext in XML_EXTENSIONS:
            flagxmlpath = pathExists(os.path.join(state.directory, f"flag.{ ext }"))

            if flagxmlpath:
                with open(flagxmlpath, encoding = 'utf-8') as file:
                    xmlFlag = minidom.parseString(file.read())
                break

        for ext in XML_EXTENSIONS:
            smokexmlpath = pathExists(os.path.join(state.directory, f"smoke.{ ext }"))

            if smokexmlpath:
                with open(smokexmlpath, encoding = 'utf-8') as file:
                    xmlSmoke = minidom.parseString(file.read())
                break

        if not spawnxmlpath:    self.report({ 'INFO' }, "GZRS2: Items requested but spawn.xml not found, no items to generate.")
        if not flagxmlpath:     self.report({ 'INFO' }, "GZRS2: Flags requested but flag.xml not found, no flags to generate.")
        if not smokexmlpath:    self.report({ 'INFO' }, "GZRS2: Smoke requested but smoke.xml not found, no smoke to generate.")

    if xmlRs:
        state.xmlRsMats =                       parseRsXML(self, xmlRs, 'MATERIAL', state)
        state.xmlGlbs =                         parseRsXML(self, xmlRs, 'GLOBAL', state)

        if state.doLights:      state.xmlLits = parseRsXML(self, xmlRs, 'LIGHT', state)
        if state.doProps:       state.xmlObjs = parseRsXML(self, xmlRs, 'OBJECT', state)
        if state.doDummies:     state.xmlDums = parseRsXML(self, xmlRs, 'DUMMY', state)
        if state.doOcclusion:   state.xmlOccs = parseRsXML(self, xmlRs, 'OCCLUSION', state)
        if state.doFog:         state.xmlFogs = parseRsXML(self, xmlRs, 'FOG', state)
        if state.doSounds:      state.xmlAmbs = parseRsXML(self, xmlRs, 'AMBIENTSOUND', state)

    if state.doMisc:
        if xmlSpawn:            state.xmlItms = parseSpawnXML(self, xmlSpawn, state)
        if xmlFlag:             state.xmlFlgs = parseFlagXML(self, xmlFlag)
        if xmlSmoke:            state.xmlSmks = parseSmokeXML(xmlSmoke)

    state.doLights =        state.doLights          and len(state.xmlLits) > 0
    state.doProps =         state.doProps           and len(state.xmlObjs) > 0
    state.doDummies =       state.doDummies         and len(state.xmlDums) > 0
    state.doOcclusion =     state.doOcclusion       and len(state.xmlOccs) > 0
    state.doFog =           state.doFog             and len(state.xmlFogs) > 0
    state.doSounds =        state.doSounds          and len(state.xmlAmbs) > 0
    state.doMisc =          state.doMisc            and len(state.xmlItms) > 0 or len(state.xmlFlgs) > 0 or len(state.xmlSmks) > 0

    with open(rspath, 'rb') as file:
        if readRs(self, file, rspath, state):
            return { 'CANCELLED' }

    if state.doBsptree:
        for ext in BSP_EXTENSIONS:
            bsppath = pathExists(f"{ rspath }{ os.extsep }{ ext }")

            if bsppath:
                with open(bsppath, 'rb') as file:
                    if readBsp(self, file, bsppath, state):
                        return { 'CANCELLED' }
                break

        if not bsppath:
            state.doBsptree = False
            self.report({ 'INFO' }, "GZRS2: Bsp mesh requested but .bsp file not found, no bsp mesh to generate.")

    if state.doCollision:
        for ext in COL_EXTENSIONS:
            colpath = pathExists(f"{ rspath }{ os.extsep }{ ext }")

            if colpath:
                with open(colpath, 'rb') as file:
                    if readCol(self, file, colpath, state):
                        return { 'CANCELLED' }
                break

        if not colpath:
            state.doCollision = False
            self.report({ 'INFO' }, "GZRS2: Collision mesh requested but .col/.cl2 file not found, no collision mesh to generate.")

    if state.doNavigation:
        for ext in NAV_EXTENSIONS:
            navpath = pathExists(f"{ rspath }{ os.extsep }{ ext }")

            if navpath:
                with open(navpath, 'rb') as file:
                    if readNav(self, file, navpath, state):
                        return { 'CANCELLED' }
                break

        if not navpath:
            state.doNavigation = False
            self.report({ 'INFO' }, "GZRS2: Navigation mesh requested but .nav file not found, no navigation mesh to generate.")

    if state.doLightmap:
        for ext in LM_EXTENSIONS:
            lmpath = pathExists(f"{ rspath }{ os.extsep }{ ext }")

            if lmpath:
                with open(lmpath, 'rb') as file:
                    if readLm(self, file, lmpath, state):
                        return { 'CANCELLED' }
                break

        if not lmpath:
            state.doLightmap = False
            self.report({ 'INFO' }, "GZRS2: Lightmaps requested but .lm file not found, no lightmaps to generate.")
        else:
            unpackLmImages(context, state)

    if state.doProps:
        for p, prop in enumerate(state.xmlObjs):
            propName = prop['name']
            elupath = os.path.join(state.directory, propName)

            for ext in XML_EXTENSIONS:
                eluxmlpath = pathExists(f"{ elupath }{ os.extsep }{ ext }")

                if eluxmlpath:
                    with open(eluxmlpath, encoding = 'utf-8') as file:
                        state.xmlEluMats[p] = minidom.parseString(file.read())
                    break

            if not pathExists(elupath):
                self.report({ 'INFO' }, f"GZRS2: Prop requested but .elu file not found, skipping: { propName }")
                continue

            with open(elupath, 'rb') as file:
                if readElu(self, file, elupath, state):
                    return { 'CANCELLED' }

    state.doLightDrivers =   state.doLightDrivers and state.doLights
    state.doFogDriver =      state.doFogDriver and state.doFog
    doDrivers =             self.panelDrivers and (state.doLightDrivers or state.doFogDriver)
    doExtras =              state.doCollision or state.doNavigation or state.doDummies or state.doOcclusion or state.doFog or state.doBounds or doDrivers

    bpy.ops.ed.undo_push()
    collections = bpy.data.collections

    rootMap =                   collections.new(state.filename)
    rootMeshesBsp =             collections.new(f"{ state.filename }_Meshes_Bsptree")           if state.doBsptree else False
    rootMeshesOct =             collections.new(f"{ state.filename }_Meshes_Octree")
    rootMeshesUni =             collections.new(f"{ state.filename }_Meshes_Unified")           if self.meshMode == 'BAKE' else False
    rootLights =                collections.new(f"{ state.filename }_Lights")                   if state.doLights else False
    rootProps =                 collections.new(f"{ state.filename }_Props")                    if state.doProps else False
    rootDummies =               collections.new(f"{ state.filename }_Dummies")                  if state.doDummies else False
    rootSounds =                collections.new(f"{ state.filename }_Sounds")                   if state.doSounds else False
    rootMisc =                  collections.new(f"{ state.filename }_Misc")                     if state.doMisc else False
    rootExtras =                collections.new(f"{ state.filename }_Extras")                   if doExtras else False
    rootBoundsBsp =             collections.new(f"{ state.filename }_Bounds_Bsptree")           if state.doBounds and state.doBsptree else False
    rootBoundsOct =             collections.new(f"{ state.filename }_Bounds_Octree")            if state.doBounds else False

    context.collection.children.link(rootMap)

    if state.doBsptree:
        rootMap.children.link(rootMeshesBsp)

    rootMap.children.link(rootMeshesOct)

    if self.meshMode == 'BAKE':
        rootMap.children.link(rootMeshesUni)

    if state.doLights:      rootMap.children.link(rootLights)
    if state.doProps:       rootMap.children.link(rootProps)
    if state.doDummies:     rootMap.children.link(rootDummies)
    if state.doSounds:      rootMap.children.link(rootSounds)
    if state.doMisc:        rootMap.children.link(rootMisc)
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

    b = 1
    o = 1

    for m, xmlRsMat in enumerate(state.xmlRsMats):
        xmlRsMatName = xmlRsMat.get('name', f"Material{ m }")
        nameSplit = xmlRsMatName.split('_mt_')
        surfaceTag = nameSplit[1].upper() if len(nameSplit) == 2 else 'NONE'
        materialSound = surfaceTag if surfaceTag in MATERIAL_SOUND_TAGS else 'NONE'

        if surfaceTag not in MATERIAL_SOUND_TAGS:
            self.report({ 'WARNING' }, f"GZRS2: Undocumented or invalid surface tag, please submit to Krunk#6051 for testing: { surfaceTag }")

        blMat, tree, links, nodes, shader, _, _, transparent, mix = setupMatBase(xmlRsMatName)

        ambient     = xmlRsMat.get('AMBIENT')
        diffuse     = xmlRsMat.get('DIFFUSE')
        specular    = xmlRsMat.get('SPECULAR')

        props = blMat.gzrs2
        props.priority  = m
        props.parent    = None

        if ambient:     props.ambient   = (ambient[0],      ambient[1],     ambient[2])
        if diffuse:     props.diffuse   = (diffuse[0],      diffuse[1],     diffuse[2])
        if specular:    props.specular  = (specular[0],     specular[1],    specular[2])

        props.sound = materialSound

        processRS2Texlayer(self, blMat, xmlRsMat, tree, links, nodes, shader, transparent, mix, state)

        state.blXmlRsMats.append(blMat)

        if state.meshMode == 'STANDARD':
            if state.doBsptree:
                bspMeshName = f"{ state.filename }_Bsptree{ b }"

                blBspMesh = bpy.data.meshes.new(bspMeshName)
                blBspMeshObj = bpy.data.objects.new(bspMeshName, blBspMesh)

                blBspMesh.gzrs2.meshType = 'RAW'

                state.blBspMeshes.append(blBspMesh)
                state.blBspMeshObjs.append(blBspMeshObj)

            octMeshName = f"{ state.filename }_Octree{ o }"

            blOctMesh = bpy.data.meshes.new(octMeshName)
            blOctMeshObj = bpy.data.objects.new(octMeshName, blOctMesh)

            blOctMesh.gzrs2.meshType = 'WORLD'

            state.blOctMeshes.append(blOctMesh)
            state.blOctMeshObjs.append(blOctMeshObj)

            b += 1
            o += 1

    if state.doCleanup and state.logCleanup:
        print()
        print("=== RS Mesh Cleanup ===")
        print()

    def cleanupFunc(blObj):
        counts = countInfoReports(context)

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

        deleteInfoReports(context, counts)

    def setupUnifiedMesh(name, setupFunc, isBakeMesh = False):
        blMesh = bpy.data.meshes.new(name)
        blObj = bpy.data.objects.new(name, blMesh)

        blMesh.gzrs2.meshType = 'RAW'

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
            lightNameLower = lightName.lower()

            position = light['POSITION']
            intensity = light['INTENSITY']
            attStart = light['ATTENUATIONSTART']
            attEnd = light['ATTENUATIONEND'] # Don't clamp here because we assign later
            castshadow = light['CASTSHADOW']
            softness = calcLightSoftness(attStart, attEnd)

            blLight = bpy.data.lights.new(lightName, 'POINT')
            blLightObj = bpy.data.objects.new(lightName, blLight)
            blLightObj.location = light['POSITION']

            blLight.color = light['COLOR']
            blLight.energy = calcLightEnergy(blLightObj, context)
            blLight.shadow_soft_size = calcLightSoftSize(blLightObj, context)
            blLight.use_shadow = castshadow

            props = blLight.gzrs2
            props.lightType = 'DYNAMIC' if 'obj_' in lightNameLower or '_obj' in lightNameLower else 'STATIC'
            props.lightSubtype = 'SUN' if 'sun_' in lightNameLower or '_sun' in lightNameLower or lightNameLower == 'omni_shadow' else 'NONE' # Castle
            props.intensity = intensity
            props.attStart = attStart
            props.attEnd = attEnd

            state.blLights.append(blLight)
            state.blLightObjs.append(blLightObj)

            rootLights.objects.link(blLightObj)

            render = calcLightRender(blLightObj, context)

            blLightObj.hide_render = render

            for viewLayer in context.scene.view_layers:
                blLightObj.hide_set(render, view_layer = viewLayer)

    if state.doDummies:
        propDums = []

    if state.doProps:
        if state.doDummies:
            for prop in state.xmlObjs:
                propName = prop['name'].split('_', 1)[1].rsplit('.', 1)[0]

                for d, dummy in enumerate(state.xmlDums):
                    if dummy['name'] == propName:
                        propDums.append(d)

        setupEluMats(self, state)

        if state.xmlEluMats:
            for elupath, materials in state.xmlEluMats.items():
                for xmlEluMat in materials:
                    setupXmlEluMat(self, elupath, xmlEluMat, state)

        if state.doCleanup and state.logCleanup:
            print()
            print("=== Elu Mesh Cleanup ===")
            print()

        for eluMesh in state.eluMeshes:
            if eluMesh.meshName.startswith(('Bip', 'Bone', 'Dummy')):
                state.gzrsValidBones.add(eluMesh.meshName)

            if eluMesh.isDummy:
                self.report({ 'INFO' }, f"GZRS2: Skipping dummy prop: { eluMesh.meshName }")
                continue

            setupElu(self, eluMesh, True, rootProps, context, state)

    processEluHeirarchy(self, state)

    if len(state.gzrsValidBones) > 0:
        self.report({ 'INFO' }, f"GZRS2: Valid bones were found in some props: { len(state.gzrsValidBones) }")

    if state.doDummies:
        reorientLocal = Matrix.Rotation(math.radians(90.0), 4, 'X')

        sp = 1
        ca = 1
        sm = 1
        fl = 1

        for d, dummy in enumerate(state.xmlDums):
            if d in propDums:
                continue

            name = dummy['name']
            nameLower = name.lower()

            if nameLower.startswith(('spawn_item', 'snd_amb')):
                continue

            RS_DUMMY_NAME_SPLIT_DATA = (
                ((  'spawn_solo', 'spawn_team'  ), '_', 3), # spawn_solo_101, spawn_team1_101
                ((  'spawn_npc', 'spawn_blitz'  ), '_', 4), # spawn_npc_melee_01, spawn_npc_melee_02, spawn_blitz_<suffix>
                ((  'camera_pos',               ), ' ', 2), # camera_pos 01, camera_pos 01
                ((  'wait_pos',                 ), '_', 3)  # wait_pos_01
            )

            RS_DUMMY_NAME_SPLIT_SUBSTRINGS = tuple(substring for substrings, _, _ in RS_DUMMY_NAME_SPLIT_DATA for substring in substrings)

            if nameLower.startswith(RS_DUMMY_NAME_SPLIT_SUBSTRINGS):
                for substrings, token, expectedCount in RS_DUMMY_NAME_SPLIT_DATA:
                    if nameLower.startswith(substrings):
                        nameSplits = nameLower.split(token)
                        splitCount = len(nameSplits)
                        splitCountError = splitCount != expectedCount
                        break

                if splitCountError:
                    self.report({ 'WARNING' }, f"GZRS2: Dummy name with incorrect formatting, incorrect placement of separators, skipping: { name }")
                    continue

                nameSuffix = nameSplits[-1]

            # TODO: Ugly code, pull these out to separate lists
            if nameLower.startswith(('spawn_solo', 'spawn_team', 'spawn_npc', 'spawn_blitz')):
                objName = f"{ state.filename }_Spawn{ sp }"
                sp += 1
            elif nameLower.startswith(('camera_pos', 'wait_pos')):
                objName = f"{ state.filename }_Camera{ ca }"
                ca += 1
            elif nameLower.startswith(('smk_')):
                objName = f"{ state.filename }_Smoke{ sm }"
                sm += 1
            elif nameLower.startswith('sun_dummy'):
                objName = f"{ state.filename }_Flare{ fl }"
                fl += 1
            else:
                objName = f"{ state.filename }_Dummy_{ name }"

            rot = dummy['DIRECTION'].to_track_quat('Y', 'Z').to_matrix()

            if nameLower.startswith(('camera_pos', 'wait_pos')):
                blCamera = bpy.data.cameras.new(objName)
                blObj = bpy.data.objects.new(objName, blCamera)
                blObj.location = dummy['POSITION']
                blObj.rotation_euler = (rot.to_4x4() @ reorientLocal).to_euler()

                props = blObj.data.gzrs2
            else:
                blObj = bpy.data.objects.new(objName, None)
                blObj.empty_display_type = 'ARROWS'
                blObj.location = dummy['POSITION']
                blObj.rotation_euler = rot.to_euler()

                props = blObj.gzrs2

            if nameLower.startswith('spawn_solo'):
                props.dummyType = 'SPAWN'
                props.spawnType = 'SOLO'
                props.spawnIndex = int(nameSuffix) - 100
            elif nameLower.startswith('spawn_team'):
                props.dummyType = 'SPAWN'
                props.spawnType = 'TEAM'
                props.spawnIndex = int(nameSuffix) - 100

                # We assume that 'spawn_team' always prefixes a single digit number starting at 1
                props.spawnTeamID = int(nameLower.split('spawn_team')[1][0])
            elif nameLower.startswith('spawn_npc'):
                props.dummyType = 'SPAWN'
                props.spawnType = 'NPC'
                props.spawnIndex = int(nameSuffix)

                # TODO: Custom value support for npc types
                if      nameLower.startswith('spawn_npc_melee'):    props.spawnEnemyType = 'MELEE'
                elif    nameLower.startswith('spawn_npc_ranged'):   props.spawnEnemyType = 'RANGED'
                elif    nameLower.startswith('spawn_npc_boss'):     props.spawnEnemyType = 'BOSS'
            elif nameLower.startswith('spawn_blitz'):
                props.dummyType = 'SPAWN'
                props.spawnType = 'BLITZ'

                # We assume that 'spawn_blitz_barricade' and 'spawn_blitz_radar' always prefix either 'r' or 'b'
                if      nameLower.startswith('spawn_blitz_barricade'):  props.spawnIndex = 1 if nameSuffix == 'r' else 2
                elif    nameLower.startswith('spawn_blitz_radar'):      props.spawnIndex = 1 if nameSuffix == 'r' else 2

                # TODO: Custom value support for blitzkrieg types
                if      nameLower.startswith('spawn_blitz_barricade'):  props.spawnBlitzType = 'BARRICADE'
                elif    nameLower.startswith('spawn_blitz_guardian'):   props.spawnBlitzType = 'GUARDIAN'
                elif    nameLower.startswith('spawn_blitz_radar'):      props.spawnBlitzType = 'RADAR'
                elif    nameLower.startswith('spawn_blitz_honoritem'):  props.spawnBlitzType = 'HONORITEM'
            elif nameLower.startswith('wait_pos'):
                props.cameraIndex = int(nameSuffix)
                props.cameraType = 'WAIT'
            elif nameLower.startswith('camera_pos'):
                props.cameraIndex = int(nameSuffix)
                props.cameraType = 'TRACK'
            elif nameLower.startswith(('smk_')):
                props.dummyType = 'SMOKE'

                # TODO: Custom value support for smoke types
                if      nameLower.startswith(('smk_ss')):   props.smokeType = 'SS'
                elif    nameLower.startswith(('smk_st')):   props.smokeType = 'ST'
                elif    nameLower.startswith(('smk_ts')):   props.smokeType = 'TS'

                state.blSmokePairs.append((nameLower, blObj))
            elif nameLower.startswith('sun_dummy'):
                props.dummyType = 'FLARE'

            state.blDummyObjs.append(blObj)

            if nameLower.startswith(('camera_pos', 'wait_pos')):    rootExtras.objects.link(blObj)
            else:                                                   rootDummies.objects.link(blObj)

    if state.doSounds:
        skippedSounds = []

        for s, sound in enumerate(state.xmlAmbs):
            if not all(tuple(key in sound for key in ('ObjName', 'type', 'filename'))):
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

            blSoundObj = bpy.data.objects.new(f"{ state.filename }_Sound{ s }", None)

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

    if state.doMisc:
        i = 1

        for gametype in state.xmlItms:
            gameID = gametype['id'].upper()

            # TODO: Custom value support for game IDs
            if gameID not in ('SOLO', 'TEAM'):
                self.report({ 'WARNING' }, f"GZRS2: Skipped game id of unsupported type: { gameID }")
                continue

            for spawn in gametype['spawns']:
                item = spawn['item']

                # TODO: Custom value support for item types
                if len(item) >= 4:
                    itemType = item[:-2].upper()
                    itemID = item[-2:]

                if len(item) < 4 or not itemType.isalpha() or not itemID.isnumeric():
                    self.report({ 'WARNING' }, f"GZRS2: Skipped item of unsupported type: { gameID }, { item }")
                    continue

                blItemObj = bpy.data.objects.new(f"{ state.filename }_Item{ i }", None)
                blItemObj.empty_display_type = 'SPHERE'
                blItemObj.location = spawn['POSITION']

                props = blItemObj.gzrs2
                props.dummyType = 'ITEM'
                props.itemGameID = gameID
                props.itemType = itemType
                props.itemID = int(itemID)
                props.itemTimer = spawn['timesec']

                state.blItemObjs.append(blItemObj)
                rootMisc.objects.link(blItemObj)

                i += 1

        for flag in state.xmlFlgs:
            name = flag['NAME'].split('.')[0]

            blFlagObj = None

            for eluMesh, blMeshObj in state.blObjPairs:
                if eluMesh.meshName != name:
                    continue

                blFlagObj = blMeshObj
                props = blFlagObj.data.gzrs2
                props.propSubtype = 'FLAG'

                # TODO: Reorient

                if 'DIRECTION'      in flag:            props.flagDirection     = flag['DIRECTION']
                if 'POWER'          in flag:            props.flagPower         = flag['POWER']

                for windtype in flag['windtypes']:
                    if 'TYPE'       in windtype:        props.flagWindType      = dataOrFirst(FLAG_WINDTYPE_DATA, windtype['TYPE'], 0)
                    if 'DELAY'      in windtype:        props.flagWindDelay     = windtype['DELAY']

                    # TODO: Multiple windtype data
                    continue

                for limit in flag['limits']:
                    if any(('AXIS' in limit,
                            'POSITION' in limit,
                            'COMPARE' in limit)):       props.flagUseLimit      = True
                    if 'AXIS'       in limit:           props.flagLimitAxis     = dataOrFirst(FLAG_LIMIT_AXIS_DATA, limit['AXIS'], 0)
                    if 'POSITION'   in limit:           props.flagLimitOffset   = limit['POSITION']
                    if 'COMPARE'    in limit:           props.flagLimitCompare  = dataOrFirst(FLAG_LIMIT_COMPARE_DATA, limit['AXIS'], 0)

                    # TODO: Multiple limit data
                    continue

                break

            if blFlagObj is None:
                self.report({ 'WARNING' }, f"GZRS2: Flag data unable to find a match, skipping: { name }")

        for smoke in state.xmlSmks:
            name = smoke['NAME'].split('.')[0]

            blSmokeDummy = None

            for nameLower, blDummyObj in state.blSmokePairs:
                if nameLower != name.lower():
                    continue

                blSmokeDummy = blDummyObj
                props = blSmokeDummy.gzrs2

                if 'DIRECTION' in smoke:        props.smokeDirection        = smoke['DIRECTION']
                if 'POWER' in smoke:            props.smokePower            = smoke['POWER']
                if 'DELAY' in smoke:            props.smokeDelay            = smoke['DELAY']
                if 'SIZE' in smoke:             props.smokeSize             = smoke['SIZE']
                if 'LIFE' in smoke:             props.smokeLife             = smoke['LIFE']
                if 'TOGGLEMINTIME' in smoke:    props.smokeToggleMinTime    = smoke['TOGGLEMINTIME']

                break

            if blSmokeDummy is None:
                self.report({ 'WARNING' }, f"GZRS2: Smoke data unable to find a match, skipping: { name }")

    if doExtras:
        if state.doCollision:
            colName = f"{ state.filename }_Collision"
            colExt = bpy.path.basename(colpath).split(os.extsep)[-1].lower()
            blColObj = setupColMesh(colName, rootExtras, context, colExt, state)
            blColObj.hide_render = True

            for viewLayer in context.scene.view_layers:
                blColObj.hide_set(True, view_layer = viewLayer)

        if state.doNavigation:
            blNavFacesObj, blNavLinksObj = setupNavMesh(state)
            rootExtras.objects.link(blNavFacesObj)
            rootExtras.objects.link(blNavLinksObj)
            blNavFacesObj.hide_render = True
            blNavLinksObj.hide_render = True

            for viewLayer in context.scene.view_layers:
                blNavFacesObj.hide_set(True, view_layer = viewLayer)
                blNavLinksObj.hide_set(True, view_layer = viewLayer)

        if state.doOcclusion:
            reorientLocal = Matrix.Rotation(math.radians(90.0), 4, 'X')

            for o, occlusion in enumerate(state.xmlOccs):
                occName = f"{ state.filename }_Occlusion{ o }"

                # We assume the occlusion points are cyclical, not z-form
                p1 = occlusion['POSITION'][0].copy()
                p2 = occlusion['POSITION'][1].copy()
                p3 = occlusion['POSITION'][2].copy()
                p4 = occlusion['POSITION'][3].copy()

                # Compare the cross products of opposite corners
                n1 = (p4 - p1).cross(p2 - p1).normalized()
                n2 = (p2 - p3).cross(p4 - p3).normalized()

                if not all((math.isclose(n1.x, n2.x, abs_tol = RS_OCCLUSION_THRESHOLD),
                            math.isclose(n1.y, n2.y, abs_tol = RS_OCCLUSION_THRESHOLD),
                            math.isclose(n1.z, n2.z, abs_tol = RS_OCCLUSION_THRESHOLD))):
                    self.report({ 'WARNING' }, f"GZRS2: Occlusion points aren't coplanar, resulting dummy may not be oriented correctly: { occName }")

                # Convert to local space
                center = (p1 + p2 + p3 + p4) / 4
                rot = n1.lerp(n2, 0.5).to_track_quat('Y', 'Z').to_matrix().to_4x4() @ reorientLocal
                rotInv = rot.inverted()

                v1 = rotInv @ (p1 - center)
                v2 = rotInv @ (p2 - center)
                v3 = rotInv @ (p3 - center)
                v4 = rotInv @ (p4 - center)

                # We assume the quad froms a rectangle
                xMin = min(v1.x, v2.x, v3.x, v4.x)
                xMax = max(v1.x, v2.x, v3.x, v4.x)
                yMin = min(v1.y, v2.y, v3.y, v4.y)
                yMax = max(v1.y, v2.y, v3.y, v4.y)

                xMid = xMax + xMin
                yMid = yMax + yMin

                xMidZero = math.isclose(xMid, 0.0, abs_tol = RS_OCCLUSION_THRESHOLD)
                yMidZero = math.isclose(yMid, 0.0, abs_tol = RS_OCCLUSION_THRESHOLD)

                if not xMidZero or not yMidZero:
                    self.report({ 'WARNING' }, f"GZRS2: Occlusion points don't form a rectangle, midpoint not zero, resulting dummy may not be oriented correctly: { occName }, { xMid }, { yMid }")

                xHDim = (xMax - xMin)
                yHDim = (yMax - yMin)

                if xHDim <= 0 or yHDim <= 0:
                    self.report({ 'WARNING' }, f"GZRS2: Occlusion points don't form a rectangle, negative dimension, resulting dummy may not be oriented correctly: { occName }, { xHDim }, { yHDim }")

                blOccObj = bpy.data.objects.new(occName, None)
                blOccObj.location = center
                blOccObj.rotation_euler = rot.to_euler()
                blOccObj.scale = Vector((xHDim, yHDim, 1))
                blOccObj.empty_display_type = 'IMAGE'
                blOccObj.empty_image_side = 'FRONT'
                blOccObj.use_empty_image_alpha = True
                blOccObj.color[3] = 0.5
                # TODO: 'wall_' vs 'wall_partition_'?
                # TODO: Custom occlusion image or sprite gizmo?
                # TODO: Duplicate the empty panel to appear for image data as well

                props = blOccObj.gzrs2
                props.dummyType = 'OCCLUSION'

                state.blOccObjs.append(blOccObj)

                rootExtras.objects.link(blOccObj)

        if state.doBounds:
            def createBBoxEmpty(name, bbmin, bbmax, blBBoxObjs, rootBounds):
                hdims = (bbmax - bbmin) / 2
                center = (bbmax + bbmin) / 2

                blBBoxObj = bpy.data.objects.new(name, None)
                blBBoxObj.empty_display_type = 'CUBE'
                blBBoxObj.location = center
                blBBoxObj.scale = hdims

                blBBoxObjs.append(blBBoxObj)
                rootBounds.objects.link(blBBoxObj)

                return blBBoxObj

            if state.doBsptree:
                for b, (bbmin, bbmax) in enumerate(state.bspTreeBounds):
                    createBBoxEmpty(f"{ state.filename }_BspBBox{ b }", bbmin, bbmax, state.blBspBBoxObjs, rootBoundsBsp)

            for b, (bbmin, bbmax) in enumerate(state.rsOctreeBounds):
                createBBoxEmpty(f"{ state.filename }_OctBBox{ b }", bbmin, bbmax, state.blOctBBoxObjs, rootBoundsOct)

        if state.doFog:
            if len(state.xmlFogs) > 1:
                self.report({ 'WARNING' }, f"GZRS2: Multiple sets of FOG tags were read! Only the first will be considered!")

            fog = state.xmlFogs[0]
            fogR = fog.get('R', 255) / 255
            fogG = fog.get('G', 255) / 255
            fogB = fog.get('B', 255) / 255

            world = ensureWorld(context)
            worldProps = world.gzrs2
            worldProps.fogColor = (fogR, fogG, fogB)
            worldProps.fogMin = fog['min']
            worldProps.fogMax = fog['max']

            state.blFogShader = shader

        if len(state.xmlGlbs) == 1:
            world = ensureWorld(context)
            worldProps = world.gzrs2

            globalData = state.xmlGlbs[0]
            if globalData['fog_enable']:    worldProps.fogEnable    = True
            if globalData['far_z']:         worldProps.farClip      = globalData['far_z']
        elif len(state.xmlGlbs) > 1:
            self.report({ 'WARNING' }, f"GZRS2: Multiple sets of GLOBAL tags were read! Only the first will be considered!")

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

    counts = countInfoReports(context)
    bpy.ops.object.select_all(action = 'DESELECT')
    bpy.ops.gzrs2.recalculate_lights_fog()
    deleteInfoReports(context, counts)

    return { 'FINISHED' }
