import bpy, mathutils
from bpy.types import Material, ShaderNode, Mesh, Object
from dataclasses import dataclass, field
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

    blMats:             list = field(default_factory = list)
    blMeshes:           list = field(default_factory = list)

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
    pos:                Vector
    nor:                Vector
    uv:                 Vector

@dataclass
class BspPolyData:
    materialID:         int
    drawFlags:          int
    vertexCount:        int
    firstVertex:        int
