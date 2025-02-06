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
import re as regex

from contextlib import redirect_stdout
from mathutils import Matrix

from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .parse_gzrs2 import *
from .readrs_gzrs2 import *
from .readelu_gzrs2 import *
from .lib_gzrs2 import *

def importRS3(self, context):
    state = GZRS2State()

    rs3DataDir = os.path.dirname(context.preferences.addons[__package__].preferences.rs3DataDir)

    if self.texSearchMode == 'PATH':
        if not rs3DataDir:
            self.report({ 'ERROR' }, f"GZRS2: Must specify a path to search for or select a different texture mode! Verify your path in the plugin's preferences!")
            return { 'CANCELLED' }

        if not matchRSDataDirectory(self, rs3DataDir, bpy.path.basename(rs3DataDir), True, state):
            self.report({ 'ERROR' }, f"GZRS2: Search path must point to a folder containing a valid data subdirectory! Verify your path in the plugin's preferences!")
            return { 'CANCELLED' }

        ensureRS3DataDict(self, state)
    else:
        ensureRS3DataDirectory(self, state)

    state.convertUnits      = self.convertUnits
    state.texSearchMode     = self.texSearchMode
    state.doCleanup         = self.doCleanup

    if self.panelLogging:
        print()
        print("=======================================================================")
        print("===========================  GZRS3 Import  ============================")
        print("=======================================================================")
        print(f"== { self.filepath }")
        print("=======================================================================")
        print()

        state.logSceneNodes         = self.logSceneNodes
        state.logEluHeaders         = self.logEluHeaders
        state.logEluMats            = self.logEluMats
        state.logEluMeshNodes       = self.logEluMeshNodes
        state.logVerboseIndices     = self.logVerboseIndices    and self.logEluMeshNodes
        state.logVerboseWeights     = self.logVerboseWeights    and self.logEluMeshNodes
        state.logCleanup            = self.logCleanup

    xmlpath = self.filepath
    state.directory = os.path.dirname(xmlpath)
    basename = bpy.path.basename(xmlpath)
    splitname = basename.split(os.extsep)
    state.filename = splitname[0]
    xmltype = splitname[-2].lower()

    if xmltype == 'scene':
        scenexmlpath = xmlpath

        for ext in XML_EXTENSIONS:
            propxmlpath = pathExists(f"{ state.directory }\\{ state.filename }{ os.extsep }prop{ os.extsep }{ ext }")
    elif xmltype == 'prop':
        propxmlpath = xmlpath

        for ext in XML_EXTENSIONS:
            scenexmlpath = pathExists(f"{ state.directory }\\{ state.filename }{ os.extsep }scene{ os.extsep }{ ext }")

    if scenexmlpath:
        with open(scenexmlpath, encoding = 'utf-8') as file:
            scenexmlstring = file.read()
            scenexmlstring = regex.sub(r"(<Umbra Synchronization[^>]+\/>)", '', scenexmlstring)
            scenexmlstring = scenexmlstring.replace("\"unreducible=true\"", "\" unreducible=true\"")

        state.rs3Graph.extend(parseSceneXML(self, minidom.parseString(scenexmlstring), state.filename, state))

    if propxmlpath:
        with open(propxmlpath, encoding = 'utf-8') as file:
            propxmlstring = file.read()
            propxmlstring = regex.sub(r"(<Umbra Synchronization[^>]+\/>)", '', propxmlstring)
            propxmlstring = propxmlstring.replace("\"unreducible=true\"", "\" unreducible=true\"")

        state.rs3Graph.extend(parsePropXML(self, minidom.parseString(propxmlstring), state.filename, state))

    elupaths = set()

    def openRS3Node(node):
        nodeType = node['type']

        if nodeType in ('SCENEINSTANCE', 'SCENEOBJECT', 'ACTOR'):
            resourcename = node['resourcename']

            resourcepath = resourceSearch(self, resourcename, state)
            if resourcepath is None: return

            if nodeType in ('SCENEINSTANCE', 'SCENEOBJECT'):
                if resourcepath.endswith('.elu'):
                    resourcebase = bpy.path.basename(resourcepath)

                    childnode = {
                        'type': 'ACTOR',
                        'name': resourcebase.split(os.extsep)[0],
                        'resourcename': resourcebase,
                        'parent': node
                    }
                    node['children'] = [childnode]

                    openRS3Node(childnode)
                else:
                    with open(resourcepath, encoding = 'utf-8') as file:
                        childstring = file.read()
                        childstring = regex.sub(r"(<Umbra Synchronization[^>]+\/>)", '', childstring)
                        childstring = childstring.replace("\"unreducible=true\"", "\" unreducible=true\"")

                    node['children'] = parseSceneXML(self, minidom.parseString(childstring), resourcename, state)

                    for childnode in node['children']:
                        childnode['parent'] = node

                        openRS3Node(childnode)
            elif nodeType in ('ACTOR'):
                # TODO: this should not be guaranteed here, see below
                node['elupath'] = resourcepath

                if resourcepath not in elupaths:
                    elupaths.add(resourcepath)

                    with open(resourcepath, 'rb') as file:
                        if readElu(self, file, resourcepath, state):
                            return { 'CANCELLED' }

                    # TODO: readElu needs to fail properly if the elu version is unsupported

                    for ext in XML_EXTENSIONS:
                        eluxmlpath = pathExists(f"{ resourcepath }{ os.extsep }{ ext }")

                        if eluxmlpath:
                            state.xmlEluMats[resourcepath] = parseEluXML(self, minidom.parse(eluxmlpath), state)
                            break

    for node in state.rs3Graph:
        openRS3Node(node)

    bpy.ops.ed.undo_push()
    collections = bpy.data.collections

    rootMap =                   collections.new(state.filename)
    rootActors =                collections.new(f"{ state.filename }_Actors")
    rootNodes =                 collections.new(f"{ state.filename }_Nodes")

    context.collection.children.link(rootMap)
    rootMap.children.link(rootActors)
    rootMap.children.link(rootNodes)

    setupEluMats(self, state)

    if state.xmlEluMats:
        for elupath, materials in state.xmlEluMats.items():
            for xmlEluMat in materials:
                setupXmlEluMat(self, elupath, xmlEluMat, state)

    if state.doCleanup and state.logCleanup:
        print()
        print("=== Actor Cleanup ===")
        print()

    for m, eluMesh in enumerate(state.eluMeshes):
        if eluMesh.elupath not in state.blActorRoots:
            blActorRoot = collections.new(f"{ eluMesh.meshName }_Actor")
            rootActors.children.link(blActorRoot)
            state.blActorRoots[eluMesh.elupath] = blActorRoot

            for viewLayer in context.scene.view_layers:
                lcRoot = lcFindRoot(viewLayer.layer_collection, rootActors)

                if lcRoot is None:
                    self.report({ 'WARNING' }, f"GZRS2: Unable to find root collection in view layer: { viewLayer }")
                    continue

                for lcChild in lcRoot.children:
                    if lcChild.collection is blActorRoot:
                        lcChild.hide_viewport = True
        else:
            blActorRoot = state.blActorRoots[eluMesh.elupath]

        setupElu(self, eluMesh, True, blActorRoot, context, state)

    processEluHeirarchy(self, state)

    def processRS3Node(node):
        nodeType = node['type']

        if nodeType in ('SCENEINSTANCE', 'SCENEOBJECT', 'EFFECTINSTANCE', 'DIRLIGHT', 'SPOTLIGHT', 'POINTLIGHT', 'OCCLUDER'):
            name = f"{ node.get('name', node.get('resourcename', 'Node')) }_{ nodeType }"

            if nodeType in ('SCENEINSTANCE', 'SCENEOBJECT', 'EFFECTINSTANCE'):
                blNodeObj = bpy.data.objects.new(name, None)
                blNodeObj.empty_display_type = 'ARROWS'
            elif nodeType in ('DIRLIGHT', 'SPOTLIGHT', 'POINTLIGHT'):
                if nodeType == 'DIRLIGHT':
                    blLight = bpy.data.lights.new(name, 'SUN')
                    blLight.color = node['DIFFUSE']
                    blLight.energy = node['POWER'] * 2 # calcLightEnergy()
                    # blLight.angle = math.radians(90 * node['SHADOWLUMINOSITY']) # TODO: Huh? What should be the sun angle?
                elif nodeType in ('SPOTLIGHT', 'POINTLIGHT'):
                    intensity = node['INTENSITY']
                    attStart = node['ATTENUATIONSTART']
                    attEnd = clampLightAttEnd(node['ATTENUATIONEND'], attStart)

                    if nodeType in ('SPOTLIGHT'):
                        # TODO: what does RENDERMINAREA do?
                        blLight = bpy.data.lights.new(name, 'SPOT')
                        blLight.spot_size = math.radians(node['FOV'])
                    if nodeType in ('POINTLIGHT'):
                        # TODO: does AREARANGE denote an area light?
                        blLight = bpy.data.lights.new(name, 'POINT')

                    blLight.color = node['COLOR']
                    blLight.energy = intensity * pow(attEnd, 2) * 2 # calcLightEnergy()
                    blLight.shadow_soft_size = (1 - calcLightSoftness(attStart, attEnd)) * pow(attEnd / 1000, 0.5) * 2 # calcLightSoftSize()

                blNodeObj = bpy.data.objects.new(name, blLight)
            elif nodeType in ('OCCLUDER'):
                # TODO: create mesh
                blNodeObj = bpy.data.objects.new(name, None)

            blNodeObj.location = node['POSITION']

            if nodeType in ('SCENEINSTANCE', 'SCENEOBJECT', 'EFFECTINSTANCE', 'DIRLIGHT', 'SPOTLIGHT'):
                dir = node['DIRECTION']
                up = node['UP']

                rot = Matrix((dir.cross(up), dir, up)).to_euler()
                rot.x = -rot.x
                rot.z = -rot.z

                blNodeObj.rotation_euler = rot

            if nodeType in ('SCENEINSTANCE', 'EFFECTINSTANCE'):
                blNodeObj.scale = node['SCALE']

            if 'parent' in node:
                blNodeObj.parent = node['parent']['blNodeObj']

            node['blNodeObj'] = blNodeObj

            rootNodes.objects.link(blNodeObj)

            if nodeType in ('DIRLIGHT', 'SPOTLIGHT', 'POINTLIGHT'):
                state.blLights.append(blLight)
            # elif nodeType in ('OCCLUDER'):
                # state.blSceneMeshes.append(blSceneMesh)

            state.blNodeObjs.append(blNodeObj)

            if 'children' in node:
                for childnode in node['children']:
                    processRS3Node(childnode)
        elif nodeType in ('ACTOR'):
            if 'parent' in node:
                blNodeObj = node['parent']['blNodeObj']
                blNodeObj.instance_type = 'COLLECTION'
                # TODO: KeyError if the .elu was an unsupported version
                blNodeObj.instance_collection = state.blActorRoots[node['elupath']]

    for node in state.rs3Graph:
        processRS3Node(node)

    counts = countInfoReports(context)
    bpy.ops.object.select_all(action = 'DESELECT')
    deleteInfoReports(context, counts)

    return { 'FINISHED' }
