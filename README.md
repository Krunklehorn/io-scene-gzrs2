# ***io_scene_gzrs2***

GunZ: The Duel RealSpace2.0 map import for Blender 3.1 or higher.  
Intended for users wishing to visualize maps and prepare the data for a modern game engine.

Please report bugs and unimplemented features to: ***Krunk#6051***

RaGEZONE thread: ***https://forum.ragezone.com/f496/io_scene_gzrs2-blender-3-1-map-1204327/***

[***DOWNLOAD v0.8.2***](https://github.com/Krunklehorn/io-scene-gzrs2/releases/download/v0.8.2/io_scene_gzrs2_v0.8.2.zip)


# Recent Updates

* (Very) basic .elu support, no .ani parsing or skinned meshes yet
  * tested on all models loaded in vanilla GunZ maps
  * some issues with orientation on a case-by-case basis (Factory, Mansion, Halloween Town etc.)
* Map geometry now actually truly does load custom normals this time I promise
* Added new switches for logging information to the console


# Current Features

* displays world geometry, occlusion planes and collision data using meshes
* displays BSP bounding boxes, sounds, spawns, powerups and other dummies using the appropriate empties
* preserves n-gons and custom mesh normals
* groups lights with similar properties, re-interprets the data to be useful in Blender
* includes a driver object for quickly tuning lights and fog
* notifies the user of..
  * missing textures and empty texture paths
  * out-of-bounds and unused material slots
  * objects with no corresponding dummy
  * unimplemented xml tags (please report these)


# Planned Features

* .elu/.ani model import
* option to re-center all geometry
* nav mesh support


# Known Issues

* quest maps and community maps have not been tested at all yet
* some alpha textures have white halos in render mode (Town)
* collision mesh and occlusion planes appear black in render mode (just disable them for now)
* textures are only searched for in the surrounding map folders, there may be other locations but I don't know yet
* some .elu models are oriented incorrectly. (Factory, Mansion, Halloween Town etc.)


![Preview](meta/preview_220327_1.jpg)
![Preview](meta/preview_220420.jpg)
![Preview](meta/preview_220327_3.jpg)


# Special Thanks

[minidom](https://github.com/python/cpython/blob/3.10/Lib/xml/dom/minidom.py)  
[three-gunz](https://github.com/LostMyCode/three-gunz)  
[open-gunz](https://github.com/open-gunz/ogz-source)  
