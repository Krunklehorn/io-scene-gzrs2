#####
# Most of the code is based on logic found in...
# - RTypes.h
# - RToken.h
# - RBspObject.h/.cpp
# - RMaterialList.h/.cpp
#
# Please report maps with unsupported features to me on Discord: Krunk#6051
#####

import bpy, os, math, mathutils
from mathutils import Vector, Matrix

from . import minidom
from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .parse_gzrs2 import *
from .read_gzrs2 import *
from .lib_gzrs2 import *

def load(self, context):
    state = GZRS2State()

    rspath = self.filepath
    xmlpath = f"{ rspath }.xml"
    colpath = f"{ rspath }.col"
    directory = os.path.split(rspath)[0]
    filename = os.path.basename(directory)

    xmlRS = minidom.parse(xmlpath)
    xmlSpawn = False
    spawnpath = f"{ directory }\\spawn.xml"

    if self.doItems:
        if os.path.exists(spawnpath):
            xmlSpawn = minidom.parse(spawnpath)
        else:
            self.doItems = False
            self.report({ 'INFO' }, "Items requested but spawn.xml not found, no items to generate.")

    state.xmlMats = parseRSXML(self, xmlRS, 'MATERIAL')
    if self.doLights:       state.xmlLits = parseRSXML(self, xmlRS, 'LIGHT')
    if self.doProps:        state.xmlObjs = parseRSXML(self, xmlRS, 'OBJECT')
    if self.doDummies or self.doProps: # Currently, props need the dummies list
                            state.xmlDums = parseRSXML(self, xmlRS, 'DUMMY')
    if self.doOcclusion:    state.xmlOccs = parseRSXML(self, xmlRS, 'OCCLUSION')
    if self.doFog:          state.xmlFogs = parseRSXML(self, xmlRS, 'FOG')
    if self.doSounds:       state.xmlAmbs = parseRSXML(self, xmlRS, 'AMBIENTSOUND')
    if self.doItems:        state.xmlItms = parseSpawnXML(self, xmlSpawn)

    self.doLights =         self.doLights and       len(state.xmlLits) != 0
    self.doProps =          self.doProps and        len(state.xmlObjs) != 0
    self.doDummies =        self.doDummies and      len(state.xmlDums) != 0
    self.doOcclusion =      self.doOcclusion and    len(state.xmlOccs) != 0
    self.doFog =            self.doFog and          len(state.xmlFogs) != 0
    self.doSounds =         self.doSounds and       len(state.xmlAmbs) != 0
    self.doItems =          self.doItems and        len(state.xmlItms) != 0

    readRs(self, rspath, state)

    if self.doCollision:
        readCol(self, colpath, state)

    if self.doFog and not self.doLights:
            self.doFog = False
            self.report({ 'INFO' }, "Fog data but no lights, fog volume will not be generated.")

    self.doLightDrivers =   self.doLightDrivers and self.doLights
    self.doFogDriver =      self.doFogDriver and self.doFog
    doExtras =              self.doCollision or self.doOcclusion or self.doFog or self.doBspBounds
    doDrivers =             self.panelDrivers and (self.doLightDrivers or self.doFogDriver)

    bpy.ops.ed.undo_push()
    collections = bpy.data.collections

    rootMap =                   collections.new(filename)
    rootMeshes =                collections.new(f"{ filename }_Meshes")

    rootLightsMain =            collections.new(f"{ filename }_Lights_Main")          if self.doLights else False
    rootLightsSoft =            collections.new(f"{ filename }_Lights_Soft")          if self.doLights else False
    rootLightsHard =            collections.new(f"{ filename }_Lights_Hard")          if self.doLights else False
    rootLightsSoftAmbient =     collections.new(f"{ filename }_Lights_SoftAmbient")   if self.doLights else False
    rootLightsSoftCasters =     collections.new(f"{ filename }_Lights_SoftCasters")   if self.doLights else False
    rootLightsHardAmbient =     collections.new(f"{ filename }_Lights_HardAmbient")   if self.doLights else False
    rootLightsHardCasters =     collections.new(f"{ filename }_Lights_HardCasters")   if self.doLights else False

    rootProps =                 collections.new(f"{ filename }_Props")                if self.doProps else False
    rootDummies =               collections.new(f"{ filename }_Dummies")              if self.doDummies else False
    rootSounds =                collections.new(f"{ filename }_Sounds")               if self.doSounds else False
    rootItems =                 collections.new(f"{ filename }_Items")                if self.doItems else False
    rootExtras =                collections.new(f"{ filename }_Extras")               if doExtras else False
    rootBspBounds =             collections.new(f"{ filename }_BspBounds")            if self.doBspBounds else False

    context.collection.children.link(rootMap)
    rootMap.children.link(rootMeshes)

    if self.doLights:
        rootMap.children.link(rootLightsMain)
        rootMap.children.link(rootLightsSoft)
        rootMap.children.link(rootLightsHard)
        rootLightsSoft.children.link(rootLightsSoftAmbient)
        rootLightsSoft.children.link(rootLightsSoftCasters)
        rootLightsHard.children.link(rootLightsHardAmbient)
        rootLightsHard.children.link(rootLightsHardCasters)

    if self.doProps:        rootMap.children.link(rootProps)
    if self.doDummies:      rootMap.children.link(rootDummies)
    if self.doSounds:       rootMap.children.link(rootSounds)
    if self.doItems:        rootMap.children.link(rootItems)
    if doExtras:            rootMap.children.link(rootExtras)
    if self.doBspBounds:
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
                self.report({ 'INFO' }, f"Unable to find root collection in view layer: { viewLayer }")

    for m, material in enumerate(state.xmlMats):
        name = f"{ filename }_Mesh{ m }_{ material['name'] }"

        mat = bpy.data.materials.new(name)
        mat.use_nodes = True

        tree = mat.node_tree
        nodes = tree.nodes

        shader = nodes.get('Principled BSDF')
        shader.inputs[7].default_value = 0.0
        texpath = material.get('DIFFUSEMAP')

        if not texpath:
            self.report({ 'INFO' }, f"Material with empty texture path: { m }")
        else:
            texpath = texpath.replace('/', '\\')
            texpath = f"{ directory }\\{ texpath }.dds"

            texpath = texpath.replace('.dds.dds', '.dds')

            if os.path.exists(texpath):
                texture = nodes.new(type = 'ShaderNodeTexImage')
                texture.image = bpy.data.images.load(texpath)
                texture.location = (-280, 300)

                tree.links.new(texture.outputs[0], shader.inputs[0])

                if material['USEOPACITY']:
                    mat.blend_method = 'BLEND'
                    mat.shadow_method = 'HASHED'
                    mat.use_backface_culling = True

                    tree.links.new(texture.outputs[1], shader.inputs[21])
                elif material['ADDITIVE']:
                    mat.blend_method = 'BLEND'

                    add = nodes.new(type = 'ShaderNodeAddShader')
                    add.location = (300, 140)

                    transparent = nodes.new(type = 'ShaderNodeBsdfTransparent')
                    transparent.location = (300, 20)

                    tree.links.new(texture.outputs[0], shader.inputs[19])
                    tree.links.new(shader.outputs[0], add.inputs[0])
                    tree.links.new(transparent.outputs[0], add.inputs[1])
                    tree.links.new(add.outputs[0], nodes.get('Material Output').inputs[0])
            else:
                self.report({ 'INFO' }, f"No texture found for material: { m }, { texpath }")

        mesh = bpy.data.meshes.new(name)
        meshObj = bpy.data.objects.new(name, mesh)

        state.blMats.append(mat)
        state.blMeshes.append(mesh)
        state.blMeshObjs.append(meshObj)

    for m, mesh in enumerate(state.blMeshes):
        meshVerts = []
        meshFaces = []
        meshUVs = []
        found = False
        firstIndex = 0

        for poly in state.bspPolys:
            if poly.materialID == m:
                found = True

                for i in range(poly.firstVertex, poly.firstVertex + poly.vertexCount):
                    meshVerts.append(state.bspVerts[i].pos)
                    meshUVs.append(state.bspVerts[i].uv)

                meshFaces.append(tuple(range(firstIndex, firstIndex + poly.vertexCount)))
                firstIndex += poly.vertexCount

        if not found:
            # TODO: append material to list instead, check if props use it later
            self.report({ 'INFO' }, f"Unused material slot, associated data will be garbage collected: { m }, { state.xmlMats[m]['name'] }")
        else:
            mesh.from_pydata(meshVerts, [], meshFaces)
            uvLayer = mesh.uv_layers.new()

            for u, uv in enumerate(meshUVs):
                uvLayer.data[u].uv = uv

            mesh.update()

            state.blMeshObjs[m].data.materials.append(state.blMats[m])
            rootMeshes.objects.link(state.blMeshObjs[m])

    if self.doLights:
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
                    if self.doFog:
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

    #####
    # .elu models, are not supported yet. The script will search for a corresponding dummy to create as an empty instead.
    # Use goweiwen's updated version of Phantom*'s .elu/.ani importer for now.
    # https://github.com/goweiwen/blender-elu-importer
    # https://forum.ragezone.com/f245/elu-ani-blender-importer-488857/
    #####

    propDums = []

    if self.doProps:
        for p, prop in enumerate(state.xmlObjs):
            propName = prop['name']
            splitName = propName.split('_', 1)[1][:-4]
            found = None
            multiple = False

            for d, dummy in enumerate(state.xmlDums):
                if dummy['name'] == splitName:
                    if found is None:
                        found = dummy
                    elif not multiple:
                        multiple = True
                        self.report({ 'INFO' }, f"Prop listed with more than one corresponding dummy, using the first: { p }, { splitName }")

                    propDums.append(d)

            if not found:
                self.report({ 'INFO' }, f"Prop listed with no corresponding dummy, skipping: { p }, { splitName }")
            else:
                pos = found['POSITION']
                dir = found['DIRECTION']
                up = Vector((0, 0, 1))
                right = dir.cross(up)
                up = right.cross(dir)
                rot = Matrix((right, dir, up))

                blPropObj = bpy.data.objects.new(f"{ filename }_Prop_{ splitName }", None)
                blPropObj.empty_display_type = 'ARROWS'
                blPropObj.location = pos
                blPropObj.rotation_euler = rot.to_euler()

                state.blPropObjs.append(blPropObj)
                rootProps.objects.link(blPropObj)

    if self.doDummies:
        for d, dummy in enumerate(state.xmlDums):
            if d in propDums:
                continue

            name = dummy['name']

            if name.startswith(('spawn_item', 'snd_amb')):
                continue

            pos = dummy['POSITION']
            dir = dummy['DIRECTION']
            up = Vector((0, 0, 1))
            right = dir.cross(up)
            up = right.cross(dir)
            rot = Matrix((right, dir, up))

            blDummyObj = bpy.data.objects.new(f"{ filename }_Dummy_{ name }", None)
            blDummyObj.empty_display_type = 'ARROWS'
            blDummyObj.location = pos
            blDummyObj.rotation_euler = rot.to_euler()

            state.blDummyObjs.append(blDummyObj)
            rootDummies.objects.link(blDummyObj)

    if self.doSounds:
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

    if self.doItems:
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

        if self.doCollision:
            name = f"{ filename }_Collision"

            blColMat = bpy.data.materials.new(name)
            blColMat.use_nodes = True
            blColMat.diffuse_color = (1.0, 0.0, 1.0, 0.25)
            blColMat.roughness = 1.0
            blColMat.blend_method = 'BLEND'

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

        if self.doOcclusion:
            name = f"{ filename }_Occlusion"

            blOccMat = bpy.data.materials.new(name)
            blOccMat.use_nodes = True
            blOccMat.diffuse_color = (0.0, 1.0, 1.0, 0.25)
            blOccMat.roughness = 1.0
            blOccMat.blend_method = 'BLEND'

            tree = blOccMat.node_tree
            nodes = tree.nodes
            nodes.remove(nodes.get('Principled BSDF'))

            transparent = nodes.new(type = 'ShaderNodeBsdfTransparent')
            transparent.location = (120, 300)

            tree.links.new(transparent.outputs[0], nodes.get('Material Output').inputs[0])

            occVerts = []
            occFaces = []
            firstIndex = 0

            for o, occlusion in enumerate(state.xmlOccs):
                points = occlusion['POSITION']
                occVertexCount = len(points)

                for point in points:
                    occVerts.append(point)

                occFaces.append(tuple(range(firstIndex, firstIndex + occVertexCount)))
                firstIndex += occVertexCount

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

        if self.doBspBounds:
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

        if self.doFog:
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

            if self.doLightDrivers:
                for g, group in enumerate(groupLights(state.blLights)):
                    property = f"GZRS2 Lightgroup { g }"
                    colorProp = f"{ property } Color"
                    energyProp = f"{ property } Energy"
                    softnessProp = f"{ property } Softness"

                    for light in group:
                        state.blDrivers.append((createArrayDriver(driverObj, colorProp, light, 'color'),
                                                createDriver(driverObj, energyProp, light, 'energy'),
                                                createDriver(driverObj, softnessProp, light, 'shadow_soft_size')))

                    driverObj.id_properties_ui(colorProp).update(subtype = 'COLOR',
                                                                 min = 0.0, max = 1.0,
                                                                 soft_min = 0.0, soft_max = 1.0,
                                                                 precision = 3, step = 1.0)

                    driverObj.id_properties_ui(energyProp).update(subtype = 'POWER',
                                                                  min = 0.0, soft_min = 0.0,
                                                                  precision = 1, step = 100)

                    driverObj.id_properties_ui(softnessProp).update(subtype = 'DISTANCE',
                                                                    precision = 2, step = 3,
                                                                    min = 0.0, soft_min = 0.0)

            if self.doFogDriver:
                shader = state.blFogShader

                state.blDrivers.append(createArrayDriver(driverObj, 'GZRS2 Fog Color', shader.inputs[0], 'default_value'))
                driverObj.id_properties_ui('GZRS2 Fog Color').update(subtype = 'COLOR',
                                                                     min = 0.0, max = 1.0,
                                                                     soft_min = 0.0, soft_max = 1.0,
                                                                     precision = 3, step = 1.0)

                state.blDrivers.append(createDriver(driverObj, 'GZRS2 Fog Density', shader.inputs[1], 'default_value'))
                driverObj.id_properties_ui('GZRS2 Fog Density').update(subtype = 'NONE',
                                                                       min = 0.000001, max = 1.0,
                                                                       soft_min = 0.000001, soft_max = 1.0,
                                                                       precision = 5, step = 0.001)

            state.blDriverObj = driverObj
            rootExtras.objects.link(driverObj)

    return { 'FINISHED' }
