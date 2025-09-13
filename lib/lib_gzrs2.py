import bpy, os, math, random, ctypes, shutil

from ctypes import *

from contextlib import redirect_stdout
from mathutils import Vector, Matrix, Euler

from ..constants_gzrs2 import *
from ..classes_gzrs2 import *
from ..io_gzrs2 import *

def getOrNone(list, i):
    try:        return list[i]
    except:     return None

def indexOrNone(list, i):
    try:        return list.index(i)
    except:     return None

def dataOrFirst(list, i, o):
    try:        return list[i][o]
    except:     return list[0][o]

def enumTagToIndex(self, tag, items):
    for i, item in enumerate(items):
        if item[0] == tag:
            return i

    print(f"GZRS2: Failed to get index for enum tag: { tag }")

    return 0

def enumIndexToTag(index, items):
    return items[index][0]

def ensureWorld(context):
    scene = context.scene
    world = scene.world

    if world is None:
        if len(bpy.data.worlds) > 0:    bpy.data.worlds[0]
        else:                           bpy.data.worlds.new()

        scene.world = world

    return world

def eulerSnapped(angles):
    angles = angles.copy()

    angles.x = round(angles.x / PI_OVER_2) * PI_OVER_2
    angles.y = round(angles.y / PI_OVER_2) * PI_OVER_2
    angles.z = round(angles.z / PI_OVER_2) * PI_OVER_2

    return angles

def vecArrayMinMax(vectors, size):
    minLen2 = float('inf')
    maxLen2 = float('-inf')
    minVector = tuple(minLen2 for _ in range(size))
    maxVector = tuple(maxLen2 for _ in range(size))

    for vector in vectors:
        len2 = sum(vector[s] ** 2 for s in range(size))

        if len2 < minLen2:
            minLen2 = len2
            minVector = vector

        if len2 > maxLen2:
            maxLen2 = len2
            maxVector = vector

    return *minVector, *maxVector

def calcCoordinateBounds(coords):
    minX = float('inf')
    minY = float('inf')
    minZ = float('inf')
    maxX = float('-inf')
    maxY = float('-inf')
    maxZ = float('-inf')

    for coord in coords:
        minX = min(minX, coord.x)
        minY = min(minY, coord.y)
        minZ = min(minZ, coord.z)
        maxX = max(maxX, coord.x)
        maxY = max(maxY, coord.y)
        maxZ = max(maxZ, coord.z)

    return Vector((minX, minY, minZ)), Vector((maxX, maxY, maxZ))

def calcPolygonBounds(polygons):
    return calcCoordinateBounds(tuple(vertex.pos for polygon in polygons for vertex in polygon.vertices))

def vec3IsClose(v1, v2, threshold):
    return all((math.isclose(v1.x, v2.x, abs_tol = threshold),
                math.isclose(v1.y, v2.y, abs_tol = threshold),
                math.isclose(v1.z, v2.z, abs_tol = threshold)))

def vec4IsClose(v1, v2, threshold):
    return all((math.isclose(v1.x, v2.x, abs_tol = threshold),
                math.isclose(v1.y, v2.y, abs_tol = threshold),
                math.isclose(v1.z, v2.z, abs_tol = threshold),
                math.isclose(v1.w, v2.w, abs_tol = threshold)))

def pathExists(path):
    if os.path.exists(path): return path
    elif path == '': return False
    elif os.name != 'nt':
        path = os.path.normpath(path.lower())
        targets = iter(path[1:].split(os.sep))
        current = os.sep + next(targets)
        target = next(targets)

        while target is not None:
            _, dirnames, filenames = next(os.walk(current))

            if os.path.splitext(target)[1] == '':
                found = False

                for dirname in dirnames:
                    if dirname.lower() == target:
                        current = os.path.join(current, dirname)
                        found = True
                        break

                if found: target = next(targets)
                else: return False
            else:
                for filename in filenames:
                    if filename.lower() == target:
                        current = os.path.join(current, filename)
                        return current

                return False

        return current

def isValidTexBase(texBase):
    if texBase.endswith(os.sep):                return False
    elif os.path.splitext(texBase)[1] == '':    return False

    return True

def texMatchDownward(root, texBase, ddsBase):
    matchBases = [texBase.lower(), ddsBase.lower()]

    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if filename.lower() in matchBases:
                return os.path.join(dirpath, filename)

def matchRSDataDirectory(self, dirpath, dirbase, isRS3, state):
    if dirpath == '' or not os.path.exists(dirpath) or not os.path.isdir(dirpath):
        return False

    if dirbase == '':
        return False

    _, dirnames, _ = next(os.walk(dirpath))

    for token in RS3_VALID_DATA_SUBDIRS if isRS3 else RS2_VALID_DATA_SUBDIRS:
        if token.lower() == dirbase.lower():
            if isRS3:   state.rs3DataDir = os.path.dirname(dirpath)
            else:       state.rs2DataDir = os.path.dirname(dirpath)

            return True

        for dirname in dirnames:
            if token.lower() == dirname.lower():
                if isRS3:   state.rs3DataDir = dirpath
                else:       state.rs2DataDir = dirpath
                
                return True

    return False

def ensureRS3DataDict(self, state):
    if len(state.rs3DataDict) > 0: return

    for dirpath, _, filenames in os.walk(state.rs3DataDir):
        for filename in filenames:
            if os.path.splitext(filename)[-1].split(os.extsep)[-1].lower() in RS3_DATA_DICT_EXTENSIONS:
                resourcepath = pathExists(os.path.join(dirpath, filename))

                if not resourcepath:
                    self.report({ 'ERROR' }, f"GZRS2: Resource found but pathExists() failed, potential case sensitivity issue: { filename }")
                    return

                state.rs3DataDict[filename.lower()] = resourcepath

def ensureRS3DataDirectory(self, state):
    if state.rs3DataDir: return

    currentDir = state.directory

    for _ in range(RES_UPWARD_SEARCH_LIMIT):
        _, dirnames, _ = next(os.walk(currentDir))

        for dirname in dirnames:
            if dirname.lower() in RS3_VALID_DATA_SUBDIRS_LOWER:
                state.rs3DataDir = os.path.join(currentDir, dirname)
                break

        currentDir = os.path.dirname(currentDir)

    if not state.rs3DataDir:
        self.report({ 'ERROR' }, f"GZRS2: Failed to find RS3 data directory!")
        return

    ensureRS3DataDict(self, state)

def textureSearch(self, texBase, texDir, isRS3, state):
    if texBase == None:
        self.report({ 'WARNING' }, f"GZRS2: Texture search attempted with no texture name: { texBase }")
        return

    if texBase == '':
        self.report({ 'WARNING' }, f"GZRS2: Texture search attempted with an empty texture name: { texBase }")
        return

    if not isValidTexBase(texBase):
        self.report({ 'WARNING' }, f"GZRS2: Texture search attempted with an invalid texture name: { texBase }")
        return

    ddsBase = f"{ texBase }{ os.extsep }dds".replace(os.extsep + 'dds' + os.extsep + 'dds', os.extsep + 'dds')

    if isRS3:
        ensureRS3DataDict(self, state)

        result = state.rs3DataDict.get(texBase.lower())
        if result: return result

        result = state.rs3DataDict.get(ddsBase.lower())
        if result: return result

        self.report({ 'WARNING' }, f"GZRS2: Texture search failed, no entry in data dictionary: { texBase }")

    if texDir != '':
        # Check the local folder
        result = pathExists(os.path.join(state.directory, texBase))
        if result: return result

        result = pathExists(os.path.join(state.directory, ddsBase))
        if result: return result

        # Check a specific sub-folder relative to the local one
        result = pathExists(os.path.join(state.directory, texDir, texBase))
        if result: return result

        result = pathExists(os.path.join(state.directory, texDir, ddsBase))
        if result: return result

        if self.texSearchMode == 'PATH':
            dataDir = state.rs3DataDir if isRS3 else state.rs2DataDir

            # Check a specific sub-folder relative to the data folder
            result = pathExists(os.path.join(dataDir, texDir, texBase))
            if result: return result

            result = pathExists(os.path.join(dataDir, texDir, ddsBase))
            if result: return result
        elif self.texSearchMode == 'BRUTE':
            parentDir = os.path.dirname(state.directory)
            targetname = texDir.split(os.sep)[0]

            # This isn't too bad, it only checks directory names
            for _ in range(TEX_UPWARD_SEARCH_LIMIT):
                _, dirnames, _ = next(os.walk(parentDir))

                for dirname in dirnames:
                    if dirname.lower() == targetname.lower():
                        # Check a specific sub-folder relative to the parent folder
                        result = pathExists(os.path.join(parentDir, texDir, texBase))
                        if result: return result

                        result = pathExists(os.path.join(parentDir, texDir, ddsBase))
                        if result: return result

                parentDir = os.path.dirname(parentDir)

            self.report({ 'WARNING' }, f"GZRS2: Texture search failed, no upward directory match: { texDir }, { texBase }")
    else:
        # Check the local folder and all sub-folders
        result = texMatchDownward(state.directory, texBase, ddsBase)
        if result: return result

        if self.texSearchMode == 'PATH':
            # Check the data folder and all sub-folders
            result = texMatchDownward(state.rs3DataDir if isRS3 else state.rs2DataDir, texBase, ddsBase)
            if result: return result
        elif self.texSearchMode == 'BRUTE':
            parentDir = os.path.dirname(state.directory)

            # This is incredibly inefficient, it checks ALL directories and ALL files
            # We could improve this with downward search caching and early exits for known system folders
            # Both of those depend on the operating system so screw it
            for _ in range(TEX_UPWARD_SEARCH_LIMIT):
                # Check the parent folder and all sub-folders
                result = texMatchDownward(parentDir, texBase, ddsBase)
                if result: return result

                parentDir = os.path.dirname(parentDir)

            self.report({ 'WARNING' }, f"GZRS2: Texture search failed, no upward file match: { texBase }")

def textureSearchLoadFake(self, texBase, texDir, isRS3, state):
    if state.texSearchMode == 'SKIP':
        return True, texBase, True

    texpath = textureSearch(self, texBase, texDir, isRS3, state)

    if texpath is None:
        return False, texBase, True

    texpath = bpy.path.abspath(texpath)

    return True, texpath, False

def resourceSearch(self, resourcename, state):
    result = pathExists(os.path.join(state.directory, resourcename))
    if result: return result

    ensureRS3DataDirectory(self, state)

    result = state.rs3DataDict.get(resourcename.lower())
    if result: return result

    splitname = resourcename.split(os.extsep)

    if splitname[-1].lower() == 'xml' and splitname[-2].lower() in ('scene', 'prop'):
        eluname = f"{ splitname[0] }{ os.extsep }elu"

        result = state.rs3DataDict.get(eluname.lower())
        if result:
            self.report({ 'WARNING' }, f"GZRS2: Resource found after missing scene.xml or prop.xml: { resourcename }, { eluname }")
            return result

    self.report({ 'ERROR' }, f"GZRS2: Resource search failed: { resourcename }")

def lcFindRoot(lc, collection):
    if lc.collection is collection: return lc
    elif len(lc.children) == 0: return

    for child in lc.children:
        next = lcFindRoot(child, collection)

        if next is not None:
            return next

def getTexImage(bpy, texpath, alphamode, state):
    texImages = state.blTexImages.setdefault(texpath, {})

    if alphamode not in texImages:
        image = bpy.data.images.load(texpath)
        image.alpha_mode = alphamode
        texImages[alphamode] = image

    return texImages[alphamode]

def getShaderNodeByID(nodes, id, *, blacklist = ()):
    for node in nodes:
        if node.bl_idname == id and node not in blacklist:
            return node

def getRelevantShaderNodes(nodes):
    group = ensureLmMixGroup()

    shader          = getShaderNodeByID(nodes, 'ShaderNodeBsdfPrincipled')
    output          = getShaderNodeByID(nodes, 'ShaderNodeOutputMaterial')
    info            = getShaderNodeByID(nodes, 'ShaderNodeObjectInfo')
    transparent     = getShaderNodeByID(nodes, 'ShaderNodeBsdfTransparent')
    mix             = getShaderNodeByID(nodes, 'ShaderNodeMixShader')
    clip            = getShaderNodeByID(nodes, 'ShaderNodeMath')
    add             = getShaderNodeByID(nodes, 'ShaderNodeAddShader')
    lightmix        = getShaderNodeByID(nodes, 'ShaderNodeGroup')

    for node in nodes:
        if node.bl_idname == 'ShaderNodeMath' and node.operation == 'GREATER_THAN':
            clip = node
        elif node.bl_idname == 'ShaderNodeGroup' and node.node_tree == group:
            lightmix = node

    return shader, output, info, transparent, mix, clip, add, lightmix

def checkShaderNodeValidity(shader, output, info, transparent, mix, clip, add, lightmix, links):
    shaderValid         = False if shader           and mix                             else None
    infoValid           = False if info             and mix                             else None
    transparentValid    = False if transparent      and mix                             else None
    mixValid            = False if mix              and output                          else None
    clipValid           = False if clip             and shader                          else None
    addValid            = False if add              and shader and transparent and mix  else None
    addValid1           = False if add              and shader                          else None
    addValid2           = False if add              and transparent                     else None
    addValid3           = False if add              and mix                             else None
    lightmixValid       = False if lightmix         and shader                          else None

    for link in links:
        if link.is_hidden or not link.is_valid:
            continue

        if      shaderValid         == False    and link.from_socket == shader.outputs[0]       and link.to_socket == mix.inputs[2]:        shaderValid         = True
        elif    infoValid           == False    and link.from_socket == info.outputs[2]         and link.to_socket == mix.inputs[0]:        infoValid           = True
        elif    transparentValid    == False    and link.from_socket == transparent.outputs[0]  and link.to_socket == mix.inputs[1]:        transparentValid    = True
        elif    mixValid            == False    and link.from_socket == mix.outputs[0]          and link.to_socket == output.inputs[0]:     mixValid            = True
        elif    clipValid           == False    and link.from_socket == clip.outputs[0]         and link.to_socket == shader.inputs[4]:     clipValid           = True
        elif    addValid1           == False    and link.from_socket == shader.outputs[0]       and link.to_socket == add.inputs[0]:        addValid1           = True
        elif    addValid2           == False    and link.from_socket == transparent.outputs[0]  and link.to_socket == add.inputs[1]:        addValid2           = True
        elif    addValid3           == False    and link.from_socket == add.outputs[0]          and link.to_socket == mix.inputs[2]:        addValid3           = True
        elif    lightmixValid       == False    and link.from_socket == lightmix.outputs[0]     and link.to_socket == shader.inputs[0]:     lightmixValid       = True

    if clipValid and clip.operation != 'GREATER_THAN':
        clipValid = False

    if addValid == False and addValid1 == True and addValid2 == True and addValid3 == True:
        addValid = True

    for link in links:
        if link.is_hidden or not link.is_valid:
            continue

        if addValid                             and link.from_socket == add.outputs[0]          and link.to_socket == mix.inputs[2]:        shaderValid         = True

    return shaderValid, infoValid, transparentValid, mixValid, clipValid, addValid, lightmixValid

