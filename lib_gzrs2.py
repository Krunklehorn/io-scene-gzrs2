import bpy, os, math
from mathutils import Vector, Matrix
from contextlib import redirect_stdout

from .constants_gzrs2 import *
# from constants_gzrs2 import *

def pathExists(path):
    if os.path.exists(path): return path
    elif path == '': return False
    elif os.name != 'nt':
        path = os.path.normpath(path.lower())
        targets = iter(path[1:].split(os.sep))
        current = os.sep + next(targets)
        target = next(targets)

        while target is not None:
            dirpath, dirnames, filenames = next(os.walk(current))

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

def textureSearch(self, texBase, targetpath, state):
    ddsBase = f"{ texBase }.dds".replace('.dds.dds', '.dds')
    ddspath = os.path.join(state.directory, ddsBase)
    texpath = os.path.join(state.directory, texBase)

    ddsExists = pathExists(ddspath)
    if ddsExists: return ddsExists

    texExists = pathExists(texpath)
    if texExists: return texExists

    if targetpath is None: return None
    elif targetpath:
        texpath = os.path.join(state.directory, targetpath, texBase)
        ddspath = os.path.join(state.directory, targetpath, ddsBase)

        ddsExists = pathExists(ddspath)
        if ddsExists: return ddsExists

        texExists = pathExists(texpath)
        if texExists: return texExists

        parentDir = os.path.dirname(state.directory)
        targetDir = targetpath.split(os.sep)[0]

        for _ in range(MAX_UPWARD_DIRECTORY_SEARCH):
            dirpath, dirnames, filenames = next(os.walk(parentDir))

            for dirname in dirnames:
                if dirname.lower() == targetDir.lower():
                    texpath = os.path.join(parentDir, targetpath, texBase)
                    ddspath = os.path.join(parentDir, targetpath, ddsBase)

                    ddsExists = pathExists(ddspath)
                    if ddsExists: return ddsExists

                    texExists = pathExists(texpath)
                    if texExists: return texExists

                    return None

            parentDir = os.path.dirname(parentDir)

        self.report({ 'INFO' }, f"GZRS2: Upward directory not found for material during texture search: { texBase }, { targetpath }")

    for dirpath, dirnames, filenames in os.walk(state.directory):
        for filename in filenames:
            if filename == ddsBase or filename == texBase:
                return os.path.join(dirpath, filename)

    if not state.gzrsTexDir:
        parentDir = os.path.dirname(state.directory)

        for _ in range(MAX_UPWARD_DIRECTORY_SEARCH):
            dirpath, dirnames, filenames = next(os.walk(parentDir))

            for dirname in dirnames:
                if dirname.lower() == 'texture':
                    state.gzrsTexDir = os.path.join(dirpath, dirname)

                    for dirpath, dirnames, filenames in os.walk(state.gzrsTexDir):
                        for filename in filenames:
                            filepath = pathExists(os.path.join(dirpath, filename))

                            if filepath: state.gzrsTexDict[filename] = filepath
                            else:
                                self.report({ 'INFO' }, f"GZRS2: Texture found but pathExists() failed, potential case sensitivity issue: { filename }")
                                return None

                    break

            parentDir = os.path.dirname(parentDir)

    if texBase in state.gzrsTexDict: return state.gzrsTexDict[texBase]
    elif ddsBase in state.gzrsTexDict: return state.gzrsTexDict[ddsBase]
    else: self.report({ 'INFO' }, f"GZRS2: Texture search failed: { texBase }")

