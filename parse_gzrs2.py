import os
import xml.dom.minidom as minidom
from collections import defaultdict
from mathutils import Vector

from . import constants_gzrs2
from .constants_gzrs2 import *
from .classes_gzrs2 import *

def parseRsXML(self, xmlRs, tagName, state: GZRS2State):
    elements = xmlRs.getElementsByTagName(tagName)
    list = []

    for element in elements:
        entry = defaultdict(lambda: False)

        if element.hasAttribute('name'):
            entry['name'] = element.getAttribute('name')
        elif element.hasAttribute('ObjName'):
            entry['ObjName'] = element.getAttribute('ObjName')
            entry['type'] = element.getAttribute('type')
            entry['filename'] = element.getAttribute('filename')
        elif element.hasAttribute('min') or element.hasAttribute('max'):
            entry['min'] = int(element.getAttribute('min'))
            entry['max'] = int(element.getAttribute('max'))
        else:
            self.report({ 'ERROR' }, f"GZRS2: No rule for .rs.xml element: { element }")
            break

        for node in filter(lambda x: x.nodeType == x.ELEMENT_NODE, element.childNodes):
            name = node.nodeName
            data = node.firstChild and node.firstChild.nodeValue

            if name in ['DIFFUSEMAP']:
                if data is not None:
                    data = data.strip()

                    if data != '':
                        data = os.path.normpath(data)

                entry[name] = data
            elif name in ['R', 'G', 'B']:
                entry[name] = int(data)
            elif name in ['INTENSITY']:
                entry[name] = float(data)
            elif name in ['ATTENUATIONSTART', 'ATTENUATIONEND', 'RADIUS']:
                if state.convertUnits: entry[name] = float(data) * 0.01
                else: entry[name] = float(data)
            elif name in ['DIFFUSE', 'AMBIENT', 'SPECULAR', 'COLOR']:
                entry[name] = tuple(float(s) for s in data.split(' '))
            elif name in ['POSITION', 'DIRECTION', 'CENTER', 'MIN_POSITION', 'MAX_POSITION']:
                vec = Vector((float(s) for s in data.split(' ')))
                if state.convertUnits: vec *= 0.01
                vec.y = -vec.y

                if tagName == 'OCCLUSION':
                    if entry[name] is False:
                        entry[name] = []

                    entry[name].append(vec)
                else:
                    entry[name] = vec
            else:
                entry[name] = True
                if data: self.report({ 'INFO' }, f"GZRS2: No rule yet for tag found in .rs.xml, it may contain useful data: { name }, { data }")

        list.append(entry)

    return list

def parseEluXML(self, xmlElu, state: GZRS2State):
    materials = xmlElu.getElementsByTagName('MATERIAL')
    list = []

    if state.logEluMats:
        print()
        print("=========  Elu Xml Materials  =========")
        print()

    for material in materials:
        materialEntry = { 'name': material.getAttribute('name'), 'textures': [] }

        for node in filter(lambda x: x.nodeType == x.ELEMENT_NODE, material.childNodes):
            name = node.nodeName
            data = node.firstChild and node.firstChild.nodeValue

            if name in ['SPECULAR_LEVEL', 'GLOSSINESS', 'SELFILLUSIONSCALE']:
                materialEntry[name] = float(data)
            elif name in ['DIFFUSE', 'AMBIENT', 'SPECULAR']:
                materialEntry[name] = tuple(float(s) for s in data.split(' '))
            elif name in ['TEXTURELIST']:
                for layer in filter(lambda x: x.nodeType == x.ELEMENT_NODE, node.childNodes):
                    for map in filter(lambda x: x.nodeType == x.ELEMENT_NODE, layer.childNodes):
                        if map.nodeName in ['DIFFUSEMAP', 'SPECULARMAP', 'SELFILLUMINATIONMAP', 'OPACITYMAP', 'NORMALMAP']:
                            data = map.firstChild and map.firstChild.nodeValue

                            if data is not None:
                                data = data.strip()

                                if data != '':
                                    data = os.path.normpath(data)

                            materialEntry['textures'].append({ 'type':map.nodeName, 'name':data })
            elif name in ['USEALPHATEST']:
                for value in node.childNodes:
                    if value.nodeType == value.ELEMENT_NODE and value.nodeName == 'ALPHATESTVALUE':
                        data = value.firstChild and value.firstChild.nodeValue
                        materialEntry['ALPHATESTVALUE'] = float(data)
            else:
                materialEntry[name] = True
                if data: self.report({ 'INFO' }, f"GZRS2: No rule yet for tag found in .elu.xml, it may contain useful data: { name }, { data }")

        list.append(materialEntry)

        if state.logEluMats:
            print(f"Material: { materialEntry['name'] }")
            print(f"        Diffuse: { materialEntry['DIFFUSE'] }")
            print(f"        Ambient: { materialEntry['AMBIENT'] }")
            print(f"        Specular: { materialEntry['SPECULAR'] } { materialEntry['SPECULAR_LEVEL'] if 'SPECULAR_LEVEL' in materialEntry else '' }")
            if 'GLOSSINESS' in materialEntry: print(f"        Glossiness: { materialEntry['GLOSSINESS'] }")
            if 'SELFILLUSIONSCALE' in materialEntry: print(f"        Emission: { materialEntry['SELFILLUSIONSCALE'] }")

            for texture in materialEntry['textures']:
                print(f"        { texture['type'] }: { texture['name'] }")

            if 'ALPHATESTVALUE' in materialEntry:
                print(f"        ALPHATESTVALUE: { materialEntry['ALPHATESTVALUE'] }")
            print()

    return list