def getLinkedImageNodes(shader, shaderValid, links, clip, clipValid, lightmix, lightmixValid, *, validOnly = True):
    texture = None
    emission = None
    alpha = None
    lightmap = None

    for link in links:
        node = link.from_node

        if node.bl_idname != 'ShaderNodeTexImage':          continue
        if validOnly and not isValidEluImageNode(node):     continue
        if link.is_hidden or not link.is_valid:             continue

        if shaderValid and link.to_node == shader:
            if link.from_socket == node.outputs[0] and link.to_socket == shader.inputs[0]:      texture     = node
            if link.from_socket == node.outputs[0] and link.to_socket == shader.inputs[26]:     emission    = node
            if link.from_socket == node.outputs[1] and link.to_socket == shader.inputs[4]:      alpha       = node
        elif clipValid and link.to_node == clip:
            if link.from_socket == node.outputs[1] and link.to_socket == clip.inputs[0]:        alpha       = node
        elif lightmixValid and link.to_node == lightmix:
            if link.from_socket == node.outputs[0] and link.to_socket == lightmix.inputs[0]:    texture     = node
            if link.from_socket == node.outputs[0] and link.to_socket == lightmix.inputs[1]:    lightmap    = node

    return texture, emission, alpha, lightmap

def getModifierByType(self, modifiers, type):
    for modifier in modifiers:
        if modifier.type == type:
            return modifier

def getValidArmature(self, object, state):
    if object is None:
        return None, None

    modifier = getModifierByType(self, object.modifiers, 'ARMATURE')

    if modifier is None:
        return None, None

    modObj = modifier.object

    if modObj is None or modObj.type != 'ARMATURE':
        return None, None

    return modObj, modObj.data

def getEluExportConstants():
    version = ELU_5007
    maxPathLength = ELU_NAME_LENGTH if version <= ELU_5005 else ELU_PATH_LENGTH

    return version, maxPathLength

def getMatTreeLinksNodes(blMat):
    tree = blMat.node_tree
    links = tree.links
    nodes = tree.nodes

    return tree, links, nodes

def getMatImageTextureNode(bpy, blMat, nodes, texpath, alphamode, x, y, loadFake, state):
    if texpath is None or loadFake:
        texture = nodes.new('ShaderNodeTexImage')

        if loadFake:
            texture.image = bpy.data.images.new(texpath, 0, 0)
            texture.image.filepath = texture.image.filepath_raw = '//' + texpath
            texture.image.source = 'FILE'
            texture.image.alpha_mode = alphamode

        texture.location = (x, y)
        texture.select = False

        return texture

    matNodes = state.blMatNodes.setdefault(blMat, {})
    haveTexture = texpath in matNodes
    haveAlphaMode = haveTexture and alphamode in matNodes[texpath]

    if not haveTexture or not haveAlphaMode:
        texture = nodes.new('ShaderNodeTexImage')
        texture.image = getTexImage(bpy, texpath, alphamode, state)
        texture.location = (x, y)
        texture.select = False

        if not haveTexture:
            matNodes[texpath] = { alphamode: texture }
        elif not haveAlphaMode:
            matNodes[texpath][alphamode] = texture

    return matNodes[texpath][alphamode]

def getMatFlagsRender(blMat, clip, addValid, clipValid, emission, alpha):
    twosided = not blMat.use_backface_culling
    additive = blMat.surface_render_method == 'BLENDED' and addValid and emission is not None
    alphatest = int(min(max(0, clip.inputs[1].default_value), 1) * 255) if clipValid else 0 # Threshold
    usealphatest = alphatest > 0
    useopacity = alpha is not None

    return twosided, additive, alphatest, usealphatest, useopacity

def decomposePath(path):
    if not path:
        return None, None, None, None

    basename = bpy.path.basename(path)
    filename, extension = os.path.splitext(basename)
    directory = os.path.dirname(path)

    return basename, filename, extension, directory

def checkIsAniTex(texName):
    return False if texName is None else texName.lower().startswith('txa')

def isChildProp(blMeshObj):
    if      blMeshObj.parent is None:                           return False
    elif    blMeshObj.parent.type != 'MESH':                    return False
    elif    blMeshObj.parent.data is None:                      return False
    elif    blMeshObj.parent.data.gzrs2.meshType == 'PROP':     return True

    return isChildProp(blMeshObj.parent)

def processAniTexParameters(isAniTex, texName, *, silent = False):
    if not isAniTex:
        return True, None, None, None

    # texNameStart = texName[-2:]
    texNameShort = texName[:-2]
    texParams = texNameShort.replace('_', ' ').split(' ')

    if len(texParams) < 4:
        if not silent:
            self.report({ 'ERROR' }, f"GZRS2: Unable to split animated texture name! { texNameShort }, { texParams } ")
        return False, None, None, None

    try:
        frameCount, frameSpeed = int(texParams[1]), int(texParams[2])
    except ValueError:
        if not silent:
            self.report({ 'ERROR' }, f"GZRS2: Animated texture name must use integers for frame count and speed! { texNameShort } ")
        return False, None, None, None
    else:
        frameGap = frameSpeed / frameCount

    return True, frameCount, frameSpeed, frameGap

def setMatFlagsTransparency(blMat, transparent, *, twosided = False):
    blMat.use_transparent_shadow = True # Settings
    blMat.use_transparency_overlap = True # Viewport Display

    # Viewport Display
    if transparent:
        blMat.use_backface_culling = False
        blMat.use_backface_culling_shadow = False
        blMat.use_backface_culling_lightprobe_volume = False
    else:
        blMat.use_backface_culling = not twosided
        blMat.use_backface_culling_shadow = not twosided
        blMat.use_backface_culling_lightprobe_volume = not twosided

def setupMatBase(name, *, blMat = None, shader = None, output = None, info = None, transparent = None, mix = None):
    blMat = blMat or bpy.data.materials.new(name)
    blMat.use_nodes = True
    blMat.surface_render_method = 'DITHERED'

    tree, links, nodes = getMatTreeLinksNodes(blMat)

    shader = shader or getShaderNodeByID(nodes, 'ShaderNodeBsdfPrincipled') or nodes.new('ShaderNodeBsdfPrincipled')
    shader.location = (20, 300)
    shader.select = False

    shader.inputs[12].default_value = 0.0 # Specular IOR Level
    shader.inputs[27].default_value = 0.0 # Emission Strength

    output = output or getShaderNodeByID(nodes, 'ShaderNodeOutputMaterial') or nodes.new('ShaderNodeOutputMaterial')
    output.location = (300, 300)
    output.select = False

    setMatFlagsTransparency(blMat, False)

    info = info or nodes.new('ShaderNodeObjectInfo')
    info.location = (120, 480)
    info.select = False

    transparent = transparent or nodes.new('ShaderNodeBsdfTransparent')
    transparent.location = (120, -40)
    transparent.select = False

    mix = mix or nodes.new('ShaderNodeMixShader')
    mix.location = (300, 140)
    mix.select = False

    mix.inputs[0].default_value = 1.0 # Factor

    links.new(info.outputs[2], mix.inputs[0])
    links.new(transparent.outputs[0], mix.inputs[1])
    links.new(shader.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], output.inputs[0])

    return blMat, tree, links, nodes, shader, output, info, transparent, mix

def setupMatNodesLightmap(blMat, tree, links, nodes, shader, *, lightmap = None, uvmap = None, lightmix = None, image = None):
    lightmap = lightmap or nodes.new('ShaderNodeTexImage')
    uvmap = uvmap or getShaderNodeByID(nodes, 'ShaderNodeUVMap') or nodes.new('ShaderNodeUVMap')
    lightmix = lightmix or nodes.new('ShaderNodeGroup')

    lightmap.image = image or lightmap.image
    uvmap.uv_map = 'UVMap.001'
    lightmix.node_tree = ensureLmMixGroup()

    lightmap.location = (-440, -20)
    uvmap.location = (-640, -20)
    lightmix.location = (-160, 300)

    lightmap.select = False
    uvmap.select = False
    lightmix.select = False

    links.new(lightmap.outputs[0], lightmix.inputs[1])
    links.new(uvmap.outputs[0], lightmap.inputs[0])
    links.new(lightmix.outputs[0], shader.inputs[0]) # Base Color

    return lightmap, uvmap, lightmix, lightmap.image

def setupMatNodesTransparency(blMat, tree, links, nodes, alphatest, usealphatest, useopacity, source, destination, *, clip = False):
    if usealphatest:
        blMat.surface_render_method = 'DITHERED'

        clip = clip or nodes.new('ShaderNodeMath')
        clip.operation = 'GREATER_THAN'
        clip.location = (-160, 160)
        clip.select = False

        links.new(source.outputs[1], clip.inputs[0])
        links.new(clip.outputs[0], destination.inputs[4]) # Alpha

        clip.inputs[1].default_value = alphatest / 255.0

        return clip
    elif useopacity:
        blMat.surface_render_method = 'DITHERED'

        links.new(source.outputs[1], destination.inputs[4]) # Alpha

def setupMatNodesAdditive(blMat, tree, links, nodes, additive, source, destination, transparent, mix, *, add = None):
    if not additive:
        return

    blMat.surface_render_method = 'BLENDED'

    add = add or nodes.new('ShaderNodeAddShader')
    add.location = (300, 0)
    add.select = False

    if source:
        fakeEmission = blMat.gzrs2.fakeEmission

        links.new(source.outputs[0], destination.inputs[26]) # Emission Color
        destination.inputs[27].default_value = fakeEmission if fakeEmission > 0.0 else 1.0 # Emission Strength

    links.new(destination.outputs[0], add.inputs[0])
    links.new(transparent.outputs[0], add.inputs[1])
    links.new(add.outputs[0], mix.inputs[2])

    return add

def processRS2Texlayer(self, blMat, xmlRsMat, tree, links, nodes, shader, transparent, mix, serverProfile, state):
    def processTexType(texType, *, offset = 0):
        texpath = xmlRsMat.get(texType)
        texBase, _, _, texDir = decomposePath(texpath)

        if texBase == None:
            # self.report({ 'WARNING' }, f"GZRS2: .rs.xml material with no texture name: { texBase }")
            return True, None, None, None, None

        if texBase == '':
            self.report({ 'WARNING' }, f"GZRS2: .rs.xml material with an empty texture name: { texBase }")
            return True, None, None, None, None

        if not isValidTexBase(texBase):
            self.report({ 'WARNING' }, f"GZRS2: .rs.xml material with an invalid texture name: { blMat.name }, { texBase }")
            return True, None, None, None, None

        success, texpath, loadFake = textureSearchLoadFake(self, texBase, texDir, False, state)

        if not success:
            self.report({ 'WARNING' }, f"GZRS2: Texture not found for .rs.xml material: { blMat.name }, { texType }, { texBase }")

        return False, getMatImageTextureNode(bpy, blMat, nodes, texpath, 'STRAIGHT', -440 + offset, 300 + offset, loadFake, state), texpath, texBase, texDir

    # TODO: Create material presets for Duelists profile to allow configuration using shader nodes

    props = blMat.gzrs2

    if serverProfile == 'DUELISTS':
        result, duelistsNormal, texpath, texBase, texDir = processTexType('NORMALMAP', offset = -40)

        if not result:
            props.duelistsNormalTexBase = texBase
            props.duelistsNormalTexDir = texDir

        result, duelistsSpecular, texpath, texBase, texDir = processTexType('SPECULARMAP', offset = -80)

        if not result:
            props.duelistsSpecularTexBase = texBase
            props.duelistsSpecularTexDir = texDir

        result, duelistsEmissive, texpath, texBase, texDir = processTexType('EMISSIVEMAP', offset = -120)

        if not result:
            props.duelistsEmissiveTexBase = texBase
            props.duelistsEmissiveTexDir = texDir

    error, texture, texpath, texBase, texDir = processTexType('DIFFUSEMAP')
    if error: return

    props.overrideTexpath   = texDir != ''
    props.writeDirectory    = texDir != ''
    props.texBase           = texBase
    props.texDir            = texDir

    if state.doLightmap:
        _, _, lightmix, _ = setupMatNodesLightmap(blMat, tree, links, nodes, shader, image = state.blLmImage)
        links.new(texture.outputs[0], lightmix.inputs[0])
    else:
        links.new(texture.outputs[0], shader.inputs[0]) # Base Color

    usealphatest = xmlRsMat['USEALPHATEST']
    alphatest = xmlRsMat['ALPHATESTVALUE']
    useopacity = xmlRsMat['USEOPACITY']
    additive = xmlRsMat['ADDITIVE']
    twosided = xmlRsMat['TWOSIDED']

    # _, texName, _, _ = decomposePath(texpath)
    # isAniTex = checkIsAniTex(texName)
    # success, frameCount, frameSpeed, frameGap = processAniTexParameters(isAniTex, texName)

    source = lightmix if state.doLightmap else texture

    setupMatNodesTransparency(blMat, tree, links, nodes, alphatest, usealphatest, useopacity, texture, shader)
    setupMatNodesAdditive(blMat, tree, links, nodes, additive, source, shader, transparent, mix)
    setMatFlagsTransparency(blMat, usealphatest or useopacity or additive, twosided = twosided)