def resourceSearch(self, resourcename, state):
    resourcepath = os.path.join(state.directory, resourcename)
    if pathExists(resourcepath): return resourcepath

    if not state.rs3DataDir:
        parentDir = os.path.dirname(state.directory)

        for _ in range(MAX_UPWARD_DIRECTORY_SEARCH):
            dirpath, dirnames, filenames = next(os.walk(parentDir))

            for dirname in dirnames:
                if dirname.lower() == 'data':
                    state.rs3DataDir = os.path.join(dirpath, dirname)

                    for dirpath, dirnames, filenames in os.walk(state.rs3DataDir):
                        for filename in filenames:
                            splitname = filename.split(os.extsep)

                            if splitname[-1].lower() in ['xml', 'elu', 'dds']:
                                resourcepath = pathExists(os.path.join(dirpath, filename))

                                if resourcepath: state.rs3DataDict[filename] = resourcepath
                                else: self.report({ 'INFO' }, f"GZRS2: Resource found but pathExists() failed, potential case sensitivity issue: { filename }")

                    break

            if state.rs3DataDir: break
            else: parentDir = os.path.dirname(parentDir)

    if resourcename in state.rs3DataDict:
        return state.rs3DataDict[resourcename]

    splitname = resourcename.split(os.extsep)

    if splitname[-1].lower() in ['xml'] and splitname[-2].lower() in ['scene', 'prop']:
        eluname = f"{ splitname[0] }.elu"
        if eluname in state.rs3DataDict:
            self.report({ 'INFO' }, f"GZRS2: Resource found after missing scene.xml or prop.xml: { resourcename }, { eluname }")
            return state.rs3DataDict[eluname]

    self.report({ 'INFO' }, f"GZRS2: Resource search failed: { resourcename }")

def lcFindRoot(lc, collection):
    if lc.collection is collection: return lc
    elif len(lc.children) == 0: return None

    for child in lc.children:
        next = lcFindRoot(child, collection)

        if next is not None:
            return next

def getTexImage(bpy, texpath, alphamode, state):
    texImages = state.blTexImages.setdefault(texpath, {})

    if not alphamode in texImages:
        image = bpy.data.images.load(texpath)
        image.alpha_mode = alphamode
        texImages[alphamode] = image

    return texImages[alphamode]

def getMatNode(bpy, blMat, nodes, texpath, alphamode, x, y, state):
    matNodes = state.blMatNodes.setdefault(blMat, {})
    haveTexture = texpath in matNodes
    haveAlphaMode = haveTexture and alphamode in matNodes[texpath]

    if not haveTexture or not haveAlphaMode:
        texture = nodes.new(type = 'ShaderNodeTexImage')
        texture.image = getTexImage(bpy, texpath, alphamode, state)
        texture.location = (x, y)
        texture.select = True

        if not haveTexture:
            matNodes[texpath] = { alphamode: texture }
        elif not haveAlphaMode:
            matNodes[texpath][alphamode] = texture


    return matNodes[texpath][alphamode]

def setupErrorMat(state):
    blErrorMat = bpy.data.materials.new(f"{ state.filename }_Error")
    blErrorMat.use_nodes = False
    blErrorMat.diffuse_color = (1.0, 0.0, 1.0, 1.0)
    blErrorMat.roughness = 1.0
    blErrorMat.blend_method = 'BLEND'
    blErrorMat.shadow_method = 'NONE'

    state.blErrorMat = blErrorMat

