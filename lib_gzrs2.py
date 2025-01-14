import bpy, os, math, ctypes, shutil

from ctypes import *

from contextlib import redirect_stdout
from mathutils import Vector, Matrix, Euler

from .constants_gzrs2 import *
from .classes_gzrs2 import *

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
            state.rs2DataDir = os.path.dirname(dirpath)
            return True

        for dirname in dirnames:
            if token.lower() == dirname.lower():
                state.rs2DataDir = dirpath
                return True

    return False

def ensureRS3DataDict(self, state):
    if len(state.rs3DataDict) > 0: return

    for dirpath, _, filenames in os.walk(state.rs3DataDir):
        for filename in filenames:
            splitname = filename.split(os.extsep)

            if splitname[-1].lower() in RS3_DATA_DICT_EXTENSIONS:
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

            self.report({ 'WARNING' }, f"GZRS2: Texture search failed, no upward directory match: { texBase }, { texDir }")
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

    texpath = os.path.abspath(texpath)

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

    if (state.selectedOnly  and not modObj.select_get() or
        state.visibleOnly   and not modObj.visible_get()):
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

    basename = os.path.basename(path)
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
        links.new(source.outputs[0], destination.inputs[26]) # Emission Color
        destination.inputs[27].default_value = 1.0 # Emission Strength

    links.new(destination.outputs[0], add.inputs[0])
    links.new(transparent.outputs[0], add.inputs[1])
    links.new(add.outputs[0], mix.inputs[2])

    return add

def processRS2Texlayer(self, blMat, xmlRsMat, tree, links, nodes, shader, transparent, mix, state):
    texpath = xmlRsMat.get('DIFFUSEMAP')
    texBase, _, _, texDir = decomposePath(texpath)

    # TODO: Don't return on failure, continue with color preset

    if texBase == None:
        # self.report({ 'WARNING' }, f"GZRS2: .rs.xml material with no texture name: { texBase }")
        return

    if texBase == '':
        self.report({ 'WARNING' }, f"GZRS2: .rs.xml material with an empty texture name: { texBase }")
        return

    if not isValidTexBase(texBase):
        self.report({ 'WARNING' }, f"GZRS2: .rs.xml material with an invalid texture name: { blMat.name }, { texBase }")
        return

    success, texpath, loadFake = textureSearchLoadFake(self, texBase, texDir, False, state)

    if not success:
        self.report({ 'WARNING' }, f"GZRS2: Texture not found for .rs.xml material: { blMat.name }, { texBase }, { texDir }")

    texture = getMatImageTextureNode(bpy, blMat, nodes, texpath, 'STRAIGHT', -440, 300, loadFake, state)

    props = blMat.gzrs2
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
        self.report({ 'ERROR' }, f"GZRS2: Unsupported texture type for .elu.xml material: { texBase }, { texType }")
        return useopacity

    if texBase == None:
        self.report({ 'ERROR' }, f"GZRS2: .elu.xml material with no texture name: { texBase }, { texType }")
        return useopacity

    if texBase == '':
        self.report({ 'ERROR' }, f"GZRS2: .elu.xml material with an empty texture name: { texBase }, { texType }")
        return useopacity

    if not isValidTexBase(texBase):
        self.report({ 'ERROR' }, f"GZRS2: .elu.xml material with an invalid texture name: { texBase }, { texType }")
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

        shader.inputs[27].default_value = emission # Emission Strength
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

