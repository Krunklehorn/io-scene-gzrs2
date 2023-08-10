# ***io_scene_gzrs2***

GunZ: The Duel RealSpace2/3 content importer for Blender 3.6.1 and up.  
Intended for users wishing to visualize GunZ content, prepare the data for a modern game engine or bake and export a lightmap.

Please report bugs and unimplemented features to: ***Krunk#6051***

RaGEZONE thread: ***https://forum.ragezone.com/f496/io_scene_gzrs2-blender-3-1-map-1204327/***

[***DOWNLOAD v0.9.1***](https://github.com/Krunklehorn/io-scene-gzrs2/releases/download/v0.9.1/io_scene_gzrs2_v0.9.1.zip)


# Latest Update
* NEW: GunZ 2 scene.xml, prop.xml and .cl2 support
* NEW: GunZ 1 .lm support, both import and export
* NEW: Experimental .col cleanup recipe
* Improved .col import discards non-hull geometry
* Improved resource caching reduces load times
* Improved material logic prevents unnecessary duplicates
* Fixed issues with negative material IDs in GunZ 2 .elus
* Fixed issues with white halos on alpha textures in render mode (Town)


# Current Import Features

* supported filetypes: .rs, .elu, .col, .lm, .scene.xml, .prop.xml, .cl2
* displays world geometry, occlusion planes and collision data using mesh objects
* displays BSP bounding boxes, sounds, spawns, powerups and other dummies using empties
* approximates fog using a volume scatter or volume absorption shader
* groups lights with similar properties, re-interprets the data to be useful in Blender
* displays lightmaps using a linked node group for quick toggling
* creates a driver object for quickly tuning lights and fog
* notifies the user of..
  * missing textures and empty texture paths
  * out-of-bounds and unused material slots
  * unimplemented xml tags


# Current Export Features

* supported filetypes: .lm (overwrite only)
* can export lightmap image data as well as UVs
  * requires an active mesh object with valid UVs in channel 3
  * requires a GunZ 1 .rs file for the same map in the same directory
* includes experimental "version 4" for bugfixes and DXT1 support (thanks to DeffJay)
  * version 4 lightmaps take less space and load faster, resolutions up to 8k are now viable
  * they require client changes and do not work with vanilla GunZ
  * contact Krunk#6051 for information on how to implement this


# Planned Features

* GunZ 1.5 elu versions: 0x0, 0x11 and 0x5001, 0x5002 & 0x5003
* GunZ 2 retail elu versions: 0x5012, 0x5013 & 0x5014
* .ani support
* nav mesh support


# Known Issues

* quest maps and community maps have not been tested at all yet
* handful of GunZ 1 elus with improper bone weights (woman-parts_eola)
* GunZ 1 UV layer 2 comes out mangled (just import the lightmap and use layer 3 for now)
* GunZ 2 some objects are not oriented correctly (spotlights)
* GunZ 2 embedded scene hierarchies are not parsed yet (lighting_candlestick_y02, lighting_chandelier_g01, etc.)


![Preview](meta/preview_220327_1.jpg)
![Preview](meta/preview_220420.jpg)
![Preview](meta/preview_220327_3.jpg)


# Special Thanks

[three-gunz](https://github.com/LostMyCode/three-gunz)  
[open-gunz](https://github.com/open-gunz/ogz-source)  
[rahulshekhawat](https://github.com/rahulshekhawat/blender-elu-ani-importer)  
[x1nixmzeng](https://github.com/x1nixmzeng/z3ResEx)  
[Nayr438](https://github.com/Nayr438)  
