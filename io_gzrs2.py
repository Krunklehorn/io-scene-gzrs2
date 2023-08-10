import sys, os, math
from struct import unpack

import mathutils
from mathutils import Vector, Matrix, Quaternion

def skipBytes(file, length):            return file.seek(length, 1)

def readBytes(file, length):            return file.read(length)
def decodeBytes(file, length):          return file.read(length).decode('utf-8')
def readChar(file):                     return unpack('<b', file.read(1))[0]
def readUChar(file):                    return unpack('<B', file.read(1))[0]
def readBool(file):                     return unpack('<?', file.read(1))[0]
def readBool32(file):                   return bool(readUInt(file))
def readUShort(file):                   return unpack('<H', file.read(2))[0]
def readShort(file):                    return unpack('<h', file.read(2))[0]
def readUInt(file):                     return unpack('<I', file.read(4))[0]
def readInt(file):                      return unpack('<i', file.read(4))[0]
def readFloat(file):                    return unpack('<f', file.read(4))[0]
def readVec2(file):                     return unpack('<2f', file.read(2 * 4))
def readVec3(file):                     return unpack('<3f', file.read(3 * 4))
def readVec4(file):                     return unpack('<4f', file.read(4 * 4))

def readBoolArray(file, length):        return tuple(readBool(file) for _ in range(length))
def readBool32Array(file, length):      return tuple(readBool32(file) for _ in range(length))
def readUShortArray(file, length):      return unpack(f'{ length }H', file.read(2 * length))
def readShortArray(file, length):       return unpack(f'{ length }h', file.read(2 * length))
def readUIntArray(file, length):        return tuple(readUInt(file) for _ in range(length))
def readIntArray(file, length):         return tuple(readInt(file) for _ in range(length))
def readFloatArray(file, length):       return tuple(readFloat(file) for _ in range(length))
def readVec2Array(file, length):        return tuple(readVec2(file) for _ in range(length))
def readVec3Array(file, length):        return tuple(readVec3(file) for _ in range(length))
def readVec4Array(file, length):        return tuple(readVec4(file) for _ in range(length))
def readString(file, length):           return (str(file.read(length), 'utf-8').split('\x00', 1)[0]).strip()

def writeBytes(file, data):             file.write(int.from_bytes(data, sys.byteorder).to_bytes(len(data), 'little'))
def writeShort(file, data):             file.write(data.to_bytes(2, 'little'))
def writeInt(file, data):               file.write(data.to_bytes(4, 'little'))

'''
'''
def readUV2(file):
    x, y = readVec2(file)

    y = -y

    return Vector((x, y))

def readUV3(file):
    x, y = readVec2(file)
    skipBytes(file, 4)

    y = -y

    return Vector((x, y))
'''
'''

'''
def readUV2(file):
    x, y = readVec2(file)

    y = -y

    return tuple((x, y))

def readUV3(file):
    x, y = readVec2(file)
    skipBytes(file, 4)

    y = -y

    return tuple((x, y))
'''

'''
'''
def readCoordinate(file, convertUnits, flipY):
    coord = Vector(readVec3(file))

    if convertUnits: coord *= 0.01
    if flipY: coord.y = -coord.y

    return coord

def readDirection(file, flipY):
    dir = Vector(readVec3(file))

    if flipY: dir.y = -dir.y

    return dir.normalized()

def readPlane(file, flipY):
    plane = Vector(readVec4(file))

    if flipY: plane.y = -plane.y

    return plane.normalized()
'''
'''

def readUV2Array(file, length): return tuple(readUV2(file) for _ in range(length))
def readUV3Array(file, length): return tuple(readUV3(file) for _ in range(length))

'''
'''
def readCoordinateArray(file, length, convertUnits, flipY):
    result = []

    for coord in readVec3Array(file, length):
        coord = Vector(coord)
        if convertUnits: coord *= 0.01
        if flipY: coord.y = -coord.y

        result.append(coord)

    return tuple(result)

def readDirectionArray(file, length, flipY):
    result = []

    for dir in readVec3Array(file, length):
        dir = Vector(dir)
        if flipY: dir.y = -dir.y

        result.append(dir.normalized())

    return tuple(result)

def readPlaneArray(file, length, flipY):
    result = []

    for plane in readVec4Array(file, length):
        plane = Vector(plane)
        if flipY: plane.y = -plane.y

        result.append(plane.normalized())

    return tuple(result)

def readTransform(file, convertUnits, flipY):
    mat = Matrix(readVec4Array(file, 4))
    mat.transpose()

    loc, rot, sca = mat.decompose()
    if convertUnits: loc *= 0.01
    if flipY:
        loc.y = -loc.y

        rot.x = -rot.x
        rot.z = -rot.z

    return Matrix.LocRotScale(loc, rot, sca)

def readBounds(file, convertUnits, flipY):
    min = Vector(readCoordinate(file, convertUnits, flipY))
    max = Vector(readCoordinate(file, convertUnits, flipY))

    return (min, max)
'''
'''

'''
def readCoordinate(file, convertUnits, flipY):
    coord = [f for f in readVec3(file)]

    if convertUnits:
        coord[0] *= 0.01
        coord[1] *= 0.01
        coord[2] *= 0.01
    if flipY: coord[1] = -coord[1]

    return tuple(coord)

def readDirection(file, flipY):
    dir = [f for f in readVec3(file)]

    if flipY: dir[1] = -dir[1]

    length = math.sqrt(dir[0] * dir[0] + dir[1] * dir[1] + dir[2] * dir[2])
    if length != 0:
        dir[0] /= length
        dir[1] /= length
        dir[2] /= length

    return tuple(dir)

def readPlane(file, flipY):
    plane = [f for f in readVec4(file)]

    if flipY: plane[1] = -plane[1]

    length = math.sqrt(plane[0] * plane[0] + plane[1] * plane[1] + plane[2] * plane[2])
    if length != 0:
        plane[0] /= length
        plane[1] /= length
        plane[2] /= length

    return tuple(plane)

def readCoordinateArray(file, length, convertUnits, flipY):
    result = []

    for coord in readVec3Array(file, length):
        coord = [f for f in coord]
        if convertUnits:
            coord[0] *= 0.01
            coord[1] *= 0.01
            coord[2] *= 0.01
        if flipY: coord[1] = -coord[1]

        result.append(coord)

    return tuple(result)

def readDirectionArray(file, length, flipY):
    result = []

    for dir in readVec3Array(file, length):
        dir = [f for f in dir]

        if flipY: dir[1] = -dir[1]

        length = math.sqrt(dir[0] * dir[0] + dir[1] * dir[1] + dir[2] * dir[2])
        if length != 0:
            dir[0] /= length
            dir[1] /= length
            dir[2] /= length

        result.append(dir)

    return tuple(result)

def readPlaneArray(file, length, flipY):
    result = []

    for plane in readVec4Array(file, length):
        plane = [f for f in plane]

        if flipY: plane[1] = -plane[1]

        length = math.sqrt(plane[0] * plane[0] + plane[1] * plane[1] + plane[2] * plane[2])
        if length != 0:
            plane[0] /= length
            plane[1] /= length
            plane[2] /= length

        result.append(plane)

    return tuple(result)

def readBounds(file, convertUnits, flipY):
    min = [c for c in readCoordinate(file, convertUnits, flipY)]
    max = [c for c in readCoordinate(file, convertUnits, flipY)]

    return (min, max)
'''

def readPath(file, length):
    path = readString(file, length)

    if path:
        path = os.path.normpath(path)

    return path
