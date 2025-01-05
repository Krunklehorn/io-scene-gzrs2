import os

from collections import defaultdict

from mathutils import Vector

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .lib_gzrs2 import *

def filterNodes(childNodes):
    for child in filter(lambda x: x.nodeType == x.ELEMENT_NODE, childNodes):
        yield (child, child.nodeName.strip(), child.firstChild and child.firstChild.nodeValue)

def parseDistance(data, convertUnits):
    value = float(data)
    if convertUnits: value *= 0.01

    return value

def parseVec3(data, nodeName, convertUnits, flipY):
    vec = Vector((float(s) for s in data.split(' ')))
    if nodeName in ('POSITION', 'CENTER', 'MIN_POSITION', 'MAX_POSITION', 'OCCLUDERPOINT') and convertUnits: vec *= 0.01
    if flipY and nodeName in ('POSITION', 'DIRECTION', 'UP', 'OCCLUDERPOINT'): vec.y = -vec.y
    if nodeName in ('DIRECTION', 'UP'): vec.normalize()

    return vec

def parseXYZ(node, nodeName, convertUnits, flipY):
    vec = Vector((float(node.getAttribute('x')), float(node.getAttribute('y')), float(node.getAttribute('z'))))
    if nodeName in ('POSITION', 'CENTER', 'MIN_POSITION', 'MAX_POSITION', 'OCCLUDERPOINT') and convertUnits: vec *= 0.01
    if flipY and nodeName in ('POSITION', 'DIRECTION', 'UP', 'OCCLUDERPOINT'): vec.y = -vec.y
    if nodeName in ('DIRECTION', 'UP'): vec.normalize()

    return vec

def parseUnknown(self, data, nodeName, xmlName, tagName):
    if data is not None:
        if isinstance(data, str):
            data = data.strip()

        self.report({ 'INFO' }, f"GZRS2: No rule yet for { tagName } tag found in { xmlName }, it may contain useful data: { nodeName }, { data }")

    return True

def parseRsXML(self, xmlRs, tagName, state):
    elements = xmlRs.getElementsByTagName(tagName)
    nodeEntries = []

    for element in elements:
        nodeEntry = defaultdict(lambda: False)

        if element.hasAttribute('name'):
            nodeEntry['name'] = element.getAttribute('name')
        elif element.hasAttribute('ObjName'):
            nodeEntry['ObjName'] = element.getAttribute('ObjName')
            nodeEntry['type'] = element.getAttribute('type')
            nodeEntry['filename'] = element.getAttribute('filename')
        elif element.hasAttribute('min') or element.hasAttribute('max'):
            nodeEntry['min'] = int(element.getAttribute('min'))
            nodeEntry['max'] = int(element.getAttribute('max'))
        elif tagName != 'GLOBAL':
            self.report({ 'ERROR' }, f"GZRS2: No rule for .rs.xml element: { element }")
            break

        for node, nodeName, data in filterNodes(element.childNodes):
            if nodeName == 'DIFFUSEMAP':
                if data is not None:
                    data = data.strip()

                    if data:
                        data = os.path.normpath(data)

                nodeEntry[nodeName] = data
            elif nodeName == 'fog_enable':
                nodeEntry[nodeName] = data.strip().lower() == 'true'
            elif nodeName in ('R', 'G', 'B'):
                nodeEntry[nodeName] = int(data)
            elif nodeName in ('INTENSITY', 'fog_min', 'fog_max', 'far_z'):
                nodeEntry[nodeName] = float(data)
            elif nodeName in ('ATTENUATIONSTART', 'ATTENUATIONEND', 'RADIUS'):
                nodeEntry[nodeName] = parseDistance(data, state.convertUnits)
            elif nodeName in ('DIFFUSE', 'AMBIENT', 'SPECULAR', 'COLOR'):
                try:                nodeEntry[nodeName] = tuple(float(s) for s in data.split(' '))
                except ValueError:  nodeEntry[nodeName] = bool(data)
            elif nodeName == 'fog_color':
                try:                nodeEntry[nodeName] = tuple(float(s) for s in data.split(','))
                except ValueError:  nodeEntry[nodeName] = bool(data)
            elif nodeName in ('POSITION', 'DIRECTION', 'CENTER', 'MIN_POSITION', 'MAX_POSITION'):
                vec = parseVec3(data, nodeName, state.convertUnits, True)

                if tagName == 'OCCLUSION':
                    if nodeEntry[nodeName] is False:
                        nodeEntry[nodeName] = []

                    nodeEntry[nodeName].append(vec)
                else:
                    nodeEntry[nodeName] = vec
            else:
                nodeEntry[nodeName] = parseUnknown(self, data, nodeName, '.rs.xml', tagName)

        nodeEntries.append(nodeEntry)

    return nodeEntries

