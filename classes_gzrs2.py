from dataclasses import dataclass, field
from io import StringIO

from bpy.types import Material, ShaderNode, Mesh, Object, Armature
from mathutils import Vector, Matrix

@dataclass
class GZRS2State:
    silentIO:           StringIO = field(default_factory = StringIO)
    filename:           str = ""
    directory:          str = ""

    convertUnits:       bool = False
    meshMode:           str = ""
    texSearchMode:      str = ""
    overwriteAction:    bool = False
    doCollision:        bool = False
    doNavigation:       bool = False
    doLightmap:         bool = False
    doLights:           bool = False
    doProps:            bool = False
    doDummies:          bool = False
    doOcclusion:        bool = False
    doFog:              bool = False
    doSounds:           bool = False
    doMisc:             bool = False
    doBounds:           bool = False
    doLightDrivers:     bool = False
    doFogDriver:        bool = False
    doBoneRolls:        bool = False
    doTwistConstraints: bool = False
    doCleanup:          bool = False

    logRsHeaders:       bool = False
    logRsPortals:       bool = False
    logRsCells:         bool = False
    logRsGeometry:      bool = False
    logRsTrees:         bool = False
    logRsPolygons:      bool = False
    logRsVerts:         bool = False
    logSceneNodes:      bool = False
    logBspHeaders:      bool = False
    logBspPolygons:     bool = False
    logBspVerts:        bool = False
    logColHeaders:      bool = False
    logColNodes:        bool = False
    logColTris:         bool = False
    logNavHeaders:      bool = False
    logNavData:         bool = False
    logLmHeaders:       bool = False
    logLmImages:        bool = False
    logEluHeaders:      bool = False
    logEluMats:         bool = False
    logEluMeshNodes:    bool = False
    logAniHeaders:      bool = False
    logAniNodes:        bool = False
    logVerboseIndices:  bool = False
    logVerboseWeights:  bool = False
    logCleanup:         bool = False

    gzrsValidBones:     set = field(default_factory = set)
    blTexImages:        dict = field(default_factory = dict)
    blMatNodes:         dict = field(default_factory = dict)

    rs2DataDir:         str = ""
    rs3DataDir:         str = ""
    rs3DataDict:        dict = field(default_factory = dict)

    rs3Graph:           list = field(default_factory = list)
    rs3DirLightCount:   int = 0
    rs3SpotLightCount:  int = 0
    rs3PointLightCount: int = 0
    rs3EffectCount:     int = 0
    rs3OccluderCount:   int = 0

    xmlRsMats:          list = field(default_factory = list)
    xmlEluMats:         dict = field(default_factory = dict)
    xmlGlbs:            list = field(default_factory = list)
    xmlLits:            list = field(default_factory = list)
    xmlObjs:            list = field(default_factory = list)
    xmlDums:            list = field(default_factory = list)
    xmlOccs:            list = field(default_factory = list)
    xmlFogs:            list = field(default_factory = list)
    xmlAmbs:            list = field(default_factory = list)
    xmlItms:            list = field(default_factory = list)
    xmlFlgs:            list = field(default_factory = list)
    xmlSmks:            list = field(default_factory = list)

    rsCPolygonCount:    int | None = None
    rsCVertexCount:     int | None = None
    rsBNodeCount:       int | None = None
    rsBPolygonCount:    int | None = None
    rsBVertexCount:     int | None = None
    rsONodeCount:       int | None = None
    rsOPolygonCount:    int | None = None
    rsOVertexCount:     int | None = None
    rsConvexVerts:      list = field(default_factory = list)
    rsOctreeVerts:      list = field(default_factory = list)
    rsConvexPolygons:   list = field(default_factory = list) # TODO: Improve performance of convex id matching
    rsOctreePolygons:   list = field(default_factory = list)
    rsOctreeBounds:     list = field(default_factory = list)
    smrPortals:         list = field(default_factory = list)
    smrCells:           list = field(default_factory = list)
    bspNodeCount:       int | None = None
    bspPolygonCount:    int | None = None
    bspVertexCount:     int | None = None
    bspTreeVerts:       list = field(default_factory = list)
    bspTreePolygons:    list = field(default_factory = list)
    bspTreeBounds:      list = field(default_factory = list)
    colVerts:           list = field(default_factory = list)
    navVerts:           list = field(default_factory = list)
    navFaces:           list = field(default_factory = list)
    navLinks:           list = field(default_factory = list)
    eluMats:            list = field(default_factory = list)
    eluMeshes:          list = field(default_factory = list)
    aniMaxTick:         int = 0
    aniMaxVisTick:      int = 0
    aniNodes:           list = field(default_factory = list)
    lmImages:           list = field(default_factory = list)
    lmPolygonOrder:     tuple = field(default_factory = tuple)
    lmLightmapIDs:      tuple = field(default_factory = tuple)
    lmUVs:              tuple = field(default_factory = tuple)

    blErrorMat:         Material    = None
    blXmlRsMats:        list = field(default_factory = list)
    blEluMats:          dict = field(default_factory = dict)
    blXmlEluMats:       dict = field(default_factory = dict)
    blBspMeshes:        list = field(default_factory = list)
    blOctMeshes:        list = field(default_factory = list)
    blSceneMeshes:      list = field(default_factory = list)
    blEluMeshes:        list = field(default_factory = list)
    blProps:            list = field(default_factory = list)

    blActors:           list = field(default_factory = list)
    blActorRoots:       dict = field(default_factory = dict)

    blConvexMesh:       Mesh        = None
    blConvexObj:        Object      = None

    blBakeMesh:         Mesh        = None
    blBakeObj:          Object      = None

    blColMat:           Material    = None
    blColMesh:          Mesh        = None
    blColObj:           Object      = None

    blNavMat:           Material    = None
    blNavFaces:         Mesh        = None
    blNavLinks:         Mesh        = None
    blNavFacesObj:      Object      = None
    blNavLinksObj:      Object      = None

    blLmImage:          list = field(default_factory = list)

    blLights:           list = field(default_factory = list)
    blBspMeshObjs:      list = field(default_factory = list)
    blOctMeshObjs:      list = field(default_factory = list)
    blSceneMeshObjs:    list = field(default_factory = list)
    blEluMeshObjs:      list = field(default_factory = list)
    blLightObjs:        list = field(default_factory = list)
    blPropObjs:         list = field(default_factory = list)
    blDummyObjs:        list = field(default_factory = list)
    blSoundObjs:        list = field(default_factory = list)
    blItemObjs:         list = field(default_factory = list)
    blOccObjs:          list = field(default_factory = list)
    blBspBBoxObjs:      list = field(default_factory = list)
    blOctBBoxObjs:      list = field(default_factory = list)

    blActorObjs:        list = field(default_factory = list)
    blNodeObjs:         list = field(default_factory = list)

    blEluMatPairs:      list = field(default_factory = list)
    blXmlEluMatPairs:   list = field(default_factory = list)
    blObjPairs:         list = field(default_factory = list)
    blBonePairs:        list = field(default_factory = list)
    blSmokePairs:       list = field(default_factory = list)

    blArmature:         Armature    = None
    blArmatureObj:      Object      = None

    blFogShader:        ShaderNode  = None

    blDrivers:          list = field(default_factory = list)
    blDriverObj:        Object      = None

