import os

TEX_UPWARD_SEARCH_LIMIT =       4
RES_UPWARD_SEARCH_LIMIT =       5
XMLELU_TEXTYPES =               ['DIFFUSEMAP', 'SPECULARMAP', 'SELFILLUMINATIONMAP', 'OPACITYMAP', 'NORMALMAP']

if os.name == 'nt':
    XML_EXTENSIONS =            ['xml']
    BSP_EXTENSIONS =            ['bsp']
    COL_EXTENSIONS =            ['col', 'cl2']
    NAV_EXTENSIONS =            ['nav']
    LM_EXTENSIONS =             ['lm']
else:
    XML_EXTENSIONS =            ['xml', 'XML']
    BSP_EXTENSIONS =            ['bsp', 'BSP']
    COL_EXTENSIONS =            ['col', 'COL', 'cl2', 'CL2']
    NAV_EXTENSIONS =            ['nav', 'NAV']
    LM_EXTENSIONS =             ['lm', 'LM']

RS2_VALID_DATA_SUBDIRS =        ['Interface', 'Maps', 'Model', 'Quest', 'Sfx', 'Shader', 'Sound', 'System']
RS3_VALID_DATA_SUBDIRS =        ['Data', 'EngineRes']
RS3_VALID_DATA_SUBDIRS_LOWER =  ['data', 'engineres']

RS3_DATA_DICT_EXTENSIONS =      ['xml', 'elu', 'dds']

RS2_ID =                        0x12345678
RS2_VERSION =                   7
RS3_ID =                        0xface5678
RS3_VERSION1 =                  5
RS3_VERSION2 =                  6
RS3_VERSION3 =                  7
RS3_VERSION4 =                  8

RS_SUPPORTED_VERSIONS =         [ RS2_VERSION, RS3_VERSION1, RS3_VERSION2, RS3_VERSION3, RS3_VERSION4 ]

BSP_ID =                        0x35849298
BSP_VERSION =                   2

PAT_ID =                        0x09784348
PAT_VERSION =                   0

LM_ID =                         0x30671804
LM_VERSION =                    3
LM_VERSION_EXT =                4

COL1_ID =                       0x05050178f
COL1_VERSION =                  0
COL2_ID =                       0x59249834
COL2_VERSION =                  1

NAV_ID =                        0x08888888f
NAV_VERSION =                   2

RM_FLAG_ADDITIVE =              0x00000001
RM_FLAG_USEOPACITY =            0x00000002
RM_FLAG_TWOSIDED =              0x00000004
RM_FLAG_NOTWALKABLE =           0x00000008
RM_FLAG_CASTSHADOW =            0x00000010
RM_FLAG_RECEIVESHADOW =         0x00000020
RM_FLAG_PASSTHROUGH =           0x00000040
RM_FLAG_HIDE =                  0x00000080
RM_FLAG_PASSBULLET =            0x00000100
RM_FLAG_PASSROCKET =            0x00000200
RM_FLAG_USEALPHATEST =          0x00000400
RM_FLAG_NOSHADE =               0x00000800
RM_FLAG_AI_NAVIGATION =         0x00001000
RM_FLAG_COLLISION_MESH =        0x00002000
RM_FLAG_DUMMY_MESH =            0x00004000
RM_FLAG_CLOTH_MESH =            0x00008000
RM_FLAG_BONE_MESH =             0x00010000
RM_FLAG_COLLISION_CLOTH_MESH =  0x00020000
RM_FLAG_COLLISION_MESHONLY =    0x00040000
RM_FLAG_USEPARTSCOLOR =         0x00080000
RM_FLAG_TEXTURE_TRANSFORM =     0x00100000
RM_FLAG_EXTRA_UV =              0x00200000
RM_FLAG_UNKNOWN1 =              0x00400000
RM_FLAG_UNKNOWN2 =              0x00800000
RM_FLAG_OCCLUDER =              0x01000000
RM_FLAG_UNKNOWN3 =              0x02000000
RM_FLAG_UNKNOWN4 =              0x04000000
RM_FLAG_UNKNOWN5 =              0x08000000

AS_AABB =                       0x01
AS_SPHERE =                     0x02
AS_2D =                         0x10
AS_3D =                         0x20

