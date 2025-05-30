import os, math, re

PI_OVER_2                       = math.pi / 2
MESH_UNFOLD_THRESHOLD =         0.001

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

RS_PATH_LENGTH =                256

BSP_ID =                        0x35849298
BSP_VERSION =                   2

TREE_MAX_DEPTH =                10
TREE_MIN_NODE_SIZE =            1.5
TREE_MAX_NODE_POLYGON_COUNT =   200

FACING_POSITIVE                 = 0
FACING_NEGATIVE                 = 1
FACING_BOTH                     = 2
FACING_POS_COP                  = 3
FACING_NEG_COP                  = 4

PAT_ID =                        0x09784348
PAT_VERSION =                   0

LM_ID =                         0x30671804
LM_VERSION =                    3
LM_VERSION_EXT =                4
LM_MIN_SIZE =                   4 * 16 * 4 # BLOCK_LENGTH * MAX_THREADS * 4

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

ELU_MAX_TRIS =                  int(1024 * 100 / 3)
ELU_WEIGHT_THRESHOLD =          0.001
ELU_MAX_COAT_TRIS =             2000
ELU_MAX_FLAG_TRIS =             165

ELU_BONE_PREFIXES =             ('Bip', 'Bone', 'Dummy', 'obj_Bip', 'obj_Bone', 'obj_Dummy')
ELU_BONE_PREFIXES_ROOT =        ('Bip01', 'Bone01', 'Dummy01', 'obj_Bip01', 'obj_Bone01', 'obj_Dummy01')

ANI_ID =                        ELU_ID

ANI_0012 =                      0x0012
ANI_1001 =                      0x1001
ANI_1002 =                      0x1002
ANI_1003 =                      0x1003

ANI_VERSIONS =                  [ ANI_0012, ANI_1001, ANI_1002, ANI_1003 ]

ANI_TICKS_PER_SECOND =          4800
ANI_FRAMES_PER_SECOND =         30
ANI_TICKS_PER_FRAME =           ANI_TICKS_PER_SECOND / ANI_FRAMES_PER_SECOND

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

RS_COORD_THRESHOLD =            0.00001
RS_COORD_THRESHOLD_SQUARED =    RS_COORD_THRESHOLD * RS_COORD_THRESHOLD
RS_DOT_THRESHOLD =              0.0001
RS_DIR_THRESHOLD =              0.0001
RS_COLOR_THRESHOLD =            0.0001
RS_LIGHT_THRESHOLD =            0.0001
ELU_VALUE_THRESHOLD =           0.01
ANI_COORD_THRESHOLD =           0.00001

SPAWN_TYPE_DATA = (
    ('SOLO',        'Solo',         "Free-for-all and Quest spawn for players"),
    ('TEAM',        'Team',         "Team oriented spawn for players"),
    ('NPC',         'Enemy',        "Quest spawn for enemies"),
    ('BLITZ',       'Blitzkrieg',   "Spawns for the blitzkrieg gametype")
)

SPAWN_ENEMY_TYPE_DATA = (
    ('MELEE',       'Melee',        "Spawn for melee enemies"),
    ('RANGED',      'Ranged',       "Spawn for ranged enemies"),
    ('BOSS',        'Boss',         "Spawn for a boss enemy")
)

SPAWN_BLITZ_TYPE_DATA = (
    ('BARRICADE',   'Barricade',    "Spawn for barricades"),
    ('GUARDIAN',    'Guardian',     "Spawn for guardians"),
    ('RADAR',       'Radar',        "Spawn for radars"),
    ('HONORITEM',   'Treasure',     "Spawn for treasures")
)

SOUND_SPACE_DATA = (
    ('2D',          '2D',           "Two-dimensional, no stereo image. Good for reverberant, omnidirectional ambience"),
    ('3D',          '3D',           "Three-dimensional, stereo enabled. Good for directional sounds with a clear source")
)

SOUND_SHAPE_DATA = (
    ('AABB',        'AABB',         "Proximity through an axis-aligned bounding box toward it's center"),
    ('SPHERE',      'Sphere',       "Proximity through a sphere toward it's center")
)

ITEM_GAME_ID_DATA = (
    ('SOLO',        'Solo',         "Free-for-all gametypes"),
    ('TEAM',        'Team',         "Team oriented gametypes")
)

ITEM_TYPE_DATA = (
    ('HP',          'Health',       "Refills a portion of the player's health"),
    ('AP',          'Armor',        "Refills a portion of the player's armor"),
    ('BULLET',      'Bullet',       "Grants some ammunition for the player's gun")
)

SMOKE_TYPE_DATA = (
    ('SS',          'Smoke',        "Standard smoke, think Factory"),
    ('ST',          'Train Steam',  "Train steam"),
    ('TS',          'Train Smoke',  "Train smoke (unused)")
)