#########################
####    RS IMPORT    ####
#########################

@dataclass
class Rs2ConvexVertex:
    pos:                Vector = (0, 0, 0)
    nor:                Vector = (0, 0, 0)
    uv1:                Vector = (0, 0)
    uv2:                Vector = (0, 0)
    oid:                int = 0

@dataclass
class RsConvexPolygon:
    matID:              int = 0
    drawFlags:          int = 0
    vertexCount:        int = 0
    vertexOffset:       int = 0

@dataclass
class Rs2TreeVertex:
    pos:                Vector = (0, 0, 0)
    nor:                Vector = (0, 0, 0)
    uv1:                Vector = (0, 0)
    uv2:                Vector = (0, 0)

@dataclass
class Rs2TreePolygon:
    matID:              int = 0
    convexID:           int = 0
    drawFlags:          int = 0
    vertexCount:        int = 0
    vertexOffset:       int = 0

@dataclass
class Rs3TreeVertex:
    pos:                Vector = (0, 0, 0)
    nor:                Vector = (0, 0, 0)
    col:                Vector = (0, 0, 0, 0) # TODO: Shader support for rs3 color data and vertex alpha data
    uv1:                Vector = (0, 0)
    uv2:                Vector = (0, 0)

@dataclass
class Rs3TreePolygon:
    matID:              int = 0
    drawFlags:          int = 0
    vertexCount:        int = 0
    vertexOffset:       int = 0

