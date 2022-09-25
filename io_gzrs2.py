import os, math
from struct import unpack

import mathutils
from mathutils import Vector, Matrix, Quaternion

def skipBytes(file, length):            return file.seek(length, 1)

def readChar(file):                     return unpack('<b', file.read(1))[0]
def readBool(file):                     return unpack('<?', file.read(1))[0]
def readBool32(file):                   return bool(readUInt(file))
def readUShort(file):                   return unpack('<H', file.read(2))[0]
def readShort(file):                    return unpack('<h', file.read(2))[0]
def readUInt(file):                     return unpack('<I', file.read(4))[0]
def readInt(file):                      return unpack('<i', file.read(4))[0]
def readFloat(file):                    return unpack('f', file.read(4))[0]
def readVec2(file):                     return unpack('2f', file.read(2 * 4))
def readVec3(file):                     return unpack('3f', file.read(3 * 4))
def readVec4(file):                     return unpack('4f', file.read(4 * 4))

def readBoolArray(file, length):        return tuple(readBool(file) for _ in range(length))
def readBool32Array(file, length):      return tuple(readBool32(file) for _ in range(length))
def readUShortArray(file, length):      return unpack(f'{ length }H', file.read(2 * length))
def readUShortArray(file, length):      return unpack(f'{ length }H', file.read(2 * length))
def readUIntArray(file, length):        return tuple(readUInt(file) for _ in range(length))
def readIntArray(file, length):         return tuple(readInt(file) for _ in range(length))
def readFloatArray(file, length):       return tuple(readFloat(file) for _ in range(length))
def readVec2Array(file, length):        return tuple(readVec2(file) for _ in range(length))
def readVec3Array(file, length):        return tuple(readVec3(file) for _ in range(length))
def readVec4Array(file, length):        return tuple(readVec4(file) for _ in range(length))
def readString(file, length):           return (str(file.read(length), 'utf-8').split('\x00', 1)[0]).strip()

def readUV2(file):
    x = readFloat(file)
    y = readFloat(file)

    y = -y

    return Vector((x, y))

def readUV3(file):
    x = readFloat(file)
    y = readFloat(file)
    skipBytes(file, 4)

    y = -y

    return Vector((x, y))

def readCoordinate(file, convertUnits, flipY):
    coord = Vector(readVec3(file))

    if convertUnits: coord *= 0.01
    if flipY: coord.y = -coord.y

    return coord

def readDirection(file, flipY):
    dir = Vector(readVec3(file))

    if flipY: dir.y = -dir.y

    return dir.normalized()

def readUV2Array(file, length): return tuple(readUV2(file) for _ in range(length))
def readUV3Array(file, length): return tuple(readUV3(file) for _ in range(length))

def readCoordinateArray(file, length, convertUnits, flipY):
    coords = readVec3Array(file, length)
    result = []

    for coord in coords:
        coord = Vector(coord)
        if convertUnits: coord *= 0.01
        if flipY: coord.y = -coord.y

        result.append(coord)

    return tuple(result)

def readDirectionArray(file, length, flipY):
    dirs = readVec3Array(file, length)
    result = []

    for dir in dirs:
        dir = Vector(dir)
        if flipY: dir.y = -dir.y

        result.append(dir.normalized())

    return tuple(result)

def readTransform(file, convertUnits, flipY):
    mat = Matrix(readVec4Array(file, 4))
    mat.transpose()

    loc, rot, sca = mat.decompose()
    if convertUnits: loc *= 0.01
    if flipY:
        rot.x = -rot.x
        rot.z = -rot.z
        loc.y = -loc.y

    return Matrix.LocRotScale(loc, rot, sca)

def readBounds(file, convertUnits, flipY):
    min = Vector(readCoordinate(file, convertUnits, flipY))
    max = Vector(readCoordinate(file, convertUnits, flipY))

    return (min, max)

def readPath(file, length):
    path = readString(file, length)

    if path != '':
        path = os.path.normpath(path)

    return path