def processRS3TexLayer(self, texlayer, blMat, tree, links, nodes, shader, emission, alphatest, usealphatest, state):
    texType = texlayer['type']
    texBase = texlayer['name']
    useopacity = texType == 'OPACITYMAP'

    if texType not in XMLELU_TEXTYPES:
        self.report({ 'WARNING' }, f"GZRS2: Unsupported texture type for .elu.xml material: { texBase }, { texType }")
        return useopacity

    if texBase == None:
        # self.report({ 'WARNING' }, f"GZRS2: .elu.xml material with no texture name: { texBase }, { texType }")
        return useopacity

    if texBase == '':
        self.report({ 'WARNING' }, f"GZRS2: .elu.xml material with an empty texture name: { texBase }, { texType }")
        return useopacity

    if not isValidTexBase(texBase):
        self.report({ 'WARNING' }, f"GZRS2: .elu.xml material with an invalid texture name: { texBase }, { texType }")
        return useopacity

    success, texpath, loadFake = textureSearchLoadFake(self, texBase, '', True, state)

    if not success:
        self.report({ 'WARNING' }, f"GZRS2: Texture not found for .elu.xml material: { texBase }, { texType }")

    if texType == 'DIFFUSEMAP':
        texture = getMatImageTextureNode(bpy, blMat, nodes, texpath, 'CHANNEL_PACKED', -540, 300, loadFake, state)
        texture.select = False

        links.new(texture.outputs[0], shader.inputs[0]) # Base Color
    elif texType == 'SPECULARMAP':
        texture = getMatImageTextureNode(bpy, blMat, nodes, texpath, 'CHANNEL_PACKED', -540, 0, loadFake, state)
        texture.select = False

        invert = nodes.new('ShaderNodeInvert')
        invert.location = (texture.location.x + 280, texture.location.y)
        invert.select = False

        # TODO: specular data is sometimes found in the alpha channel of the diffuse or normal maps
        links.new(texture.outputs[0], invert.inputs[1])
        links.new(invert.outputs[0], shader.inputs[2]) # Roughness
    elif texType == 'SELFILLUMINATIONMAP':
        texture = getMatImageTextureNode(bpy, blMat, nodes, texpath, 'CHANNEL_PACKED', -540, -300, loadFake, state)
        texture.select = False

        links.new(texture.outputs[0], shader.inputs[26]) # Emission Color

        shader.inputs[27].default_value = blMat.gzrs2.fakeEmission = emission # Emission Strength
    elif texType == 'OPACITYMAP':
        texture = getMatImageTextureNode(bpy, blMat, nodes, texpath, 'CHANNEL_PACKED', -540, 300, loadFake, state)
        texture.select = False

        setupMatNodesTransparency(blMat, tree, links, nodes, alphatest, usealphatest, useopacity, texture, shader)
    elif texType == 'NORMALMAP':
        texture = getMatImageTextureNode(bpy, blMat, nodes, texpath, 'NONE', -540, -600, loadFake, state)
        texture.image.colorspace_settings.name = 'Non-Color'
        texture.select = False

        normal = nodes.new('ShaderNodeNormalMap')
        normal.location = (-260, -600)
        normal.select = False

        links.new(texture.outputs[0], normal.inputs[1])
        links.new(normal.outputs[0], shader.inputs[5]) # Normal

    return useopacity

def setupDebugMat(name, color):
    blDebugMat = bpy.data.materials.new(name)
    blDebugMat.use_nodes = True
    blDebugMat.diffuse_color = color
    blDebugMat.roughness = 1.0
    blDebugMat.surface_render_method = 'BLENDED'

    setMatFlagsTransparency(blDebugMat, True)

    if color[3] < 1.0:
        tree, links, nodes = getMatTreeLinksNodes(blDebugMat)

        nodes.remove(getShaderNodeByID(nodes, 'ShaderNodeBsdfPrincipled'))
        output = getShaderNodeByID(nodes, 'ShaderNodeOutputMaterial')

        transparent = nodes.new('ShaderNodeBsdfTransparent')
        transparent.location = (120, 300)

        links.new(transparent.outputs[0], output.inputs[0])

    return blDebugMat

def setObjFlagsDebug(blObj):
    # Visibility
    blObj.visible_camera = False
    blObj.visible_diffuse = False
    blObj.visible_glossy = False
    blObj.visible_volume_scatter = False
    blObj.visible_transmission = False
    blObj.visible_shadow = False

    # Viewport Display
    blObj.show_wire = True
    blObj.display.show_shadows = False

def getErrorMat(state):
    blErrorMat = state.blErrorMat

    if blErrorMat is not None:
        return blErrorMat

    errName = f"{ state.filename }_Error"
    blErrorMat = bpy.data.materials.get(errName)

    if blErrorMat is not None:
        return blErrorMat

    blErrorMat = setupDebugMat(errName, (1.0, 0.0, 1.0, 1.0))

    state.blErrorMat = blErrorMat

    return blErrorMat

def setupColPlanes(rootExtras, context, state):
    reorientPlane = Matrix.Rotation(math.radians(90.0), 4, 'X')
    p = 0

    def processCol1Hierarchy(node):
        nonlocal p

        # Forks & bevels only
        if len(node.triangles) > 0:
            return None

        plane = node.plane
        planeNormal = node.plane.xyz
        planeDistance = node.plane.w

        # Useful planes only
        if vec3IsClose(planeNormal, Vector((0, 0, 0)), RS_DIR_THRESHOLD):
            return None

        if math.isclose(planeDistance, 0, abs_tol = RS_COORD_THRESHOLD):
            return None

        planeName = f"{ state.filename }_Plane{ p }"
        p += 1

        blPlaneObj = bpy.data.objects.new(planeName, None)

        rotation = planeNormal.to_track_quat('Y', 'Z').to_matrix().to_4x4() @ reorientPlane
        translation = Matrix.Translation(planeNormal * -planeDistance)

        blPlaneObj.matrix_world = translation @ rotation
        blPlaneObj.empty_display_type = 'IMAGE'
        blPlaneObj.empty_image_side = 'FRONT'
        blPlaneObj.use_empty_image_alpha = True
        blPlaneObj.color[3] = 0.5
        # TODO: Custom image or sprite gizmo?
        # TODO: Duplicate the empty panel to appear for image data as well

        rootExtras.objects.link(blPlaneObj)

        blPlaneObjNeg = processCol1Hierarchy(node.negative) if node.negative else None
        blPlaneObjPos = processCol1Hierarchy(node.positive) if node.positive else None

        if blPlaneObjNeg is not None:
            transform = blPlaneObjNeg.matrix_world
            blPlaneObjNeg.parent = blPlaneObj
            blPlaneObjNeg.matrix_world = transform

        if blPlaneObjPos is not None:
            transform = blPlaneObjPos.matrix_world
            blPlaneObjPos.parent = blPlaneObj
            blPlaneObjPos.matrix_world = transform

        return blPlaneObj

    return processCol1Hierarchy(state.col1Root)

def setupColMesh(name, collection, context, extension, state):
    blColMat = setupDebugMat(name, (1.0, 0.0, 1.0, 0.25))

    hullName = name + "_Hull"
    solidName = name + "_Solid"

    blColMeshHull = bpy.data.meshes.new(hullName)
    blColMeshSolid = bpy.data.meshes.new(solidName)

    blColObjHull = bpy.data.objects.new(hullName, blColMeshHull)
    blColObjSolid = bpy.data.objects.new(solidName, blColMeshSolid)

    blColMeshHull.gzrs2.meshType = 'RAW'
    blColMeshSolid.gzrs2.meshType = 'RAW'

    colVertsHull = tuple(vertex for triangle in state.colTrisHull for vertex in triangle.vertices)
    colVertsSolid = tuple(vertex for triangle in state.colTrisSolid for vertex in triangle.vertices)

    colNormsHull = tuple(triangle.normal for triangle in state.colTrisHull for _ in range(3))
    colNormsSolid = tuple(triangle.normal for triangle in state.colTrisSolid for _ in range(3))

    colFacesHull = tuple(tuple(range(i, i + 3)) for i in range(0, len(colVertsHull), 3))
    colFacesSolid = tuple(tuple(range(i, i + 3)) for i in range(0, len(colVertsSolid), 3))

    blColMeshHull.from_pydata(colVertsHull, (), colFacesHull)
    blColMeshSolid.from_pydata(colVertsSolid, (), colFacesSolid)

    blColMeshHull.normals_split_custom_set_from_vertices(colNormsHull)
    blColMeshSolid.normals_split_custom_set_from_vertices(colNormsSolid)

    blColMeshHull.validate()
    blColMeshSolid.validate()

    blColMeshHull.update()
    blColMeshSolid.update()

    setObjFlagsDebug(blColObjHull)
    setObjFlagsDebug(blColObjSolid)

    state.blColMat = blColMat
    state.blColMeshHull = blColMeshHull
    state.blColMeshSolid = blColMeshSolid
    state.blColObjHull = blColObjHull
    state.blColObjSolid = blColObjSolid

    blColObjHull.data.materials.append(blColMat)
    blColObjSolid.data.materials.append(blColMat)

    collection.objects.link(blColObjHull)
    collection.objects.link(blColObjSolid)

    counts = countInfoReports(context)

    if state.doCleanup and state.logCleanup:
        print()
        print("=== Col Mesh Cleanup ===")
        print()

    if state.doCleanup:
        # TODO: convertUnits should affect thresholds
        def subCleanup():
            for _ in range(10):
                bpy.ops.mesh.dissolve_degenerate()
                bpy.ops.mesh.delete_loose()
                bpy.ops.mesh.select_all(action = 'SELECT')
                bpy.ops.mesh.remove_doubles(threshold = 0.0001)

        # TODO: convertUnits should affect thresholds
        def cleanupFunc(blObj):
            for viewLayer in context.scene.view_layers:
                viewLayer.objects.active = blObj

            bpy.ops.object.select_all(action = 'DESELECT')
            blObj.select_set(True)

            bpy.ops.object.mode_set(mode = 'EDIT')

            if extension == 'col':
                bpy.ops.mesh.intersect(mode = 'SELECT', separate_mode = 'ALL', threshold = 0.0001, solver = 'FAST')
                bpy.ops.mesh.select_all(action = 'SELECT')

                subCleanup()

                bpy.ops.mesh.intersect(mode = 'SELECT', separate_mode = 'ALL')
                bpy.ops.mesh.select_all(action = 'SELECT')

                subCleanup()

                for _ in range(10):
                    bpy.ops.mesh.fill_holes(sides = 0)
                    bpy.ops.mesh.tris_convert_to_quads(face_threshold = 0.0174533, shape_threshold = 0.0174533)

                    subCleanup()

                bpy.ops.mesh.vert_connect_nonplanar(angle_limit = 0.0174533)

                subCleanup()
            elif extension == 'cl2':
                bpy.ops.mesh.remove_doubles(threshold = 0.0001, use_sharp_edge_from_normals = True)
                bpy.ops.mesh.tris_convert_to_quads(face_threshold = 0.0174533, shape_threshold = 0.0174533)

            bpy.ops.mesh.dissolve_limited(angle_limit = 0.0174533)
            bpy.ops.mesh.delete_loose()
            bpy.ops.mesh.select_all(action = 'SELECT')
            bpy.ops.mesh.normals_make_consistent(inside = True)
            bpy.ops.mesh.select_all(action = 'DESELECT')

            bpy.ops.object.mode_set(mode = 'OBJECT')

        if state.logCleanup:
            print(hullName)
            cleanupFunc(blColObjHull)
            print()
        else:
            with redirect_stdout(state.silentIO):
                cleanupFunc(blColObjHull)

    deleteInfoReports(context, counts)

    return blColObjHull, blColObjSolid

def setupNavMesh(state):
    facesName = f"{ state.filename }_Navmesh"
    linksName = f"{ state.filename }_Navlinks"

    blNavMat = setupDebugMat(facesName, (0.0, 1.0, 0.0, 0.25))

    blNavFaces = bpy.data.meshes.new(facesName)
    blNavLinks = bpy.data.meshes.new(linksName)

    blNavFacesObj = bpy.data.objects.new(facesName, blNavFaces)
    blNavLinksObj = bpy.data.objects.new(linksName, blNavLinks)

    blNavFaces.gzrs2.meshType = 'NAVIGATION'

    blNavFaces.from_pydata(state.navVerts, (), state.navFaces)
    blNavFaces.validate()
    blNavFaces.update()

    linksVerts = tuple((state.navVerts[face[0]] + state.navVerts[face[1]] + state.navVerts[face[2]]) / 3.0 for face in state.navFaces)
    linksEdges = tuple((l, link[i]) for i in range(3) for l, link in enumerate(state.navLinks) if link[i] >= 0)

    blNavLinks.from_pydata(linksVerts, linksEdges, ())
    blNavLinks.validate()
    blNavLinks.update()

    setObjFlagsDebug(blNavFacesObj)
    setObjFlagsDebug(blNavLinksObj)

    state.blNavMat = blNavMat
    state.blNavFaces = blNavFaces
    state.blNavLinks = blNavLinks
    state.blNavFacesObj = blNavFacesObj
    state.blNavLinksObj = blNavLinksObj

    blNavFacesObj.data.materials.append(blNavMat)

    return blNavFacesObj, blNavLinksObj

