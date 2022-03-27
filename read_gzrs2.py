from .constants_gzrs2 import *
from .classes_gzrs2 import *
from .io_gzrs2 import *

def readRs(self, path, state: GZRS2State):
    file = open(path, 'rb')
    
    id = readUInt(file)
    version = readUInt(file)
    matCount = readInt(file)
    for i in range(matCount): # skip material strings
        count = 0

        while count < 256:
            char = str(file.read(1), 'utf-8')
            if char == chr(0):
                break
            else:
                count = count + 1

    if id != RS_ID or version != RS_VERSION:
        self.report({ 'ERROR' }, f"RS header invalid! { id }, { version }")
        file.close()
        
        return
    elif matCount != len(state.xmlMats):
        self.report({ 'ERROR' }, f"RS material count did not match the XML parse! { matCount }, { len(state.xmlMats) }")
        file.close()
        
        return
    
    rsPolyCount = readInt(file)
    file.seek(4, 1) # skip total vertex count

    for _ in range(rsPolyCount):
        file.seek(4 + 4 + (4 * 4) + 4, 1) # skip material id, draw flags, plane and area data
        vertexCount = readInt(file)

        for _ in range(vertexCount): file.seek(4 * 3, 1) # skip vertex data
        for _ in range(vertexCount): file.seek(4 * 3, 1) # skip normal data

    file.seek(4 * 4, 1) # skip unused, unknown counts
    file.seek(4 * 2, 1) # skip leaf and polygon counts
    bspTotalVertices = readInt(file)
    file.seek(4, 1) # skip indices count
    
    firstVertex = 0

    def openBspNode():
        nonlocal firstVertex
        
        if self.doBspBounds:
            state.bspBounds.append(readBounds(file, self.convertUnits))
        else:
            file.seek(4 * 6, 1) # skip bounds data
        
        file.seek(4 * 4, 1) # skip plane data

        if readBool(file): openBspNode() # positive
        if readBool(file): openBspNode() # negative

        bspPolyCount = readInt(file)

        for _ in range(bspPolyCount):
            materialID = readInt(file)
            file.seek(4, 1) # skip polygon index
            drawFlags = readUInt(file)
            vertexCount = readInt(file)

            for j in range(vertexCount):
                pos = readCoordinate(file, self.convertUnits)
                nor = readCoordinate(file, self.convertUnits)
                uv = readUV(file)
                file.seek(4 * 2, 1) # skip lightmap uv data
                
                state.bspVerts.append(BspVertex(pos, nor, uv))

            file.seek(4 * 3, 1) # skip plane normal

            if not (0 <= materialID < len(state.xmlMats)):
                self.report({ 'INFO' }, f"Material ID out of bounds, setting to 0 and continuing. { materialID }, { len(state.xmlMats) }")
                materialID = 0

            state.bspPolys.append(BspPolyData(materialID, drawFlags, vertexCount, firstVertex))
            firstVertex += vertexCount

    openBspNode()

    if len(state.bspVerts) != bspTotalVertices:
        self.report({ 'ERROR' }, f"Bsp vertex count did not match vertices written! { len(state.bspVerts) }, { bspTotalVertices }")

    file.close()

def readCol(self, path, state: GZRS2State):
    file = open(path, 'rb')
    
    id = readUInt(file)
    version = readUInt(file)
    
    if id != R_COL_ID or version != R_COL_VERSION:
        self.report({ 'ERROR' }, f"Col header invalid! { id }, { version }")
        file.close()
        
        return
    
    file.seek(4, 1) # skip node count
    colTotalPolys = readInt(file)
    
    colPolysWritten = 0
    
    def openColNode():
        nonlocal colPolysWritten
        
        file.seek(4 * 4 + 1, 1) # skip plane data and solidity bool

        if readBool(file): openColNode() # positive
        if readBool(file): openColNode() # negative
        
        colPolyCount = readInt(file)
        
        for _ in range(colPolyCount):
            state.colVerts.append(readCoordinate(file, self.convertUnits))
            state.colVerts.append(readCoordinate(file, self.convertUnits))
            state.colVerts.append(readCoordinate(file, self.convertUnits))
            file.seek(4 * 3, 1) # skip normal
        
        colPolysWritten += colPolyCount
        
    openColNode()
    
    if colPolysWritten != colTotalPolys:
        self.report({ 'ERROR' }, f"Col polygon count did not match polygons written! { colPolysWritten }, { colTotalPolys }")
    
    file.close()