def setupEluMat(self, eluMat, state):
    power = eluMat.power
    alphatest = eluMat.alphatest
    useopacity = eluMat.useopacity
    twosided = eluMat.twosided
    additive = eluMat.additive
    texName = eluMat.texName
    texBase = eluMat.texBase
    texDir = eluMat.texDir

    for eluMat2, blMat2 in state.blEluMatPairs:
        if (math.isclose(power, eluMat2.power, rel_tol = 0.01) and
            math.isclose(alphatest, eluMat2.alphatest, rel_tol = 0.01) and
            useopacity == eluMat2.useopacity and twosided == eluMat2.twosided and additive == eluMat2.additive and
            texName == eluMat2.texName and texBase == eluMat2.texBase and texDir == eluMat2.texDir):
            state.blEluMats.setdefault(eluMat.elupath, {})[eluMat.matID] = blMat2
            return

    blMat = bpy.data.materials.new(texName or f"Material_{ eluMat.matID }_{ eluMat.subMatID }")
    blMat.use_nodes = True

    tree = blMat.node_tree
    nodes = tree.nodes

    shader = nodes.get('Principled BSDF')
    shader.location = (20, 300)
    shader.select = False
    shader.inputs[7].default_value = power / 100.0

    nodes.active = shader
    nodes.get('Material Output').select = False

    if texBase:
        texpath = textureSearch(self, texBase, texDir, state)

        if texpath is not None:
            texture = getMatNode(bpy, blMat, nodes, texpath, 'STRAIGHT', -260, 300, state)

            tree.links.new(texture.outputs[0], shader.inputs[0])

            nodes.active = texture

            blMat.use_backface_culling = not twosided

            if alphatest > 0:
                blMat.blend_method = 'CLIP'
                blMat.shadow_method = 'CLIP'
                blMat.show_transparent_back = True
                blMat.use_backface_culling = False
                blMat.alpha_threshold = 1.0 - (alphatest / 100.0)

                tree.links.new(texture.outputs[1], shader.inputs[21])
            elif useopacity:
                blMat.blend_method = 'HASHED'
                blMat.shadow_method = 'HASHED'
                blMat.show_transparent_back = True
                blMat.use_backface_culling = False

                tree.links.new(texture.outputs[1], shader.inputs[21])

            if additive:
                blMat.blend_method = 'BLEND'
                blMat.show_transparent_back = True
                blMat.use_backface_culling = False

                add = nodes.new(type = 'ShaderNodeAddShader')
                transparent = nodes.new(type = 'ShaderNodeBsdfTransparent')

                add.location = (300, 140)
                transparent.location = (300, 20)

                add.select = False
                transparent.select = False

                tree.links.new(texture.outputs[0], shader.inputs[19])
                tree.links.new(shader.outputs[0], add.inputs[0])
                tree.links.new(transparent.outputs[0], add.inputs[1])
                tree.links.new(add.outputs[0], nodes.get('Material Output').inputs[0])
        else:
            self.report({ 'INFO' }, f"GZRS2: Texture not found for .elu material: { texpath }")

    state.blEluMats.setdefault(eluMat.elupath, {})[eluMat.matID] = blMat
    state.blEluMatPairs.append((eluMat, blMat))

