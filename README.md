# io_scene_gzrs2

GunZ: The Duel RealSpace2.0 map import for Blender 2.8 or higher.  
Intended for users wishing to visualize maps and prepare the data for a modern game engine.

Download the repo as a .zip using the big green "Code" button and install as a plugin.  
Please report bugs and unimplemented features to: Krunk#6051


![Preview](meta/preview_220327_1.jpg)
![Preview](meta/preview_220327_2.jpg)
![Preview](meta/preview_220327_3.jpg)


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
* other community suggestions


# Special Thanks

[minidom](https://github.com/python/cpython/blob/3.10/Lib/xml/dom/minidom.py)  
[three-gunz](https://github.com/LostMyCode/three-gunz)  
[open-gunz](https://github.com/open-gunz/ogz-source)  
