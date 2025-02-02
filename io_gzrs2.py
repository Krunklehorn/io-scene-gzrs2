import sys, os

from struct import pack, unpack, iter_unpack
from itertools import chain

from mathutils import Vector, Matrix

def skipBytes(file, length):                return file.seek(length, 1)

def readBytes(file, length):                return file.read(length)
def decodeBytes(file, length):              return file.read(length).decode('utf-8')
def readChar(file):                         return unpack('<b', file.read(1))[0]
def readUChar(file):                        return unpack('<B', file.read(1))[0]
def readCharBool(file):                     return False if readChar(file) < 0 else True
def readBool(file):                         return unpack('<?', file.read(1))[0]
def readBool32(file):                       return unpack('<?xxx', file.read(4))[0]
def readUShort(file):                       return unpack('<H', file.read(2))[0]
def readShort(file):                        return unpack('<h', file.read(2))[0]
def readUInt(file):                         return unpack('<I', file.read(4))[0]
def readInt(file):                          return unpack('<i', file.read(4))[0]
def readFloat(file):                        return unpack('<f', file.read(4))[0]
def readVec2(file):                         return unpack('<2f', file.read(2 * 4))
def readVec3(file):                         return unpack('<3f', file.read(3 * 4))
def readVec4(file):                         return unpack('<4f', file.read(4 * 4))

def readBoolArray(file, length):            return unpack(f'<{ length }?', file.read(length))
def readBool32Array(file, length):          return tuple(readBool32(file) for _ in range(length))
def readUShortArray(file, length):          return unpack(f'<{ length }H', file.read(2 * length))
def readShortArray(file, length):           return unpack(f'<{ length }h', file.read(2 * length))
def readUIntArray(file, length):            return unpack(f'<{ length }I', file.read(4 * length))
def readIntArray(file, length):             return unpack(f'<{ length }i', file.read(4 * length))
def readFloatArray(file, length):           return unpack(f'<{ length }f', file.read(4 * length))
def readVec2Array(file, length):            return tuple(iter_unpack('<2f', file.read(2 * 4 * length)))
def readVec3Array(file, length):            return tuple(iter_unpack('<3f', file.read(3 * 4 * length)))
def readVec4Array(file, length):            return tuple(iter_unpack('<4f', file.read(4 * 4 * length)))
def readString(file, length):               return str(file.read(length), 'utf-8').split('\x00', 1)[0].strip()
def readStringAlt(file, length):            return str(file.read(length).split(b'\x00', 1)[0], 'utf-8').strip()

def readUV2(file):
    uv = Vector(readVec2(file))

    uv.y = -uv.y

    return uv

def readUV3(file):
    uv = Vector(readVec2(file))
    skipBytes(file, 4)

    uv.y = -uv.y

    return uv

def readUV4(file):
    uv = Vector(readVec2(file))
    skipBytes(file, 8)

    uv.y = -uv.y

    return uv

def readCoordinate(file, convertUnits, flipY, *, swizzle = False):
    coord = Vector(readVec3(file))

    if convertUnits:    coord *= 0.01
    if flipY:           coord.y = -coord.y
    if swizzle:         coord.xyz = coord.xzy

    return coord

def readDirection(file, flipY, *, swizzle = False):
    dir = Vector(readVec3(file))
    dir.normalize()

    if flipY:       dir.y = -dir.y
    if swizzle:     dir.xyz = dir.xzy

    return dir

def readPlane(file, convertUnits, flipY):
    plane = Vector(readVec4(file))
    plane.normalize()

    if convertUnits:    plane.w *= 0.01
    if flipY:           plane.y = -plane.y

    return plane

def readUV2Array(file, length):
    uvs = tuple(Vector(data) for data in readVec2Array(file, length))
    for uv in uvs: uv.y = -uv.y

    return uvs

def readUV3Array(file, length):
    uvs = tuple(Vector(data).to_2d() for data in readVec3Array(file, length))
    for uv in uvs: uv.y = -uv.y

    return uvs

def readUV4Array(file, length):
    uvs = tuple(Vector(data).to_2d() for data in readVec4Array(file, length))
    for uv in uvs: uv.y = -uv.y

    return uvs

