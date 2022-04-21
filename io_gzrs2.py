import sys, math
from struct import unpack

import mathutils
from mathutils import Vector, Matrix, Quaternion

def skipBytes(file, length):            return file.seek(length, 1)

def readBool(file):                     return unpack('<?', file.read(1))[0]
def readBool32(file):                   return bool(readUInt(file))
def readUInt(file):                     return unpack('<I', file.read(4))[0]
def readInt(file):                      return unpack('<i', file.read(4))[0]

def readFloat(file):                    return unpack('f', file.read(4))[0]
def readVec2(file):                     return unpack('2f', file.read(2 * 4))
def readVec3(file):                     return unpack('3f', file.read(3 * 4))
def readVec4(file):                     return unpack('4f', file.read(4 * 4))

def readBoolArray(file, length):        return tuple(readBool(file) for _ in range(length))
def readBool32Array(file, length):      return tuple(readBool32(file) for _ in range(length))
def readUIntArray(file, length):        return tuple(readUInt(file) for _ in range(length))
def readIntArray(file, length):         return tuple(readInt(file) for _ in range(length))
def readFloatArray(file, length):       return tuple(readFloat(file) for _ in range(length))
def readVec2Array(file, length):        return tuple(readVec2(file) for _ in range(length))
def readVec3Array(file, length):        return tuple(readVec3(file) for _ in range(length))
def readVec4Array(file, length):        return tuple(readVec4(file) for _ in range(length))

def readUShort(file):                   return unpack('H', file.read(2 + b'\0\0'))[0]
def readUShortArray(file, length):      return unpack(f'{ length }H', file.read(2 * length))

def readStringStripped(file, length):   return str(file.read(length), 'utf-8').split('\x00', 1)[0]
def readStringPacked(file, length):
        count = 0

        while count < length:
            char = str(file.read(1), 'utf-8')

            if char == chr(0):
                break
            else:
                count = count + 1

def readUV(file):
    uv = Vector(readVec2(file))
    uv.y = -uv.y

    return uv

def readCoordinate(file, convertUnits):
    coord = Vector(readVec3(file))
    if convertUnits: coord *= 0.01
    coord.y = -coord.y

    return coord

def readCoordinateArray(file, length, convertUnits):
    coords = readVec3Array(file, length)
    result = []

    for coord in coords:
        coord = Vector(coord)
        if convertUnits: coord *= 0.01
        coord.y = -coord.y

        result.append(coord)

    return tuple(result)

def readTransform(file, convertUnits):
    mat = Matrix(readVec4Array(file, 4))
    mat.transpose()

    quat = Quaternion((0, 1, 0), math.radians(180))
    quat.rotate(Quaternion((1, 0, 0), math.radians(-90)))

    loc, rot, sca = mat.decompose()
    if convertUnits: loc *= 0.01
    loc.y = -loc.y
    loc.rotate(quat)
    rot.rotate(quat)

    return Matrix.LocRotScale(loc, rot, sca)

def readBounds(file, convertUnits):
    min = Vector(readCoordinate(file, convertUnits))
    max = Vector(readCoordinate(file, convertUnits))

    return (min, max)