def parseSpawnXML(self, xmlSpawn, state: GZRS2State):
    gametypes = xmlSpawn.getElementsByTagName('GAMETYPE')
    list = []

    for gametype in gametypes:
        id = gametype.getAttribute('id')
        gametypeEntry = { 'id': id, 'spawns': [] }
        spawns = gametype.getElementsByTagName('SPAWN')

        for spawn in spawns:
            spawnEntry = defaultdict(lambda: False)
            spawnEntry['item'] = spawn.getAttribute('item')
            spawnEntry['timesec'] = int(spawn.getAttribute('timesec'))

            for node in filter(lambda x: x.nodeType == x.ELEMENT_NODE, spawn.childNodes):
                name = node.nodeName
                data = node.firstChild and node.firstChild.nodeValue

                if name in ['POSITION']:
                    vec = Vector((float(s) for s in data.split(' ')))
                    if state.convertUnits: vec *= 0.01
                    vec.y = -vec.y

                    spawnEntry[name] = vec
                else:
                    spawnEntry[name] = True
                    if data: self.report({ 'INFO' }, f"GZRS2: No rule yet for tag found in spawn.xml, it may contain useful data: { name }, { data }")

            gametypeEntry['spawns'].append(spawnEntry)

        list.append(gametypeEntry)

    return list

'''
class testSelf:
    convertUnits = False
    logEluHeaders = True
    logEluMats = True
    logEluMeshNodes = True

    def report(self, t, s):
        print(s)

testPaths = {
    # 'ELU_0': "..\\..\\GunZ\\clean\\Model\\weapon\\blade\\blade_2011_4lv.elu.xml"
    # 'ELU_5004': "..\\..\\GunZ\\clean\\Model\\weapon\\rocketlauncher\\rocket.elu.xml"
    # 'ELU_5005': "..\\..\\GunZ\\clean\\Model\\weapon\\dagger\\dagger04.elu.xml"
    # 'ELU_5006': "..\\..\\GunZ\\clean\\Model\\weapon\\katana\\katana10.elu.xml"
    # 'ELU_5007': "..\\..\\GunZ\\clean\\Model\\weapon\\blade\\blade07.elu.xml"

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

    for m, material in enumerate(parseEluXML(testSelf(), minidom.parse(path))):
        print(f"Name: { material['name'] }")
        print(f"    Diffuse: { material['DIFFUSE'] }")
        print(f"    Ambient: { material['AMBIENT'] }")
        print(f"    Specular: { material['SPECULAR'] } { material['SPECULAR_LEVEL'] if 'SPECULAR_LEVEL' in material else '' }")
        if 'GLOSSINESS' in material: print(f"    Glossiness: { material['GLOSSINESS'] }")
        if 'SELFILLUSIONSCALE' in material: print(f"    Emission: { material['SELFILLUSIONSCALE'] }")

        for m, map in enumerate(material['textures']):
            print(f"    { map['type'] }: { map['name'] }")

        if 'ALPHATESTVALUE' in material:
            print(f"    ALPHATESTVALUE: { material['ALPHATESTVALUE'] }")
        print()
'''