def parseSpawnXML(self, xmlSpawn, state):
    gametypes = xmlSpawn.getElementsByTagName('GAMETYPE')
    gametypeEntries = []

    for gametype in gametypes:
        id = gametype.getAttribute('id')
        gametypeEntry = { 'id': id, 'spawns': [] }
        spawns = gametype.getElementsByTagName('SPAWN')

        for spawn in spawns:
            spawnEntry = {}
            spawnEntry['item'] = spawn.getAttribute('item')
            spawnEntry['timesec'] = int(spawn.getAttribute('timesec'))

            for node, nodeName, data in filterNodes(spawn.childNodes):
                if nodeName == 'POSITION':
                    spawnEntry[nodeName] = parseVec3(data, nodeName, state.convertUnits, True)
                else:
                    spawnEntry[nodeName] = parseUnknown(self, data, nodeName, 'spawn.xml', 'SPAWN')

            gametypeEntry['spawns'].append(spawnEntry)

        gametypeEntries.append(gametypeEntry)

    return gametypeEntries

def parseFlagXML(self, xmlFlag):
    flags = xmlFlag.getElementsByTagName('FLAG')
    flagEntries = []

    for flag in flags:
        name = flag.getAttribute('NAME')
        direction = int(flag.getAttribute('DIRECTION'))
        power = float(flag.getAttribute('POWER'))

        flagEntry = {
            'NAME': name,
            'DIRECTION': direction,
            'POWER': power,
            'windtypes': [],
            'limits': [] # ZClothEmblem.cpp
        }

        windtypes = flag.getElementsByTagName('WINDTYPE')

        for windtype in windtypes:
            flagEntry['windtypes'].append({
                'TYPE': int(windtype.getAttribute('TYPE')),
                'DELAY': int(windtype.getAttribute('DELAY'))
            })

        limits = flag.getElementsByTagName('RESTRICTION')

        for limit in limits:
            limitEntry = {}

            if limit.hasAttribute('POSITION'):
                print(name)
                print(limit.getAttribute('POSITION'))
                print(float(limit.getAttribute('POSITION')))

            if limit.hasAttribute('AXIS'):      limitEntry['AXIS']      = int(limit.getAttribute('AXIS'))
            if limit.hasAttribute('POSITION'):  limitEntry['POSITION']  = float(limit.getAttribute('POSITION'))
            if limit.hasAttribute('COMPARE'):   limitEntry['COMPARE']   = int(limit.getAttribute('COMPARE'))

            flagEntry['limits'].append(limitEntry)

        flagEntries.append(flagEntry)

    return flagEntries

def parseSmokeXML(xmlSmoke):
    smokes = xmlSmoke.getElementsByTagName('SMOKE')
    smokeEntries = []

    for smoke in smokes:
        smokeEntry = {
            'NAME': smoke.getAttribute('NAME'),
            'DIRECTION': int(smoke.getAttribute('DIRECTION')),
            'POWER': float(smoke.getAttribute('POWER')),
            'DELAY': int(smoke.getAttribute('DELAY')),
            'SIZE': float(smoke.getAttribute('SIZE'))
        }

        if smoke.hasAttribute('LIFE'):              smokeEntry['LIFE']              = float(smoke.getAttribute('LIFE'))
        if smoke.hasAttribute('TOGGLEMINTIME'):     smokeEntry['TOGGLEMINTIME']     = float(smoke.getAttribute('TOGGLEMINTIME'))

        smokeEntries.append(smokeEntry)

    return smokeEntries

