import mathutils
from struct import unpack
from mathutils import Vector

def readBool(file):     return bool(int.from_bytes(file.read(1), byteorder = 'little', signed = False))
def readUInt(file):     return int.from_bytes(file.read(4), byteorder = 'little', signed = False)
def readInt(file):      return int.from_bytes(file.read(4), byteorder = 'little', signed = True)
def readFloat(file):    return unpack('f', file.read(4))[0]

def readVec2(file):
    bytes = file.read(4)
    bytes += file.read(4)

    return unpack('2f', bytes)

def readVec3(file):
    bytes = file.read(4)
    bytes += file.read(4)
    bytes += file.read(4)

    return unpack('3f', bytes)

def readVec4(file):
    bytes = file.read(4)
    bytes += file.read(4)
    bytes += file.read(4)
    bytes += file.read(4)

    return unpack('4f', bytes)

def readUV(file):
    uv = Vector(readVec2(file))
    uv.y = -uv.y

    return uv

def readCoordinate(file, convertUnits):
    pos = Vector(readVec3(file))
    if convertUnits: pos *= 0.01
    pos.y = -pos.y

    return pos

def readBounds(file, convertUnits):
    min = Vector(readCoordinate(file, convertUnits))
    max = Vector(readCoordinate(file, convertUnits))

    return (min, max)