def setupEluMat(self, m, eluMat, state):
    elupath = eluMat.elupath
    matID = eluMat.matID
    subMatID = eluMat.subMatID
    subMatCount = eluMat.subMatCount

    ambient = eluMat.ambient
    diffuse = eluMat.diffuse
    specular = eluMat.specular
    exponent = eluMat.exponent
    alphatest = eluMat.alphatest
    useopacity = eluMat.useopacity
    additive = eluMat.additive
    twosided = eluMat.twosided
    texName = eluMat.texName
    texBase = eluMat.texBase
    texDir = eluMat.texDir

    for eluMat2, blMat2 in state.blEluMatPairs:
        if subMatID     !=  eluMat2.subMatID:       continue
        if subMatCount  !=  eluMat2.subMatCount:    continue

        if not compareColors(ambient,    eluMat2.ambient):   continue
        if not compareColors(diffuse,    eluMat2.diffuse):   continue
        if not compareColors(specular,   eluMat2.specular):  continue

        if not math.isclose(exponent,    eluMat2.exponent,   abs_tol = ELU_VALUE_THRESHOLD): continue
        if not math.isclose(alphatest,   eluMat2.alphatest,  abs_tol = ELU_VALUE_THRESHOLD): continue

        if useopacity   != eluMat2.useopacity:  continue
        if additive     != eluMat2.additive:    continue
        if twosided     != eluMat2.twosided:    continue

        if eluMat.texpath       != eluMat2.texpath:     continue
        if eluMat.alphapath     != eluMat2.alphapath:   continue

        blEluMatsAtIndex = state.blEluMats.setdefault(elupath, {}).setdefault(matID, {})
        blEluMatsAtIndex[subMatID] = blMat2

        return

    matName = texName or f"Material_{ m }"
    blMat, tree, links, nodes, shader, _, _, transparent, mix = setupMatBase(matName)

    props = blMat.gzrs2
    props.priority      = matID if subMatID == -1 else subMatID
    props.parent        = None
    props.ambient       = (ambient[0], ambient[1], ambient[2])
    props.diffuse       = (diffuse[0], diffuse[1], diffuse[2])
    props.specular      = (specular[0], specular[1], specular[2])
    props.exponent      = eluMat.exponent

    if texBase == None:
        # self.report({ 'WARNING' }, f"GZRS2: .elu material with no texture name: { blMat.name }, { texBase }")
        pass
    elif texBase == '':
        self.report({ 'WARNING' }, f"GZRS2: .elu material with an empty texture name: { blMat.name }, { texBase }")
    elif not isValidTexBase(texBase):
        self.report({ 'WARNING' }, f"GZRS2: .elu material with an invalid texture name: { blMat.name }, { texBase }")
    else:
        success, texpath, loadFake = textureSearchLoadFake(self, texBase, texDir, False, state)

        if not success:
            self.report({ 'WARNING' }, f"GZRS2: Texture not found for .elu material: { blMat.name }, { texBase }")

        texture = getMatImageTextureNode(bpy, blMat, nodes, texpath, 'STRAIGHT', -440, 300, loadFake, state)

        props.overrideTexpath   = texDir != ''
        props.writeDirectory    = texDir != ''
        props.texBase           = texBase
        props.texDir            = texDir

        links.new(texture.outputs[0], shader.inputs[0]) # Base Color
        usealphatest = alphatest > 0

        # _, texName, _, _ = decomposePath(texpath)
        # isAniTex = checkIsAniTex(texName)
        # success, frameCount, frameSpeed, frameGap = processAniTexParameters(isAniTex, texName)

        setupMatNodesTransparency(blMat, tree, links, nodes, alphatest, usealphatest, useopacity, texture, shader)
        setupMatNodesAdditive(blMat, tree, links, nodes, additive, texture, shader, transparent, mix)
        setMatFlagsTransparency(blMat, usealphatest or useopacity or additive, twosided = twosided)

    blEluMatsAtIndex = state.blEluMats.setdefault(elupath, {}).setdefault(matID, {})
    blEluMatsAtIndex[subMatID] = blMat
    state.blEluMatPairs.append((eluMat, blMat))

def setupEluMats(self, state):
    for m, eluMat in enumerate(state.eluMats):
        setupEluMat(self, m, eluMat, state)

    for eluMat1, blMat1 in state.blEluMatPairs:
        if eluMat1.subMatID == -1: continue

        for eluMat2, blMat2 in state.blEluMatPairs:
            if eluMat2 == eluMat1: continue
            if eluMat2.subMatID != -1: continue
            if eluMat2.matID != eluMat1.matID: continue

            blMat1.gzrs2.parent = blMat2
            break

def setupXmlEluMat(self, elupath, xmlEluMat, state):
    specular    = xmlEluMat['SPECULAR_LEVEL']
    glossiness  = xmlEluMat['GLOSSINESS']
    emission    = xmlEluMat['SELFILLUSIONSCALE']
    alphatest   = xmlEluMat['ALPHATESTVALUE']
    additive    = xmlEluMat['ADDITIVE']
    twosided    = xmlEluMat['TWOSIDED']

    for xmlEluMat2, blMat2 in state.blXmlEluMatPairs:
        if not math.isclose(specular,       xmlEluMat2['SPECULAR_LEVEL'],       abs_tol = ELU_VALUE_THRESHOLD): continue
        if not math.isclose(glossiness,     xmlEluMat2['GLOSSINESS'],           abs_tol = ELU_VALUE_THRESHOLD): continue
        if not math.isclose(emission,       xmlEluMat2['SELFILLUSIONSCALE'],    abs_tol = ELU_VALUE_THRESHOLD): continue
        if not math.isclose(alphatest,      xmlEluMat2['ALPHATESTVALUE'],       abs_tol = ELU_VALUE_THRESHOLD): continue

        if additive != xmlEluMat2['ADDITIVE']: continue
        if twosided != xmlEluMat2['TWOSIDED']: continue
        if len(xmlEluMat['textures']) != len(xmlEluMat2['textures']): continue

        match = True

        for t, texture in enumerate(xmlEluMat['textures']):
            texType = texture['type']
            texName = texture['name']

            if texType in XMLELU_TEXTYPES and texName:
                texture2 = xmlEluMat2['textures'][t]
                texType2 = texture2['type']
                texName2 = texture2['name']

                if texType2 in XMLELU_TEXTYPES and texName2:
                    if texType != texType2 or texName != texName2:
                        match = False
                        break

        if match:
            state.blXmlEluMats.setdefault(elupath, []).append(blMat2)
            return

    matName = xmlEluMat['name']
    blMat, tree, links, nodes, shader, _, _, transparent, mix = setupMatBase(matName)

    shader.inputs[6].default_value = glossiness / 100.0 # Metallic
    shader.inputs[12].default_value = min(specular / 100.0 / 2.0, 0.5) # Specular IOR Level

    usealphatest = alphatest > 0
    useopacity = False

    for texlayer in xmlEluMat['textures']:
        useopacity = useopacity or processRS3TexLayer(self, texlayer, blMat, tree, links, nodes, shader, emission, alphatest, usealphatest, state)

    setupMatNodesAdditive(blMat, tree, links, nodes, additive, None, shader, transparent, mix)
    setMatFlagsTransparency(blMat, usealphatest or useopacity or additive, twosided = twosided)

    state.blXmlEluMats.setdefault(elupath, []).append(blMat)
    state.blXmlEluMatPairs.append((xmlEluMat, blMat))

# TODO: Improve performance of convex id matching
'''
def setupRsConvexMesh(self, _, blMesh, _, _, state, *, allowLightmapUVs = True):
    meshVerts = []
    meshNorms = []
    meshFaces = []
    meshMatIDs = []
    meshUV1 = []
    meshUV2 = []

    # The convex polygons will never support atlased lightmaps because the lightmap ID can differ across an octree split
    # It's another reason why atlasing should be phased out, we can just increase lightmap resolution
    fromLightmap = state.doLightmap and allowLightmapUVs

    offset = 0

    for p, polygon in enumerate(state.rsConvexPolygons):
        for v in range(polygon.vertexOffset, polygon.vertexOffset + polygon.vertexCount):
            meshVerts.append(state.rsConvexVerts[v].pos)
            meshNorms.append(state.rsConvexVerts[v].nor)
            meshUV1.append(state.rsConvexVerts[v].uv1)

            if fromLightmap:
                uv2 = state.lmUVs[state.rsConvexVerts[v].oid].copy()
                uv2.y += 1.0

                meshUV2.append(uv2)
            else:
                meshUV2.append(state.rsConvexVerts[v].uv2)

        meshFaces.append(tuple(range(offset, offset + polygon.vertexCount)))
        offset += polygon.vertexCount

        meshMatIDs.append(polygon.matID)

    blMesh.from_pydata(meshVerts, (), meshFaces)
    blMesh.normals_split_custom_set_from_vertices(meshNorms)

    uvLayer1 = blMesh.uv_layers.new()
    for c, uv in enumerate(meshUV1): uvLayer1.data[c].uv = uv

    uvLayer2 = blMesh.uv_layers.new()
    for c, uv in enumerate(meshUV2): uvLayer2.data[c].uv = uv

    blMesh.validate()
    blMesh.update()

    return meshMatIDs
'''

def setupRsTreeMesh(self, m, blMesh, treePolygons, treeVerts, state, *, allowLightmapUVs = True):
    meshVerts = []
    meshNorms = []
    meshFaces = []
    meshMatIDs = []
    meshUV1 = []
    meshUV2 = []

    fromLightmap = state.doLightmap and allowLightmapUVs

    if fromLightmap:
        numCells = len(state.lmImages)
        cellSpan = int(math.sqrt(nextSquare(numCells)))

    found = False
    offset = 0

    for p, polygon in enumerate(treePolygons):
        if state.meshMode != 'BAKE' and polygon.matID != m:
            continue

        found = True

        if fromLightmap and numCells > 1:
            c = state.lmLightmapIDs[p]
            cx = c % cellSpan
            cy = c // cellSpan

        for v in range(polygon.vertexOffset, polygon.vertexOffset + polygon.vertexCount):
            meshVerts.append(treeVerts[v].pos)
            meshNorms.append(treeVerts[v].nor)
            meshUV1.append(treeVerts[v].uv1)

            if fromLightmap:
                uv2 = state.lmUVs[v].copy()

                if numCells > 1:
                    uv2.x += cx
                    uv2.y -= cy
                    uv2 /= cellSpan

                uv2.y += 1.0
                meshUV2.append(uv2)
            else:
                meshUV2.append(treeVerts[v].uv2)

        meshFaces.append(tuple(range(offset, offset + polygon.vertexCount)))
        offset += polygon.vertexCount

        if state.meshMode == 'BAKE':
            meshMatIDs.append(polygon.matID)

    if state.meshMode == 'STANDARD' and not found:
        self.report({ 'INFO' }, f"GZRS2: Unused rs material slot: { m }, { state.xmlRsMats[m]['name'] }")
        return False

    blMesh.from_pydata(meshVerts, (), meshFaces)
    blMesh.normals_split_custom_set_from_vertices(meshNorms)

    uvLayer1 = blMesh.uv_layers.new()
    for c, uv in enumerate(meshUV1): uvLayer1.data[c].uv = uv

    uvLayer2 = blMesh.uv_layers.new()
    for c, uv in enumerate(meshUV2): uvLayer2.data[c].uv = uv

    blMesh.validate()
    blMesh.update()

    if state.meshMode == 'STANDARD': return True
    elif state.meshMode == 'BAKE': return tuple(meshMatIDs)

# This only works if the user has an Info area open somewhere
# Luckily, the Scripting layout has one by default
def countInfoReports(context):
    counts = {}

    for workspace in bpy.data.workspaces:
        for screen in filter(lambda x: not x.is_temporary, workspace.screens):
            for area in filter(lambda x: x.type == 'INFO', screen.areas):
                for region in filter(lambda x: x.type == 'WINDOW', area.regions):
                    with context.temp_override(screen = screen, area = area, region = region):
                        key = (screen, area, region)
                        count = 0

                        # Info operations don't support negative indices, so we count until select_pick() fails
                        while bpy.ops.info.select_pick(report_index = count) != { 'CANCELLED' }:
                            count += 1

                        counts[key] = count

    return counts

def deleteInfoReports(context, counts):
    for workspace in bpy.data.workspaces:
        for screen in filter(lambda x: not x.is_temporary, workspace.screens):
            for area in filter(lambda x: x.type == 'INFO', screen.areas):
                for region in filter(lambda x: x.type == 'WINDOW', area.regions):
                    with context.temp_override(screen = screen, area = area, region = region):
                        key = (screen, area, region)
                        count = 0

                        # Info operations don't support negative indices, so we count until select_pick() fails
                        while bpy.ops.info.select_pick(report_index = count) != { 'CANCELLED' }:
                            count += 1

                        bpy.ops.info.select_all(action = 'DESELECT')

                        # Start at the last and count backward
                        for i in range(count, counts[key], -1):
                            bpy.ops.info.select_pick(report_index = i - 1, extend = True)

                        bpy.ops.info.report_delete()

