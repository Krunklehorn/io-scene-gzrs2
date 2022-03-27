from collections import defaultdict
from mathutils import Vector

from . import minidom, constants_gzrs2
from .constants_gzrs2 import *

def parseRSXML(self, xmlRs, tagName):
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
            self.report({ 'ERROR' }, f"No rule for *.RS.xml element: { element }")
            break

        for node in element.childNodes:
            name = node.nodeName
            
            if node.nodeType == node.TEXT_NODE:
                continue
            elif node.nodeType == node.ELEMENT_NODE:
                data = node.firstChild and node.firstChild.nodeValue
                    
                if name in ['DIFFUSEMAP']:
                    entry[name] = data
                elif name in ['R', 'G', 'B']:
                    entry[name] = int(data)
                elif name in ['INTENSITY']:
                    entry[name] = float(data)
                elif name in ['ATTENUATIONSTART', 'ATTENUATIONEND', 'RADIUS']:
                    if self.convertUnits: entry[name] = float(data) * 0.01
                    else: entry[name] = float(data)
                elif name in ['DIFFUSE', 'AMBIENT', 'SPECULAR', 'COLOR']:
                    entry[name] = tuple(float(s) for s in data.split(' '))
                elif name in ['POSITION', 'DIRECTION', 'CENTER', 'MIN_POSITION', 'MAX_POSITION']:
                    vec = Vector((float(s) for s in data.split(' ')))
                    if self.convertUnits: vec *= 0.01
                    vec.y = -vec.y
                    
                    if tagName == 'OCCLUSION':
                        if entry[name] is False:
                            entry[name] = []
                        
                        entry[name].append(vec)
                    else:
                        entry[name] = vec
                else:
                    entry[name] = True
                    
                    if data: self.report({ 'INFO' }, f"No rule yet for tag found in *.RS.xml, it may contain useful data: { name }, { data }")
            else:
                self.report({ 'ERROR' }, f"No rule for *.RS.xml node type: { node.nodeType }")
                break

        list.append(entry)
    
    return list

def parseSpawnXML(self, xmlSpawn):
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
            
            for node in spawn.childNodes:
                name = node.nodeName
                
                if node.nodeType == node.TEXT_NODE:
                    continue
                elif node.nodeType == node.ELEMENT_NODE:
                    data = node.firstChild and node.firstChild.nodeValue
                    
                    if name in ['POSITION']:
                        vec = Vector((float(s) for s in data.split(' ')))
                        if self.convertUnits: vec *= 0.01
                        vec.y = -vec.y
                        
                        spawnEntry[name] = vec
                    else:
                        spawnEntry[name] = True
                        if data: self.report({ 'INFO' }, f"No rule yet for tag found in spawn.xml, it may contain useful data: { name }, { data }")
                else:
                    self.report({ 'ERROR' }, f"No rule for spawn.xml node type: { node.nodeType }")
                    break

            gametypeEntry['spawns'].append(spawnEntry)
        list.append(gametypeEntry)
    
    return list