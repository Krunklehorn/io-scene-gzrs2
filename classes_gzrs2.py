from dataclasses import dataclass, field
from io import StringIO

from bpy.types import Material, ShaderNode, Mesh, Object, Armature
from mathutils import Vector, Matrix

@dataclass
class GZRS2State:
    silence:            StringIO = field(default_factory = StringIO)
    filename:           str = ""
    directory:          str = ""

    convertUnits:       bool = False
    meshMode:           str = ""
    doCleanup:          bool = False
    doCollision:        bool = False
    doLightmap:         bool = False
    doLights:           bool = False
    doProps:            bool = False
    doDummies:          bool = False
    doOcclusion:        bool = False
    doFog:              bool = False
    doSounds:           bool = False
    doItems:            bool = False
    doBspBounds:        bool = False
    doLightDrivers:     bool = False
    doFogDriver:        bool = False
    doBoneRolls:        bool = False
    doTwistConstraints: bool = False

    logRsPortals:       bool = False
    logRsCells:         bool = False
    logRsGeometry:      bool = False
    logRsTrees:         bool = False
    logRsLeaves:        bool = False
    logRsVerts:         bool = False
    logSceneNodes:      bool = False
    logColHeaders:      bool = False
    logColNodes:        bool = False
    logColTris:         bool = False
    logLmHeaders:       bool = False
    logLmImages:        bool = False
    logEluHeaders:      bool = False
    logEluMats:         bool = False
    logEluMeshNodes:    bool = False
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
    xmlLits:            list = field(default_factory = list)
    xmlObjs:            list = field(default_factory = list)
    xmlDums:            list = field(default_factory = list)
    xmlOccs:            list = field(default_factory = list)
    xmlFogs:            list = field(default_factory = list)
    xmlAmbs:            list = field(default_factory = list)
    xmlItms:            list = field(default_factory = list)

    rsPolygonCount:     int = 0
    rsVertexCount:      int = 0
    bspBounds:          list = field(default_factory = list)
    rsVerts:            list = field(default_factory = list)
    rsLeaves:           list = field(default_factory = list)
    smrPortals:         list = field(default_factory = list)
    smrCells:           list = field(default_factory = list)
    colVerts:           list = field(default_factory = list)
    eluMats:            list = field(default_factory = list)
    eluMeshes:          list = field(default_factory = list)
    lmImages:           list = field(default_factory = list)
    lmPolygonIDs:       tuple = field(default_factory = tuple)
    lmIndices:          tuple = field(default_factory = tuple)
    lmUVs:              tuple = field(default_factory = tuple)
    lmMixGroup:         Object      = None

    blErrorMat:         Material    = None
    blXmlRsMats:        list = field(default_factory = list)
    blEluMats:          dict = field(default_factory = dict)
    blXmlEluMats:       dict = field(default_factory = dict)
    blMeshes:           list = field(default_factory = list)
    blProps:            list = field(default_factory = list)

    blActors:           list = field(default_factory = list)
    blActorRoots:       dict = field(default_factory = dict)

    blColMat:           Material    = None
    blColGeo:           Mesh        = None
    blColObj:           Object      = None

    blLmImage:          list = field(default_factory = list)

    blOccMat:           Material    = None
    blOccMGeo:          Mesh        = None
    blOccMObj:          Object      = None

    blLights:           list = field(default_factory = list)
    blMeshObjs:         list = field(default_factory = list)
    blLightObjs:        list = field(default_factory = list)
    blPropObjs:         list = field(default_factory = list)
    blDummyObjs:        list = field(default_factory = list)
    blSoundObjs:        list = field(default_factory = list)
    blItemObjs:         list = field(default_factory = list)
    blBBoxObjs:         list = field(default_factory = list)

    blActorObjs:        list = field(default_factory = list)
    blNodeObjs:         list = field(default_factory = list)

    blEluMatPairs:      list = field(default_factory = list)
    blXmlEluMatPairs:   list = field(default_factory = list)
    blObjPairs:         list = field(default_factory = list)
    blBonePairs:        list = field(default_factory = list)

    blArmature:         Armature    = None
    blArmatureObj:      Object      = None

    blFogMat:           Material    = None
    blFogShader:        ShaderNode  = None
    blFog:              Mesh        = None
    blFogObj:           Object      = None

    blDrivers:          list = field(default_factory = list)
    blDriverObj:        Object      = None

@dataclass
class RsVertex:
    pos:                Vector = (0, 0, 0)
    nor:                Vector = (0, 0, 0)
    col:                Vector = (0, 0, 0, 0)
    alpha:              float = 1
    uv1:                Vector = (0, 0)
    uv2:                Vector = (0, 0)

@dataclass
class RsLeaf:
    materialID:         int = 0
    drawFlags:          int = 0
    vertexCount:        int = 0
    vertexOffset:       int = 0

@dataclass
class RsPortal:
    name:               str = ""
    vertices:           tuple = field(default_factory = tuple)
    cellID1:            int = 0
    cellID2:            int = 0

@dataclass
class RsCell:
    name:               str = ""
    planes:             tuple = field(default_factory = tuple)
    faces:              tuple = field(default_factory = tuple)
    geometry:           tuple = field(default_factory = tuple)

@dataclass
class RsGeometry:
    vertexCount:        int = 0
    indexCount:         int = 0
    trees:              tuple = field(default_factory = tuple)

@dataclass
class RsTree:
    matCount:           int = 0
    lightmapID:         int = 0
    vertexCount:        int = 0
    vertexOffset:       int = 0

@dataclass
class EluMaterial:
    elupath:            str = ""
    matID:              int = 0
    subMatID:           int = 0
    ambient:            Vector = (0, 0, 0, 0)
    diffuse:            Vector = (0, 0, 0, 0)
    specular:           Vector = (0, 0, 0, 0)
    power:              float = 0.0
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
class LmImage:
    size:               int = 0
    data:               tuple = field(default_factory = tuple)

##########################
####    ELU EXPORT    ####
##########################

@dataclass
class RSELUExportState:
    convertUnits:           bool = False
    selectedOnly:           bool = False
    visibleOnly:            bool = False
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
    power:              float = 0.0
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
    scaleAA:            Vector = (0, 0, 0, 0)
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

#########################
####    LM EXPORT    ####
#########################

@dataclass
class RSLMExportState:
    doUVs:              bool = False
    lmVersion4:         bool = False

    logLmHeaders:       bool = False
    logLmImages:        bool = False