def setupElu(self, eluMesh, oneOfMany, collection, context, state):
    meshName = eluMesh.meshName
    meshNameLower = meshName.lower()
    meshVersion = eluMesh.version
    _, propFilename, _, _ = decomposePath(eluMesh.elupath)

    doNorms = len(eluMesh.normals) > 0
    doUV1 = len(eluMesh.uv1s) > 0
    doUV2 = len(eluMesh.uv2s) > 0
    doSlots = len(eluMesh.slotIDs) > 0
    doColors = len(eluMesh.colors) > 0
    doWeights = len(eluMesh.weights) > 0

    meshVerts = []
    meshNorms = [] if doNorms else None
    meshFaces = []
    meshUV1 = [] if doUV1 else None
    meshUV2 = [] if doUV2 else None
    meshSlots = [] if doSlots else None
    meshColors = [] if doColors else None
    meshGroups = {} if doWeights else None
    index = 0

    blMesh = bpy.data.meshes.new(meshName)
    blMeshObj = bpy.data.objects.new(meshName, blMesh)

    props = blMesh.gzrs2
    props.meshType = 'PROP'
    props.propFilename = propFilename

    if meshVersion <= ELU_5007:
        if 'sky_' in meshNameLower or '_sky' in meshNameLower:
            props.propSubtype = 'SKY'

            blMeshObj.visible_volume_scatter = False
            blMeshObj.visible_transmission = False
            blMeshObj.visible_shadow = False

    for face in eluMesh.faces:
        degree = face.degree

        # Reverses the winding order for GunZ 1 elus
        for v in range(degree - 1, -1, -1) if meshVersion <= ELU_5007 else range(degree):
            meshVerts.append(eluMesh.vertices[face.ipos[v]])
            if doNorms: meshNorms.append(eluMesh.normals[face.inor[v]])
            if doUV1: meshUV1.append(eluMesh.uv1s[face.iuv1[v]])
            if doUV2: meshUV2.append(eluMesh.uv2s[face.iuv2[v]])
            if doColors: meshColors.append(eluMesh.colors[face.ipos[v]])

        meshFaces.append(tuple(range(index, index + degree)))
        if doSlots: meshSlots.append(face.slotID)
        index += degree

    blMesh.from_pydata(meshVerts, (), meshFaces)

    if doNorms:
        blMesh.normals_split_custom_set_from_vertices(meshNorms)

    if doUV1:
        uvLayer1 = blMesh.uv_layers.new()
        for c, uv in enumerate(meshUV1): uvLayer1.data[c].uv = uv

    if doUV2:
        uvLayer2 = blMesh.uv_layers.new()
        for c, uv in enumerate(meshUV2): uvLayer2.data[c].uv = uv

    if doSlots:
        for p, id in enumerate(meshSlots):
            blMesh.polygons[p].material_index = id

    if doColors:
        color1 = blMesh.color_attributes.new('Color', 'FLOAT_COLOR', 'POINT')
        for c, color in enumerate(meshColors):
            color1.data[c].color = (color[0], color[1], color[2], 0.0) # TODO: Shader support for vertex alpha data

    blMesh.validate()
    blMesh.update()

    if oneOfMany and meshVersion <= ELU_5007:
        # Rotate GunZ 1 elus to face forward when loading from a map
        blMeshObj.matrix_world = Matrix.Rotation(math.radians(-180.0), 4, 'Z') @ eluMesh.transform
    else:
        blMeshObj.matrix_world = eluMesh.transform

    if doWeights:
        modifier = blMeshObj.modifiers.new("Armature", 'ARMATURE')

        index = 0

        eluMeshNames = [eluMesh.meshName for eluMesh in state.eluMeshes]
        invalidBones = set()

        for face in eluMesh.faces:
            degree = face.degree

            # Reverses the winding order for GunZ 1 elus
            for v in range(degree - 1, -1, -1) if meshVersion <= ELU_5007 else range(degree):
                weight = eluMesh.weights[face.ipos[v]]

                for d in range(weight.degree):
                    if meshVersion <= ELU_5007:     boneName = weight.meshNames[d]
                    else:                           boneName = getOrNone(eluMeshNames, weight.meshIDs[d])

                    if boneName in eluMeshNames:    state.gzrsValidBones.add(boneName)
                    else:                           invalidBones.add(boneName)

                    value = weight.values[d]

                    if value < ELU_WEIGHT_THRESHOLD:
                        continue

                    if boneName not in meshGroups:
                        meshGroups[boneName] = blMeshObj.vertex_groups.new(name = boneName)

                    meshGroups[boneName].add((index,), value, 'REPLACE')

                index += 1

        for boneName in invalidBones:
            self.report({ 'WARNING' }, f"GZRS2: Failed to find bone for weight group: { boneName }")

    elupath = eluMesh.elupath
    eluMatID = eluMesh.matID
    slotIDs = eluMesh.slotIDs

    slotCount = max(1, max(slotIDs) + 1) if doSlots else 1

    if meshVersion <= ELU_5007:
        baseMat = None

        if elupath in state.blEluMats:
            blEluMatsAtPath = state.blEluMats[elupath]

            if eluMatID in blEluMatsAtPath:
                blEluMatsAtIndex = blEluMatsAtPath[eluMatID]

                # We assume all sub-materials have a valid base
                if len(blEluMatsAtIndex) > 1:
                    for s in range(slotCount):
                        if s not in slotIDs:            blMesh.materials.append(None)
                        elif s in blEluMatsAtIndex:     blMesh.materials.append(blEluMatsAtIndex[s])
                        else:
                            self.report({ 'WARNING' }, f"GZRS2: Failed to find .elu sub-material for mesh at index/sub-index: { meshName }, { eluMatID }/{ s }")
                            blMesh.materials.append(getErrorMat(state))
                else:
                    baseMat = blEluMatsAtIndex[-1]
            else:
                self.report({ 'WARNING' }, f"GZRS2: Missing .elu material for mesh at index: { meshName }, { eluMatID }")
                baseMat = getErrorMat(state)
        else:
            self.report({ 'WARNING' }, f"GZRS2: Missing .elu materials for mesh: { meshName }")
            baseMat = getErrorMat(state)

        if baseMat is not None:
            for s in range(slotCount):
                if s not in slotIDs:    blMesh.materials.append(None)
                else:                   blMesh.materials.append(baseMat)
    else:
        if eluMatID < 0:
            if -1 in slotIDs:
                if not eluMesh.drawFlags & RM_FLAG_HIDE:
                    self.report({ 'WARNING' }, f"GZRS2: Double negative material index: { meshName }, { eluMatID }, { slotIDs }")

                    blMesh.materials.append(getErrorMat(state))
            elif elupath in state.blXmlEluMats:
                for blXmlEluMat in state.blXmlEluMats[elupath]:
                    blMesh.materials.append(blXmlEluMat)
            else:
                self.report({ 'WARNING' }, f"GZRS2: No .elu.xml material available after negative index: { meshName }, { eluMatID }")

                blMesh.materials.append(getErrorMat(state))
        else:
            if elupath in state.blXmlEluMats:
                if len(state.blXmlEluMats[elupath]) > eluMatID:
                    blMesh.materials.append(state.blXmlEluMats[elupath][eluMatID])
                else:
                    self.report({ 'WARNING' }, f"GZRS2: Missing .elu.xml material for mesh at index: { meshName }, { eluMatID }")

                    blMesh.materials.append(getErrorMat(state))
            else:
                self.report({ 'WARNING' }, f"GZRS2: No .elu.xml materials available for mesh: { meshName }")

                blMesh.materials.append(getErrorMat(state))

    collection.objects.link(blMeshObj)

    for viewLayer in context.scene.view_layers:
        viewLayer.objects.active = blMeshObj

    if state.doCleanup:
        # TODO: convertUnits should affect thresholds
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

        if state.logCleanup:
            print(meshName)
            cleanupFunc(blMeshObj)
            print()
        else:
            with redirect_stdout(state.silentIO):
                cleanupFunc(blMeshObj)

    state.blEluMeshes.append(blMesh)
    state.blEluMeshObjs.append(blMeshObj)

    if eluMesh.drawFlags & RM_FLAG_HIDE:
        blMeshObj.hide_render = True

        for viewLayer in context.scene.view_layers:
            blMeshObj.hide_set(True, view_layer = viewLayer)

    state.blObjPairs.append((eluMesh, blMeshObj))

def processEluHeirarchy(self, state):
    for child, childObj in state.blObjPairs:
        if child.parentName == '':
            continue

        found = False

        for parent, parentObj in state.blObjPairs:
            if child != parent and child.parentName == parent.meshName:
                if child.version <= ELU_5007:
                    transform = childObj.matrix_world

                childObj.parent = parentObj

                if child.version <= ELU_5007:
                    childObj.matrix_world = transform

                found = True
                break

        if not found:
            self.report({ 'WARNING' }, f"GZRS2: Parent not found for .elu child mesh: { child.meshName }, { child.parentName }")

def createBackupFile(path, *, purgeUnused = False):
    if not os.path.isfile(path):
        return

    directory = os.path.dirname(path)
    basename = bpy.path.basename(path)
    splitname = basename.split(os.extsep)
    filename = splitname[0]
    extension = ''

    for token in splitname[1:]:
        extension += os.extsep + token

    shutil.copy2(path, os.path.join(directory, filename + "_backup") + extension)

    if purgeUnused:
        os.remove(path)

# TODO: This pattern is ugly, wrap and generalize with a function call
# TODO: Try the walrus operator for succinct error handling
def checkMeshesEmptySlots(blMeshObjs, self = None):
    if not self:
        names = set()

    for blMeshObj in blMeshObjs:
        for matSlot in blMeshObj.material_slots:
            if matSlot.material is None:
                if self:
                    self.report({ 'ERROR' }, f"GZRS2: Mesh objects cannot have empty material slots: { blMeshObj.name }")
                    return { 'CANCELLED' }
                else:
                    names.add(blMeshObj.name)

    if not self:
        return tuple(names), len(names) > 0

def checkMatTypeOverlaps(blWorldMats, blPropMats, self = None):
    if not self:
        names = set()

    for blWorldMat in blWorldMats:
        if blWorldMat in blPropMats:
            if self:
                self.report({ 'ERROR' }, f"GZRS2: Prop materials must be exclusive to props: { blWorldMat.name }")
                return { 'CANCELLED' }
            else:
                names.add(blWorldMat.name)

    if not self:
        return tuple(names), len(names) > 0

def checkPropsParentForks(blPropObjs, self = None):
    if not self:
        names = set()

    for blPropObj in blPropObjs:
        if len(set(matSlot.material.gzrs2.parent for matSlot in blPropObj.material_slots)) > 1:
            if self:
                self.report({ 'ERROR' }, f"GZRS2: Mesh objects of type 'Prop' with multiple materials must link to the same parent, or none at all: { blPropObj.name }")
                return { 'CANCELLED' }
            else:
                names.add(blPropObj.name)

    if not self:
        return tuple(names), len(names) > 0

def checkPropsParentChains(blPropObjs, self = None):
    if not self:
        names = set()

    for blPropObj in blPropObjs:
        for matSlot in blPropObj.material_slots:
            parentMat = matSlot.material.gzrs2.parent

            if parentMat is not None and parentMat.gzrs2.parent is not None:
                if self:
                    self.report({ 'ERROR' }, f"GZRS2: Mesh objects of type 'Prop' cannot have materials that form parent chains: { blPropObj.name }")
                    return { 'CANCELLED' }
                else:
                    names.add(blPropObjs.name)

    if not self:
        return tuple(names), len(names) > 0

def largerSubtuple(x, y):
    if all(x[m] == y[m] for m in range(min(len(x), len(y)))):
        x = max(x, y)

    return x

def getUniqueMatLists(blMeshObjs):
    matListSet = set(tuple(matSlot.material for matSlot in blMeshObj.material_slots) for blMeshObj in blMeshObjs)
    matListSet = set(filter(lambda x: len(x) > 0, matListSet))
    matListSet = set(max(largerSubtuple(matList1, matList2) for matList2 in matListSet) for matList1 in matListSet)

    return matListSet

# Divide into base-materials and sub-materials
#   Base:   One unique material with no parent, whether explicitly defined or implied by a placeholder
#   Sub:    Multiple unique materials or single unique material with parent
def divideMeshMats(blPropObjs):
    # We assume the meshes have no empty slots, parent forks or parent chains
    uniqueMatLists = getUniqueMatLists(blPropObjs)

    singleMatLists  = set(filter(lambda x: len(set(x)) == 1,   uniqueMatLists))
    multiMatLists   = set(filter(lambda x: len(set(x)) > 1,    uniqueMatLists))

    singleMats  = set(matList[0]    for matList in singleMatLists)
    multiMats   = set(material      for matList in multiMatLists for material in matList)

    blBaseMats  = set(filter(lambda x: x.gzrs2.parent is None       and     x not in multiMats,     singleMats))
    blSubMats   = set(filter(lambda x: x.gzrs2.parent is not None   or      x in multiMats,         singleMats))
    blSubMats   |= multiMats

    blBaseMats  |= set(subMat.gzrs2.parent for subMat in blSubMats) - { None }
    blBaseMats  = tuple(sorted(blBaseMats, key = lambda x: (x.gzrs2.priority, x.name)))

    # Generate subIDs
    subIDsByMat = {}

    for blSubMat in blSubMats:
        for matList in uniqueMatLists:
            for s, material in enumerate(matList):
                if material != blSubMat:
                    continue

                if blSubMat not in subIDsByMat:
                    subIDsByMat[blSubMat] = { s }
                    break
                elif s not in subIDsByMat[blSubMat]:
                    subIDsByMat[blSubMat].add(s)

    subIDsByMat = { blSubMat: tuple(sorted(subIDs)) for blSubMat, subIDs in subIDsByMat.items() }

    return blBaseMats, blSubMats, subIDsByMat, uniqueMatLists

def checkSubMatsSwizzles(subIDsByMat, self = None):
    if not self:
        names = set()

    for blSubMat, subIDs in subIDsByMat.items():
        if len(subIDs) > 1:
            if self:
                self.report({ 'ERROR' }, f"GZRS2: Child materials must be placed in the same slot across all meshes that share them: { blSubMat.name }")
                return { 'CANCELLED' }
            else:
                names.add(blSubMat.name)

    if not self:
        return tuple(names), len(names) > 0

def checkSubMatsCollisions(subIDsByMat, self = None):
    if not self:
        names = set()

    items = tuple(filter(lambda x: x[0].gzrs2.parent is not None, subIDsByMat.items()))
    items = tuple((mat1, mat2, ids1, ids2) for mat1, ids1 in items for mat2, ids2 in items)
    items = tuple(filter(lambda x: x[0] != x[1] and x[0].gzrs2.parent == x[1].gzrs2.parent, items))

    for blSubMat1, blSubMat2, subIDs1, subIDs2 in items:
        if any(subID1 in subIDs2 for subID1 in subIDs1):
            if self:
                self.report({ 'ERROR' }, f"GZRS2: Child materials cannot link to the same parent if they occupy the same slot as another: { blSubMat1.name }, { blSubMat2.name }")
                return { 'CANCELLED' }
            else:
                names.add(blSubMat1.name)
                names.add(blSubMat2.name)

    if not self:
        return tuple(names), len(names) > 0

def generateMatGraph(blBaseMats, blSubMats, subIDsByMat, uniqueMatLists):
    # Associate & sort materials
    matGraph = []
    seenSubMats = set()

    for blBaseMat in blBaseMats:
        subMats = tuple(filter(lambda x: x.gzrs2.parent == blBaseMat, blSubMats))
        subMats = tuple(sorted(subMats, key = lambda x: subIDsByMat[x][0]))

        matGraph.append((blBaseMat, subMats))
        seenSubMats |= set(subMats)

    blImplicitSubMats = blSubMats - seenSubMats

    # if set(blSubMat.gzrs2.parent for blSubMat in blImplicitSubMats) - { None } != set(): print("Error 1!")

    for subMats in uniqueMatLists:
        uniqueMats = set(subMats)

        if len(uniqueMats) < 2: continue
        if uniqueMats - seenSubMats == set(): continue
        # if set(uniqueMat.gzrs2.parent for uniqueMat in uniqueMats) != { None }: print("Error 2!")
        # if uniqueMats - blImplicitSubMats != set(): print("Error 3!")

        matGraph.append((None, subMats))
        seenSubMats |= uniqueMats

    # if blSubMats - seenSubMats != set(): print("Error 4!")

    return matGraph

def isValidEluImageNode(node):
    if node is None: return False
    if node.bl_idname != 'ShaderNodeTexImage': return False
    if node.image is None: return False
    if node.image.source != 'FILE': return False
    if node.image.filepath == '': return False

    return True

def makePathExtSingle(path):
    dir = os.path.dirname(path)
    base = bpy.path.basename(path)
    name1, ext1 = os.path.splitext(base)
    name2, ext2 = os.path.splitext(name1)

    if ext2 != '': path = os.path.join(dir, name1)

    return path