def setupXmlEluMat(self, elupath, xmlEluMat, state):
    specular = xmlEluMat['SPECULAR_LEVEL']
    glossiness = xmlEluMat['GLOSSINESS']
    emission = xmlEluMat['SELFILLUSIONSCALE']
    alphatest = xmlEluMat['ALPHATESTVALUE']
    twosided = xmlEluMat['TWOSIDED']
    additive = xmlEluMat['ADDITIVE']

    for xmlEluMat2, blMat2 in state.blXmlEluMatPairs:
        if (math.isclose(specular, xmlEluMat2['SPECULAR_LEVEL'], rel_tol = 0.01) and
            math.isclose(glossiness, xmlEluMat2['GLOSSINESS'], rel_tol = 0.01) and
            math.isclose(emission, xmlEluMat2['SELFILLUSIONSCALE'], rel_tol = 0.01) and
            math.isclose(alphatest, xmlEluMat2['ALPHATESTVALUE'], rel_tol = 0.01) and
            twosided == xmlEluMat2['TWOSIDED'] and additive == xmlEluMat2['ADDITIVE'] and
            len(xmlEluMat['textures']) == len(xmlEluMat2['textures'])):
            match = True

            for t, texture in enumerate(xmlEluMat['textures']):
                textype = texture['type']
                texname = texture['name']

                if textype in XMLELU_TEXTYPES and texname:
                    texture2 = xmlEluMat2['textures'][t]
                    textype2 = texture2['type']
                    texname2 = texture2['name']

                    if textype2 in XMLELU_TEXTYPES and texname2:
                        if textype != textype2 or texname != texname2:
                            match = False
                            break

            if match:
                state.blXmlEluMats.setdefault(elupath, []).append(blMat2)
                return

    blMat = bpy.data.materials.new(f"{ state.filename }_{ xmlEluMat['name'] }")
    blMat.use_nodes = True

    tree = blMat.node_tree
    nodes = tree.nodes

    shader = nodes.get('Principled BSDF')
    shader.location = (20, 300)
    shader.select = False
    shader.inputs[6].default_value = glossiness / 100.0
    shader.inputs[7].default_value = specular / 100.0

    nodes.active = shader
    nodes.get('Material Output').select = False

    for texlayer in xmlEluMat['textures']:
        textype = texlayer['type']
        texname = texlayer['name']

        if textype in XMLELU_TEXTYPES:
            if texname:
                texpath = textureSearch(self, texname, '', state)

                if texpath is not None:
                    if textype == 'DIFFUSEMAP':
                        texture = getMatNode(bpy, blMat, nodes, texpath, 'CHANNEL_PACKED', -540, 300, state)
                        tree.links.new(texture.outputs[0], shader.inputs[0])
                    elif textype == 'SPECULARMAP':
                        texture = getMatNode(bpy, blMat, nodes, texpath, 'CHANNEL_PACKED', -540, 0, state)

                        invert = nodes.new(type = 'ShaderNodeInvert')
                        invert.location = (texture.location.x + 280, texture.location.y)

                        tree.links.new(texture.outputs[1], invert.inputs[1])
                        tree.links.new(invert.outputs[0], shader.inputs[9])
                    elif textype == 'SELFILLUMINATIONMAP':
                        texture = getMatNode(bpy, blMat, nodes, texpath, 'CHANNEL_PACKED', -540, -300, state)
                        tree.links.new(texture.outputs[0], shader.inputs[19])
                        shader.inputs[20].default_value = emission
                    elif textype == 'OPACITYMAP':
                        texture = getMatNode(bpy, blMat, nodes, texpath, 'CHANNEL_PACKED', -540, 300, state)
                        tree.links.new(texture.outputs[1], shader.inputs[21])

                        blMat.blend_method = 'CLIP'
                        blMat.shadow_method = 'CLIP'
                        blMat.alpha_threshold = alphatest / 255.0
                    elif textype == 'NORMALMAP':
                        texture = getMatNode(bpy, blMat, nodes, texpath, 'NONE', -540, -600, state)
                        texture.image.colorspace_settings.name = 'Non-Color'
                        normal = nodes.new(type = 'ShaderNodeNormalMap')
                        normal.location = (-260, -600)
                        tree.links.new(texture.outputs[0], normal.inputs[1])
                        tree.links.new(normal.outputs[0], shader.inputs[22])
                else:
                    self.report({ 'INFO' }, f"GZRS2: Texture not found for .elu.xml material: { texname }, { textype }")
            else:
                self.report({ 'INFO' }, f"GZRS2: .elu.xml material with empty texture name: { texname }, { textype }")
        else:
            self.report({ 'INFO' }, f"GZRS2: Unsupported texture type for .elu.xml material: { texname }, { textype }")

    blMat.use_backface_culling = not twosided

    if additive:
        blMat.blend_method = 'BLEND'
        blMat.show_transparent_back = True
        blMat.use_backface_culling = False

        add = nodes.new(type = 'ShaderNodeAddShader')
        add.location = (300, 140)

        transparent = nodes.new(type = 'ShaderNodeBsdfTransparent')
        transparent.location = (300, 20)

        tree.links.new(shader.outputs[0], add.inputs[0])
        tree.links.new(transparent.outputs[0], add.inputs[1])
        tree.links.new(add.outputs[0], nodes.get('Material Output').inputs[0])

    state.blXmlEluMats.setdefault(elupath, []).append(blMat)
    state.blXmlEluMatPairs.append((xmlEluMat, blMat))

