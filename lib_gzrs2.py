import bpy, math

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
    driver = source.driver_add(sourceProp).driver
    var = driver.variables.new()
    var.name = sourceProp
    var.targets[0].id = target
    var.targets[0].data_path = f"[\"{ targetProp }\"]"
    driver.expression = var.name

    return driver