def parseSceneXML(self, xmlScene, xmlName, state):
    instances = xmlScene.getElementsByTagName('SCENEINSTANCE')
    actors = xmlScene.getElementsByTagName('ACTOR')
    dirlights = xmlScene.getElementsByTagName('DIRLIGHT')
    spotlights = xmlScene.getElementsByTagName('SPOTLIGHT')
    pointlights = xmlScene.getElementsByTagName('LIGHT')
    effects = xmlScene.getElementsByTagName('EFFECTINSTANCE')
    occluders = xmlScene.getElementsByTagName('OCCLUDER')
    nodeEntries = []

    if state.logSceneNodes and instances:
        print()
        print("=========  Scene.xml Nodes  =========")
        print()

    for instance in instances:
        instanceEntry = { 'type': 'SCENEINSTANCE', 'name': None, 'resourcename': None }

        for node, nodeName, data in filterNodes(instance.childNodes):
            if nodeName == 'COMMON':
                instanceEntry['name'] = node.getAttribute('name')

                for child, childName, data in filterNodes(node.childNodes):
                    if childName in ('POSITION', 'DIRECTION', 'UP', 'SCALE'):
                        instanceEntry[childName] = parseVec3(data, childName, state.convertUnits, False)
                    else:
                        instanceEntry[childName] = parseUnknown(self, data, childName, xmlName, 'SCENEINSTANCE')
            elif nodeName == 'PROPERTY':
                for child, childName, data in filterNodes(node.childNodes):
                    if childName == 'FILENAME':
                        if data is not None:
                            data = data.strip()

                        instanceEntry['resourcename'] = data
                    elif childName not in ('UMBRAID', 'USESELECTUPDATE_HAVEVISIBLE', 'USESELECTUPDATE_HAVEANI'):
                        instanceEntry[childName] = parseUnknown(self, data, childName, xmlName, 'SCENEINSTANCE')
            elif nodeName not in ('SCENE', 'USER_PROPERTY'):
                instanceEntry[nodeName] = parseUnknown(self, data, nodeName, xmlName, 'SCENEINSTANCE')

        if state.logSceneNodes:
            print(f"Instance: { instanceEntry['name'] }")
            print(f"Filename: { instanceEntry['resourcename'] }")
            print("         Position:           ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*instanceEntry['POSITION']))
            print("         Direction:          ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*instanceEntry['DIRECTION']))
            print("         Up:                 ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*instanceEntry['UP']))
            print("         Scale:              ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*instanceEntry['SCALE']))
            for k, v in instanceEntry.items():
                if k not in ('type', 'name', 'resourcename', 'POSITION', 'DIRECTION', 'UP', 'SCALE'):
                    print(f"        { k }: { v }")
            print()

        nodeEntries.append(instanceEntry)

    for actor in actors:
        actorEntry = { 'type': 'ACTOR', 'name': None, 'resourcename': None }

        for node, nodeName, data in filterNodes(actor.childNodes):
            if nodeName == 'COMMON':
                actorEntry['name'] = node.getAttribute('name')
            elif nodeName == 'PROPERTY':
                for child, childName, data in filterNodes(node.childNodes):
                    if childName == 'FILENAME':
                        if data is not None:
                            data = data.strip()

                        actorEntry['resourcename'] = data
                    else:
                        actorEntry[childName] = parseUnknown(self, data, childName, xmlName, 'ACTOR')
            else:
                actorEntry[nodeName] = parseUnknown(self, data, nodeName, xmlName, 'ACTOR')

        nodeEntries.append(actorEntry)

    for dirlight in dirlights:
        state.rs3DirLightCount = state.rs3DirLightCount + 1
        dirlightEntry = { 'type': 'DIRLIGHT', 'name': state.rs3DirLightCount }

        for node, nodeName, data in filterNodes(dirlight.childNodes):
            if nodeName == 'COMMON':
                for child, childName, data in filterNodes(node.childNodes):
                    if childName in ('POSITION', 'DIRECTION', 'UP', 'SCALE'):
                        dirlightEntry[childName] = parseVec3(data, childName, state.convertUnits, False)
                    else:
                        dirlightEntry[childName] = parseUnknown(self, data, childName, xmlName, 'DIRLIGHT')
            elif nodeName == 'PROPERTY':
                for child, childName, data in filterNodes(node.childNodes):
                    if childName in ('SHADOWLUMINOSITY', 'POWER', 'SKYSPECULAR'):
                        dirlightEntry[childName] = float(data)
                    elif childName in ('AMBIENT', 'DIFFUSE', 'SPECULAR'):
                        dirlightEntry[childName] = tuple(float(s) for s in data.split(' '))
                    else:
                        dirlightEntry[childName] = parseUnknown(self, data, childName, xmlName, 'DIRLIGHT')
            else:
                dirlightEntry[nodeName] = parseUnknown(self, data, nodeName, xmlName, 'DIRLIGHT')

        nodeEntries.append(dirlightEntry)

    for spotlight in spotlights:
        state.rs3SpotLightCount = state.rs3SpotLightCount + 1
        spotlightEntry = { 'type': 'SPOTLIGHT', 'name': state.rs3SpotLightCount }

        for node, nodeName, data in filterNodes(spotlight.childNodes):
            if nodeName == 'COMMON':
                for child, childName, data in filterNodes(node.childNodes):
                    if childName in ('POSITION', 'DIRECTION', 'UP', 'SCALE'):
                        spotlightEntry[childName] = parseVec3(data, childName, state.convertUnits, False)
                    else:
                        spotlightEntry[childName] = parseUnknown(self, data, childName, xmlName, 'SPOTLIGHT')
            elif nodeName == 'PROPERTY':
                for child, childName, data in filterNodes(node.childNodes):
                    if childName == 'USERENDERMINAREA':
                        spotlightEntry[childName] = data.strip().lower() == 'true'
                    elif childName == 'FOV':
                        spotlightEntry[childName] = float(data)
                    elif childName in ('ATTENUATIONEND', 'ATTENUATIONSTART', 'INTENSITY', 'RENDERMINAREA'):
                        spotlightEntry[childName] = parseDistance(data, state.convertUnits)
                    elif childName == 'COLOR':
                        spotlightEntry[childName] = tuple(float(s) for s in data.split(' '))
                    else:
                        spotlightEntry[childName] = parseUnknown(self, data, childName, xmlName, 'SPOTLIGHT')
            else:
                spotlightEntry[nodeName] = parseUnknown(self, data, nodeName, xmlName, 'SPOTLIGHT')

        nodeEntries.append(spotlightEntry)

    for pointlight in pointlights:
        state.rs3PointLightCount = state.rs3PointLightCount + 1
        pointlightEntry = { 'type': 'POINTLIGHT', 'name': state.rs3PointLightCount }

        for node, nodeName, data in filterNodes(pointlight.childNodes):
            if nodeName == 'COMMON':
                for child, childName, data in filterNodes(node.childNodes):
                    if childName in ('POSITION', 'SCALE'):
                        pointlightEntry[childName] = parseVec3(data, childName, state.convertUnits, False)
                    elif childName not in ('DIRECTION', 'UP'):
                        pointlightEntry[childName] = parseUnknown(self, data, childName, xmlName, 'POINTLIGHT')
            elif nodeName == 'PROPERTY':
                for child, childName, data in filterNodes(node.childNodes):
                    if childName == 'INTENSITY':
                        pointlightEntry[childName] = float(data)
                    elif childName in ('ATTENUATIONEND', 'ATTENUATIONSTART'):
                        pointlightEntry[childName] = parseDistance(data, state.convertUnits)
                    elif childName in ('COLOR', 'AREARANGE'):
                        pointlightEntry[childName] = tuple(float(s) for s in data.split(' '))
                    elif childName != 'FOV':
                        pointlightEntry[childName] = parseUnknown(self, data, childName, xmlName, 'POINTLIGHT')
            else:
                pointlightEntry[nodeName] = parseUnknown(self, data, nodeName, xmlName, 'POINTLIGHT')

        nodeEntries.append(pointlightEntry)

    for effect in effects:
        state.rs3EffectCount = state.rs3EffectCount + 1
        effectEntry = { 'type': 'EFFECTINSTANCE', 'name': state.rs3EffectCount }

        for node, nodeName, data in filterNodes(effect.childNodes):
            if nodeName == 'COMMON':
                effectEntry['name'] = node.getAttribute('name')

                for child, childName, data in filterNodes(node.childNodes):
                    if childName in ('POSITION', 'DIRECTION', 'UP', 'SCALE'):
                        effectEntry[childName] = parseVec3(data, childName, state.convertUnits, False)
                    else:
                        effectEntry[childName] = parseUnknown(self, data, childName, xmlName, 'EFFECTINSTANCE')
            elif nodeName == 'PROPERTY':
                for child, childName, data in filterNodes(node.childNodes):
                    if childName == 'FILENAME':
                        if data is not None:
                            data = data.strip()

                        effectEntry['resourcename'] = data
                    else:
                        effectEntry[childName] = parseUnknown(self, data, childName, xmlName, 'EFFECTINSTANCE')
            elif nodeName not in ('SCENE', 'USER_PROPERTY'):
                effectEntry[nodeName] = parseUnknown(self, data, nodeName, xmlName, 'EFFECTINSTANCE')

        nodeEntries.append(effectEntry)

    for occluder in occluders:
        state.rs3OccluderCount = state.rs3OccluderCount + 1
        occluderEntry = { 'type': 'OCCLUDER', 'name': state.rs3OccluderCount }

        for node, nodeName, data in filterNodes(effect.childNodes):
            if nodeName == 'COMMON':
                for child, childName, data in filterNodes(node.childNodes):
                    if childName in ('POSITION', 'SCALE'):
                        occluderEntry[childName] = parseVec3(data, childName, state.convertUnits, False)
                    else:
                        occluderEntry[childName] = parseUnknown(self, data, childName, xmlName, 'OCCLUDER')
            elif nodeName == 'PROPERTY':
                for child, childName, data in filterNodes(node.childNodes):
                    if childName == 'LOCALSCALE':
                        occluderEntry[childName] = parseVec3(data, childName, state.convertUnits, False)
                    elif childName == 'OCCLUDERPOINT':
                        occluderEntry[childName] = []

                        for _, dataType, data in filterNodes(child.childNodes):
                            if dataType == 'P':
                                occluderEntry[childName].append(parseVec3(data, childName, state.convertUnits, False))
                    else:
                        occluderEntry[childName] = parseUnknown(self, data, childName, xmlName, 'OCCLUDER')
            else:
                occluderEntry[nodeName] = parseUnknown(self, data, nodeName, xmlName, 'OCCLUDER')

        nodeEntries.append(occluderEntry)

    return nodeEntries

def parsePropXML(self, xmlProp, xmlName, state):
    objects = xmlProp.getElementsByTagName('SCENEOBJECT')
    objectEntries = []

    if state.logSceneNodes and objects:
        print()
        print("=========  Prop.xml Nodes  =========")
        print()

    for object in objects:
        objectEntry = { 'type': 'SCENEOBJECT', 'name': None, 'resourcename': None }

        for node, nodeName, data in filterNodes(object.childNodes):
            if nodeName == 'COMMON':
                objectEntry['id'] = node.getAttribute('id')

                for child, childName, data in filterNodes(node.childNodes):
                    if childName in ('POSITION', 'DIRECTION', 'UP'):
                        if child.hasAttribute('x') and child.hasAttribute('y') and child.hasAttribute('z'):
                            objectEntry[childName] = parseXYZ(child, childName, state.convertUnits, False)
                    else:
                        objectEntry[childName] = parseUnknown(self, data, childName, xmlName, 'SCENEOBJECT')
            elif nodeName == 'PROPERTY':
                for child, childName, data in filterNodes(node.childNodes):
                    if childName in ('NAME', 'SceneFileName'):
                        if data is not None:
                            data = data.strip()

                        if childName == 'NAME': objectEntry['name'] = data
                        else: objectEntry['resourcename'] = data
                    elif childName not in ('Show', 'PartsColor', 'CameraCollision', 'UMBRAID'):
                        objectEntry[childName] = parseUnknown(self, data, childName, xmlName, 'SCENEOBJECT')
            elif nodeName != 'TOOL':
                objectEntry[nodeName] = parseUnknown(self, data, nodeName, xmlName, 'SCENEOBJECT')

        if state.logSceneNodes:
            print(f"Object: { objectEntry['id'] } { objectEntry['name'] }")
            print(f"Filename: { objectEntry['resourcename'] }")
            print("         Position:           ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*objectEntry['POSITION']))
            print("         Direction:          ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*objectEntry['DIRECTION']))
            print("         Up:                 ({:>6.03f}, {:>6.03f}, {:>6.03f})".format(*objectEntry['UP']))
            for k, v in objectEntry.items():
                if k not in ('type', 'id', 'name', 'resourcename', 'POSITION', 'DIRECTION', 'UP'):
                    print(f"        { k }: { v }")
            print()

        objectEntries.append(objectEntry)

    return objectEntries

def parseEluXML(self, xmlElu, state):
    materials = xmlElu.getElementsByTagName('MATERIAL')
    materialEntries = []

    if state.logEluMats:
        print()
        print("=========  Elu.xml Materials  =========")
        print()

    for material in materials:
        materialEntry = {
            'name': material.getAttribute('name'),
            'textures': [],
            'SPECULAR_LEVEL': 0.0,
            'GLOSSINESS': 0.0,
            'SELFILLUSIONSCALE': 1.0,
            'USEALPHATEST': False,
            'ALPHATESTVALUE': 128.0,
            'USEOPACITY': False,
            'ADDITIVE': False,
            'TWOSIDED': False
        }

        for node, nodeName, data in filterNodes(material.childNodes):
            if nodeName in ('SPECULAR_LEVEL', 'GLOSSINESS', 'SELFILLUSIONSCALE'):
                materialEntry[nodeName] = float(data)
            elif nodeName in ('DIFFUSE', 'AMBIENT', 'SPECULAR'):
                materialEntry[nodeName] = tuple(float(s) for s in data.split(' '))
            elif nodeName == 'TEXTURELIST':
                for layer, _, __ in filterNodes(node.childNodes):
                    for _, dataType, data in filterNodes(layer.childNodes):
                        if dataType in XMLELU_TEXTYPES:
                            if data is not None:
                                data = data.strip()

                                if data:
                                    data = os.path.normpath(data)
                            else:
                                data = ''

                            materialEntry['textures'].append({ 'type': dataType, 'name': data })
            elif nodeName == 'USEALPHATEST':
                materialEntry[nodeName] = True

                for value in node.childNodes:
                    if value.nodeType == value.ELEMENT_NODE and value.nodeName.strip() == 'ALPHATESTVALUE':
                        materialEntry['ALPHATESTVALUE'] = float(value.firstChild and value.firstChild.nodeValue)
            else:
                materialEntry[nodeName] = parseUnknown(self, data, nodeName, '.elu.xml', 'MATERIAL')

        if state.logEluMats:
            print(f"Material: { materialEntry['name'] }")
            print(f"        Diffuse:        { materialEntry['DIFFUSE'] }")
            print(f"        Ambient:        { materialEntry['AMBIENT'] }")
            if 'SPECULAR_LEVEL' in materialEntry:
                print(f"        Specular:       { materialEntry['SPECULAR'] } { materialEntry['SPECULAR_LEVEL'] }")
            else:
                print(f"        Specular:       { materialEntry['SPECULAR'] }")
            if 'GLOSSINESS' in materialEntry:
                print(f"        Glossiness:     { materialEntry['GLOSSINESS'] }")
            if 'SELFILLUSIONSCALE' in materialEntry:
                print(f"        Emission:       { materialEntry['SELFILLUSIONSCALE'] }")

            for texture in materialEntry['textures']:
                print(f"        { texture['type'] }: { texture['name'] }")

            if 'ALPHATESTVALUE' in materialEntry:
                print(f"        ALPHATESTVALUE: { materialEntry['ALPHATESTVALUE'] }")

            for k, v in materialEntry.items():
                if k not in ('type', 'name', 'textures', 'DIFFUSE', 'AMBIENT', 'SPECULAR', 'SPECULAR_LEVEL', 'GLOSSINESS', 'SELFILLUSIONSCALE', 'ALPHATESTVALUE'):
                    print(f"        { k }: { v }")
            print()

        materialEntries.append(materialEntry)

    return materialEntries