def setupRsMesh(self, m, blMesh, state):
    meshVerts = []
    meshNorms = []
    meshFaces = []
    meshMatIDs = []
    meshUV1 = []
    meshUV2 = []
    meshUV3 = None

    if state.doLightmap:
        meshUV3 = []
        numCells = len(state.lmImages)
        cellSpan = int(math.sqrt(nextSquare(numCells)))

    found = False
    index = 0

    for l, leaf in enumerate(state.rsLeaves):
        if leaf.materialID == m or state.meshMode == 'BAKE':
            found = True

            if meshUV3 is not None and numCells > 1:
                c = state.lmImageIndices[l]
                cx = c % cellSpan
                cy = c // cellSpan

            for v in range(leaf.vertexOffset, leaf.vertexOffset + leaf.vertexCount):
                meshVerts.append(state.rsVerts[v].pos)
                meshNorms.append(state.rsVerts[v].nor)
                meshUV1.append(state.rsVerts[v].uv1)
                meshUV2.append(state.rsVerts[v].uv2)

                if meshUV3 is not None:
                    uv3 = state.lmUVs[v]

                    if numCells > 1:
                        uv3.x += cx
                        uv3.y -= cy
                        uv3 /= cellSpan

                    uv3.y += 1.0
                    meshUV3.append(uv3)

            meshFaces.append(tuple(range(index, index + leaf.vertexCount)))
            index += leaf.vertexCount

            if state.meshMode == 'BAKE':
                meshMatIDs.append(leaf.materialID)

    if state.meshMode == 'STANDARD' and not found:
        self.report({ 'INFO' }, f"GZRS2: Unused rs material slot: { m }, { state.xmlRsMats[m]['name'] }")
        return False

    blMesh.from_pydata(meshVerts, [], meshFaces)

    blMesh.use_auto_smooth = True
    blMesh.normals_split_custom_set_from_vertices(meshNorms)

    uvLayer1 = blMesh.uv_layers.new()
    for c, uv in enumerate(meshUV1): uvLayer1.data[c].uv = uv

    uvLayer2 = blMesh.uv_layers.new()
    for c, uv in enumerate(meshUV2): uvLayer2.data[c].uv = uv

    if meshUV3 is not None:
        uvLayer3 = blMesh.uv_layers.new()
        for c, uv in enumerate(meshUV3): uvLayer3.data[c].uv = uv

    blMesh.validate()
    blMesh.update()

    if state.meshMode == 'STANDARD': return True
    elif state.meshMode == 'BAKE': return tuple(meshMatIDs)

