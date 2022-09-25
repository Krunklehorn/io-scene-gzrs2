# ***io_scene_gzrs2***

GunZ: The Duel RealSpace2.0/3.0 map and model importer for Blender 3.3.0.  
Intended for users wishing to visualize GunZ content and prepare the data for a modern game engine.

Please report bugs and unimplemented features to: ***Krunk#6051***

RaGEZONE thread: ***https://forum.ragezone.com/f496/io_scene_gzrs2-blender-3-1-map-1204327/***

[***DOWNLOAD v0.9.0***](https://github.com/Krunklehorn/io-scene-gzrs2/releases/download/v0.9.0/io_scene_gzrs2_v0.9.0.zip)


# Latest Update

* NEW: major elu support, versions 0x5004 - 0x5011 may be loaded independently including skinned actor meshes
* NEW: rs and elu support for GunZ 2 alpha content
* NEW: smart texture search checks local, relative and upward paths and supports non-dds formats
* rs UV layer 2 is now included
* prop dummies are now skipped and all props are loaded whether they have a corresponding dummy or not
* materials can now be both transparent and additive, clipped alpha testing is also supported
* fixed broken prop orientations (Factory, Mansion, Halloween Town, etc.)
* fixed operator switches overwriting each other on subsequent imports
* fixed issues with file paths on posix systems thanks to Nayr
* removed local copy of minidom
* additional log switches have been setup
* additional material flags are recognized


# Current Features

* displays world geometry, occlusion planes and collision data using meshes
* displays BSP bounding boxes, sounds, spawns, powerups and other dummies using the appropriate empties
* groups lights with similar properties, re-interprets the data to be useful in Blender
* includes a driver object for quickly tuning lights and fog
* notifies the user of..
  * missing textures and empty texture paths
  * out-of-bounds and unused material slots
  * unimplemented xml tags (please report these)


# Planned Features

* GunZ 1.5 elu support: 0x0, 0x11 and 0x5001, 0x5002 & 0x5003
* GunZ 2 retail elu support: 0x5012, 0x5013 & 0x5014
* .ani support
* nav mesh support


# Known Issues

* quest maps and community maps have not been tested at all yet
* some alpha textures have white halos in render mode (Town)
* collision mesh and occlusion planes appear black in render mode (just disable them)


![Preview](meta/preview_220327_1.jpg)
![Preview](meta/preview_220420.jpg)
![Preview](meta/preview_220327_3.jpg)


# Special Thanks

[three-gunz](https://github.com/LostMyCode/three-gunz)  
[open-gunz](https://github.com/open-gunz/ogz-source)  
[rahulshekhawat](https://github.com/rahulshekhawat/blender-elu-ani-importer)  
[x1nixmzeng](https://github.com/x1nixmzeng/z3ResEx)  
[Nayr438](https://github.com/Nayr438)  
