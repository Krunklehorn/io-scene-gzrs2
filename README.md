# ***io_scene_gzrs2***

GunZ: The Duel RealSpace2/3 content importer for Blender 4.2.x LTS.<br>
Intended for users wishing to visualize and modify GunZ content or prepare the data for a modern game engine.

Please report bugs and unimplemented features to: ***Krunk#6051***

RaGEZONE thread: ***https://forum.ragezone.com/f496/io_scene_gzrs2-blender-3-1-map-1204327/***

## ***Make sure you specify a working directory in addon preferences.​***
***Don't update Blender's major version. This plugin will only support the v4.2 branch until further notice.***

![Beta Select](meta/steambetaselect_241122.jpg)

# Latest Update

[***ONLY WORKS WITH BLENDER 4.2.x!! >> DOWNLOAD v0.9.5.2***](https://github.com/Krunklehorn/io-scene-gzrs2/releases/tag/v0.9.5)

* NEW: .ani import support for GunZ 1 versions: 0x0012, 0x1001, 0x1002 and 0x1003
  * Animations become Actions, manage them with the Timeline or Dopesheet areas, combine them using NLA tracks
  * Per-object visibility is controlled through the object's viewport alpha channel (Object -> Viewport Display -> Color)
  * Bone type: Animates the selected armature's bones, disconnects bones to allow translation, controls bone position and rotation, but not scale
  * TM type: Controls object world space matrices, supports scaling but does not support parenting
  * Vertex type: Adds absolute mode shape keys, animates by keying Evaluation Time, may fail for meshes with duplicate or overlapping vertices
* NEW: .nav import & export support
  * When exporting, automatically triangulates quads and ngons however, users should do so manually for best results
  * When exporting, selected mesh must be non-manifold
* NEW: Material guidelines for .elu export have been simplified, see below!
* NEW: Reconfigured shader nodes and implemented material presets
* NEW: Added material info to the Realspace panel
* Simplified texture searching, renamed 'Smart' texture mode to 'Brute'
* Implicit effects now control additive rendering ('\_ef' and 'ef\_' prefixes)
* Sky objects no longer catch rays ('obj\_sky\_' and 'obj\_ef\_sky' prefixes)
* Mesh nodes beginning with "Dummy" are now treated as bones
* Other minor fixes


# Current Import Features

* Fully supported filetypes: .elu, .ani, .col, .cl2, .nav
* Mostly supported filetypes: .rs, .lm
* Partially supported filetypes: .scene.xml, .prop.xml

<!-- -->

* Displays world geometry, occlusion, collision and navigation data using mesh objects
* Displays BSP bounding boxes, sounds, spawns, powerups and other dummies using empties
* Approximates fog using a volume scatter or volume absorption shader
* Groups lights with similar properties, re-interprets the data to be useful in Blender
* Displays lightmaps using a linked node group for quick toggling
* Creates a driver object for quickly tuning lights and fog


# Current Export Features

## Model Export (.elu)

* GunZ 1 version 0x5007
* Supports both static and skinned meshes
* Automatically triangulates quads and ngons

<!-- -->

* Exports smooth normals if custom split normals are included
* Exports bone weight data from vertex groups
* Exports UV data from UV channel 0
* Exports cloth physics data from color attribute channel 0

<!-- -->

* Requires valid materials in each slot, if present (see below)
* Requires bones be contained in an Armature object
* Requires Armatures be linked using an Armature modifier (not parented!)
* Requires vertex groups corresponding to bones by exact name (case-sensitive!)
* Requires unique names for all bones across all linked armatures

![Basic Material](meta/basicmaterial_241215.jpg)

### Material ID/Sub-ID Guidelines

Realspace materials are not well defined. Certain effects are implicit, some cancel each other out, some behave differently based on context. Frankly, it's a mess.

The following guidelines help you set your material IDs and sub-IDs to sane values during export...

1. Material IDs must not have gaps. Example: cannot export with IDs 0, 3, and 4. Instead, use 0, 1, and 2.
2. Different meshes can use the same material, but one mesh with different materials must mark them as sub-materials by unchecking Base.
3. The sub-IDs of sub-materials must match the material slot they are used in. The top slot is 0.
4. Groups of sub-materials need a base of the same ID.*
5. The sub-material count of a base material must be high enough to hold it's sub-materials.

*No. 4 is handled for you automatically. Future updates will handle more.

These guidelines are based on patterns found in the vanilla GunZ content. Please submit an issue if you belive these guidelines are too restrictive or in error.

### Notes on texture paths, labels and valid data subdirectories...

RealSpace2's .elu format references textures using relative file paths. Paths are either relative to the .elu or relative to GunZ.exe.

Blender on the other hand, references textures using absolute file paths. Paths are always relative to your system's root. (ex: C:/...)

If you get this error during export...

    Unable to determine data path for texture in ELU material!

...this means one of your Image Texture node labels does not contain a valid RealSpace2 data subdirectory.
This check is not case sensitive. Valid data subdirectories are...

    GunZ 1/.mrs: 'Interface', 'Maps', 'Model', 'Quest', 'Sfx', 'Shader', 'Sound' and 'System'
    GunZ 2/.mrf: 'Data', 'EngineRes'

To work around this difference, you can control what path is written during export by labeling an Image Texture node. (right click -> rename)
- If an Image Texture node has no label, the file name of the image is written, which RealSpace2 interprets as .elu relative
- If it does have a label, the label needs to be a file path relative to Gunz.exe

The plugin will automatically truncate and verify the result for you. It will also remove double extensions (tex.bmp.dds -> tex.bmp) and sanitize double dds errors. (tex.dds.dds -> tex.dds)

Advanced users can still use the Maiet Character Viewer (MCV) to modify material paths after exporting.

### Examples of valid path labels:
- "model\woman\shoes.tga"
- "Documents\My Custom Gunz Content\SFX\fireball.bmp.dds"

### Examples of invalid path labels:
- "shoes.tga" -> just omit the label entirely
- "Documents\My Custom Gunz Content\fireball.bmp.dds" -> rearrange your folders, include a data subdirectory


## Navmesh Export (.nav)

* Automatically triangulates quads and ngons
  * For best results, user should do so manually
* Selected mesh must be non-manifold


## Lightmap Export (.lm)

* overwrite only
* supports image data as well as UVs
  * requires a GunZ 1 .rs file for the same map in the same directory
  * UV export requires an active mesh object with valid UVs in channel 3
* includes experimental "version 4" for bugfixes and DXT1 support (thanks to DeffJay)
  * version 4 lightmaps take less space and load faster, resolutions up to 8k are now viable
  * for private servers only, v4 lightmaps do not work with vanilla GunZ
  * contact Krunk#6051 for information on how to implement this


# Planned Features

* GunZ 1: .rs smoke.xml support
* GunZ 1: .rs flag.xml support
* GunZ 1: alpha .elu versions: 0x11, 0x5001, 0x5002 and 0x5003
* GunZ 1: .nav support
* GunZ 1: lightmap export UV generation

<!-- -->

* GunZ 2: .env.xml support
* GunZ 2: embedded scene hierarchies (ex: props with attached lights)
* GunZ 2: texture composition layers (terrain)


# Known Issues

* GunZ 1: handful of .elus with improper bone weights (woman-parts_eola)
* GunZ 1: all polygons in UV channel 2 come out garbled (import the lightmap and use channel 3 for now)
* GunZ 1: some polygons in UV channel 3 come out garbled on maps with multiple lightmaps (Citadel)
* GunZ 1: some elus with reversed winding-order/flipped normals (woman-parts27, woman-parts_sum08, woman-parts_santa, etc.)
* GunZ 1: some .elu map materials with incorrect flags that should be overridden by their .rs.xml counterparts
* GunZ 1: some maps with a ton of skipped dummies (Halloween Town)

<!-- -->

* GunZ 2: some objects are not oriented correctly (spotlights)
* GunZ 2: embedded scene hierarchies are not parsed yet (lighting_candlestick_y02, lighting_chandelier_g01, etc.)
* GunZ 2: materials do not support composition layers yet (weird colored terrain)


# Screenshots

![Preview](meta/preview_220327_1.jpg)
![Preview](meta/preview_220420.jpg)
![Preview](meta/preview_220327_3.jpg)


# Special Thanks

[three-gunz](https://github.com/LostMyCode/three-gunz)<br>
[open-gunz](https://github.com/open-gunz/ogz-source)<br>
[rahulshekhawat](https://github.com/rahulshekhawat/blender-elu-ani-importer)<br>
[x1nixmzeng, ThePhailure772, Lotus & coyotez1n](https://github.com/x1nixmzeng/z3ResEx)<br>
[Nayr438](https://github.com/Nayr438)<br>
[DeffJay](https://github.com/Jetman823)<br>
[HeroBanana](https://github.com/HeroBanana)<br>
bastardgoose<br>
Menotso<br>
Ennui