ELU_ID =                        0x0107f060
ELU_0 =                         0x0             # Mangled 0x5007
ELU_11 =                        0x11
ELU_5001 =                      0x5001          # GunZ: The Duel, Alpha/Beta
ELU_5002 =                      0x5002
ELU_5003 =                      0x5003
ELU_5004 =                      0x5004          # GunZ: The Duel, Client
ELU_5005 =                      0x5005
ELU_5006 =                      0x5006
ELU_5007 =                      0x5007
ELU_5008 =                      0x5008          # GunZ 2: The Second Duel, Alpha
ELU_5009 =                      0x5009
ELU_500A =                      0x500A
ELU_500B =                      0x500B
ELU_500C =                      0x500C
ELU_500D =                      0x500D
ELU_500E =                      0x500E
ELU_500F =                      0x500F
ELU_5010 =                      0x5010
ELU_5011 =                      0x5011          # GunZ 2: The Second Duel, Client
ELU_5012 =                      0x5012
ELU_5013 =                      0x5013
ELU_5014 =                      0x5014

ELU_VERSIONS =                  [ ELU_0, ELU_11, ELU_5001, ELU_5002, ELU_5003, ELU_5004, ELU_5005, ELU_5006, ELU_5007,
                                  ELU_5008, ELU_5009, ELU_500A, ELU_500B, ELU_500C, ELU_500D, ELU_500E, ELU_500F, ELU_5010,
                                  ELU_5011, ELU_5012, ELU_5013, ELU_5014 ]

ELU_IMPORT_VERSIONS =           [ ELU_0, ELU_11, ELU_5004, ELU_5005, ELU_5006, ELU_5007, ELU_5008, ELU_5009, ELU_500A, ELU_500B, ELU_500C,
                                  ELU_500D, ELU_500E, ELU_500F, ELU_5010, ELU_5011, ELU_5012, ELU_5013, ELU_5014 ]

ELU_EXPORT_VERSIONS =           [ ELU_5007 ]

ELU_NAME_LENGTH =               40
ELU_PATH_LENGTH =               256
ELU_PHYS_KEYS =                 4

ANI_TICKS_PER_SECOND =          4800
ANI_FRAMES_PER_SECOND =         30
ANI_TICKS_PER_FRAME =           ANI_TICKS_PER_SECOND / ANI_FRAMES_PER_SECOND

ANI_ID =                        ELU_ID

ANI_0012 =                      0x0012
ANI_1001 =                      0x1001
ANI_1002 =                      0x1002
ANI_1003 =                      0x1003

ANI_VERSIONS =                  [ ANI_0012, ANI_1001, ANI_1002, ANI_1003 ]

ANI_TYPE_TRANSFORM =            0
ANI_TYPE_VERTEX =               1
ANI_TYPE_BONE =                 2
ANI_TYPE_TM =                   3
ANI_TYPES =                     [ ANI_TYPE_TRANSFORM, ANI_TYPE_VERTEX, ANI_TYPE_BONE, ANI_TYPE_TM ]
ANI_TYPES_PRETTY =              {
                                    ANI_TYPE_TRANSFORM: 'TRANSFORM',
                                    ANI_TYPE_VERTEX: 'VERTEX',
                                    ANI_TYPE_BONE: 'BONE',
                                    ANI_TYPE_TM: 'TM'
                                }
ANI_IMPORT_TYPES =              [ ANI_TYPE_TRANSFORM, ANI_TYPE_VERTEX, ANI_TYPE_BONE, ANI_TYPE_TM ]

RS_VERTEX_THRESHOLD =           0.0001
RS_VERTEX_THRESHOLD_SQUARED =   RS_VERTEX_THRESHOLD * RS_VERTEX_THRESHOLD
RS_COLOR_THRESHOLD =            0.0001
RS_LIGHT_THRESHOLD =            0.0001
RS_SOUND_THRESHOLD =            0.000001
ELU_VALUE_THRESHOLD =           0.01
ANI_VERTEX_THRESHOLD =          0.0001

DDSD_CAPS =                     0x00000001
DDSD_HEIGHT =                   0x00000002
DDSD_WIDTH =                    0x00000004
DDSD_PITCH =                    0x00000008
DDSD_PIXELFORMAT =              0x00001000
DDSD_MIPMAPCOUNT =              0x00020000
DDSD_LINEARSIZE =               0x00080000
DDSD_DEPTH =                    0x00800000

DDPF_ALPHAPIXELS =              0x00000001
DDPF_ALPHA =                    0x00000002
DDPF_FOURCC =                   0x00000004
DDPF_RGB =                      0x00000040
DDPF_YUV =                      0x00000200
DDPF_LUMINANCE =                0x00020000

DDSCAPS_COMPLEX =               0x00000008
DDSCAPS_TEXTURE =               0x00001000
DDSCAPS_MIPMAP =                0x00400000