def readCoordinateArray(file, length, convertUnits, flipY, *, swizzle = False):
    coords = tuple(Vector(data) for data in readVec3Array(file, length))

    if convertUnits:
        for coord in coords:
            coord *= 0.01

    if flipY:
        for coord in coords:
            coord.y = -coord.y

    if swizzle:
        for coord in coords:
            coord.xyz = coord.xzy

    return coords

def readDirectionArray(file, length, flipY, *, swizzle = False):
    dirs = tuple(Vector(data) for data in readVec3Array(file, length))

    for dir in dirs:
        dir.normalize()

    if flipY:
        for dir in dirs:
            dir.y = -dir.y

    if swizzle:
        for dir in dirs:
            dir.xyz = dir.xzy

    return dirs

def readPlaneArray(file, length, flipY):
    planes = tuple(Vector(data) for data in readVec4Array(file, length))

    for plane in planes:
        plane.normalize()

    if flipY:
        for plane in planes:
            plane.y = -plane.y

    return planes

def readTransform(file, convertUnits, *, swizzle = False):
    transform = Matrix(readVec4Array(file, 4))

    # MCPlug2_Ani.cpp
    if swizzle:
        temp = transform.copy()

        row = temp.row[0]
        transform[0][0] = row.x
        transform[0][1] = row.z
        transform[0][2] = row.y

        row = temp.row[1]
        transform[2][0] = row.x
        transform[2][1] = row.z
        transform[2][2] = row.y

        row = temp.row[2]
        transform[1][0] = row.x
        transform[1][1] = row.z
        transform[1][2] = row.y

        row = temp.row[3]
        transform[3][0] = row.x
        transform[3][1] = row.z
        transform[3][2] = row.y

    transform.transpose()

    loc, rot, sca = transform.decompose()

    if convertUnits: loc *= 0.01

    return Matrix.LocRotScale(loc, rot, sca)

def readBounds(file, convertUnits):
    min = Vector(readCoordinate(file, convertUnits, False))
    max = Vector(readCoordinate(file, convertUnits, False))

    return min, max

def readPath(file, length):
    path = readString(file, length)

    if path:
        path = os.path.normpath(path)

    return path

def writeBytes(file, data):                 file.write(int.from_bytes(data, sys.byteorder).to_bytes(len(data), 'little'))
def writeChar(file, data):                  file.write(pack('<b', data))
def writeUChar(file, data):                 file.write(pack('<B', data))
def writeCharBool(file, data):              writeChar(file, -1 if not data else 1)
def writeBool(file, data):                  file.write(pack('<?', data))
def writeBool32(file, data):                writeUInt(file, int(data))
def writeUShort(file, data):                file.write(pack('<H', data))
def writeShort(file, data):                 file.write(pack('<h', data))
def writeUInt(file, data):                  file.write(pack('<I', data))
def writeInt(file, data):                   file.write(pack('<i', data))
def writeFloat(file, data):                 file.write(pack('<f', data))
def writeVec2(file, data):                  file.write(pack('<2f', *data))
def writeVec3(file, data):                  file.write(pack('<3f', *data))
def writeVec4(file, data):                  file.write(pack('<4f', *data))

def writeBoolArray(file, data):             file.write(pack(f'<{ len(data) }?', *data))
def writeBool32Array(file, data):           file.write(pack(f'<{ len(data) }I', *tuple(int(d) for d in data)))
def writeUShortArray(file, data):           file.write(pack(f'<{ len(data) }H', *data))
def writeShortArray(file, data):            file.write(pack(f'<{ len(data) }h', *data))
def writeUIntArray(file, data):             file.write(pack(f'<{ len(data) }I', *data))
def writeIntArray(file, data):              file.write(pack(f'<{ len(data) }i', *data))
def writeFloatArray(file, data):            file.write(pack(f'<{ len(data) }f', *data))
def writeVec2Array(file, data):             file.write(pack(f'<{ 2 * len(data) }f', *tuple(chain.from_iterable(data))))
def writeVec3Array(file, data):             file.write(pack(f'<{ 3 * len(data) }f', *tuple(chain.from_iterable(data))))
def writeVec4Array(file, data):             file.write(pack(f'<{ 4 * len(data) }f', *tuple(chain.from_iterable(data))))
def writeString(file, data, length):        file.write(pack(f'<{ length }s', bytes(data, 'utf-8')))
def writeStringPacked(file, data):          file.write(bytes(data, 'utf-8') + b'\x00')