def makeRS2DataPath(path):
    if path is None or path == '':
        return False

    result = None

    # TODO: True case-insensitivity, compare with .lower() and calculate an index then split manually
    for token in RS2_VALID_DATA_SUBDIRS:
        if token in path:
            result = token + path.split(token, 1)[1]
            break

        lower = token.lower()
        if lower in path:
            result = lower + path.split(lower, 1)[1]
            break

        upper = token.upper()
        if upper in path:
            result = upper + path.split(upper, 1)[1]
            break

    if result is None:
        return False

    result = makePathExtSingle(result)

    return result

# This data doesn't appear to be used for anything
# Blender matrices don't support arbitrary scale anyways
# It would have to be a custom mesh property, and nothing has broken without it
def calcEtcData(worldMat, parentWorld):
    localMat = parentWorld.inverted() @ worldMat
    loc, rot, sca = localMat.decompose()
    rotAxis, rotAngle = rot.to_axis_angle()

    apScale = sca
    rotAA = Vector((rotAxis.x, rotAxis.y, rotAxis.z, rotAngle))
    stretchAA = Vector((0, 1, 0, 0))
    etcMatrix = worldMat @ Matrix.LocRotScale(loc, rot, None).inverted()

    return apScale, rotAA, stretchAA, etcMatrix

def getSelectedObjects(context):
    objects = set()

    for area in filter(lambda x: x.type == 'OUTLINER', context.screen.areas):
        for region in filter(lambda x: x.type == 'WINDOW', area.regions):
            with context.temp_override(area = area, region = region):
                for object in context.selected_ids:
                    objects.add(object)

                break

    return objects

def getFilteredObjects(context, state):
    filterMode = state.filterMode

    if      filterMode == 'ALL':        objects = set(context.scene.objects)
    elif    filterMode == 'SELECTED':   objects = getSelectedObjects(context)
    elif    filterMode == 'VISIBLE':    objects = set(context.visible_objects)

    if state.includeChildren:
        objects |= set(child for object in objects for child in object.children_recursive)

    return objects

def nextSquare(x):
    result = 1

    while result ** 2 < x:
        result += 1

    return int(result ** 2)

def simpleSign(x):
    if math.isclose(x, 0, abs_tol = RS_COORD_THRESHOLD): return 0
    else: return -1 if x < 0 else 1

def calcDepthLimit(bbmin, bbmax):
    span = bbmax - bbmin

    limit = 0
    length = float('inf')

    while length > TREE_MIN_NODE_SIZE and limit < TREE_MAX_DEPTH:
        axis = (0 if span.x > span.z else 2) if span.x > span.y else (1 if span.y > span.z else 2)

        length = span[axis]
        span[axis] /= 2

        limit += 1

    return limit

def calcPlanePointDistance(plane, point):
    return point.dot(plane) + plane.w

def calcPlaneEdgeIntersection(plane, p1, p2):
    delta = p2 - p1
    t = -calcPlanePointDistance(plane, p1) / delta.dot(plane)

    if t < 0 or t > 1:
        raise GZRS2EdgePlaneIntersectionError(f"GZRS2: calcPlaneEdgeIntersection() created a t value outside the 0-1 range: { t }!")

    return p1 + delta * t, t

def calcVertexPlaneInfo(polygon, plane, *, getter = lambda x: x):
    distances = tuple(calcPlanePointDistance(plane, getter(vertex)) for vertex in polygon.vertices)
    signs = tuple(simpleSign(distance) for distance in distances)

    posCount = sum(int(sign > 0) for sign in signs)
    negCount = sum(int(sign < 0) for sign in signs)

    return signs, posCount, negCount

# Y-forward, counter-clockwise, -pi to pi
def calcVertexPlaneAngle(vertex, worldMatrixInv):
    local = worldMatrixInv @ vertex

    return math.atan2(local.x, -local.y)

def classifyFacing(polygon, plane, *, getter = lambda x: x):
    _, posCount, negCount = calcVertexPlaneInfo(polygon, plane, getter = getter)

    if posCount == 0 and negCount == 0:
        normDot = polygon.normal.dot(plane)

        if normDot >= 0:    return FACING_POS_COP
        else:               return FACING_NEG_COP
    elif negCount == 0:     return FACING_POSITIVE
    elif posCount == 0:     return FACING_NEGATIVE
    else:                   return FACING_BOTH

def splitPolygon(polygon, plane, *, markUsed = True, getter = lambda x: x):
    signs, posCount, negCount = calcVertexPlaneInfo(polygon, plane, getter = getter)

    if posCount == 0 and negCount == 0:
        if markUsed:
            polygon.used = True

        normDot = polygon.normal.dot(plane)

        if normDot >= 0:    return polygon, None
        else:               return None, polygon
    elif negCount == 0:     return polygon, None
    elif posCount == 0:     return None, polygon

    posVertices = []
    negVertices = []

    # Group vertices into two sides
    for i in range(polygon.vertexCount):
        o = (i + 1) % polygon.vertexCount

        v1 = polygon.vertices[i]
        v2 = polygon.vertices[o]

        sign1 = signs[i]
        sign2 = signs[o]

        if isinstance(v1, Vector):
            if sign1 >= 0: posVertices.append(v1.copy())
            if sign1 <= 0: negVertices.append(v1.copy())
            if sign1 != 0 and sign2 != 0 and sign1 != sign2:
                pos, _ = calcPlaneEdgeIntersection(plane, v1, v2)

                posVertices.append(pos.copy())
                negVertices.append(pos.copy())
        elif isinstance(v1, Rs2TreeVertex):
            if sign1 >= 0: posVertices.append(Rs2TreeVertex(v1.pos.copy(), v1.nor.normalized(), v1.uv1.copy(), v1.uv2.copy()))
            if sign1 <= 0: negVertices.append(Rs2TreeVertex(v1.pos.copy(), v1.nor.normalized(), v1.uv1.copy(), v1.uv2.copy()))
            if sign1 != 0 and sign2 != 0 and sign1 != sign2:
                pos, t  = calcPlaneEdgeIntersection(plane, v1.pos, v2.pos)
                nor     = v1.nor.lerp(v2.nor, t)
                uv1     = v1.uv1.lerp(v2.uv1, t)
                uv2     = v1.uv2.lerp(v2.uv2, t)

                posVertices.append(Rs2TreeVertex(pos.copy(), nor.normalized(), uv1.copy(), uv2.copy()))
                negVertices.append(Rs2TreeVertex(pos.copy(), nor.normalized(), uv1.copy(), uv2.copy()))

    posVertices = tuple(posVertices)
    negVertices = tuple(negVertices)

    posCount = len(posVertices)
    negCount = len(negVertices)

    if isinstance(polygon, Col1HullPolygon):
        posPolygon = Col1HullPolygon(posCount, posVertices, polygon.normal.normalized(), polygon.used)
        negPolygon = Col1HullPolygon(negCount, negVertices, polygon.normal.normalized(), polygon.used)
    elif isinstance(polygon, Col1BoundaryPolygon):
        posPolygon = Col1BoundaryPolygon(posCount, posVertices, polygon.normal.normalized())
        negPolygon = Col1BoundaryPolygon(negCount, negVertices, polygon.normal.normalized())
    elif isinstance(polygon, Rs2TreePolygonExport):
        posPolygon = Rs2TreePolygonExport(polygon.matID, polygon.convexID, polygon.drawFlags, posCount, posVertices, polygon.normal.normalized(), polygon.used)
        negPolygon = Rs2TreePolygonExport(polygon.matID, polygon.convexID, polygon.drawFlags, negCount, negVertices, polygon.normal.normalized(), polygon.used)

    return posPolygon, negPolygon

def partitionPolygons(polygons, plane, *, markUsed = True, tuplize = True, getter = lambda x: x):
    posPolygons = []
    negPolygons = []

    for polygon in polygons:
        posPolygon, negPolygon = splitPolygon(polygon, plane, markUsed = markUsed, getter = getter)

        if posPolygon is not None:  posPolygons.append(posPolygon)
        if negPolygon is not None:  negPolygons.append(negPolygon)

    if tuplize:
        posPolygons = tuple(posPolygons)
        negPolygons = tuple(negPolygons)

    return posPolygons, negPolygons

def choosePlane(polygons, *, checkCounts = False, getter = lambda x: x):
    chosenCost = float('inf')
    chosenPolygon = None
    chosenPlane = None

    for polygon1 in polygons:
        if polygon1.used:
            continue

        counts = [0 for _ in range(5)]

        normal = polygon1.normal.normalized()
        plane = normal.to_4d()
        plane.w = -normal.dot(getter(polygon1.vertices[0]))

        for polygon2 in polygons:
            counts[classifyFacing(polygon2, plane, getter = getter)] += 1

        # Always prioritize balance
        cost = abs(counts[FACING_POSITIVE] - counts[FACING_NEGATIVE])
        cost += counts[FACING_BOTH] / 2
        cost += (counts[FACING_POS_COP] + counts[FACING_NEG_COP]) / 10

        # Prioritize balance, then cuts
        '''
        if depth < 4:
            cost = abs(counts[FACING_POSITIVE] - counts[FACING_NEGATIVE])
            cost += counts[FACING_BOTH] / 2
        else:
            cost = abs(counts[FACING_POSITIVE] - counts[FACING_NEGATIVE]) / 2
            cost += counts[FACING_BOTH]

        cost += (counts[FACING_POS_COP] + counts[FACING_NEG_COP]) / 10
        '''

        if cost >= chosenCost:
            continue

        if checkCounts:
            posCount = counts[FACING_POSITIVE] + counts[FACING_POS_COP]
            negCount = counts[FACING_NEGATIVE] + counts[FACING_NEG_COP]

            if posCount == 0 or negCount == 0:
                continue

        chosenCost = cost
        chosenPolygon = polygon1
        chosenPlane = plane

    if chosenPolygon:
        chosenPolygon.used = True

    return chosenPlane

def createOctreeNode(octPolygons, octPlanes, bbmin, bbmax, depthLimit, windowManager, *, depth = 0):
    windowManager.progress_update(depth)

    if depth < depthLimit and len(octPolygons) > TREE_MAX_NODE_POLYGON_COUNT:
        plane = None
        positive = None
        negative = None

        if depth < len(octPlanes):
            plane = octPlanes[depth]
            octPlanes[depth] = None

        if plane is None:
            span = bbmax - bbmin
            center = (bbmax + bbmin) / 2
            axis = (0 if span.x > span.z else 2) if span.x > span.y else (1 if span.y > span.z else 2)

            dir = Vector((0, 0, 0))
            dir[axis] = -1

            plane = dir.to_4d()
            plane.w = -dir.dot(center)

        posOctPolygons, negOctPolygons = partitionPolygons(octPolygons, plane, getter = lambda x: x.pos)

        posbbmin, posbbmax = calcPolygonBounds(posOctPolygons)
        negbbmin, negbbmax = calcPolygonBounds(negOctPolygons)

        if len(posOctPolygons) > 0: positive = createOctreeNode(posOctPolygons, octPlanes, posbbmin, posbbmax, depthLimit, windowManager, depth = depth + 1)
        if len(negOctPolygons) > 0: negative = createOctreeNode(negOctPolygons, octPlanes, negbbmin, negbbmax, depthLimit, windowManager, depth = depth + 1)

        return Rs2TreeNodeExport(bbmin, bbmax, plane, positive, negative, ())

    return Rs2TreeNodeExport(bbmin, bbmax, Vector((0, 0, 0, 0)), None, None, octPolygons)

def createBsptreeNode(bspPolygons, bspPlanes, bbmin, bbmax, windowManager, *, depth = 0):
    windowManager.progress_update(random.randint(0, 1))
    plane = None
    positive = None
    negative = None

    if depth < len(bspPlanes):
        plane = bspPlanes[depth]
        bspPlanes[depth] = None

    if plane is None:
        plane = choosePlane(bspPolygons, checkCounts = True, getter = lambda x: x.pos)

    if plane is not None:
        posBspPolygons, negBspPolygons = partitionPolygons(bspPolygons, plane, getter = lambda x: x.pos)

        posbbmin, posbbmax = calcPolygonBounds(posBspPolygons)
        negbbmin, negbbmax = calcPolygonBounds(negBspPolygons)

        if len(posBspPolygons) > 0: positive = createBsptreeNode(posBspPolygons, bspPlanes, posbbmin, posbbmax, windowManager, depth = depth + 1)
        if len(negBspPolygons) > 0: negative = createBsptreeNode(negBspPolygons, bspPlanes, negbbmin, negbbmax, windowManager, depth = depth + 1)

        return Rs2TreeNodeExport(bbmin, bbmax, plane, positive, negative, ())

    return Rs2TreeNodeExport(bbmin, bbmax, Vector((0, 0, 0, 0)), None, None, bspPolygons)

# Counter-clockwise, normals face away
def createBoundsQuad(bbmin, bbmax, side):
    side = int(side)
    odd = bool(side % 2)
    a0 = side // 2
    a1 = (a0 + 1) % 3
    a2 = (a0 + 2) % 3
    axis = bbmin[a0] if odd else bbmax[a0]

    vertices = [Vector((0, 0, 0)) for _ in range(4)]

    vertices[0][a0] = axis
    vertices[0][a1] = bbmin[a1]
    vertices[0][a2] = bbmin[a2]

    vertices[1][a0] = axis
    vertices[1][a1] = bbmin[a1]
    vertices[1][a2] = bbmax[a2]

    vertices[2][a0] = axis
    vertices[2][a1] = bbmax[a1]
    vertices[2][a2] = bbmax[a2]

    vertices[3][a0] = axis
    vertices[3][a1] = bbmax[a1]
    vertices[3][a2] = bbmin[a2]

    vertices = tuple(vertices) if odd else tuple(reversed(vertices))

    normal = Vector((0, 0, 0))
    normal[a0] = -1 if odd else 1

    return Col1BoundaryPolygon(4, vertices, normal)

def createColTriangles(polygons):
    triangles = []

    for polygon in polygons:
        vertexPairs = enumerate(polygon.vertices)
        vertexPairs = tuple((v1, v2, vertex1, vertex2) for v1, vertex1 in vertexPairs for v2, vertex2 in vertexPairs if v1 != v2)

        for _, _, vertex1, vertex2 in vertexPairs:
            if vec3IsClose(vertex1, vertex2, RS_COORD_THRESHOLD):
                raise GZRS2DegeneratePolygonError("GZRS2: createColTriangles() found a degenerate polygon! Try using the \"Pre-process Geometry\" operation or turn on the Mesh Analyzer and set it to \"Intersect\" to search for issues!")

    for polygon in polygons:
        for v in range(polygon.vertexCount - 2):
            v1 = polygon.vertices[0].copy()
            v2 = polygon.vertices[v + 1].copy()
            v3 = polygon.vertices[v + 2].copy()
            normal = polygon.normal.normalized()

            triangles.append(ColTriangle((v1, v2, v3), normal))

    return tuple(triangles)