@dataclass
class Rs3Portal:
    name:               str = ""
    vertices:           tuple = field(default_factory = tuple)
    cellID1:            int = 0
    cellID2:            int = 0

@dataclass
class Rs3Cell:
    name:               str = ""
    planes:             tuple = field(default_factory = tuple)
    faces:              tuple = field(default_factory = tuple)
    geometry:           tuple = field(default_factory = tuple)

@dataclass
class Rs3Geometry:
    vertexCount:        int = 0
    indexCount:         int = 0
    trees:              tuple = field(default_factory = tuple)

@dataclass
class Rs3Tree:
    matCount:           int = 0
    lightmapID:         int = 0
    vertexCount:        int = 0
    vertexOffset:       int = 0

#########################
####   ELU  IMPORT   ####
#########################

@dataclass
class EluMaterial:
    elupath:            str = ""
    matID:              int = 0
    subMatID:           int = 0
    ambient:            Vector = (0, 0, 0, 0)
    diffuse:            Vector = (0, 0, 0, 0)
    specular:           Vector = (0, 0, 0, 0)
    exponent:           float = 0.0
    subMatCount:        int = 0
    texpath:            str = ""
    alphapath:          str = ""
    twosided:           bool = False
    additive:           bool = False
    alphatest:          int = 0
    useopacity:         bool = False
    texBase:            str = ""
    texName:            str = ""
    texExt:             str = ""
    texDir:             str = ""
    isAniTex:           bool = False
    frameCount:         int = 0
    frameSpeed:         int = 0
    frameGap:           float = 0.0

@dataclass
class EluMeshNode:
    elupath:            str = ""
    version:            int = 0
    meshName:           str = ""
    parentName:         str = ""
    drawFlags:          int = 0
    transform:          Matrix = ((0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0))
    vertices:           tuple = field(default_factory = tuple)
    normals:            tuple = field(default_factory = tuple)
    uv1s:               tuple = field(default_factory = tuple)
    uv2s:               tuple = field(default_factory = tuple)
    colors:             tuple = field(default_factory = tuple)
    faces:              tuple = field(default_factory = tuple)
    weights:            tuple = field(default_factory = tuple)
    slots:              tuple = field(default_factory = tuple)
    slotIDs:            tuple = field(default_factory = tuple)
    isDummy:            bool = False
    matID:              int = 0

@dataclass
class EluIndex:
    ipos:               int = 0
    inor:               int = 0
    iuv1:               int = 0
    iuv2:               int = 0

@dataclass
class EluFace:
    degree:             int = 0
    ipos:               tuple = field(default_factory = tuple)
    inor:               tuple = field(default_factory = tuple)
    iuv1:               tuple = field(default_factory = tuple)
    iuv2:               tuple = field(default_factory = tuple)
    slotID:             int = 0

@dataclass
class EluWeight:
    degree:             int = 0
    meshNames:          list = field(default_factory = list)
    meshIDs:            list = field(default_factory = list)
    values:             list = field(default_factory = list)
    offsets:            tuple = field(default_factory = tuple)

@dataclass
class EluPhysInfo:
    parentName:         tuple = field(default_factory = tuple)
    parentID:           tuple = field(default_factory = tuple)
    weight:             tuple = field(default_factory = tuple)
    offset:             tuple = field(default_factory = tuple)
    num:                int = 0

@dataclass
class EluSlot:
    slotID:             int = 0
    indexOffset:        int = 0
    faceCount:          int = 0
    maskID:             int = 0

@dataclass
class AniNodeTransform:
    meshName:           int = 0
    baseMat:            Matrix = ((0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0))
    posKeyCount:        int = 0
    posVectors:         tuple = field(default_factory = tuple)
    posTicks:           tuple = field(default_factory = tuple)
    rotKeyCount:        int = 0
    rotQuats:           tuple = field(default_factory = tuple)
    rotTicks:           tuple = field(default_factory = tuple)
    visKeyCount:        int = 0
    visValues:          tuple = field(default_factory = tuple)
    visTicks:           tuple = field(default_factory = tuple)