def writeUV2(file, uv):
    uv = uv.copy()
    uv.y = -uv.y

    writeVec2(file, uv.to_2d())

def writeUV3(file, uv):
    uv = uv.to_3d()
    uv.y = -uv.y
    uv[2] = 0

    writeVec3(file, uv)

def writeCoordinate(file, coord, convertUnits, flipY, *, swizzle = False):
    coord = coord.to_3d()

    if swizzle:         coord.xyz = coord.xzy
    if flipY:           coord.y = -coord.y
    if convertUnits:    coord *= 100

    writeVec3(file, coord)

def writeDirection(file, dir, flipY, *, swizzle = False):
    dir = dir.to_3d()
    dir.normalize()

    if swizzle:     dir.xyz = dir.xzy
    if flipY:       dir.y = -dir.y

    writeVec3(file, dir)

def writePlane(file, plane, convertUnits, flipY):
    plane = plane.to_4d()
    plane.normalize()

    if flipY:           plane.y = -plane.y
    if convertUnits:    plane.w *= 100

    writeVec4(file, plane)

def writeUV2Array(file, uvs):
    uvs = tuple(uv.to_2d() for uv in uvs)

    for uv in uvs:
        uv.y = -uv.y

    writeVec2Array(file, uvs)

def writeUV3Array(file, uvs):
    uvs = tuple(uv.to_3d() for uv in uvs)

    for uv in uvs:
        uv.y = -uv.y
        uv[2] = 0

    writeVec3Array(file, uvs)

def writeCoordinateArray(file, coords, convertUnits, flipY, *, swizzle = False):
    coords = tuple(coord.to_3d() for coord in coords)

    for coord in coords:
        if swizzle:         coord.xyz = coord.xzy
        if flipY:           coord.y = -coord.y
        if convertUnits:    coord *= 100

    writeVec3Array(file, coords)

def writeDirectionArray(file, dirs, flipY, *, swizzle = False):
    dirs = tuple(dir.to_3d() for dir in dirs)

    for dir in dirs:
        dir.normalize()
        if swizzle:     dir.xyz = dir.xzy
        if flipY:       dir.y = -dir.y

    writeVec3Array(file, dirs)

def writePlaneArray(file, planes, flipY):
    planes = tuple(plane.to_4d() for plane in planes)

    for plane in planes:
        plane.normalize()
        if flipY: plane.y = -plane.y

    writeVec4Array(file, planes)

def writeTransform(file, transform, convertUnits, flipY, *, swizzle = False):
    loc, rot, sca = transform.to_4x4().decompose()

    if convertUnits: loc *= 100
    if flipY:
        loc.y = -loc.y

        rot.x = -rot.x
        rot.z = -rot.z

    transform = Matrix.LocRotScale(loc, rot, sca)

    # MCPlug2_Ani.cpp
    transform.transpose()

    if swizzle:
        temp = transform.copy()

        row = temp.row[0]
        transform[0][0] = row.x
        transform[0][1] = row.z
        transform[0][2] = row.y

        row = temp.row[1]
        transform[2][0] = row.x
        transform[2][1] = row.z
        transform[2][2] = row.y

        row = temp.row[2]
        transform[1][0] = row.x
        transform[1][1] = row.z
        transform[1][2] = row.y

        row = temp.row[3]
        transform[3][0] = row.x
        transform[3][1] = row.z
        transform[3][2] = row.y

    writeVec4Array(file, tuple(transform))

def writeBounds(file, bbmin, bbmax, convertUnits):
    writeCoordinate(file, bbmin, convertUnits, False)
    writeCoordinate(file, bbmax, convertUnits, False)
