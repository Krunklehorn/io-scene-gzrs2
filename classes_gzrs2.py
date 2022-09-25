from dataclasses import dataclass, field

import bpy, mathutils
from bpy.types import Material, ShaderNode, Mesh, Object, Armature, Bone
from mathutils import Vector, Matrix

@dataclass
class GZRS2State:
    convertUnits:       bool = False
    doCleanup:          bool = False
    doCollision:        bool = False
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
    logEluHeaders:      bool = False
    logEluMats:         bool = False
    logEluMeshNodes:    bool = False
    logVerboseIndices:  bool = False
    logVerboseWeights:  bool = False
    logCleanup:         bool = False

    xmlRsMats:          list = field(default_factory = list)
    xmlEluMats:         dict = field(default_factory = dict)
    xmlLits:            list = field(default_factory = list)
    xmlObjs:            list = field(default_factory = list)
    xmlDums:            list = field(default_factory = list)
    xmlOccs:            list = field(default_factory = list)
    xmlFogs:            list = field(default_factory = list)
    xmlAmbs:            list = field(default_factory = list)
    xmlItms:            list = field(default_factory = list)

    bspBounds:          list = field(default_factory = list)
    rsVerts:            list = field(default_factory = list)
    rsLeaves:           list = field(default_factory = list)
    smrPortals:         list = field(default_factory = list)
    smrCells:           list = field(default_factory = list)
    colVerts:           list = field(default_factory = list)
    eluMats:            list = field(default_factory = list)
    eluMeshes:          list = field(default_factory = list)

    blXmlRsMats:        list = field(default_factory = list)
    blXmlEluMats:       dict = field(default_factory = dict)
    blEluMats:          dict = field(default_factory = dict)
    blMeshes:           list = field(default_factory = list)
    blProps:            list = field(default_factory = list)

    blColMat:           Material    = None
    blColGeo:           Mesh        = None
    blColObj:           Object      = None

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
    faces:              list = None
    geometry:           list = None

@dataclass
class RsGeometry:
    vertexCount:        int = 0
    indexCount:         int = 0
    trees:              list = None

@dataclass
class RsTree:
    matCount:           int = 0
    lightmapID:         int = 0
    vertexCount:        int = 0
    vertexOffset:       int = 0

@dataclass
class EluMaterial:
    matID:              int = 0
    subMatID:           int = 0
    ambient:            Vector = (0, 0, 0, 0)
    diffuse:            Vector = (0, 0, 0, 0)
    specular:           Vector = (0, 0, 0, 0)
    power:              float = 0.0
    subMatCount:        int = 0
    texPath:            str = ""
    alphaPath:          str = ""
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
    version:            int = 0
    meshName:           str = ""
    parentName:         str = ""
    transform:          Matrix = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    vertices:           list = None
    normals:            list = None
    uv1s:               list = None
    uv2s:               list = None
    colors:             list = None
    faces:              list = None
    weights:            list = None
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
    ipos:               list = None
    inor:               list = None
    iuv1:               list = None
    iuv2:               list = None
    matID:              int = 0

@dataclass
class EluWeight:
    degree:             int = 0
    meshName:           list = None
    meshID:             list = None
    value:              list = None

@dataclass
class EluPhysInfo:
    parentName:         tuple = field(default_factory = tuple)
    parentID:           tuple = field(default_factory = tuple)
    weight:             tuple = field(default_factory = tuple)
    offset:             tuple = field(default_factory = tuple)
    num:                int = 0
