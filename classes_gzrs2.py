from dataclasses import dataclass, field
from typing import Any

import bpy, mathutils
from bpy.types import Material, ShaderNode, Mesh, Object
from mathutils import Vector

@dataclass
class GZRS2State:
    xmlMats:            list = field(default_factory = list)
    xmlLits:            list = field(default_factory = list)
    xmlObjs:            list = field(default_factory = list)
    xmlDums:            list = field(default_factory = list)
    xmlOccs:            list = field(default_factory = list)
    xmlFogs:            list = field(default_factory = list)
    xmlAmbs:            list = field(default_factory = list)
    xmlItms:            list = field(default_factory = list)

    bspBounds:          list = field(default_factory = list)
    bspVerts:           list = field(default_factory = list)
    bspPolys:           list = field(default_factory = list)
    colVerts:           list = field(default_factory = list)
    eluMats:            list = field(default_factory = list)
    eluMeshNodes:       list = field(default_factory = list)

    blMats:             list = field(default_factory = list)
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

    blFogMat:           Material    = None
    blFogShader:        ShaderNode  = None
    blFog:              Mesh        = None
    blFogObj:           Object      = None

    blDrivers:          list = field(default_factory = list)
    blDriverObj:        Object      = None

@dataclass
class BspVertex:
    pos:                Vector = (0, 0, 0)
    nor:                Vector = (0, 0, 0)
    uv:                 Vector = (0, 0)

@dataclass
class BspPolyData:
    materialID:         int = 0
    drawFlags:          int = 0
    vertexCount:        int = 0
    firstVertex:        int = 0

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
    isAlphaMap:         bool = False
    isDiffuseMap:       bool = False
    texName:            str = ""
    texBase:            str = ""
    texExt:             str = ""
    texDir:             str = ""
    isAniTex:           bool = False
    frameCount:         int = 0
    frameSpeed:         int = 0
    frameGap:           float = 0.0

@dataclass
class EluMeshNode:
    meshID:             int = 0
    matID:              int = 0
    parentMesh:         Any = None
    baseMesh:           Any = None
    meshName:           str = ""
    parentName:         str = ""
    baseMatrix:         Vector = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    etcMatrix:          Vector = None
    apScale:            Vector = None
    rotAxis:            Vector = None
    scaleAxis:          Vector = None
    rotAngle:           float = None
    scaleAngle:         float = None
    partsType:          str = None      # "eq_parts_etc"
    partsPosInfoType:   str = None      # "eq_parts_pos_info_etc"
    cutParts:           str = None      # "cut_parts_upper_body"
    lookAtParts:        str = None      # "lookat_parts_etc"
    weaponDummyType:    str = None      # "weapon_dummy_etc"
    alphaSortValue:     float = 0.0
    vertices:           list = None
    minVertex:          Vector = (0, 0, 0)
    maxVertex:          Vector = (0, 0, 0)
    faces:              list = None
    normals:            list = None
    vertexColors:       list = None
    physInfos:          list = None
    isDummy:            bool = False
    isDummyMesh:        bool = False
    isWeaponMesh:       bool = False
    isCollisionMesh:    bool = False
    isPhysMesh:         bool = False
    isClothMesh:        bool = False

@dataclass
class EluFace:
    index:              tuple = field(default_factory = tuple)
    uv:                 tuple = field(default_factory = tuple)
    matID:              int = 0
    sigID:              int = -1
    normal:             Vector = (0, 0, 0)

@dataclass
class EluNormalInfo:
    faceNormal:         Vector = (0, 0, 0)
    vertexNormals:      tuple = field(default_factory = tuple)

@dataclass
class EluPhysInfo:
    parentName:         tuple = field(default_factory = tuple)
    parentID:           tuple = field(default_factory = tuple)
    weight:             tuple = field(default_factory = tuple)
    offset:             tuple = field(default_factory = tuple)
    num:                int = 0