def setupColMesh(name, collection, context, extension, state):
    blColMat = setupDebugMat(name, (1.0, 0.0, 1.0, 0.25))

    blColMesh = bpy.data.meshes.new(name)
    blColObj = bpy.data.objects.new(name, blColMesh)

    blColMesh.gzrs2.meshType = 'RAW'

    colFaces = tuple(tuple(range(i, i + 3)) for i in range(0, len(state.colVerts), 3))

    blColMesh.from_pydata(state.colVerts, (), colFaces)
    blColMesh.validate()
    blColMesh.update()

    setObjFlagsDebug(blColObj)

    state.blColMat = blColMat
    state.blColMesh = blColMesh
    state.blColObj = blColObj

    blColObj.data.materials.append(blColMat)

    collection.objects.link(blColObj)

    for viewLayer in context.scene.view_layers:
        blColObj.hide_set(False, view_layer = viewLayer)
        viewLayer.objects.active = blColObj

    if state.doCleanup and state.logCleanup:
        print()
        print("=== Col Mesh Cleanup ===")
        print()

    if state.doCleanup:
        reportCount = 0

        bpy.ops.object.select_all(action = 'DESELECT')
        blColObj.select_set(True)
        bpy.ops.object.select_all(action = 'DESELECT')

        bpy.ops.object.mode_set(mode = 'EDIT')

        bpy.ops.mesh.select_mode(type = 'VERT')
        bpy.ops.mesh.select_all(action = 'SELECT')

        reportCount += 3

        def subCleanup():
            nonlocal reportCount

            for _ in range(10):
                bpy.ops.mesh.dissolve_degenerate()
                bpy.ops.mesh.delete_loose()
                bpy.ops.mesh.select_all(action = 'SELECT')
                bpy.ops.mesh.remove_doubles(threshold = 0.0001)
                reportCount += 4

        def cleanupFunc():
            nonlocal reportCount

            if extension == 'col':
                bpy.ops.mesh.intersect(mode = 'SELECT', separate_mode = 'ALL', threshold = 0.0001, solver = 'FAST')
                bpy.ops.mesh.select_all(action = 'SELECT')
                reportCount += 2

                subCleanup()

                bpy.ops.mesh.intersect(mode = 'SELECT', separate_mode = 'ALL')
                bpy.ops.mesh.select_all(action = 'SELECT')
                reportCount += 2

                subCleanup()

                for _ in range(10):
                    bpy.ops.mesh.fill_holes(sides = 0)
                    bpy.ops.mesh.tris_convert_to_quads(face_threshold = 0.0174533, shape_threshold = 0.0174533)
                    reportCount += 2

                    subCleanup()

                bpy.ops.mesh.vert_connect_nonplanar(angle_limit = 0.0174533)
                reportCount += 1

                subCleanup()
            elif extension == 'cl2':
                bpy.ops.mesh.remove_doubles(threshold = 0.0001, use_sharp_edge_from_normals = True)
                bpy.ops.mesh.tris_convert_to_quads(face_threshold = 0.0174533, shape_threshold = 0.0174533)
                reportCount += 2

            bpy.ops.mesh.dissolve_limited(angle_limit = 0.0174533)
            bpy.ops.mesh.delete_loose(use_faces = True)
            bpy.ops.mesh.select_all(action = 'SELECT')
            bpy.ops.mesh.normals_make_consistent(inside = True)
            bpy.ops.mesh.select_all(action = 'DESELECT')
            reportCount += 5

            bpy.ops.object.mode_set(mode = 'OBJECT')

        if state.logCleanup:
            print(name)
            cleanupFunc()
            print()
        else:
            with redirect_stdout(state.silentIO):
                cleanupFunc()

        deleteInfoReports(reportCount, context)

        blColMesh.gzrs2.meshType = 'COLLISION'

    bpy.ops.object.select_all(action = 'DESELECT')
    deleteInfoReports(1, context)

    return blColObj

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
            self.report({ 'WARNING' }, f"GZRS2: Texture not found for .elu material: { blMat.name }, { texBase }, { texDir }")

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
    shader.inputs[12].default_value = specular / 100.0 # Specular IOR Level

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
def setupRsConvexMesh(self, _, blMesh, state, *, allowLightmapUVs = True):
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