def createVertexIndex(list, new):
    for i, item in enumerate(list):
        if vec3IsClose(item, new, RS_COORD_THRESHOLD):
            return i

    list.append(new)

    return len(list) - 1

def getPartitionPolygon(plane, boundsPolygons):
    vertices = []
    outputPolygons = []

    # Record points of intersection
    for polygon in boundsPolygons:
        signs, posCount, negCount = calcVertexPlaneInfo(polygon, plane)

        # Ignore and delete coplanar polygons
        if posCount == 0 and negCount == 0:
            continue

        for i in range(polygon.vertexCount):
            o = (i + 1) % polygon.vertexCount

            v1 = polygon.vertices[i]
            v2 = polygon.vertices[o]

            sign1 = signs[i]
            sign2 = signs[o]

            if sign1 == 0: createVertexIndex(vertices, v1)
            elif sign2 != 0 and sign1 != sign2:
                pos, _ = calcPlaneEdgeIntersection(plane, v1, v2)

                createVertexIndex(vertices, pos)

        outputPolygons.append(polygon)

    vertices = tuple(vertices)
    outputPolygons = tuple(outputPolygons)

    vertexCount = len(vertices)

    if vertexCount < 3:
        return False, None, None, outputPolygons

    # Sort points by angle
    center = Vector((0, 0, 0))
    for vertex in vertices: center += vertex
    center /= vertexCount

    up = plane.xyz.copy()
    forward = vertices[0] - center
    right = forward.cross(up)

    up.normalize()
    forward.normalize()
    right.normalize()

    translation = Matrix.Translation(-center)
    rotation = Matrix((right, forward, up)).to_4x4()
    matrix = rotation @ translation

    vertices = sorted(vertices, key = lambda x: calcVertexPlaneAngle(x, matrix))

    # Positive must face away
    posVertices = tuple(vertex.copy() for vertex in reversed(vertices))
    negVertices = tuple(vertex.copy() for vertex in vertices)

    return True, Col1BoundaryPolygon(vertexCount, posVertices, -up.copy()), Col1BoundaryPolygon(vertexCount, negVertices, up.copy()), outputPolygons

def createColtreeNode(colPolygons, boundsPolygons, windowManager, *, depth = 0):
    windowManager.progress_update(random.randint(0, 1))

    colPolygonCount = len(colPolygons)
    boundsPolygonCount = len(boundsPolygons)

    # print("\t" * depth, "Create:", colPolygonCount, boundsPolygonCount)

    if colPolygonCount == 0:
        if boundsPolygonCount == 0:
            # print("\t" * depth, "Empty!")
            return None

        boundsVertices = []
        boundsIndices = tuple(tuple(createVertexIndex(boundsVertices, vertex) for vertex in polygon.vertices) for polygon in boundsPolygons)
        boundsVertices = tuple(boundsVertices)

        bevelPlanes = []

        polygonPairs = enumerate(boundsPolygons)
        polygonPairs = tuple((p1, p2, polygon1, polygon2) for p1, polygon1 in polygonPairs for p2, polygon2 in polygonPairs if p1 != p2)

        # Create planes for convex edges sharper than a specified threshold
        for p1, p2, polygon1, polygon2 in polygonPairs:
            indexList1 = boundsIndices[p1]
            indexList2 = boundsIndices[p2]

            indexCount1 = len(indexList1)
            indexCount2 = len(indexList2)

            indices1 = tuple((i, (i + 1) % indexCount1) for i in range(indexCount1))
            indices2 = tuple((i, (i + 1) % indexCount2) for i in range(indexCount2))

            indices = tuple((indexList1[i1], indexList1[i2], indexList2[i3], indexList2[i4]) for i1, i2 in indices1 for i3, i4 in indices2)

            for i1, i2, i3, i4 in indices:
                if (i1 == i2 and i3 == i4) or (i1 == i4 and i2 == i3):
                    normal1 = polygon1.normal
                    normal2 = polygon2.normal

                    if normal1.dot(normal2) < math.cos(math.radians(110)):
                        halfNormal = normal1 + normal2
                        halfNormal.normalize()

                        plane = halfNormal.to_4d()
                        plane.w = -halfNormal.dot(boundsVertices[i1])

                        bevelPlanes.append(plane)

        # Create planes for convex vertices
        for i, vertex1 in enumerate(boundsVertices):
            normals = []
            averageNormal = Vector((0, 0, 0))

            # Consider the normal of each polygon this vertex is connected to
            for p, polygon in enumerate(boundsPolygons):
                indices = boundsIndices[p]
                indexCount = polygon.vertexCount

                for v, vertex2 in enumerate(polygon.vertices):
                    if indices[v] != i:
                        continue

                    normals.append(polygon.normal)

                    # Weight the accumulation based on the angle between the edges
                    e1 = polygon.vertices[(v + 1 + indexCount) % indexCount] - vertex2
                    e2 = polygon.vertices[(v - 1 + indexCount) % indexCount] - vertex2

                    len1 = e1.length
                    len2 = e2.length

                    if math.isclose(len1, 0, abs_tol = RS_COORD_THRESHOLD): continue
                    if math.isclose(len2, 0, abs_tol = RS_COORD_THRESHOLD): continue

                    costheta = e1.dot(e2) / (len1 * len2)

                    if costheta > 1 or costheta < -1: continue

                    theta = math.acos(costheta)

                    averageNormal += polygon.normal * theta

                    break

            # Verify convexity
            normalPairs = enumerate(normals)
            normalPairs = tuple((normal1, normal2) for n1, normal1 in normalPairs for n2, normal2 in normalPairs if n1 != n2)

            if all((normal1.dot(normal2) >= 0 for normal1, normal2 in normalPairs)):
                continue

            averageNormal.normalize()

            plane = averageNormal.to_4d()
            plane.w = -averageNormal.dot(vertex1)

            bevelPlanes.append(plane)

        bevelPlanes = tuple(bevelPlanes)

        # print("\t" * depth, "Export solid:", len(boundsPolygons))
        result = Col1TreeNode(Vector((0, 0, 0, 0)), True, None, None, createColTriangles(boundsPolygons))

        for plane in bevelPlanes:
            # print("\t" * depth, "Export bevel:", plane)
            result = Col1TreeNode(plane, False, None, result, ())

        return result

    if (plane := choosePlane(colPolygons)):
        # print("\t" * depth, "Plane:", plane)
        posColPolygons, negColPolygons = partitionPolygons(colPolygons, plane)

        append, posPolygon, negPolygon, boundsPolygons = getPartitionPolygon(plane, boundsPolygons)
        posBoundsPolygons, negBoundsPolygons = partitionPolygons(boundsPolygons, plane, markUsed = False, tuplize = False)

        if append:
            posBoundsPolygons.append(posPolygon)
            negBoundsPolygons.append(negPolygon)

        posBoundsPolygons = tuple(posBoundsPolygons)
        negBoundsPolygons = tuple(negBoundsPolygons)

        # print("\t" * depth, "Positive:", len(posColPolygons), len(posBoundsPolygons))
        positive = createColtreeNode(posColPolygons, posBoundsPolygons, windowManager, depth = depth + 1)
        # print("\t" * depth, "Negative:", len(negColPolygons), len(negBoundsPolygons))
        negative = createColtreeNode(negColPolygons, negBoundsPolygons, windowManager, depth = depth + 1)

        # print("\t" * depth, "Export fork:", bool(positive), bool(negative))
        return Col1TreeNode(plane, False, positive, negative, ())

    # print("\t" * depth, "Export hull:", colPolygonCount)
    return Col1TreeNode(Vector((0, 0, 0, 0)), False, None, None, createColTriangles(colPolygons))

def getTreeNodeCount(tree):
    count = 1

    if tree.negative: count += getTreeNodeCount(tree.negative)
    if tree.positive: count += getTreeNodeCount(tree.positive)

    return count

def getTreePolygonCount(tree):
    count = len(tree.polygons)

    if tree.negative: count += getTreePolygonCount(tree.negative)
    if tree.positive: count += getTreePolygonCount(tree.positive)

    return count

def getTreeTriangleCount(tree):
    count = len(tree.triangles)

    if tree.negative: count += getTreeTriangleCount(tree.negative)
    if tree.positive: count += getTreeTriangleCount(tree.positive)

    return count

def getTreeVertexCount(tree):
    count = sum(polygon.vertexCount for polygon in tree.polygons)

    if tree.negative: count += getTreeVertexCount(tree.negative)
    if tree.positive: count += getTreeVertexCount(tree.positive)

    return count

def getTreeIndicesCount(tree):
    count = sum(polygon.vertexCount - 2 for polygon in tree.polygons) * 3

    if tree.negative: count += getTreeIndicesCount(tree.negative)
    if tree.positive: count += getTreeIndicesCount(tree.positive)

    return count

def getTreeDepth(tree, *, depth = 0):
    if tree.negative: depth = max(depth, getTreeDepth(tree.negative))
    if tree.positive: depth = max(depth, getTreeDepth(tree.positive))

    depth = depth + 1

    return depth

def unpackLmImages(context, state):
    numCells = len(state.lmImages)

    if numCells == 0:
        return

    lmImage = state.lmImages[0]
    imageSize = lmImage.size

    if numCells == 1:
        blLmImage = bpy.data.images.new(f"{ state.filename }_LmImage", imageSize, imageSize)
        blLmImage.pixels = tuple(v for p in range(imageSize * imageSize) for v in (lmImage.data[p * 3 + 2], lmImage.data[p * 3 + 1], lmImage.data[p * 3 + 0], 1.0))
    elif numCells > 1:
        cellSpan = int(math.sqrt(nextSquare(numCells)))
        atlasSize = imageSize * cellSpan
        atlasPixels = [i for _ in range(atlasSize * atlasSize) for i in (0.0, 0.0, 0.0, 1.0)]

        for c, lmImage in enumerate(state.lmImages):
            cx = c % cellSpan
            cy = cellSpan - 1 - c // cellSpan

            for p in range(imageSize * imageSize):
                px = p % imageSize
                py = p // imageSize

                a = cx * imageSize
                a += cy * imageSize * atlasSize
                a += px + py * atlasSize

                atlasPixels[a * 4 + 0] = lmImage.data[p * 3 + 2]
                atlasPixels[a * 4 + 1] = lmImage.data[p * 3 + 1]
                atlasPixels[a * 4 + 2] = lmImage.data[p * 3 + 0]

        blLmImage = bpy.data.images.new(f"{ state.filename }_LmAtlas{ numCells }", atlasSize, atlasSize)
        blLmImage.pixels = atlasPixels

    blLmImage.pack()

    worldProps = ensureWorld(context).gzrs2
    worldProps.lightmapImage = blLmImage

    state.blLmImage = blLmImage