@dataclass
class AniNodeVertex:
    meshName:           int = 0
    vertexKeyCount:     int = 0
    vertexCount:        int = 0
    vertexTicks:        tuple = field(default_factory = tuple)
    vertexPositions:    tuple = field(default_factory = tuple)
    visKeyCount:        int = 0
    visValues:          tuple = field(default_factory = tuple)
    visTicks:           tuple = field(default_factory = tuple)

AniNodeBone = AniNodeTransform

@dataclass
class AniNodeTM:
    meshName:           int = 0
    firstMat:           Matrix = ((0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0))
    tmKeyCount:         int = 0
    tmMats:             tuple = field(default_factory = tuple)
    tmTicks:            tuple = field(default_factory = tuple)
    visKeyCount:        int = 0
    visValues:          tuple = field(default_factory = tuple)
    visTicks:           tuple = field(default_factory = tuple)

ANI_TYPES_ENUM = {
    AniNodeTransform: 'TRANSFORM',
    AniNodeVertex: 'VERTEX',
    AniNodeBone: 'BONE',
    AniNodeTM: 'TM'
}

@dataclass
class LmImage:
    size:               int = 0
    data:               tuple = field(default_factory = tuple)

##########################
####    ELU EXPORT    ####
##########################

@dataclass
class RSELUExportState:
    convertUnits:           bool = False
    uncapLimits:            bool = False
    filterMode:             str = 'ALL'
    includeChildren:        bool = False

    logEluHeaders:          bool = False
    logEluMats:             bool = False
    logEluMeshNodes:        bool = False
    logVerboseIndices:      bool = False
    logVerboseWeights:      bool = False

@dataclass
class EluMaterialExport:
    matID:              int = 0
    subMatID:           int = 0
    ambient:            Vector = (0, 0, 0, 0)
    diffuse:            Vector = (0, 0, 0, 0)
    specular:           Vector = (0, 0, 0, 0)
    exponent:           float = 0.0
    subMatCount:        int = 0
    texpath:            str = ""
    alphapath:          str = ""
    twosided:           bool = False
    additive:           bool = False
    alphatest:          int = 0

@dataclass
class EluMeshNodeExport:
    meshName:           str = ""
    parentName:         str = ""
    transform:          Matrix = ((0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0))
    apScale:            Vector = (0, 0, 0)
    rotAA:              Vector = (0, 0, 0, 0)
    stretchAA:          Vector = (0, 0, 0, 0)
    etcMatrix:          Matrix = ((0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0))
    vertexCount:        int = 0
    vertices:           tuple = field(default_factory = tuple)
    faceCount:          int = 0
    faces:              tuple = field(default_factory = tuple)
    colorCount:         int = 0
    colors:             tuple = field(default_factory = tuple)
    matID:              int = 0
    weightCount:        int = 0
    weights:            tuple = field(default_factory = tuple)
    slotIDs:            tuple = field(default_factory = tuple)

@dataclass
class EluFaceExport:
    indices:            tuple = field(default_factory = tuple)
    uv1s:               tuple = field(default_factory = tuple)
    slotID:             int = 0
    normal:             Vector = (0, 0, 0)
    normals:            tuple = field(default_factory = tuple)

@dataclass
class EluWeightExport:
    meshNames:          tuple = field(default_factory = tuple)
    values:             tuple = field(default_factory = tuple)
    meshIDs:            tuple = field(default_factory = tuple)
    degree:             int = 0
    offsets:            tuple = field(default_factory = tuple)

##########################
####    NAV EXPORT    ####
##########################

@dataclass
class RSNAVExportState:
    convertUnits:           bool = False

    logNavHeaders:          bool = False
    logNavData:             bool = False

#########################
####    LM EXPORT    ####
#########################

@dataclass
class RSLMExportState:
    doUVs:              bool = False
    lmVersion4:         bool = False

    logLmHeaders:       bool = False
    logLmImages:        bool = False
