import os, bpy, math

from .constants_gzrs2 import *

def pathExists(path, startDir):
    if os.path.exists(path): return path
    elif path == '': return False
    elif os.name != 'nt':
        path = os.path.normpath(path.lower())
        targets = iter(path[1:].split(os.sep))
        current = os.sep + next(targets)
        target = next(targets)

        while target is not None:
            dirpath, dirnames, files = next(os.walk(current))

            if os.path.splitext(target)[1] == '':
                found = False

                for dirname in dirnames:
                    if dirname.lower() == target:
                        current = os.path.join(current, dirname)
                        found = True
                        break

                if found: target = next(targets)
                else: return False
            else:
                for file in files:
                    if file.lower() == target:
                        current = os.path.join(current, file)
                        return current

                return False

        return current

def textureSearch(self, startDir, texBase, targetPath):
    ddsBase = f"{ texBase }.dds".replace('.dds.dds', '.dds')
    ddsPath = os.path.join(startDir, ddsBase)
    texPath = os.path.join(startDir, texBase)

    ddsExists = pathExists(ddsPath, startDir)
    if ddsExists: return ddsExists

    texExists = pathExists(texPath, startDir)
    if texExists: return texExists

    if targetPath is None: return None
    elif targetPath == '':
        for dirpath, dirnames, files in os.walk(startDir):
            for file in files:
                if file == ddsBase or file == texBase:
                    return os.path.join(dirpath, file)

        parentDir = os.path.dirname(startDir)

        for _ in range(MAX_UPWARD_DIRECTORY_SEARCH):
            dirpath, dirnames, files = next(os.walk(parentDir))

            for dirname in dirnames:
                if dirname.lower() == 'texture':
                    for dirpath, dirnames, files in os.walk(os.path.join(dirpath, dirname)):
                        for file in files:
                            if file == texBase or file == ddsBase:
                                return os.path.join(dirpath, file)

            parentDir = os.path.dirname(parentDir)

        self.report({ 'INFO' }, f"GZRS2: Texture directory not found for material during texture search: { texBase }")
    else:
        texPath = os.path.join(startDir, targetPath, texBase)
        ddsPath = os.path.join(startDir, targetPath, ddsBase)

        ddsExists = pathExists(ddsPath, startDir)
        if ddsExists: return ddsExists

        texExists = pathExists(texPath, startDir)
        if texExists: return texExists

        parentDir = os.path.dirname(startDir)
        targetDir = targetPath.split(os.sep)[0]

        for _ in range(MAX_UPWARD_DIRECTORY_SEARCH):
            dirpath, dirnames, files = next(os.walk(parentDir))

            for dirname in dirnames:
                if dirname.lower() == targetDir.lower():
                    texPath = os.path.join(parentDir, targetPath, texBase)
                    ddsPath = os.path.join(parentDir, targetPath, ddsBase)

                    ddsExists = pathExists(ddsPath, startDir)
                    if ddsExists: return ddsExists

                    texExists = pathExists(texPath, startDir)
                    if texExists: return texExists

                    return None

            parentDir = os.path.dirname(parentDir)

        self.report({ 'INFO' }, f"GZRS2: Upward directory not found for material during texture search: { texBase }, { targetPath }")

def compareLights(light1, light2):
    return all((math.isclose(light1.color[0],            light2.color[0],            rel_tol = 0.0001),
                math.isclose(light1.color[1],            light2.color[1],            rel_tol = 0.0001),
                math.isclose(light1.color[2],            light2.color[2],            rel_tol = 0.0001),
                math.isclose(light1.energy,              light2.energy,              rel_tol = 0.0001),
                math.isclose(light1.shadow_soft_size,    light2.shadow_soft_size,    rel_tol = 0.0001)))

def groupLights(lights):
        groups = []
        skip = []

        for l1, light1 in enumerate(lights):
            if l1 in skip: continue
            else: skip.append(l1)

            matches = [light1]

            for l2, light2 in enumerate(lights):
                if l2 in skip: continue

                if compareLights(light1, light2):
                    skip.append(l2)
                    matches.append(light2)

            if len(lights) > 1:
                groups.append(matches)

        return groups

def createArrayDriver(target, targetProp, sources, sourceProp):
    target[targetProp] = getattr(sources, sourceProp)
    curves = sources.driver_add(sourceProp)

    for c, curve in enumerate(curves):
        driver = curve.driver
        var = driver.variables.new()
        var.name = sourceProp
        var.targets[0].id = target
        var.targets[0].data_path = f"[\"{ targetProp }\"][{ c }]"
        driver.expression = var.name

    return curves

def createDriver(target, targetProp, source, sourceProp):
    target[targetProp] = getattr(source, sourceProp)
    curve = source.driver_add(sourceProp)

    driver = curve.driver
    var = driver.variables.new()
    var.name = sourceProp
    var.targets[0].id = target
    var.targets[0].data_path = f"[\"{ targetProp }\"]"
    driver.expression = var.name

    return driver