def packLmImageData(self, imageSize, floats, state, *, fromAtlas = False, atlasSize = 0, cx = 0, cy = 0):
    sopath = os.path.join(os.path.dirname(__file__), 'clib_gzrs2', 'clib_gzrs2.x86_64-w64-mingw32.so')
    success = True

    try:
        clib = ctypes.CDLL(sopath)
    except OSError as ex:
        print(f"GZRS2: Failed to load C library, defaulting to pure Python: { ex }, { sopath }")
        success = False

    if success:
        clib.packLmImageData.restype = py_object
        clib.packLmImageData.argtypes = [c_uint, py_object, c_bool, c_bool, c_bool, c_uint, c_uint, c_uint]

        try:
            return clib.packLmImageData(imageSize, floats, state.lmVersion4, state.mod4Fix, fromAtlas, atlasSize, cx, cy)
        except (ValueError, ctypes.ArgumentError) as ex:
            print(f"GZRS2: Failed to call C function, defaulting to pure Python: { ex }, { sopath }")

    pixelCount = imageSize ** 2

    if not state.lmVersion4:
        imageData = bytearray(pixelCount * 3)
        exportRange = (255 / 4) if state.mod4Fix else 255

        if not fromAtlas:
            for p in range(pixelCount):
                imageData[p * 3 + 0] = int(floats[p * 4 + 2] * exportRange)
                imageData[p * 3 + 1] = int(floats[p * 4 + 1] * exportRange)
                imageData[p * 3 + 2] = int(floats[p * 4 + 0] * exportRange)
        else:
            for p in range(pixelCount):
                px = p % imageSize
                py = p // imageSize

                f = cx * imageSize
                f += cy * imageSize * atlasSize
                f += px + py * atlasSize

                imageData[p * 3 + 0] = int(floats[f * 4 + 2] * exportRange)
                imageData[p * 3 + 1] = int(floats[f * 4 + 1] * exportRange)
                imageData[p * 3 + 2] = int(floats[f * 4 + 0] * exportRange)

    else:
        imageData = bytearray(pixelCount // 2)
        imageShorts = memoryview(imageData).cast('H')
        imageInts = memoryview(imageData).cast('I')
        missed = False

        blockLength = 4
        blockStride = blockLength ** 2
        blockCount = pixelCount // blockStride
        blockSpan = int(math.sqrt(blockCount))

        blocks = [[Vector((0, 0, 0)), Vector((0, 0, 0)), [Vector((0, 0, 0)) for _ in range(blockStride)]] for b in range(blockCount)]

        for b, block in enumerate(blocks):
            bx = b % blockSpan
            by = b // blockSpan
            maximum = Vector((0, 0, 0))
            minimum = Vector((1, 1, 1))
            maxlen2 = 0
            minlen2 = 3

            for p in range(blockStride):
                px = p % blockLength
                py = p // blockLength

                if not fromAtlas:
                    f = bx * blockLength
                    f += by * blockLength * imageSize
                    f += px + py * imageSize
                else:
                    f = cx * imageSize
                    f += cy * imageSize * atlasSize
                    f += bx * blockLength
                    f += by * blockLength * atlasSize
                    f += px + py * atlasSize

                pixel = Vector((floats[f * 4 + 0], floats[f * 4 + 1], floats[f * 4 + 2]))
                len2 = pixel.length_squared

                if len2 > maxlen2:
                    maxlen2 = len2
                    maximum = pixel

                if len2 < minlen2:
                    minlen2 = len2
                    minimum = pixel

                block[2][p] = pixel

            block[0] = maximum
            block[1] = minimum

        for b, block in enumerate(blocks):
            ushort1 = vectorToRGB565(block[0])
            ushort2 = vectorToRGB565(block[1])

            if ushort1 == ushort2:
                if ushort1 == 0:
                    imageShorts[b * 4 + 0] = ushort1 + 1
                    imageShorts[b * 4 + 1] = ushort1
                    imageInts[b * 2 + 1] = 21845 # 0x5555 -> 0101010101010101
                else:
                    imageShorts[b * 4 + 0] = ushort1
                    imageShorts[b * 4 + 1] = ushort1 - 1
                    imageInts[b * 2 + 1] = 0
            else:
                rgb1 = block[0]
                rgb2 = block[1]

                if ushort1 < ushort2:
                    ushort1, ushort2 = ushort2, ushort1
                    rgb1, rgb2 = rgb2, rgb1

                imageShorts[b * 4 + 0] = ushort1
                imageShorts[b * 4 + 1] = ushort2

                p0 = rgb1
                p1 = rgb2
                p2 = (2.0 * rgb1 + rgb2) / 3.0
                p3 = (2.0 * rgb2 + rgb1) / 3.0

                for p, pixel in enumerate(block[2]):
                    d0 = (p0 - pixel).length_squared
                    d1 = (p1 - pixel).length_squared
                    d2 = (p2 - pixel).length_squared
                    d3 = (p3 - pixel).length_squared

                    minimum = min(d0, d1, d2, d3)

                    s = p * 2

                    if minimum == d0:
                        imageInts[b * 2 + 1] &= ~(3 << (s + 0)) # Set both bits to 0        = 0
                    elif minimum == d1:
                        imageInts[b * 2 + 1] |=  (1 << (s + 0)) # Set bit 1 & clear bit 2   = 1
                        imageInts[b * 2 + 1] &= ~(1 << (s + 1))
                    elif minimum == d2:
                        imageInts[b * 2 + 1] &= ~(1 << (s + 0)) # Clear bit 1 & set bit 2   = 2
                        imageInts[b * 2 + 1] |=  (1 << (s + 1))
                    elif minimum == d3:
                        imageInts[b * 2 + 1] |=  (3 << (s + 0)) # Set both bits to 1        = 3
                    else:
                        missed = True

        if missed:
            print("Warning! Failed to pick a distance for one or more dds pixels!")

        imageShorts.release()
        imageInts.release()

    return imageData

def vectorToRGB565(vec):
    r = int((vec.x + 8 / 255.0) * 31) << 11
    g = int((vec.y + 4 / 255.0) * 63) << 5
    b = int((vec.z + 8 / 255.0) * 31)

    return r | g | b

def rgb565ToVector(rgb):
    r = ((rgb >> 11) & 0b11111 ) / 31.0
    g = ((rgb >>  5) & 0b111111) / 63.0
    b = ((rgb >>  0) & 0b11111 ) / 31.0

    return Vector((r, g, b))

def writeDDSHeader(file, imageSize, pixelCount, ddsSize):
    writeBytes(file, b'DDS ')
    writeUInt(file, ddsSize)
    # writeUInt(file, DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_MIPMAPCOUNT | DDSD_LINEARSIZE)
    writeUInt(file, DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_LINEARSIZE)
    writeInt(file, imageSize)
    writeInt(file, imageSize)
    writeUInt(file, pixelCount // 2)
    writeUInt(file, 0)
    writeUInt(file, 0) # writeUInt(file, mipCount)
    for _ in range(11):
        writeUInt(file, 0)

    writeUInt(file, 32)
    writeUInt(file, DDPF_FOURCC)
    writeBytes(file, b'DXT1')
    for _ in range(5):
        writeUInt(file, 0)

    # writeUInt(file, DDSCAPS_COMPLEX | DDSCAPS_TEXTURE | DDSCAPS_MIPMAP)
    writeUInt(file, DDSCAPS_TEXTURE)
    for _ in range(4):
        writeUInt(file, 0)

def writeBMPHeader(file, imageSize, bmpSize):
    writeBytes(file, b'BM')
    writeUInt(file, bmpSize)
    writeShort(file, 0)
    writeShort(file, 0)
    writeUInt(file, 14 + 40)

    writeUInt(file, 40)
    writeUInt(file, imageSize)
    writeUInt(file, imageSize)
    writeShort(file, 1)
    writeShort(file, 24)
    for _ in range(6):
        writeUInt(file, 0)

def generateLightmapData(self, image, numCells, state):
    if image is None:
        self.report({ 'ERROR' }, "GZRS2: No lightmap assigned! Check the World tab!")
        return False, False

    imageWidth, imageHeight = image.size
    mipCount = math.log2(imageWidth) if imageWidth != 0 else None

    if imageWidth < LM_MIN_SIZE or imageHeight < LM_MIN_SIZE or imageWidth != imageHeight or not mipCount.is_integer():
        self.report({ 'ERROR' }, f"GZRS2: Lightmap is not valid! Image must be a square, power of two texture with a side length greater than { LM_MIN_SIZE }! { image.name }")
        return False, False

    mipCount = int(mipCount)

    # Never atlas, we increase the lightmap resolution instead
    imageDatas = []
    imageSizes = []

    if numCells < 2:
        imageSize = imageWidth
        floats = image.pixels[:]

        imageDatas.append(packLmImageData(self, imageSize, floats, state))
        imageSizes.append(imageSize)
    '''
    else:
        cellSpan = int(math.sqrt(nextSquare(numCells)))
        atlasSize = imageWidth
        imageSize = atlasSize // cellSpan
        floats = image.pixels[:]

        for c in range(numCells):
            cx = c % cellSpan
            cy = cellSpan - 1 - c // cellSpan

            imageDatas.append(packLmImageData(self, imageSize, floats, state, fromAtlas = True, atlasSize = atlasSize, cx = cx, cy = cy))
            imageSizes.append(imageSize)
    '''

    return tuple(imageDatas), tuple(imageSizes)

def dumpImageData(imageDatas, imageSizes, imageCount, directory, filename, state):
    basename = os.path.join(directory, filename)
    ext = '.dds' if state.lmVersion4 else '.bmp'

    for i in range(imageCount):
        imageData = imageDatas[i]
        imageSize = imageSizes[i]

        imgpath = basename + f"_LmImage{ i }" + ext

        pixelCount = imageSize ** 2

        with open(imgpath, 'wb') as file:
            if state.lmVersion4:
                ddsSize = 76 + 32 + 20 + pixelCount // 2
                writeUInt(file, ddsSize)
                writeDDSHeader(file, imageSize, pixelCount, ddsSize)
            else:
                bmpSize = 14 + 40 + pixelCount * 3
                writeUInt(file, bmpSize)
                writeBMPHeader(file, imageSize, bmpSize)

            file.write(imageData)

def ensureLmMixGroup():
    group = bpy.data.node_groups.get('Lightmap Mix')

    if group is None:
        group = bpy.data.node_groups.new('Lightmap Mix',  'ShaderNodeTree')
        groupA = group.interface.new_socket(name = 'A', in_out = 'INPUT', socket_type = 'NodeSocketColor')
        groupB = group.interface.new_socket(name = 'B', in_out = 'INPUT', socket_type = 'NodeSocketColor')
        groupResult = group.interface.new_socket(name = 'Result', in_out = 'OUTPUT', socket_type = 'NodeSocketColor')

        groupA.default_value = (1.0, 1.0, 1.0, 1.0)
        groupB.default_value = (1.0, 1.0, 1.0, 1.0)
        groupResult.default_value = (1.0, 1.0, 1.0, 1.0)

        groupIn = group.nodes.new('NodeGroupInput')
        groupOut = group.nodes.new('NodeGroupOutput')
        groupToLinear = group.nodes.new('ShaderNodeGamma')
        groupMod4x = group.nodes.new('ShaderNodeMixRGB')
        groupTosRGB = group.nodes.new('ShaderNodeGamma')
        groupMix = group.nodes.new('ShaderNodeMixRGB')

        groupMod4x.label = 'Mod4'
        groupMix.label = 'Lightmap'

        groupMod4x.blend_type = 'MULTIPLY'
        groupMix.blend_type = 'MULTIPLY'

        groupMod4x.inputs[0].default_value = 0.0
        groupMix.inputs[0].default_value = 0.0

        groupToLinear.inputs[1].default_value = 1 / 2.2
        groupMod4x.inputs[1].default_value = (1.0, 1.0, 1.0, 1.0)
        groupTosRGB.inputs[1].default_value = 2.2
        groupMix.inputs[1].default_value = (1.0, 1.0, 1.0, 1.0)

        groupMod4x.inputs[2].default_value = (4.0, 4.0, 4.0, 1.0)
        groupMix.inputs[2].default_value = (1.0, 1.0, 1.0, 1.0)

        groupIn.location = (-540, 0)
        groupOut.location = (0, 0)
        groupToLinear.location = (-360, 120)
        groupMod4x.location = (-360, 0)
        groupTosRGB.location = (-360, -200)
        groupMix.location = (-180, 0)

        group.links.new(groupIn.outputs['A'], groupMix.inputs[1])
        group.links.new(groupIn.outputs['B'], groupToLinear.inputs[0])
        group.links.new(groupToLinear.outputs[0], groupMod4x.inputs[1])
        group.links.new(groupMod4x.outputs[0], groupTosRGB.inputs[0])
        group.links.new(groupTosRGB.outputs[0], groupMix.inputs[2])
        group.links.new(groupMix.outputs[0], groupOut.inputs[0])

        groupIn.select = False
        groupOut.select = False
        groupToLinear.select = False
        groupMod4x.select = False
        groupTosRGB.select = False
        groupMix.select = False

        group.use_fake_user = True

    return group

def clampLightAttEnd(attEnd, attStart):
    return max(attEnd, attStart + 0.001)

def calcLightSoftness(attStart, attEnd):
    attEnd = clampLightAttEnd(attEnd, attStart)
    return (attEnd - attStart) / attEnd

# TODO: Find a way to get sun lights to work properly with fog
'''
def updateLightSubtype(blLightObj):
    blLight = blLightObj.data
    props = blLight.gzrs2

    if props.lightSubtype == 'NONE':
        blLightObj.data.type = 'POINT'
        blLightObj.rotation_euler = Euler((0, 0, 0))
    else:
        target = Vector((0, 0, 0)) # TODO: Support for light targets using an object field property
        dir = target - blLightObj.location

        blLightObj.data.type = 'SUN'
        blLightObj.rotation_euler = dir.to_track_quat('-Z', 'Z').to_euler()
'''

def calcLightEnergy(blLightObj, context):
    blLight = blLightObj.data
    props = blLight.gzrs2
    worldProps = ensureWorld(context).gzrs2

    intensity = props.intensity
    attEnd = clampLightAttEnd(props.attEnd, props.attStart)

    if props.lightSubtype == 'NONE':
        intensity *= pow(worldProps.lightIntensity, 2) * pow(attEnd, 2)
    else:
        # TODO: Find a way to get sun lights to work properly with fog
        # intensity *= worldProps.sunIntensity
        intensity *= pow(worldProps.sunIntensity, 2) * pow(attEnd, 2) * 10

    intensity *= 2

    return intensity

def calcLightSoftSize(blLightObj, context):
    blLight = blLightObj.data
    props = blLight.gzrs2
    worldProps = ensureWorld(context).gzrs2

    attStart = props.attStart
    attEnd = clampLightAttEnd(props.attEnd, attStart)

    softSize = 1 - calcLightSoftness(attStart, attEnd)
    softSize *= worldProps.lightSoftSize
    softSize *= pow(attEnd / 1000, 0.5)
    softSize *= 2

    return softSize

def calcLightRender(blLightObj, context):
    blLight = blLightObj.data
    props = blLight.gzrs2

    dynamic = props.lightType == 'DYNAMIC'
    softness = calcLightSoftness(props.attStart, props.attEnd)
    castshadow = blLight.use_shadow
    hide = dynamic or (softness <= 0.1 and not castshadow)

    return hide

def compareColors(color1, color2):
    return all((math.isclose(color1[0],                 color2[0],                  abs_tol = RS_COLOR_THRESHOLD),
                math.isclose(color1[1],                 color2[1],                  abs_tol = RS_COLOR_THRESHOLD),
                math.isclose(color1[2],                 color2[2],                  abs_tol = RS_COLOR_THRESHOLD)))

def compareLights(light1, light2):
    return all((math.isclose(light1.color[0],           light2.color[0],            abs_tol = RS_COLOR_THRESHOLD),
                math.isclose(light1.color[1],           light2.color[1],            abs_tol = RS_COLOR_THRESHOLD),
                math.isclose(light1.color[2],           light2.color[2],            abs_tol = RS_COLOR_THRESHOLD),
                math.isclose(light1.energy,             light2.energy,              abs_tol = RS_LIGHT_THRESHOLD),
                math.isclose(light1.shadow_soft_size,   light2.shadow_soft_size,    abs_tol = RS_LIGHT_THRESHOLD)))

def groupLights(lights):
    groups = []
    skip = []

    for l1, light1 in enumerate(lights):
        if l1 in skip: continue
        else: skip.append(l1)

        matches = [light1]

        for l2, light2 in enumerate(lights):
            if l2 in skip: continue

            if compareLights(light1, light2):
                skip.append(l2)
                matches.append(light2)

        if len(lights) > 1:
            groups.append(matches)

    return groups

def createArrayDriver(target, targetPath, source, sourceProp, *, idType = 'OBJECT'):
    curves = source.driver_add(sourceProp)

    for c, curve in enumerate(curves):
        driver = curve.driver
        var = driver.variables.new()
        var.name = sourceProp
        var.targets[0].id_type = idType
        var.targets[0].id = target
        var.targets[0].data_path = f"{ targetPath }[{ c }]"
        driver.expression = sourceProp

    return curves

def createDriver(target, targetPath, source, sourceProp, *, idType = 'OBJECT'):
    curve = source.driver_add(sourceProp)

    driver = curve.driver
    var = driver.variables.new()
    var.name = sourceProp
    var.targets[0].id_type = idType
    var.targets[0].id = target
    var.targets[0].data_path = targetPath
    driver.expression = sourceProp

    return driver
