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

import bpy, os, io, math, mathutils
import xml.dom.minidom as minidom
from mathutils import Vector, Matrix
import re as regex

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .parse_gzrs2 import *
from .readrs_gzrs2 import *
from .readelu_gzrs2 import *
from .lib_gzrs2 import *

def importRs3(self, context):
    state = GZRS2State()

    state.convertUnits = self.convertUnits
    state.doCleanup = self.doCleanup

    if self.panelLogging:
        print()
        print("=======================================================================")
        print("===========================  GZRS3 Import  ============================")
        print("=======================================================================")
        print(f"== { self.filepath }")
        print("=======================================================================")
        print()

        state.logSceneNodes = self.logSceneNodes
        state.logEluHeaders = self.logEluHeaders
        state.logEluMats = self.logEluMats
        state.logEluMeshNodes = self.logEluMeshNodes
        state.logVerboseIndices = self.logVerboseIndices
        state.logVerboseWeights = self.logVerboseWeights
        state.logCleanup = self.logCleanup

    xmlpath = self.filepath
    state.directory = os.path.dirname(xmlpath)
    splitname = os.path.basename(xmlpath).split(os.extsep)
    state.filename = splitname[0]
    xmltype = splitname[-2].lower()

    if xmltype == 'scene':
        scenexmlpath = xmlpath

        for ext in XML_EXTENSIONS:
            propxmlpath = pathExists(f"{ state.directory }\{ state.filename }.prop.{ ext }")
    elif xmltype == 'prop':
        propxmlpath = xmlpath

        for ext in XML_EXTENSIONS:
            scenexmlpath = pathExists(f"{ state.directory }\{ state.filename }.scene.{ ext }")

    if scenexmlpath:
        with open(scenexmlpath) as file:
            scenexmlstring = file.read()
            scenexmlstring = regex.sub(r"(<Umbra Synchronization[^>]+\/>)", '', scenexmlstring)

        state.rs3Graph.extend(parseSceneXML(self, minidom.parseString(scenexmlstring), state.filename, state))

    if propxmlpath:
        with open(propxmlpath) as file:
            propxmlstring = file.read()
            propxmlstring = regex.sub(r"(<Umbra Synchronization[^>]+\/>)", '', propxmlstring)

        state.rs3Graph.extend(parsePropXML(self, minidom.parseString(propxmlstring), state.filename, state))

    elupaths = set()

    def openRs3Node(node):
        if node['type'] in ['SCENEINSTANCE', 'SCENEOBJECT', 'ACTOR']:
            resourcename = node['resourcename']

            resourcepath = resourceSearch(self, resourcename, state)
            if resourcepath is None: return

            if node['type'] in ['SCENEINSTANCE', 'SCENEOBJECT']:
                if resourcepath.endswith('.elu'):
                    resourcebase = os.path.basename(resourcepath)

                    childnode = {
                        'type': 'ACTOR',
                        'name': resourcebase.split(os.extsep)[0],
                        'resourcename': resourcebase,
                        'parent': node
                    }
                    node['children'] = [childnode]

                    openRs3Node(childnode)
                else:
                    with open(resourcepath) as file:
                        childstring = file.read()
                        childstring = regex.sub(r"(<Umbra Synchronization[^>]+\/>)", '', childstring)

                    node['children'] = parseSceneXML(self, minidom.parseString(childstring), resourcename, state)

                    for childnode in node['children']:
                        childnode['parent'] = node

                        openRs3Node(childnode)
            elif node['type'] in ['ACTOR']:
                node['elupath'] = resourcepath

                if not resourcepath in elupaths:
                    elupaths.add(resourcepath)

                    readElu(self, resourcepath, state)

                    for ext in XML_EXTENSIONS:
                        eluxmlpath = pathExists(f"{ resourcepath }.{ ext }")

                        if eluxmlpath:
                            state.xmlEluMats[resourcepath] = parseEluXML(self, minidom.parse(eluxmlpath), state)
                            break

    for node in state.rs3Graph:
        openRs3Node(node)

    bpy.ops.ed.undo_push()
    collections = bpy.data.collections

    rootMap =                   collections.new(state.filename)
    rootActors =                collections.new(f"{ state.filename }_Actors")
    rootNodes =                 collections.new(f"{ state.filename }_Nodes")

    context.collection.children.link(rootMap)
    rootMap.children.link(rootActors)
    rootMap.children.link(rootNodes)

    setupErrorMat(state)

    for eluMat in state.eluMats:
        setupEluMat(self, eluMat, state)

    if state.xmlEluMats:
        for elupath, materials in state.xmlEluMats.items():
            for xmlEluMat in materials:
                setupXmlEluMat(self, elupath, xmlEluMat, state)

    if state.doCleanup and state.logCleanup:
        print()
        print("=== Actor Cleanup ===")
        print()

    for m, eluMesh in enumerate(state.eluMeshes):
        if not eluMesh.elupath in state.blActorRoots:
            blActorRoot = collections.new(f"{ state.filename }_Actor_{ eluMesh.meshName }")
            rootActors.children.link(blActorRoot)
            state.blActorRoots[eluMesh.elupath] = blActorRoot

            for viewLayer in context.scene.view_layers:
                lcRoot = lcFindRoot(viewLayer.layer_collection, rootActors)

                if lcRoot is not None:
                    for lcChild in lcRoot.children:
                        if lcChild.collection is blActorRoot:
                            lcChild.hide_viewport = True
                else:
                    self.report({ 'INFO' }, f"GZRS2: Unable to find root collection in view layer: { viewLayer }")
        else:
            blActorRoot = state.blActorRoots[eluMesh.elupath]

        setupElu(self, f"{ state.filename }_{ eluMesh.meshName }", eluMesh, True, blActorRoot, context, state)

    processEluHeirarchy(self, state)

    def processRs3Node(node):
        if node['type'] in ['SCENEINSTANCE', 'SCENEOBJECT', 'EFFECTINSTANCE', 'DIRLIGHT', 'SPOTLIGHT', 'POINTLIGHT', 'OCCLUDER']:
            name = f"{ state.filename }_{ node['type'] }_{ node.get('name', node.get('resourcename', 'Node')) }"

            if node['type'] in ['SCENEINSTANCE', 'SCENEOBJECT', 'EFFECTINSTANCE']:
                blNodeObj = bpy.data.objects.new(name, None)
                blNodeObj.empty_display_type = 'ARROWS'
            elif node['type'] in ['DIRLIGHT', 'SPOTLIGHT', 'POINTLIGHT']:
                if node['type'] in ['SPOTLIGHT']:
                    # TODO: what does RENDERMINAREA do?
                    softness = (node['ATTENUATIONEND'] - node['ATTENUATIONSTART']) / node['ATTENUATIONEND']
                    hardness = 0.001 / (1 - min(softness, 0.9999))

                    blLight = bpy.data.lights.new(name, 'SPOT')
                    blLight.color = node['COLOR']
                    blLight.energy = node['INTENSITY'] * pow(node['ATTENUATIONEND'], 2) * 10
                    blLight.shadow_soft_size = hardness * node['ATTENUATIONEND']
                    blLight.spot_size = math.radians(node['FOV'])
                elif node['type'] in ['DIRLIGHT']:
                    blLight = bpy.data.lights.new(name, 'SUN')
                    blLight.color = node['DIFFUSE']
                    blLight.energy = node['POWER'] * 100
                    blLight.angle = math.radians(90 * node['SHADOWLUMINOSITY'])
                elif node['type'] in ['POINTLIGHT']:
                    # TODO: does AREARANGE denote an area light?
                    softness = (node['ATTENUATIONEND'] - node['ATTENUATIONSTART']) / node['ATTENUATIONEND']
                    hardness = 0.001 / (1 - min(softness, 0.9999))

                    blLight = bpy.data.lights.new(name, 'POINT')
                    blLight.color = node['COLOR']
                    blLight.energy = node['INTENSITY'] * pow(node['ATTENUATIONEND'], 2) * 10
                    blLight.shadow_soft_size = hardness * node['ATTENUATIONEND']

                blNodeObj = bpy.data.objects.new(name, blLight)
            elif node['type'] in ['OCCLUDER']:
                # TODO: create mesh
                blNodeObj = bpy.data.objects.new(name, None)

            blNodeObj.location = node['POSITION']

            if node['type'] in ['SCENEINSTANCE', 'SCENEOBJECT', 'EFFECTINSTANCE', 'DIRLIGHT', 'SPOTLIGHT']:
                dir = node['DIRECTION']
                up = node['UP']

                rot = Matrix((dir.cross(up), dir, up)).to_euler()
                rot.x = -rot.x
                rot.z = -rot.z

                blNodeObj.rotation_euler = rot

            if node['type'] in ['SCENEINSTANCE', 'EFFECTINSTANCE']:
                blNodeObj.scale = node['SCALE']

            if 'parent' in node:
                blNodeObj.parent = node['parent']['blNodeObj']

            node['blNodeObj'] = blNodeObj

            rootNodes.objects.link(blNodeObj)

            if node['type'] in ['DIRLIGHT', 'SPOTLIGHT', 'POINTLIGHT']:
                state.blLights.append(blLight)
            # elif node['type'] in ['OCCLUDER']:
                # state.blMeshes.append(blMesh)

            state.blNodeObjs.append(blNodeObj)

            if 'children' in node:
                for childnode in node['children']:
                    processRs3Node(childnode)
        elif node['type'] in ['ACTOR']:
            if 'parent' in node:
                blNodeObj = node['parent']['blNodeObj']
                blNodeObj.instance_type = 'COLLECTION'
                blNodeObj.instance_collection = state.blActorRoots[node['elupath']]

    for node in state.rs3Graph:
        processRs3Node(node)

    bpy.ops.object.select_all(action = 'DESELECT')

    return { 'FINISHED' }