def setupElu(self, name, eluMesh, oneOfMany, collection, context, state):
    doNorms = len(eluMesh.normals) > 0
    doUV1 = len(eluMesh.uv1s) > 0
    doUV2 = len(eluMesh.uv2s) > 0
    doWeights = len(eluMesh.weights) > 0
    doSlots = len(eluMesh.slots) > 0 and not eluMesh.drawFlags & RM_FLAG_HIDE

    faces = []
    faceVerts = []
    faceNorms = [] if doNorms else None
    faceUV1 = [] if doUV1 else None
    faceUV2 = [] if doUV2 else None
    faceSlot = [] if doSlots else None
    groups = {} if doWeights else None
    index = 0

    blMesh = bpy.data.meshes.new(name)
    blMeshObj = bpy.data.objects.new(name, blMesh)

    for face in eluMesh.faces:
        degree = face.degree

        # Reverses the winding order for GunZ 1 elus
        for v in range(degree - 1, -1, -1) if eluMesh.version <= ELU_5007 else range(degree):
            faceVerts.append(eluMesh.vertices[face.ipos[v]])
            if doNorms: faceNorms.append(eluMesh.normals[face.inor[v]])
            if doUV1: faceUV1.append(eluMesh.uv1s[face.iuv1[v]])
            if doUV2: faceUV2.append(eluMesh.uv2s[face.iuv2[v]])

        faces.append(tuple(range(index, index + degree)))
        if doSlots: faceSlot.append(face.slotID)
        index += degree

    blMesh.from_pydata(faceVerts, [], faces)

    if doNorms:
        blMesh.use_auto_smooth = True
        blMesh.normals_split_custom_set_from_vertices(faceNorms)

    if doUV1:
        uvLayer1 = blMesh.uv_layers.new()
        for c, uv in enumerate(faceUV1): uvLayer1.data[c].uv = uv

    if doUV2:
        uvLayer2 = blMesh.uv_layers.new()
        for c, uv in enumerate(faceUV2): uvLayer2.data[c].uv = uv

    if doSlots:
        for p, id in enumerate(faceSlot): blMesh.polygons[p].material_index = id

    blMesh.validate()
    blMesh.update()

    if oneOfMany and eluMesh.version <= ELU_5007: # Rotates GunZ 1 elus to face forward when loading from a map
        blMeshObj.matrix_local = Matrix.Rotation(math.radians(-180.0), 4, 'Z') @ eluMesh.transform
    else:
        blMeshObj.matrix_local = eluMesh.transform

    if doWeights:
        modifier = blMeshObj.modifiers.new("Armature", 'ARMATURE')
        modifier.use_deform_preserve_volume = True

        index = 0

        for face in eluMesh.faces:
            degree = face.degree

            # Reverses the winding order for GunZ 1 elus
            for v in range(degree - 1, -1, -1) if eluMesh.version <= ELU_5007 else range(degree):
                weight = eluMesh.weights[face.ipos[v]]

                for d in range(weight.degree):
                    if eluMesh.version <= ELU_5007:
                        parentName = weight.meshName[d]
                        found = False

                        for p, parent in enumerate(state.eluMeshes):
                            if parent.meshName == parentName:
                                meshID = p
                                found = True
                                break

                        if not found:
                            self.report({ 'ERROR' }, f"GZRS2: Named search failed to find mesh id for weight group: { eluMesh.meshName }, { parentName }")
                    else:
                        meshID = weight.meshID[d]

                    if not meshID in groups:
                        boneName = state.eluMeshes[meshID].meshName
                        state.gzrsValidBones.add(boneName)
                        groups[meshID] = blMeshObj.vertex_groups.new(name = boneName)

                    groups[meshID].add([index], weight.value[d], 'REPLACE')

                index += 1

    elupath = eluMesh.elupath
    eluMatID = eluMesh.matID

    if eluMesh.version <= ELU_5007:
        if elupath in state.blEluMats:
            if eluMatID in state.blEluMats[elupath]:
                blMesh.materials.append(state.blEluMats[elupath][eluMatID])
            else:
                self.report({ 'INFO' }, f"GZRS2: Missing .elu material by index: { eluMesh.meshName }, { eluMatID }")
                blMesh.materials.append(state.blErrorMat)
        else:
            self.report({ 'INFO' }, f"GZRS2: No .elu material available by path: { eluMesh.meshName }")
            blMesh.materials.append(state.blErrorMat)
    else:
        if eluMatID < 0:
            if -1 in eluMesh.slotIDs:
                if not eluMesh.drawFlags & RM_FLAG_HIDE:
                    self.report({ 'INFO' }, f"GZRS2: Double negative material index: { eluMesh.meshName }, { eluMatID }, { eluMesh.slotIDs }")
                    blMesh.materials.append(state.blErrorMat)
            elif elupath in state.blXmlEluMats:
                for blXmlEluMat in state.blXmlEluMats[elupath]:
                    blMesh.materials.append(blXmlEluMat)
            else:
                self.report({ 'INFO' }, f"GZRS2: No .elu.xml material available after negative index: { eluMesh.meshName }, { eluMatID }")
                blMesh.materials.append(state.blErrorMat)
        else:
            if elupath in state.blXmlEluMats:
                if len(state.blXmlEluMats[elupath]) > eluMatID:
                    blMesh.materials.append(state.blXmlEluMats[elupath][eluMatID])
                else:
                    self.report({ 'INFO' }, f"GZRS2: Missing .elu.xml material by index: { eluMesh.meshName }, { eluMatID }")
                    blMesh.materials.append(state.blErrorMat)
            else:
                self.report({ 'INFO' }, f"GZRS2: No .elu.xml material available by path: { eluMesh.meshName }")
                blMesh.materials.append(state.blErrorMat)

    collection.objects.link(blMeshObj)

    for viewLayer in context.scene.view_layers:
        viewLayer.objects.active = blMeshObj

    if state.doCleanup:
        if state.logCleanup: print(eluMesh.meshName)

        def cleanupFunc():
            bpy.ops.object.select_all(action = 'DESELECT')
            blMeshObj.select_set(True)
            bpy.ops.object.shade_smooth(use_auto_smooth = doNorms)
            bpy.ops.object.select_all(action = 'DESELECT')

            bpy.ops.object.mode_set(mode = 'EDIT')

            bpy.ops.mesh.select_mode(type = 'VERT')
            bpy.ops.mesh.select_all(action = 'SELECT')
            bpy.ops.mesh.delete_loose()
            bpy.ops.mesh.select_all(action = 'SELECT')
            bpy.ops.mesh.remove_doubles(use_sharp_edge_from_normals = True)
            bpy.ops.mesh.select_all(action = 'DESELECT')

        if state.logCleanup:
            cleanupFunc()
            print()
        else:
            with redirect_stdout(state.silence):
                cleanupFunc()

    bpy.ops.object.mode_set(mode = 'OBJECT')

    state.blMeshes.append(blMesh)
    state.blMeshObjs.append(blMeshObj)

    if eluMesh.drawFlags & RM_FLAG_HIDE:
        blMeshObj.hide_viewport = True
        blMeshObj.hide_render = True

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
            self.report({ 'INFO' }, f"GZRS2: Parent not found for elu child mesh: { child.meshName }, { child.parentName }")

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
            cy = cellSpan - 1 - c // cellSpan # OpenGL -> DirectX

            for p in range(imageSize * imageSize):
                px = p % imageSize
                py = p // imageSize

                a = cx * imageSize
                a += cy * atlasSize * imageSize
                a += px + py * atlasSize

                atlasPixels[a * 4 + 0] = lmImage.data[p * 3 + 2]
                atlasPixels[a * 4 + 1] = lmImage.data[p * 3 + 1]
                atlasPixels[a * 4 + 2] = lmImage.data[p * 3 + 0]

        blLmImage = bpy.data.images.new(f"{ state.filename }_LmAtlas{ numCells }", atlasSize, atlasSize)
        blLmImage.pixels = atlasPixels

    blLmImage.pack()

    state.blLmImage = blLmImage