FLAG_WINDTYPE_DATA = (
    ('NO_WIND',                 'None',             ""),
    ('RANDOM_WIND',             'Random',           ""),
    ('CALM_WIND',               'Calm',             ""),
    ('LIGHT_AIR_WIND',          'Light Air',        ""),
    ('SLIGHT_BREEZE_WIND',      'Slight Breeze',    ""),
    ('GENTLE_BREEZE_WIND',      'Gentle Breeze',    ""),
    ('MODERATE_BREEZE_WIND',    'Moderate Breeze',  ""),
    ('FRESH_BREEZE_WIND',       'Fresh Breeze',     ""),
    ('STRONG_BREEZE_WIND',      'Strong Breeze',    ""),
    ('NEAR_GALE_WIND',          'Near Gale',        ""),
    ('GALE_WIND',               'Gale',             ""),
    ('STRONG_GALE_WIND',        'Strong Gale',      ""),
    ('STROM_WIND',              'Storm',            ""),
    ('VIOLENT_STROM_WIND',      'Violent Storm',    ""),
    ('HURRICANE_WIND',          'Hurricane',        "")
)

FLAG_LIMIT_AXIS_DATA = (
    ('X',           'X',        "X-axis"),
    ('Y',           'Y',        "Y-axis"),
    ('Z',           'Z',        "Z-axis")
)

FLAG_LIMIT_COMPARE_DATA = (
    ('LESS',        'Less',     "Vertex position less than the specified position along the specified axis"),
    ('GREATER',     'Greater',  "Vertex position greater than the specified position along the specified axis")
)

MESH_TYPE_DATA = (
    ('NONE',        'None',         "Not a Realspace mesh. Will not be exported"),
    ('RAW',         'Raw',          "Freshly imported, may need modification. Will not be exported"),
    ('WORLD',       'World',        "World mesh, lit statically, necessary for graphics, must be fully sealed with no leaks"),
    ('PROP',        'Prop',         "Prop mesh, lit dynamically, does not contribute to bsptree or octree data. Recorded in .rs.xml, exports to .elu"),
    ('COLLISION',   'Collision',    "Collision mesh, not visible, necessary for gameplay, must be fully sealed with no leaks"),
    ('NAVIGATION',  'Navigation',   "Navigation mesh, not visible, only necessary for Quest mode")
)

PROP_SUBTYPE_DATA = (
    ('NONE',        'None',         "Mesh has no special properties"),
    ('SKY',         'Sky',          "Mesh is assumed to be large and surrounding the entire map"),
    ('FLAG',        'Flag',         "Mesh is affected by wind forces")
)

CAMERA_TYPE_DATA = (
    ('WAIT',        'Wait',         "Camera position between rounds, mainly used for Team Deathmatch, Duel etc"),
    ('TRACK',       'Track',        "Camera position along a track, mainly used on the character select screen")
)

MATERIAL_SOUND_DATA = (
    ('NONE',    'None',             ""),
    ('CLO',     'Cloth (Missing)',  ""),
    ('CON',     'Concrete',         ""),
    ('DRT',     'Dirt',             ""),
    ('FSH',     'Flesh',            ""),
    ('GLS',     'Glass',            ""),
    ('MET',     'Metal',            ""),
    ('PNT',     'Gravel',           ""),
    ('SND',     'Sand',             ""),
    ('SNW',     'Snow',             ""),
    ('WAT',     'Water',            ""),
    ('WOD',     'Wood',             "")
)

SPAWN_TYPE_TAGS             = [data[0] for data in SPAWN_TYPE_DATA]
SPAWN_ENEMY_TYPE_TAGS       = [data[0] for data in SPAWN_ENEMY_TYPE_DATA]
SPAWN_BLITZ_TYPE_TAGS       = [data[0] for data in SPAWN_BLITZ_TYPE_DATA]
SOUND_SPACE_TAGS            = [data[0] for data in SOUND_SPACE_DATA]
SOUND_SHAPE_TAGS            = [data[0] for data in SOUND_SHAPE_DATA]
ITEM_GAME_ID_TAGS           = [data[0] for data in ITEM_GAME_ID_DATA]
ITEM_TYPE_TAGS              = [data[0] for data in ITEM_TYPE_DATA]
SMOKE_TYPE_TAGS             = [data[0] for data in SMOKE_TYPE_DATA]
FLAG_WINDTYPE_TAGS          = [data[0] for data in FLAG_WINDTYPE_DATA]
FLAG_LIMIT_AXIS_TAGS        = [data[0] for data in FLAG_LIMIT_AXIS_DATA]
FLAG_LIMIT_COMPARE_TAGS     = [data[0] for data in FLAG_LIMIT_COMPARE_DATA]
MESH_TYPE_TAGS              = [data[0] for data in MESH_TYPE_DATA]
PROP_SUBTYPE_TAGS           = [data[0] for data in PROP_SUBTYPE_DATA]
CAMERA_TYPE_TAGS            = [data[0] for data in CAMERA_TYPE_DATA]
MATERIAL_SOUND_TAGS         = [data[0] for data in MATERIAL_SOUND_DATA]

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
