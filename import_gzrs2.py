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

import bpy, os, io, math, mathutils
import xml.dom.minidom as minidom
from mathutils import Vector, Matrix
from contextlib import redirect_stdout

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .parse_gzrs2 import *
from .readrs_gzrs2 import *
from .readcol_gzrs2 import *
from .readelu_gzrs2 import *
from .lib_gzrs2 import *

def importRs(self, context):
    state = GZRS2State()
    silence = io.StringIO()

    state.convertUnits = self.convertUnits
    state.doCleanup = self.doCleanup
    state.doCollision = self.doCollision
    state.doLights = self.doLights
    state.doProps = self.doProps
    state.doDummies = self.doDummies
    state.doOcclusion = self.doOcclusion
    state.doFog = self.doFog
    state.doSounds = self.doSounds
    state.doItems = self.doItems
    state.doBspBounds = self.doBspBounds
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
        state.logEluHeaders = self.logEluHeaders
        state.logEluMats = self.logEluMats
        state.logEluMeshNodes = self.logEluMeshNodes
        state.logVerboseIndices = self.logVerboseIndices
        state.logVerboseWeights = self.logVerboseWeights
        state.logCleanup = self.logCleanup

    rspath = self.filepath
    directory = os.path.dirname(rspath)
    filename = os.path.splitext(os.path.basename(rspath))[0]

    xmlrspath = f"{ rspath }.xml"
    spawnpath = os.path.join(directory, "spawn.xml")
    colpath = f"{ rspath }.col"

    xmlRs = False
    xmlRsExists = pathExists(xmlrspath, directory)

    if xmlRsExists:
        xmlrspath = xmlRsExists
        xmlRs = minidom.parse(xmlrspath)
    else:
        xmlrspath = f"{ rspath }.XML"
        xmlRsExists = pathExists(xmlrspath, directory)

        if xmlRsExists:
            xmlrspath = xmlRsExists
            xmlRs = minidom.parse(xmlrspath)
        else:
            self.report({ 'ERROR' }, "Map xml not found, no materials or objects to generate!")

    xmlSpawn = False

    if state.doItems:
        xmlSpawnExists = pathExists(spawnpath, directory)

        if xmlSpawnExists:
            spawnpath = xmlSpawnExists
            xmlSpawn = minidom.parse(spawnpath)
        else:
            spawnpath = os.path.join(directory, "spawn.XML")
            xmlSpawnExists = pathExists(spawnpath, directory)

            if xmlSpawnExists:
                spawnpath = xmlSpawnExists
                xmlSpawn = minidom.parse(spawnpath)
            else:
                self.report({ 'INFO' }, "Items requested but spawn.xml not found, no items to generate.")

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
        colExists = pathExists(colpath, directory)

        if colExists:
            colpath = colExists
            readCol(self, colpath, state)
        else:
            colpath = f"{ rspath }.COL"
            colExists = pathExists(colpath, directory)

            if colExists:
                colpath = colExists
                readCol(self, colpath, state)
            else:
                state.doCollision = False
                self.report({ 'INFO' }, "Collision mesh requested but .col file not found, no collision mesh to generate.")

    if state.doProps:
        doXmlElu = False

        for p, prop in enumerate(state.xmlObjs):
            elupath = os.path.join(directory, prop['name'])
            xmlelupath = f"{ elupath }.xml"
            xmlEluExists = pathExists(xmlelupath, directory)

            if xmlEluExists:
                xmlelupath = xmlEluExists
                xmlElu = minidom.parse(xmlelupath)
                state.xmlEluMats[p] = parseEluXML(self, xmlElu, state)
                doXmlElu = True
            else:
                xmlelupath = f"{ elupath }.XML"
                xmlEluExists = pathExists(xmlelupath, directory)

                if xmlEluExists:
                    xmlelupath = xmlEluExists
                    xmlElu = minidom.parse(xmlelupath)
                    state.xmlEluMats[p] = parseEluXML(self, xmlElu, state)
                    doXmlElu = True

            readElu(self, elupath, state)

    if state.doFog and not state.doLights:
            state.doFog = False
            self.report({ 'INFO' }, "Fog data but no lights, fog volume will not be generated.")

    state.doLightDrivers =   state.doLightDrivers and state.doLights
    state.doFogDriver =      state.doFogDriver and state.doFog
    doExtras =              state.doCollision or state.doOcclusion or state.doFog or state.doBspBounds
    doDrivers =             self.panelDrivers and (state.doLightDrivers or state.doFogDriver)

    bpy.ops.ed.undo_push()
    collections = bpy.data.collections

    rootMap =                   collections.new(filename)
    rootMeshes =                collections.new(f"{ filename }_Meshes")

    rootLightsMain =            collections.new(f"{ filename }_Lights_Main")            if state.doLights else False
    rootLightsSoft =            collections.new(f"{ filename }_Lights_Soft")            if state.doLights else False
    rootLightsHard =            collections.new(f"{ filename }_Lights_Hard")            if state.doLights else False
    rootLightsSoftAmbient =     collections.new(f"{ filename }_Lights_SoftAmbient")     if state.doLights else False
    rootLightsSoftCasters =     collections.new(f"{ filename }_Lights_SoftCasters")     if state.doLights else False
    rootLightsHardAmbient =     collections.new(f"{ filename }_Lights_HardAmbient")     if state.doLights else False
    rootLightsHardCasters =     collections.new(f"{ filename }_Lights_HardCasters")     if state.doLights else False

    rootProps =                 collections.new(f"{ filename }_Props")                  if state.doProps else False
    rootDummies =               collections.new(f"{ filename }_Dummies")                if state.doDummies else False
    rootSounds =                collections.new(f"{ filename }_Sounds")                 if state.doSounds else False
    rootItems =                 collections.new(f"{ filename }_Items")                  if state.doItems else False
    rootExtras =                collections.new(f"{ filename }_Extras")                 if doExtras else False
    rootBspBounds =             collections.new(f"{ filename }_BspBounds")              if state.doBspBounds else False

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

    if state.doProps:        rootMap.children.link(rootProps)
    if state.doDummies:      rootMap.children.link(rootDummies)
    if state.doSounds:       rootMap.children.link(rootSounds)
    if state.doItems:        rootMap.children.link(rootItems)
    if doExtras:            rootMap.children.link(rootExtras)
    if state.doBspBounds:
        rootExtras.children.link(rootBspBounds)

        def lcFindRoot(lc):
            if lc.collection is rootMap: return lc
            elif len(lc.children) == 0: return None

            for child in lc.children:
                next = lcFindRoot(child)

                if next is not None:
                    return next

        for viewLayer in context.scene.view_layers:
            lcRootMap = lcFindRoot(viewLayer.layer_collection)

            if lcRootMap is not None:
                for lcExtras in lcRootMap.children:
                        if lcExtras.collection is rootExtras:
                            for lcBspBounds in lcExtras.children:
                                if lcBspBounds.collection is rootBspBounds:
                                    lcBspBounds.hide_viewport = True
            else:
                self.report({ 'INFO' }, f"GZRS2: Unable to find root collection in view layer: { viewLayer }")

    for m, material in enumerate(state.xmlRsMats):
        name = f"{ filename }_{ material['name'] }"

        blMat = bpy.data.materials.new(name)
        blMat.use_nodes = True

        tree = blMat.node_tree
        nodes = tree.nodes

        shader = nodes.get('Principled BSDF')
        shader.inputs[7].default_value = 0.0
        texname = material.get('DIFFUSEMAP')

        if texname:
            texpath = textureSearch(self, directory, texname, '')

            if texpath is not None:
                texture = nodes.new(type = 'ShaderNodeTexImage')
                texture.image = bpy.data.images.load(texpath)
                texture.location = (-280, 300)

                tree.links.new(texture.outputs[0], shader.inputs[0])

                blMat.use_backface_culling = not material['TWOSIDED']

                if material['USEALPHATEST']:
                    blMat.blend_method = 'CLIP'
                    blMat.shadow_method = 'CLIP'
                    blMat.show_transparent_back = True
                    blMat.use_backface_culling = False
                    blMat.alpha_threshold = 0.5

                    tree.links.new(texture.outputs[1], shader.inputs[21])
                elif material['USEOPACITY']:
                    blMat.blend_method = 'HASHED'
                    blMat.shadow_method = 'HASHED'
                    blMat.show_transparent_back = True
                    blMat.use_backface_culling = False

                    tree.links.new(texture.outputs[1], shader.inputs[21])

                if material['ADDITIVE']:
                    blMat.blend_method = 'BLEND'
                    blMat.show_transparent_back = True
                    blMat.use_backface_culling = False

                    add = nodes.new(type = 'ShaderNodeAddShader')
                    add.location = (300, 140)

                    transparent = nodes.new(type = 'ShaderNodeBsdfTransparent')
                    transparent.location = (300, 20)

                    tree.links.new(texture.outputs[0], shader.inputs[19])
                    tree.links.new(shader.outputs[0], add.inputs[0])
                    tree.links.new(transparent.outputs[0], add.inputs[1])
                    tree.links.new(add.outputs[0], nodes.get('Material Output').inputs[0])
            else:
                self.report({ 'INFO' }, f"GZRS2: Texture not found for bsp material: { m }, { texname }")
        else:
            self.report({ 'INFO' }, f"GZRS2: Bsp material with empty texture name: { m }")

        blMesh = bpy.data.meshes.new(name)
        blMeshObj = bpy.data.objects.new(name, blMesh)

        state.blXmlRsMats.append(blMat)
        state.blMeshes.append(blMesh)
        state.blMeshObjs.append(blMeshObj)

    if state.doCleanup and state.logCleanup:
        print()
        print("=== RS Mesh Cleanup ===")
        print()

    for m, blMesh in enumerate(state.blMeshes):
        meshVerts = []
        meshFaces = []
        meshNorms = []
        meshUV1 = []
        meshUV2 = []
        found = False
        index = 0

        for leaf in state.rsLeaves:
            if leaf.materialID == m:
                found = True

                for v in range(leaf.vertexOffset, leaf.vertexOffset + leaf.vertexCount):
                    meshVerts.append(state.rsVerts[v].pos)
                    meshNorms.append(state.rsVerts[v].nor)
                    meshUV1.append(state.rsVerts[v].uv1)
                    meshUV2.append(state.rsVerts[v].uv2)
                    # TODO: import color as well

                meshFaces.append(tuple(range(index, index + leaf.vertexCount)))
                index += leaf.vertexCount

        if not found:
            self.report({ 'INFO' }, f"GZRS2: Unused rs material slot: { m }, { state.xmlRsMats[m]['name'] }")
            continue

        blMesh.from_pydata(meshVerts, [], meshFaces)

        blMesh.use_auto_smooth = True
        blMesh.normals_split_custom_set_from_vertices(meshNorms)

        uvLayer1 = blMesh.uv_layers.new()
        for u, uv in enumerate(meshUV1): uvLayer1.data[u].uv = uv

        uvLayer2 = blMesh.uv_layers.new()
        for u, uv in enumerate(meshUV2): uvLayer2.data[u].uv = uv

        blMesh.update()

        blMesh.materials.append(state.blXmlRsMats[m])

        rootMeshes.objects.link(state.blMeshObjs[m])

        for viewLayer in context.scene.view_layers:
            viewLayer.objects.active = state.blMeshObjs[m]

        if state.doCleanup:
            if state.logCleanup: print(blMesh.name)

            bpy.ops.object.select_all(action = 'DESELECT')
            state.blMeshObjs[m].select_set(True)
            bpy.ops.object.shade_smooth(use_auto_smooth = True)
            bpy.ops.object.select_all(action = 'DESELECT')

            bpy.ops.object.mode_set(mode = 'EDIT')

            bpy.ops.mesh.select_mode(type = 'VERT')
            bpy.ops.mesh.select_all(action = 'SELECT')

            if state.logCleanup:
                bpy.ops.mesh.delete_loose()
            else:
                with redirect_stdout(silence):
                    bpy.ops.mesh.delete_loose()

            bpy.ops.mesh.select_all(action = 'SELECT')

            if state.logCleanup:
                bpy.ops.mesh.remove_doubles(use_sharp_edge_from_normals = True)
            else:
                with redirect_stdout(silence):
                    bpy.ops.mesh.remove_doubles(use_sharp_edge_from_normals = True)

            bpy.ops.mesh.select_all(action = 'DESELECT')

            if state.logCleanup: print()

        bpy.ops.object.mode_set(mode = 'OBJECT')

    if state.doLights:
        for l, light in enumerate(state.xmlLits):
            name = light['name']
            softness = (light['ATTENUATIONEND'] - light['ATTENUATIONSTART']) / light['ATTENUATIONEND']
            hardness = 0.001 / (1 - min(softness, 0.9999))

            lit = bpy.data.lights.new(f"{ filename }_Light_{ name }", 'POINT')
            lit.color = light['COLOR']
            lit.energy = light['INTENSITY'] * pow(light['ATTENUATIONEND'], 2) * 2
            lit.shadow_soft_size = hardness * light['ATTENUATIONEND']
            lit.cycles.cast_shadow = light['CASTSHADOW']

            litObj = bpy.data.objects.new(f"{ filename }_Light_{ name }", lit)
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
            for p, prop in enumerate(state.xmlObjs):
                propName = prop['name'].split('_', 1)[1].rsplit('.', 1)[0]

                for d, dummy in enumerate(state.xmlDums):
                    if dummy['name'] == propName:
                        propDums.append(d)

        for material in state.eluMats:
            name = material.texName or f"{ material.matID }[{ material.subMatID }]"
            blMat = bpy.data.materials.new(f"{ filename }_{ name }")
            blMat.use_nodes = True

            tree = blMat.node_tree
            nodes = tree.nodes

            shader = nodes.get('Principled BSDF')
            shader.location = (0, 300)
            shader.inputs[7].default_value = material.power / 100.0

            if material.texBase != '':
                texpath = textureSearch(self, directory, material.texBase, material.texDir)

                if texpath is not None:
                    texture = nodes.new(type = 'ShaderNodeTexImage')
                    texture.image = bpy.data.images.load(texpath)
                    texture.location = (-280, 300)

                    tree.links.new(texture.outputs[0], shader.inputs[0])

                    blMat.use_backface_culling = not material.twosided

                    if material.alphatest:
                        blMat.blend_method = 'CLIP'
                        blMat.shadow_method = 'CLIP'
                        blMat.show_transparent_back = True
                        blMat.use_backface_culling = False
                        blMat.alpha_threshold = 1.0 - (material.alphatest / 100.0)

                        tree.links.new(texture.outputs[1], shader.inputs[21])
                    elif material.useopacity:
                        blMat.blend_method = 'HASHED'
                        blMat.shadow_method = 'HASHED'
                        blMat.show_transparent_back = True
                        blMat.use_backface_culling = False

                        tree.links.new(texture.outputs[1], shader.inputs[21])

                    if material.additive:
                        blMat.blend_method = 'BLEND'
                        blMat.show_transparent_back = True
                        blMat.use_backface_culling = False

                        add = nodes.new(type = 'ShaderNodeAddShader')
                        add.location = (300, 140)

                        transparent = nodes.new(type = 'ShaderNodeBsdfTransparent')
                        transparent.location = (300, 20)

                        tree.links.new(texture.outputs[0], shader.inputs[19])
                        tree.links.new(shader.outputs[0], add.inputs[0])
                        tree.links.new(transparent.outputs[0], add.inputs[1])
                        tree.links.new(add.outputs[0], nodes.get('Material Output').inputs[0])
                else:
                    self.report({ 'INFO' }, f"GZRS2: Texture not found for .elu material: { material.texPath }")

            if not material.matID in state.blEluMats:
                state.blEluMats[material.matID] = {}

            state.blEluMats[material.matID][material.subMatID] = blMat

        if doXmlElu:
            for e, xmlEluMats in enumerate(state.xmlEluMats):
                state.blXmlEluMats[e] = []

                for m, material in enumerate(xmlEluMats):
                    blMat = bpy.data.materials.new(f"{ filename }_{ material['name'] }")
                    blMat.use_nodes = True

                    tree = blMat.node_tree
                    nodes = tree.nodes

                    shader = nodes.get('Principled BSDF')
                    shader.location = (0, 300)
                    shader.inputs[6].default_value = material['GLOSSINESS'] / 100.0 if 'GLOSSINESS' in material else 0.0
                    shader.inputs[7].default_value = 0.0

                    diffuse = None
                    opacity = None

                    for texture in material['textures']:
                        textype = texture['type']
                        texname = texture['name']

                        if textype in ['DIFFUSEMAP', 'SPECULARMAP', 'SELFILLUMINATIONMAP', 'OPACITYMAP', 'NORMALMAP']:
                            if texname:
                                texpath = textureSearch(self, directory, texname, '')

                                if texpath is not None:
                                    if textype == 'DIFFUSEMAP':
                                        if opacity is None:
                                            texture = nodes.new(type = 'ShaderNodeTexImage')
                                            texture.image = bpy.data.images.load(texpath)
                                            texture.location = (-560, 300)
                                        else:
                                            texture = opacity

                                        tree.links.new(texture.outputs[0], shader.inputs[0])
                                        diffuse = texture
                                    elif textype == 'SPECULARMAP':
                                        texture = nodes.new(type = 'ShaderNodeTexImage')
                                        texture.image = bpy.data.images.load(texpath)
                                        texture.location = (-560, 0)
                                        tree.links.new(texture.outputs[0], shader.inputs[7])
                                    elif textype == 'SELFILLUMINATIONMAP':
                                        texture = nodes.new(type = 'ShaderNodeTexImage')
                                        texture.image = bpy.data.images.load(texpath)
                                        texture.location = (-560, -300)
                                        tree.links.new(texture.outputs[0], shader.inputs[19])
                                    elif textype == 'OPACITYMAP':
                                        if diffuse is None:
                                            texture = nodes.new(type = 'ShaderNodeTexImage')
                                            texture.image = bpy.data.images.load(texpath)
                                            texture.location = (-560, 300)
                                        else:
                                            texture = diffuse

                                        tree.links.new(texture.outputs[1], shader.inputs[21])
                                        opacity = texture

                                        blMat.blend_method = 'CLIP'
                                        blMat.shadow_method = 'CLIP'
                                        blMat.alpha_threshold = material['ALPHATESTVALUE'] / 255.0 if 'ALPHATESTVALUE' in material else 0.5
                                    elif textype == 'NORMALMAP':
                                        texture = nodes.new(type = 'ShaderNodeTexImage')
                                        normal = nodes.new(type = 'ShaderNodeNormalMap')
                                        texture.image = bpy.data.images.load(texpath)
                                        texture.image.colorspace_settings.name = 'Non-Color'
                                        texture.location = (-560, -600)
                                        normal.location = (-280, -600)
                                        tree.links.new(texture.outputs[0], normal.inputs[1])
                                        tree.links.new(normal.outputs[0], shader.inputs[22])
                                else:
                                    self.report({ 'INFO' }, f"GZRS2: Texture not found for .elu.xml material: { textype }, { texname }")
                            else:
                                self.report({ 'INFO' }, f"GZRS2: .elu.xml material with empty texture name: { m }, { textype }")
                        else:
                            self.report({ 'INFO' }, f"GZRS2: Unsupported texture type for .elu.xml material: { textype }, { texname }")

                    state.blXmlEluMats[e].append(blMat)

        if state.doCleanup and state.logCleanup:
            print()
            print("=== Elu Mesh Cleanup ===")
            print()

        for m, eluMesh in enumerate(state.eluMeshes):
            name = f"{ filename }_Prop_{ eluMesh.meshName }"

            if eluMesh.isDummy:
                self.report({ 'INFO' }, f"GZRS2: Skipping dummy prop: { eluMesh.meshName }")
                continue
            else:
                doNorms = len(eluMesh.normals) > 0
                doUV1 = len(eluMesh.uv1s) > 0
                doUV2 = len(eluMesh.uv2s) > 0

                propVerts = []
                propFaces = []
                propNorms = [] if doNorms else None
                propUV1 = [] if doUV1 else None
                propUV2 = [] if doUV2 else None
                index = 0

                blProp = bpy.data.meshes.new(name)
                blPropObj = bpy.data.objects.new(name, blProp)

                for face in eluMesh.faces:
                    degree = face.degree

                    # Reverses the winding order for GunZ 1 elus
                    for v in range(degree - 1, -1, -1) if eluMesh.version <= ELU_5007 else range(degree):
                        propVerts.append(eluMesh.vertices[face.ipos[v]])
                        if doNorms: propNorms.append(eluMesh.normals[face.inor[v]])
                        if doUV1: propUV1.append(eluMesh.uv1s[face.iuv1[v]])
                        if doUV2: propUV2.append(eluMesh.uv2s[face.iuv2[v]])

                    propFaces.append(tuple(range(index, index + degree)))
                    index += degree

                blProp.from_pydata(propVerts, [], propFaces)

                if doNorms:
                    blProp.use_auto_smooth = True
                    blProp.normals_split_custom_set_from_vertices(propNorms)

                if doUV1:
                    uvLayer1 = blProp.uv_layers.new()
                    for u, uv in enumerate(propUV1): uvLayer1.data[u].uv = uv

                if doUV2:
                    uvLayer2 = blProp.uv_layers.new()
                    for u, uv in enumerate(propUV2): uvLayer2.data[u].uv = uv

                blProp.validate()
                blProp.update()

                if eluMesh.version <= ELU_5007:
                    if eluMesh.matID in state.blEluMats:
                        blProp.materials.append(state.blEluMats[eluMesh.matID][-1])
                    else:
                        self.report({ 'INFO' }, f"GZRS2: Missing .elu material: { eluMesh.meshName }, { eluMesh.matID }")
                elif doXmlElu:
                    if state.blXmlEluMats[m][eluMesh.matID]:
                        blProp.materials.append(state.blXmlEluMats[m][eluMesh.matID])
                    else:
                        self.report({ 'INFO' }, f"GZRS2: Missing .elu.xml material: { eluMesh.meshName }, { eluMesh.matID }")
                else:
                    self.report({ 'INFO' }, f"GZRS2: .elu.xml material requested where none was parsed, skipping: { eluMesh.meshName }, { eluMesh.matID }")

                if eluMesh.version <= ELU_5007:
                    blPropObj.matrix_world = Matrix.Rotation(math.radians(-180.0), 4, 'Z') @ eluMesh.transform
                else:
                    blPropObj.matrix_world = eluMesh.transform

                rootProps.objects.link(blPropObj)

                for viewLayer in context.scene.view_layers:
                    viewLayer.objects.active = blPropObj

                if state.doCleanup:
                    if state.logCleanup: print(eluMesh.meshName)

                    bpy.ops.object.select_all(action = 'DESELECT')
                    blPropObj.select_set(True)
                    bpy.ops.object.shade_smooth(use_auto_smooth = doNorms)
                    bpy.ops.object.select_all(action = 'DESELECT')

                    bpy.ops.object.mode_set(mode = 'EDIT')

                    bpy.ops.mesh.select_mode(type = 'VERT')
                    bpy.ops.mesh.select_all(action = 'SELECT')

                    if state.logCleanup:
                        bpy.ops.mesh.delete_loose()
                    else:
                        with redirect_stdout(silence):
                            bpy.ops.mesh.delete_loose()

                    bpy.ops.mesh.select_all(action = 'SELECT')

                    if state.logCleanup:
                        bpy.ops.mesh.remove_doubles(use_sharp_edge_from_normals = True)
                    else:
                        with redirect_stdout(silence):
                            bpy.ops.mesh.remove_doubles(use_sharp_edge_from_normals = True)

                    bpy.ops.mesh.select_all(action = 'DESELECT')

                    if state.logCleanup: print()

                bpy.ops.object.mode_set(mode = 'OBJECT')

                state.blProps.append(blProp)
                state.blPropObjs.append(blPropObj)

    if state.doDummies:
        for d, dummy in enumerate(state.xmlDums):
            if d in propDums:
                continue

            name = dummy['name']

            if name.startswith(('spawn_item', 'snd_amb')):
                continue

            dir = dummy['DIRECTION']
            dir.y = -dir.y
            up = Vector((0, 0, 1))
            right = dir.cross(up)
            up = right.cross(dir)
            rot = Matrix((right, dir, up)).to_euler()

            blDummyObj = bpy.data.objects.new(f"{ filename }_Dummy_{ name }", None)
            blDummyObj.empty_display_type = 'ARROWS'
            blDummyObj.location = dummy['POSITION']
            blDummyObj.rotation_euler = rot

            state.blDummyObjs.append(blDummyObj)
            rootDummies.objects.link(blDummyObj)

    if state.doSounds:
        for sound in state.xmlAmbs:
            name = sound['ObjName']
            radius = sound['RADIUS']
            type = sound['type']
            space = '2D' if type[0] == 'a' else '3D'
            shape = 'AABB' if type[1] == '0' else 'SPHERE'

            blSoundObj = bpy.data.objects.new(f"{ filename }_Sound_{ name }", None)

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

            blSoundObj['gzrs2_sound_type'] = type
            blSoundObj['gzrs2_sound_space'] = space
            blSoundObj['gzrs2_sound_shape'] = shape
            blSoundObj['gzrs2_sound_filename'] = sound['filename']

            state.blSoundObjs.append(blSoundObj)
            rootSounds.objects.link(blSoundObj)

    if state.doItems:
        for gametype in state.xmlItms:
            id = gametype['id']

            for s, spawn in enumerate(gametype['spawns']):
                item = spawn['item']

                blItemObj = bpy.data.objects.new(f"{ filename }_Item_{ id }{ s }_{ item }", None)
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
        # For now you'll just have to  disable the collision and occlusion meshes during render.
        #####

        if state.doCollision:
            name = f"{ filename }_Collision"

            blColMat = bpy.data.materials.new(name)
            blColMat.use_nodes = True
            blColMat.diffuse_color = (1.0, 0.0, 1.0, 0.25)
            blColMat.roughness = 1.0
            blColMat.blend_method = 'HASHED'

            tree = blColMat.node_tree
            nodes = tree.nodes
            nodes.remove(nodes.get('Principled BSDF'))

            transparent = nodes.new(type = 'ShaderNodeBsdfTransparent')
            transparent.location = (120, 300)

            tree.links.new(transparent.outputs[0], nodes.get('Material Output').inputs[0])

            blColGeo = bpy.data.meshes.new(name)
            blColObj = bpy.data.objects.new(name, blColGeo)

            blColGeo.from_pydata(state.colVerts, [], [tuple(range(i, i + 3)) for i in range(0, len(state.colVerts), 3)])
            blColGeo.update()

            blColObj.visible_volume_scatter = False
            blColObj.visible_shadow = False
            blColObj.show_wire = True

            state.blColMat = blColMat
            state.blColGeo = blColGeo
            state.blColObj = blColObj

            blColObj.data.materials.append(blColMat)
            rootExtras.objects.link(blColObj)

            for viewLayer in context.scene.view_layers:
                blColObj.hide_set(True, view_layer = viewLayer)

        if state.doOcclusion:
            name = f"{ filename }_Occlusion"

            blOccMat = bpy.data.materials.new(name)
            blOccMat.use_nodes = True
            blOccMat.diffuse_color = (0.0, 1.0, 1.0, 0.25)
            blOccMat.roughness = 1.0
            blOccMat.blend_method = 'HASHED'

            tree = blOccMat.node_tree
            nodes = tree.nodes
            nodes.remove(nodes.get('Principled BSDF'))

            transparent = nodes.new(type = 'ShaderNodeBsdfTransparent')
            transparent.location = (120, 300)

            tree.links.new(transparent.outputs[0], nodes.get('Material Output').inputs[0])

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

            blOccGeo = bpy.data.meshes.new(name)
            blOccObj = bpy.data.objects.new(name, blOccGeo)

            blOccGeo.from_pydata(occVerts, [], occFaces)
            blOccGeo.update()

            blOccObj.visible_volume_scatter = False
            blOccObj.visible_shadow = False
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

                blBBoxObj = bpy.data.objects.new(f"{ filename }_BspBBox{ b }", None)
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

            for l, litObj in enumerate(state.blLightObjs):
                p1.x = min(p1.x, litObj.location.x)
                p1.y = min(p1.y, litObj.location.y)
                p1.z = min(p1.z, litObj.location.z)
                p2.x = max(p2.x, litObj.location.x)
                p2.y = max(p2.y, litObj.location.y)
                p2.z = max(p2.z, litObj.location.z)

            hdims = (p2 - p1) / 2
            center = p1 + hdims

            blFogMat = bpy.data.materials.new(name = f"{ filename }_Fog")
            blFogMat.use_nodes = True
            tree = blFogMat.node_tree
            nodes = tree.nodes

            nodes.remove(nodes.get('Principled BSDF'))

            shader = None

            if min(color[:3]) > 0.5:
                shader = nodes.new(type = 'ShaderNodeVolumeScatter')
                shader.inputs[0].default_value = color
                shader.inputs[1].default_value = 0.00001
            else:
                shader = nodes.new(type = 'ShaderNodeVolumeAbsorption')
                shader.inputs[0].default_value = color
                shader.inputs[1].default_value = 0.1

            shader.location = (120, 300)

            tree.links.new(shader.outputs[0], nodes.get('Material Output').inputs[1])

            bpy.ops.mesh.primitive_cube_add(location = center, scale = hdims)
            blFogObj = context.active_object
            blFogMesh = blFogObj.data
            blFogObj.name = blFogMesh.name = f"{ filename }_Fog"
            blFogObj.display_type = 'WIRE'

            state.blFogMat = blFogMat
            state.blFogShader = shader
            state.blFogMesh = blFogMesh
            state.blFogObj = blFogObj

            blFogObj.data.materials.append(blFogMat)

            for collection in blFogObj.users_collection:
                collection.objects.unlink(blFogObj)
            rootExtras.objects.link(blFogObj)

            bpy.ops.object.select_all(action = 'DESELECT')

        if doDrivers:
            driverObj = bpy.data.objects.new(f"{ filename }_Drivers", None)
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

    return { 'FINISHED' }
