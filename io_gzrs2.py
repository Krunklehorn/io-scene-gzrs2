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
    x, y = readVec2(file)

    y = -y

    return Vector((x, y))

def readUV3(file):
    x, y = readVec2(file)
    skipBytes(file, 4)

    y = -y

    return Vector((x, y))

def readUV4(file):
    x, y = readVec2(file)
    skipBytes(file, 8)

    y = -y

    return Vector((x, y))

def readCoordinate(file, convertUnits, flipY, *, swizzle = False):
    coord = Vector(readVec3(file))

    if swizzle:
        # MCPlug2_Ani.cpp
        (x, y, z) = coord.to_tuple()
        coord.y = z
        coord.z = y

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

def readUV2Array(file, length): return tuple(readUV2(file) for _ in range(length))
def readUV3Array(file, length): return tuple(readUV3(file) for _ in range(length))
def readUV4Array(file, length): return tuple(readUV4(file) for _ in range(length))

def readCoordinateArray(file, length, convertUnits, flipY, *, swizzle = False):
    result = []

    for coord in readVec3Array(file, length):
        coord = Vector(coord)

        if swizzle:
            # MCPlug2_Ani.cpp
            (x, y, z) = coord.to_tuple()
            coord.y = z
            coord.z = y

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

def readTransform(file, convertUnits, flipY, *, swizzle = False):
    mat = Matrix(readVec4Array(file, 4))

    # MCPlug2_Ani.cpp
    if swizzle:
        temp = mat.copy()

        row = temp.row[0]
        mat[0][0] = row.x
        mat[0][1] = row.z
        mat[0][2] = row.y

        row = temp.row[1]
        mat[2][0] = row.x
        mat[2][1] = row.z
        mat[2][2] = row.y

        row = temp.row[2]
        mat[1][0] = row.x
        mat[1][1] = row.z
        mat[1][2] = row.y

        row = temp.row[3]
        mat[3][0] = row.x
        mat[3][1] = row.z
        mat[3][2] = row.y

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

def writeUV2(file, uv):
    uv = uv.copy()
    uv.y = -uv.y

    writeVec2(file, uv[:2])

def writeUV3(file, uv):
    uv = uv.copy()
    uv.y = -uv.y

    writeVec3(file, (uv[0], uv[1], 0.0))

def writeCoordinate(file, coord, convertUnits, flipY):
    coord = coord.copy()

    if convertUnits: coord *= 100
    if flipY: coord.y = -coord.y

    writeVec3(file, coord[:3])

def writeDirection(file, dir, flipY):
    dir = dir.copy()

    if flipY: dir.y = -dir.y

    writeVec3(file, dir.normalized()[:3])

def writePlane(file, plane, flipY):
    plane = plane.copy()

    if flipY: plane.y = -plane.y

    writeVec4(file, plane.normalized()[:4])

def writeUV2Array(file, uvs):
    uvs = tuple(uv.copy() for uv in uvs)

    for uv in uvs:
        uv.y = -uv.y

    writeVec2Array(file, tuple(uv[:2] for uv in uvs))

def writeUV3Array(file, uvs):
    uvs = tuple(uv.copy() for uv in uvs)

    for uv in uvs:
        uv.y = -uv.y

    writeVec3Array(file, tuple((uv[0], uv[1], 0.0) for uv in uvs))

def writeCoordinateArray(file, coords, convertUnits, flipY):
    coords = tuple(coord.copy() for coord in coords)

    for coord in coords:
        if convertUnits: coord *= 100
        if flipY: coord.y = -coord.y

    writeVec3Array(file, tuple(coord[:3] for coord in coords))

def writeDirectionArray(file, dirs, flipY):
    dirs = tuple(dir.copy() for dir in dirs)

    for dir in dirs:
        if flipY: dir.y = -dir.y

    writeVec3Array(file, tuple(dir[:3] for dir in dirs))

def writePlaneArray(file, planes, flipY):
    planes = tuple(plane.copy() for plane in planes)

    for plane in planes:
        if flipY: plane.y = -plane.y

        plane.normalize()

    writeVec4Array(file, tuple(plane[:4] for plane in planes))

def writeTransform(file, transform, convertUnits, flipY):
    transform = transform.copy()

    loc, rot, sca = transform.decompose()

    if convertUnits: loc *= 100
    if flipY:
        loc.y = -loc.y

        rot.x = -rot.x
        rot.z = -rot.z

    writeVec4Array(file, tuple(Matrix.LocRotScale(loc, rot, sca).transposed()))

def writeBounds(file, bounds, convertUnits, flipY):
    bounds = (bounds[0].copy(), bounds[1].copy())

    writeCoordinate(file, bounds[0], convertUnits, flipY)
    writeCoordinate(file, bounds[1], convertUnits, flipY)
