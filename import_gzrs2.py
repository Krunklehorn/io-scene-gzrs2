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
from .readcol_gzrs2 import *
from .readlm_gzrs2 import *
from .readelu_gzrs2 import *
from .lib_gzrs2 import *

def importRS2(self, context):
    state = GZRS2State()

    state.convertUnits = self.convertUnits
    state.meshMode = self.meshMode
    state.doCleanup = self.doCleanup
    state.doCollision = self.doCollision and self.meshMode != 'BAKE'
    state.doLightmap = self.doLightmap
    state.doLights = self.doLights
    state.tweakLights = self.tweakLights and self.doLights
    state.doProps = self.doProps
    state.doDummies = self.doDummies and self.meshMode != 'BAKE'
    state.doOcclusion = self.doOcclusion and self.meshMode != 'BAKE'
    state.doFog = self.doFog
    state.doSounds = self.doSounds and self.meshMode != 'BAKE'
    state.doItems = self.doItems and self.meshMode != 'BAKE'
    state.doBspBounds = self.doBspBounds and self.meshMode != 'BAKE'
    state.doLightDrivers = self.doLightDrivers
    state.doFogDriver = self.doFogDriver

    if self.panelLogging:
        print()
        print("=======================================================================")
        print("===========================  GZRS2 Import  ============================")
        print("=======================================================================")
        print(f"== { self.filepath }")
        print("=======================================================================")
        print()

        state.logRsPortals = self.logRsPortals
        state.logRsCells = self.logRsCells
        state.logRsGeometry = self.logRsGeometry
        state.logRsTrees = self.logRsTrees
        state.logRsLeaves = self.logRsLeaves
        state.logRsVerts = self.logRsVerts
        state.logColHeaders = self.logColHeaders
        state.logColNodes = self.logColNodes
        state.logColTris = self.logColTris
        state.logLmHeaders = self.logLmHeaders
        state.logLmImages = self.logLmImages
        state.logEluHeaders = self.logEluHeaders
        state.logEluMats = self.logEluMats
        state.logEluMeshNodes = self.logEluMeshNodes
        state.logVerboseIndices = self.logVerboseIndices and self.logEluMeshNodes
        state.logVerboseWeights = self.logVerboseWeights and self.logEluMeshNodes
        state.logCleanup = self.logCleanup

    rspath = self.filepath
    state.directory = os.path.dirname(rspath)
    state.filename = os.path.basename(rspath).split(os.extsep)[0]

    xmlRs = False
    for ext in XML_EXTENSIONS:
        rsxmlpath = pathExists(f"{ rspath }.{ ext }")

        if rsxmlpath:
            xmlRs = minidom.parse(rsxmlpath)
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
                xmlSpawn = minidom.parse(spawnxmlpath)
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

    if state.doCollision:
        for ext in COL_EXTENSIONS:
            colpath = pathExists(f"{ rspath }.{ ext }")

            if colpath:
                readCol(self, colpath, state)
                break

        if not colpath:
            state.doCollision = False
            self.report({ 'INFO' }, "GZRS2: Collision mesh requested but .col file not found, no collision mesh to generate.")

    if state.doLightmap:
        lmpath = pathExists(f"{ rspath }.lm")

        if lmpath:
            readLm(self, lmpath, state)
            unpackLmImages(state)
            setupLmMixGroup(state)
        else:
            state.doLightmap = False
            self.report({ 'INFO' }, "GZRS2: Lightmaps requested but .lm file not found, no lightmaps to generate.")

    if state.doProps:
        for p, prop in enumerate(state.xmlObjs):
            elupath = os.path.join(state.directory, prop['name'])

            for ext in XML_EXTENSIONS:
                eluxmlpath = pathExists(f"{ elupath }.{ ext }")

                if eluxmlpath:
                    state.xmlEluMats[p] = parseEluXML(self, minidom.parse(eluxmlpath), state)
                    break

            readElu(self, elupath, state)

    if state.doFog and not state.doLights:
        state.doFog = False
        self.report({ 'INFO' }, "GZRS2: Fog data but no lights, fog volume will not be generated.")

    state.doLightDrivers =   state.doLightDrivers and state.doLights
    state.doFogDriver =      state.doFogDriver and state.doFog
    doDrivers =             self.panelDrivers and (state.doLightDrivers or state.doFogDriver)
    doExtras =              state.doCollision or state.doOcclusion or state.doFog or state.doBspBounds or doDrivers

    bpy.ops.ed.undo_push()
    collections = bpy.data.collections

    rootMap =                   collections.new(state.filename)
    rootMeshes =                collections.new(f"{ state.filename }_Meshes")

    rootLightsMain =            collections.new(f"{ state.filename }_Lights_Main")            if state.doLights else False
    rootLightsSoft =            collections.new(f"{ state.filename }_Lights_Soft")            if state.doLights else False
    rootLightsHard =            collections.new(f"{ state.filename }_Lights_Hard")            if state.doLights else False
    rootLightsSoftAmbient =     collections.new(f"{ state.filename }_Lights_SoftAmbient")     if state.doLights else False
    rootLightsSoftCasters =     collections.new(f"{ state.filename }_Lights_SoftCasters")     if state.doLights else False
    rootLightsHardAmbient =     collections.new(f"{ state.filename }_Lights_HardAmbient")     if state.doLights else False
    rootLightsHardCasters =     collections.new(f"{ state.filename }_Lights_HardCasters")     if state.doLights else False

    rootProps =                 collections.new(f"{ state.filename }_Props")                  if state.doProps else False
    rootDummies =               collections.new(f"{ state.filename }_Dummies")                if state.doDummies else False
    rootSounds =                collections.new(f"{ state.filename }_Sounds")                 if state.doSounds else False
    rootItems =                 collections.new(f"{ state.filename }_Items")                  if state.doItems else False
    rootExtras =                collections.new(f"{ state.filename }_Extras")                 if doExtras else False
    rootBspBounds =             collections.new(f"{ state.filename }_BspBounds")              if state.doBspBounds else False

    context.collection.children.link(rootMap)
    rootMap.children.link(rootMeshes)

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
    if state.doBspBounds:
        rootExtras.children.link(rootBspBounds)

        for viewLayer in context.scene.view_layers:
            lcRoot = lcFindRoot(viewLayer.layer_collection, rootMap)

            if lcRoot is not None:
                for lcExtras in lcRoot.children:
                    if lcExtras.collection is rootExtras:
                        for lcBspBounds in lcExtras.children:
                            if lcBspBounds.collection is rootBspBounds:
                                lcBspBounds.hide_viewport = True
            else:
                self.report({ 'WARNING' }, f"GZRS2: Unable to find root collection in view layer: { viewLayer }")

    setupErrorMat(state)

    if state.meshMode == 'BAKE':
        name = f"{ state.filename }_Bake"

        blMesh = bpy.data.meshes.new(name)
        blMeshObj = bpy.data.objects.new(name, blMesh)

        state.blMeshes.append(blMesh)
        state.blMeshObjs.append(blMeshObj)

    for m, xmlRsMat in enumerate(state.xmlRsMats):
        xmlRsMatName = xmlRsMat.get('name', f"Material_{ m }")

        blMat = bpy.data.materials.new(xmlRsMatName)
        blMat.use_nodes = True

        tree = blMat.node_tree
        nodes = tree.nodes

        output = getShaderNodeByID(self, nodes, 'ShaderNodeOutputMaterial')
        shader = getShaderNodeByID(self, nodes, 'ShaderNodeBsdfPrincipled')
        shader.location = (20, 300)
        shader.select = False
        shader.inputs[12].default_value = 0.0 # Specular IOR Level

        nodes.active = shader
        output.select = False

        texname = xmlRsMat.get('DIFFUSEMAP')

        processRS2Texlayer(self, m, xmlRsMatName, texname, blMat, xmlRsMat, tree, nodes, shader, state)

        state.blXmlRsMats.append(blMat)

        if state.meshMode == 'STANDARD':
            blMesh = bpy.data.meshes.new(xmlRsMatName)
            blMeshObj = bpy.data.objects.new(xmlRsMatName, blMesh)

            state.blMeshes.append(blMesh)
            state.blMeshObjs.append(blMeshObj)

    if state.meshMode == 'STANDARD':
        if state.doCleanup and state.logCleanup:
            print()
            print("=== RS Mesh Cleanup ===")
            print()

        for m, blMesh in enumerate(state.blMeshes):
            if not setupRsMesh(self, m, blMesh, state):
                continue

            blMesh.materials.append(state.blXmlRsMats[m])

            rootMeshes.objects.link(state.blMeshObjs[m])

            for viewLayer in context.scene.view_layers:
                viewLayer.objects.active = state.blMeshObjs[m]

            if state.doCleanup:
                if state.logCleanup: print(blMesh.name)

                def cleanupFunc():
                    bpy.ops.object.select_all(action = 'DESELECT')
                    state.blMeshObjs[m].select_set(True)
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

                if state.logCleanup:
                    cleanupFunc()
                    print()
                else:
                    with redirect_stdout(state.silentIO):
                        cleanupFunc()

                deleteInfoReports(9, context)
    elif state.meshMode == 'BAKE':
        blMesh = state.blMeshes[0]
        blMeshObj = state.blMeshObjs[0]

        meshMatIDs = setupRsMesh(self, 0, blMesh, state)

        for blXmlRsMat in state.blXmlRsMats:
            blMesh.materials.append(blXmlRsMat)

        for p, polygon in blMesh.polygons.items():
            polygon.material_index = meshMatIDs[p]

        rootMeshes.objects.link(blMeshObj)

        for viewLayer in context.scene.view_layers:
            viewLayer.objects.active = blMeshObj

        with redirect_stdout(state.silentIO):
            bpy.ops.object.select_all(action = 'DESELECT')
            blMeshObj.select_set(True)
            bpy.ops.object.material_slot_remove_unused()
            bpy.ops.object.select_all(action = 'DESELECT')

            bpy.ops.object.mode_set(mode = 'EDIT')

            bpy.ops.mesh.select_mode(type = 'VERT')
            bpy.ops.mesh.select_all(action = 'DESELECT')

            bpy.ops.object.mode_set(mode = 'OBJECT')

        deleteInfoReports(5, context)

    if state.doLights:
        for light in state.xmlLits:
            name = light['name']
            softness = (light['ATTENUATIONEND'] - light['ATTENUATIONSTART']) / light['ATTENUATIONEND']
            hardness = 0.001 / (1 - min(softness, 0.9999))

            lit = bpy.data.lights.new(f"{ state.filename }_Light_{ name }", 'POINT')
            lit.color = light['COLOR']
            lit.energy = light['INTENSITY'] * pow(light['ATTENUATIONEND'], 2) * 2
            lit.shadow_soft_size = hardness * light['ATTENUATIONEND']
            lit.cycles.cast_shadow = light['CASTSHADOW']

            litObj = bpy.data.objects.new(f"{ state.filename }_Light_{ name }", lit)
            litObj.location = light['POSITION']

            state.blLights.append(lit)
            state.blLightObjs.append(litObj)

            # Some simple tweaks to help with contrast and shadow sharpness. The numbers were
            # tuned for outdoor maps with sunlight like Battle Arena, Castle and Factory, but
            # should be a decent starting point for other maps too.
            if self.tweakLights and softness <= 0.1:
                if light['CASTSHADOW']:
                    if state.doFog:
                        lit.energy *= 100
                        lit.shadow_soft_size = 0
                    else:
                        lit.energy *= 10
                else:
                    lit.energy /= 100

            if name.startswith(('main_Omni', 'sun_omni', 'Omni_main', 'Omni_sun', 'Omni_def', 'Omni_shadow')):
                rootLightsMain.objects.link(litObj)
            elif softness <= 0.1:
                if light['CASTSHADOW']: rootLightsHardCasters.objects.link(litObj)
                else: rootLightsHardAmbient.objects.link(litObj)
            else:
                if light['CASTSHADOW']: rootLightsSoftCasters.objects.link(litObj)
                else: rootLightsSoftAmbient.objects.link(litObj)

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
            if eluMesh.meshName.startswith(("Bip01", "Bone")):
                state.gzrsValidBones.add(eluMesh.meshName)

            if eluMesh.isDummy:
                self.report({ 'INFO' }, f"GZRS2: Skipping dummy prop: { eluMesh.meshName }")
                continue

            setupElu(self, eluMesh, True, rootProps, context, state)

    processEluHeirarchy(self, state)

    if len(state.gzrsValidBones) > 0:
        self.report({ 'INFO' }, f"GZRS2: Valid bones were found in some props: { len(state.gzrsValidBones) }")

    if state.doDummies:
        for d, dummy in enumerate(state.xmlDums):
            if d in propDums:
                continue

            name = dummy['name']

            if name.startswith(('spawn_item', 'snd_amb')):
                continue

            dir = dummy['DIRECTION']
            up = Vector((0, 0, 1))
            right = dir.cross(up)
            up = right.cross(dir)
            rot = Matrix((right, dir, up)).to_euler()

            blDummyObj = bpy.data.objects.new(f"{ state.filename }_Dummy_{ name }", None)
            blDummyObj.empty_display_type = 'ARROWS'
            blDummyObj.location = dummy['POSITION']
            blDummyObj.rotation_euler = rot

            state.blDummyObjs.append(blDummyObj)
            rootDummies.objects.link(blDummyObj)

    skippedSounds = []

    if state.doSounds:
        for s, sound in enumerate(state.xmlAmbs):
            if not all(key in sound for key in ['ObjName', 'type', 'filename']):
                skippedSounds.append(s)
                continue

            name = sound['ObjName']
            radius = sound['RADIUS']
            type = sound['type']
            space = '2D' if type[0] == 'a' else '3D'
            shape = 'AABB' if type[1] == '0' else 'SPHERE'

            if (shape == 'AABB' and not ('MIN_POSITION' in sound and 'MAX_POSITION' in sound)) or (shape == 'SPHERE' and 'CENTER' not in sound):
                skippedSounds.append(s)
                continue

            blSoundObj = bpy.data.objects.new(f"{ state.filename }_Sound_{ name }", None)

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
                blSoundObj.scale = (radius, radius, radius)

            blSoundObj.location.y = -blSoundObj.location.y

            blSoundObj['gzrs2_sound_type'] = type
            blSoundObj['gzrs2_sound_space'] = space
            blSoundObj['gzrs2_sound_shape'] = shape
            blSoundObj['gzrs2_sound_filename'] = sound['filename']

            state.blSoundObjs.append(blSoundObj)
            rootSounds.objects.link(blSoundObj)

    if len(skippedSounds) > 0:
        self.report({ 'WARNING' }, f"GZRS2: Skipped sounds with missing attributes: { skippedSounds }")

    if state.doItems:
        for gametype in state.xmlItms:
            id = gametype['id']

            for s, spawn in enumerate(gametype['spawns']):
                item = spawn['item']

                blItemObj = bpy.data.objects.new(f"{ state.filename }_Item_{ id }{ s }_{ item }", None)
                blItemObj.empty_display_type = 'SPHERE'
                blItemObj.location = spawn['POSITION']
                blItemObj['gzrs2_item_item'] = item
                blItemObj['gzrs2_item_timesec'] = str(spawn['timesec'])

                state.blItemObjs.append(blItemObj)
                rootItems.objects.link(blItemObj)

    if doExtras:
        #####
        # The goal here was to create a material that would be semi-transparent when viewed in solid and
        # material preview modes, but would only show up as wireframe during render. This works fine on
        # a default cube, but a complex mesh will still render a bunch of opaque black. Idk why ._.
        # For now, we just have to disable the collision and occlusion meshes during render.
        #####

        if state.doCollision:
            colName = f"{ state.filename }_Collision"

            blColMat = bpy.data.materials.new(colName)
            blColMat.use_nodes = True
            blColMat.diffuse_color = (1.0, 0.0, 1.0, 0.25)
            blColMat.roughness = 1.0
            # blColMat.blend_method = 'BLEND'
            blColMat.surface_render_method = 'BLENDED'
            blColMat.shadow_method = 'NONE'
            blColMat.use_transparency_overlap = True
            blColMat.use_backface_culling = False
            blColMat.use_backface_culling_shadow = False
            blColMat.use_backface_culling_lightprobe_volume = False

            tree = blColMat.node_tree
            nodes = tree.nodes
            nodes.remove(getShaderNodeByID(self, nodes, 'ShaderNodeBsdfPrincipled'))

            output = getShaderNodeByID(self, nodes, 'ShaderNodeOutputMaterial')

            transparent = nodes.new('ShaderNodeBsdfTransparent')
            transparent.location = (120, 300)

            tree.links.new(transparent.outputs[0], output.inputs[0])

            blColGeo = bpy.data.meshes.new(colName)
            blColObj = bpy.data.objects.new(colName, blColGeo)

            blColGeo.from_pydata(state.colVerts, [], [tuple(range(i, i + 3)) for i in range(0, len(state.colVerts), 3)])
            blColGeo.update()

            blColObj.visible_camera = False
            blColObj.visible_diffuse = False
            blColObj.visible_glossy = False
            blColObj.visible_volume_scatter = False
            blColObj.visible_transmission = False
            blColObj.visible_shadow = False
            blColObj.display.show_shadows = False
            blColObj.show_wire = True

            state.blColMat = blColMat
            state.blColGeo = blColGeo
            state.blColObj = blColObj

            blColObj.data.materials.append(blColMat)
            rootExtras.objects.link(blColObj)

            for viewLayer in context.scene.view_layers:
                blColObj.hide_set(True, view_layer = viewLayer)

        if state.doOcclusion:
            occName = f"{ state.filename }_Occlusion"

            blOccMat = bpy.data.materials.new(occName)
            blOccMat.use_nodes = True
            blOccMat.diffuse_color = (0.0, 1.0, 1.0, 0.25)
            blOccMat.roughness = 1.0
            # blOccMat.blend_method = 'BLEND'
            blOccMat.surface_render_method = 'BLENDED'
            blOccMat.shadow_method = 'NONE'
            blOccMat.use_transparency_overlap = True
            blOccMat.use_backface_culling = False
            blOccMat.use_backface_culling_shadow = False
            blOccMat.use_backface_culling_lightprobe_volume = False

            tree = blOccMat.node_tree
            nodes = tree.nodes
            nodes.remove(getShaderNodeByID(self, nodes, 'ShaderNodeBsdfPrincipled'))

            output = getShaderNodeByID(self, nodes, 'ShaderNodeOutputMaterial')

            transparent = nodes.new('ShaderNodeBsdfTransparent')
            transparent.location = (120, 300)

            tree.links.new(transparent.outputs[0], output.inputs[0])

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

            blOccGeo = bpy.data.meshes.new(occName)
            blOccObj = bpy.data.objects.new(occName, blOccGeo)

            blOccGeo.from_pydata(occVerts, [], occFaces)
            blOccGeo.update()

            blOccObj.visible_camera = False
            blOccObj.visible_diffuse = False
            blOccObj.visible_glossy = False
            blOccObj.visible_volume_scatter = False
            blOccObj.visible_transmission = False
            blOccObj.visible_shadow = False
            blOccObj.display.show_shadows = False
            blOccObj.show_wire = True

            state.blOccMat = blOccMat
            state.blOccGeo = blOccGeo
            state.blOccObj = blOccObj

            blOccObj.data.materials.append(blOccMat)
            rootExtras.objects.link(blOccObj)

            for viewLayer in context.scene.view_layers:
                blOccObj.hide_set(True, view_layer = viewLayer)

        if state.doBspBounds:
            for b, bounds in enumerate(state.bspBounds):
                p1, p2 = bounds
                hdims = (p2 - p1) / 2
                center = p1 + hdims

                blBBoxObj = bpy.data.objects.new(f"{ state.filename }_BspBBox{ b }", None)
                blBBoxObj.empty_display_type = 'CUBE'
                blBBoxObj.location = center
                blBBoxObj.scale = hdims

                state.blBBoxObjs.append(blBBoxObj)
                rootBspBounds.objects.link(blBBoxObj)

        if state.doFog:
            fog = state.xmlFogs[0]

            color = (fog['R'] / 255.0, fog['G'] / 255.0, fog['B'] / 255.0, 1.0)
            p1 = Vector((math.inf, math.inf, math.inf))
            p2 = Vector((-math.inf, -math.inf, -math.inf))

            for litObj in state.blLightObjs:
                p1.x = min(p1.x, litObj.location.x)
                p1.y = min(p1.y, litObj.location.y)
                p1.z = min(p1.z, litObj.location.z)
                p2.x = max(p2.x, litObj.location.x)
                p2.y = max(p2.y, litObj.location.y)
                p2.z = max(p2.z, litObj.location.z)

            hdims = (p2 - p1) / 2
            center = p1 + hdims

            fogName = f"{ state.filename }_Fog"

            blFogMat = bpy.data.materials.new(fogName)
            blFogMat.use_nodes = True
            tree = blFogMat.node_tree
            nodes = tree.nodes

            nodes.remove(getShaderNodeByID(self, nodes, 'ShaderNodeBsdfPrincipled'))

            output = getShaderNodeByID(self, nodes, 'ShaderNodeOutputMaterial')

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

            tree.links.new(shader.outputs[0], output.inputs[1])

            nodes.active = shader
            output.select = False

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
                        state.blDrivers.append((createArrayDriver(driverObj, colorProp, light, 'color'),
                                                createDriver(driverObj, energyProp, light, 'energy'),
                                                createDriver(driverObj, softnessProp, light, 'shadow_soft_size')))

                    driverObj.id_properties_ui(colorProp).update(subtype = 'COLOR', min = 0.0, max = 1.0, soft_min = 0.0, soft_max = 1.0, precision = 3, step = 1.0)
                    driverObj.id_properties_ui(energyProp).update(subtype = 'POWER', min = 0.0, max = math.inf, soft_min = 0.0, soft_max = math.inf, precision = 1, step = 100)
                    driverObj.id_properties_ui(softnessProp).update(subtype = 'DISTANCE', min = 0.0, max = math.inf, soft_min = 0.0, soft_max = math.inf, precision = 2, step = 3)

            if state.doFogDriver:
                shader = state.blFogShader

                state.blDrivers.append(createArrayDriver(driverObj, 'GZRS2 Fog Color', shader.inputs[0], 'default_value'))
                driverObj.id_properties_ui('GZRS2 Fog Color').update(subtype = 'COLOR', min = 0.0, max = 1.0, soft_min = 0.0, soft_max = 1.0, precision = 3, step = 1.0)

                state.blDrivers.append(createDriver(driverObj, 'GZRS2 Fog Density', shader.inputs[1], 'default_value'))
                driverObj.id_properties_ui('GZRS2 Fog Density').update(subtype = 'NONE', min = 0.000001, max = 1.0, soft_min = 0.000001, soft_max = 1.0, precision = 5, step = 0.001)

            state.blDriverObj = driverObj
            rootExtras.objects.link(driverObj)

    bpy.ops.object.select_all(action = 'DESELECT')
    deleteInfoReports(1, context)

    return { 'FINISHED' }