def packLmImageData(lmVersion4, imageSize, floats, fromAtlas = False, atlasSize = 0, cx = 0, cy = 0):
    pixelCount = imageSize ** 2

    if not lmVersion4:
        imageData = bytearray(pixelCount * 3)

        for p in range(pixelCount):
            if not fromAtlas:
                f = p
            else:
                px = p % imageSize
                py = p // imageSize

                f = cx * imageSize
                f += cy * atlasSize * imageSize
                f += px + py * atlasSize

            imageData[p * 3 + 0] = int(floats[f * 4 + 2] * 64)
            imageData[p * 3 + 1] = int(floats[f * 4 + 1] * 64)
            imageData[p * 3 + 2] = int(floats[f * 4 + 0] * 64)
    else:
        imageData = bytearray(pixelCount // 2)
        imageShorts = memoryview(imageData).cast('H')
        imageInts = memoryview(imageData).cast('I')

        blockLength = 4
        blockStride = blockLength ** 2
        blockCount = pixelCount // blockStride
        blockSpan = int(math.sqrt(blockCount))

        blocks = [[Vector((0, 0, 0)), Vector((0, 0, 0)), [Vector((0, 0, 0)) for _ in range(blockStride)]] for b in range(blockCount)]

        for b, block in enumerate(blocks):
            bx = b % blockSpan
            by = blockSpan - 1 - b // blockSpan # OpenGL -> DirectX
            maximum = Vector((0, 0, 0))
            minimum = Vector((1, 1, 1))
            maxlen2 = 0
            minlen2 = 3

            for p in range(blockStride):
                px = p % blockLength
                py = p // blockLength

                if not fromAtlas:
                    f = bx * blockLength
                    f += by * imageSize * blockLength
                    f += px + (blockLength - 1 - py) * imageSize # OpenGL -> DirectX
                else:
                    f = cx * imageSize
                    f += cy * atlasSize * imageSize
                    f += bx * blockLength
                    f += by * atlasSize * blockLength
                    f += px + (blockLength - 1 - py) * atlasSize # OpenGL -> DirectX

                pixel = Vector((floats[f * 4 + 0], floats[f * 4 + 1], floats[f * 4 + 2]))

                len2 = pixel.length_squared

                block[2][p] = pixel

                if len2 > maxlen2:
                    maxlen2 = len2
                    maximum = pixel

                if len2 < minlen2:
                    minlen2 = len2
                    minimum = pixel

            block[0] = maximum
            block[1] = minimum

        for b, block in enumerate(blocks):
            uint1 = VectorToRGB565(block[0])
            uint2 = VectorToRGB565(block[1])

            if uint1 == uint2:
                if uint1 == 0:
                    imageShorts[b * 4 + 0] = uint1 + 1
                    imageShorts[b * 4 + 1] = uint1
                    imageInts[b * 2 + 1] = 21845
                else:
                    imageShorts[b * 4 + 0] = uint1
                    imageShorts[b * 4 + 1] = uint1 - 1
                    imageInts[b * 2 + 1] = 0
            else:
                rgb1 = block[0]
                rgb2 = block[1]

                if uint1 < uint2:
                    uint1, uint2 = uint2, uint1
                    rgb1, rgb2 = rgb2, rgb1

                imageShorts[b * 4 + 0] = uint1
                imageShorts[b * 4 + 1] = uint2

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

        imageShorts.release()
        imageInts.release()

    return imageData

def VectorToRGB565(vec):
    r = int((vec.x + 8 / 255.0) * 31) << 11
    g = int((vec.y + 4 / 255.0) * 63) << 5
    b = int((vec.z + 8 / 255.0) * 31)

    return r | g | b

def RGB565ToVector(rgb):
    r = ((rgb >> 11) & 0b11111 ) / 31.0
    g = ((rgb >>  5) & 0b111111) / 63.0
    b = ((rgb >>  0) & 0b11111 ) / 31.0

    return Vector((r, g, b))

def setupLmMixGroup(state):
    if 'Lightmap Mix' in bpy.data.node_groups:
        state.lmMixGroup = bpy.data.node_groups['Lightmap Mix']
    else:
        group = bpy.data.node_groups.new('Lightmap Mix', 'ShaderNodeTree')
        groupA = group.inputs.new('NodeSocketColor', 'A')
        groupB = group.inputs.new('NodeSocketColor', 'B')
        groupResult = group.outputs.new('NodeSocketColor', 'Result')

        groupA.default_value = (1.0, 1.0, 1.0, 1.0)
        groupB.default_value = (1.0, 1.0, 1.0, 1.0)
        groupResult.default_value = (1.0, 1.0, 1.0, 1.0)

        groupIn = group.nodes.new('NodeGroupInput')
        groupOut = group.nodes.new('NodeGroupOutput')

        groupMix = group.nodes.new(type = 'ShaderNodeMixRGB')
        groupMix.blend_type = 'MULTIPLY'
        groupMix.inputs[0].default_value = 1.0
        groupMix.inputs[1].default_value = (1.0, 1.0, 1.0, 1.0)
        groupMix.inputs[2].default_value = (1.0, 1.0, 1.0, 1.0)

        groupIn.location = (-360, 0)
        groupOut.location = (0, 0)
        groupMix.location = (-180, 0)

        group.links.new(groupIn.outputs['A'], groupMix.inputs[1])
        group.links.new(groupIn.outputs['B'], groupMix.inputs[2])
        group.links.new(groupMix.outputs[0], groupOut.inputs[0])

        groupIn.select = False
        groupOut.select = False
        groupMix.select = True

        group.nodes.active = groupMix

        state.lmMixGroup = group

def compareLights(light1, light2):
    return all((math.isclose(light1.color[0],            light2.color[0],            rel_tol = 0.0001),
                math.isclose(light1.color[1],            light2.color[1],            rel_tol = 0.0001),
                math.isclose(light1.color[2],            light2.color[2],            rel_tol = 0.0001),
                math.isclose(light1.energy,              light2.energy,              rel_tol = 0.0001),
                math.isclose(light1.shadow_soft_size,    light2.shadow_soft_size,    rel_tol = 0.0001)))

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

def createArrayDriver(target, targetProp, sources, sourceProp):
    target[targetProp] = getattr(sources, sourceProp)
    curves = sources.driver_add(sourceProp)

    for c, curve in enumerate(curves):
        driver = curve.driver
        var = driver.variables.new()
        var.name = sourceProp
        var.targets[0].id = target
        var.targets[0].data_path = f"[\"{ targetProp }\"][{ c }]"
        driver.expression = var.name

    return curves

def createDriver(target, targetProp, source, sourceProp):
    target[targetProp] = getattr(source, sourceProp)
    curve = source.driver_add(sourceProp)

    driver = curve.driver
    var = driver.variables.new()
    var.name = sourceProp
    var.targets[0].id = target
    var.targets[0].data_path = f"[\"{ targetProp }\"]"
    driver.expression = var.name

    return driver