# TODO: Broken?
def deleteInfoReports(num, context):
    # This only works if the user has an Info area open somewhere
    # Luckily, the Scripting layout has one by default

    for workspace in bpy.data.workspaces:
        for screen in workspace.screens:
            for area in screen.areas:
                if area.ui_type != 'INFO': continue

                for region in area.regions:
                    if region.type != 'WINDOW': continue

                    with context.temp_override(screen = screen, area = area, region = region):
                        # Info operations don't support negative indices, so we count until select_pick() fails
                        infoCount = 0

                        while bpy.ops.info.select_pick(report_index = infoCount) != { 'CANCELLED' }:
                            infoCount += 1

                        bpy.ops.info.select_all(action = 'DESELECT')

                        # Start at the last and count backward
                        for i in range(infoCount - 1, max(-1, infoCount - 1 - num), -1):
                            bpy.ops.info.select_pick(report_index = i, extend = True)

                        bpy.ops.info.report_delete()
                        return

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
        modifier.use_deform_preserve_volume = True

        index = 0

        eluMeshNames = [eluMesh.meshName for eluMesh in state.eluMeshes]
        invalidBones = set()

        for face in eluMesh.faces:
            degree = face.degree

            # Reverses the winding order for GunZ 1 elus
            for v in range(degree - 1, -1, -1) if meshVersion <= ELU_5007 else range(degree):
                weight = eluMesh.weights[face.ipos[v]]

                for d in range(weight.degree):
                    if meshVersion <= ELU_5007: boneName = weight.meshNames[d]
                    else:                           boneName = state.eluMeshes[weight.meshIDs[d]].meshName

                    if boneName in eluMeshNames:    state.gzrsValidBones.add(boneName)
                    else:                           invalidBones.add(boneName)

                    if boneName not in meshGroups:
                        meshGroups[boneName] = blMeshObj.vertex_groups.new(name = boneName)

                    meshGroups[boneName].add((index,), weight.values[d], 'REPLACE')

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
        def cleanupFunc(blObj):
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

        if state.logCleanup:
            print(meshName)
            cleanupFunc(blMeshObj)
            print()
        else:
            with redirect_stdout(state.silentIO):
                cleanupFunc(blMeshObj)

        deleteInfoReports(9, context)

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

def createBackupFile(path):
    if not os.path.isfile(path):
        return

    directory = os.path.dirname(path)
    splitname = os.path.basename(path).split(os.extsep)
    filename = splitname[0]
    extension = '.' + splitname[1]

    if len(splitname) > 2:
        extension += '.' + splitname[2]

    shutil.copy2(path, os.path.join(directory, filename + "_backup") + extension)

# TODO: This pattern is ugly, wrap and generalize with a function call
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

# Divide into base-materials and sub-materials
#   Base:   One unique material with no parent, whether explicitly defined or implied by a placeholder
#   Sub:    Multiple unique materials or single unique material with parent
def divideMeshMats(blMeshObjs):
    def filterUnique(seenSet, item):
        notInside = item not in seenSet
        seenSet.add(item)

        return notInside

    seenSet = set()

    # We assume the meshes have no empty slots, parent forks or parent chains
    meshMatLists    = tuple((blMeshObj, tuple(matSlot.material for matSlot in blMeshObj.material_slots)) for blMeshObj in blMeshObjs)
    meshMatLists    = tuple(filter(lambda x: len(x[1]) > 0, meshMatLists))
    meshMatLists    = tuple(filter(lambda x: filterUnique(seenSet, x[1]), meshMatLists))

    singleMatLists  = tuple(filter(lambda x: len(set(x[1])) == 1,   meshMatLists))
    multiMatLists   = tuple(filter(lambda x: len(set(x[1])) > 1,    meshMatLists))

    singleMats  = set(matList[0]    for _, matList in singleMatLists)
    multiMats   = set(material      for _, matList in multiMatLists for material in matList)

    baseMats    = set(filter(lambda x: x.gzrs2.parent is None       and     x not in multiMats,     singleMats))
    subMats     = set(filter(lambda x: x.gzrs2.parent is not None   or      x in multiMats,         singleMats))
    subMats     |= multiMats

    baseMats    |= set(subMat.gzrs2.parent for subMat in subMats) - { None }
    baseMats    = tuple(sorted(baseMats, key = lambda x: (x.gzrs2.priority, x.name)))

    return baseMats, subMats, meshMatLists

def recordSubIDs(blSubMats, blPropMatLists):
    subIDsByMat = {}

    for blSubMat in blSubMats:
        for blPropObj, matList in blPropMatLists:
            for s, material in enumerate(matList):
                if material != blSubMat:
                    continue

                subIDs = subIDsByMat.setdefault(blSubMat, [s])

                if s not in subIDs:
                    subIDs.append(s)

    subIDsByMat = { blSubMat: tuple(sorted(subIDs)) for blSubMat, subIDs in subIDsByMat.items() }

    return subIDsByMat

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

def checkSubMatsCollisions(blSubMats, blPropMatLists, subIDsByMat, self = None):
    if not self:
        names = set()

    for blSubMat1, subIDs1 in subIDsByMat.items():
        for subID1 in subIDs1:
            for blSubMat2, subIDs2 in subIDsByMat.items():
                for subID2 in subIDs2:
                    if      subID1 != subID2:                                   continue
                    elif    blSubMat2 == blSubMat1:                             continue
                    elif    blSubMat2.gzrs2.parent != blSubMat1.gzrs2.parent:   continue
                    elif    self:
                        self.report({ 'ERROR' }, f"GZRS2: Child materials cannot link to the same parent if they occupy the same slot as another: { blSubMat.name }")
                        return { 'CANCELLED' }
                    else:
                        names.add(blSubMat1.name)
                        names.add(blSubMat2.name)

    if not self:
        return tuple(names), len(names) > 0

def generateMatGraph(blBaseMats, blSubMats, subIDsByMat, blPropObjs):
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

    for blPropObj in blPropObjs:
        subMats = tuple(matSlot.material for matSlot in blPropObj.material_slots)
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
    base = os.path.basename(path)
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

def getFilteredObjects(context, state):
    if state.selectedOnly:
        if state.includeChildren:
            objects = set()

            for object in context.selected_objects:
                objects.add(object)

                for child in object.children_recursive:
                    objects.add(child)
        else:
            objects = context.selected_objects
    else:
        objects = context.scene.objects

    objects = tuple(object for object in objects if object.visible_get()) if state.visibleOnly else tuple(objects)

    return objects

def nextSquare(x):
    result = 1

    while result ** 2 < x:
        result += 1

    return int(result ** 2)

def unpackLmImages(state):
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

    state.blLmImage = blLmImage

def packLmImageData(self, imageSize, floats, fromAtlas = False, atlasSize = 0, cx = 0, cy = 0):
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
            return clib.packLmImageData(imageSize, floats, self.lmVersion4, self.mod4Fix, fromAtlas, atlasSize, cx, cy)
        except (ValueError, ctypes.ArgumentError) as ex:
            print(f"GZRS2: Failed to call C function, defaulting to pure Python: { ex }")

    pixelCount = imageSize ** 2

    if not self.lmVersion4:
        imageData = bytearray(pixelCount * 3)
        exportRange = (255 / 4) if self.mod4Fix else 255

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

        groupMod4x.inputs[0].default_value = 1.0
        groupMix.inputs[0].default_value = 1.0

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
    return all((math.isclose(color1[0], color2[0], abs_tol = RS_COLOR_THRESHOLD),
                math.isclose(color1[1], color2[1], abs_tol = RS_COLOR_THRESHOLD),
                math.isclose(color1[2], color2[2], abs_tol = RS_COLOR_THRESHOLD)))

def compareLights(light1, light2):
    return all((math.isclose(light1.color[0],            light2.color[0],            abs_tol = RS_LIGHT_THRESHOLD),
                math.isclose(light1.color[1],            light2.color[1],            abs_tol = RS_LIGHT_THRESHOLD),
                math.isclose(light1.color[2],            light2.color[2],            abs_tol = RS_LIGHT_THRESHOLD),
                math.isclose(light1.energy,              light2.energy,              abs_tol = RS_LIGHT_THRESHOLD),
                math.isclose(light1.shadow_soft_size,    light2.shadow_soft_size,    abs_tol = RS_LIGHT_THRESHOLD)))

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
