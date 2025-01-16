# ***io_scene_gzrs2***

GunZ: The Duel RealSpace2/3 content importer for Blender 4.2.x LTS.<br>
Intended for users wishing to visualize and modify GunZ content or prepare the data for a modern game engine.

Please report bugs and unimplemented features to: ***Krunk#6051***

RaGEZONE thread: ***https://forum.ragezone.com/f496/io_scene_gzrs2-blender-3-1-map-1204327/***

## ***Make sure you specify a working directory in addon preferences.​***
***Don't update Blender's major version. This plugin will only support the v4.2 branch until further notice.***

![Beta Select](meta/steambetaselect_241122.jpg)

# Latest Update

[***ONLY WORKS WITH BLENDER 4.2.x!! >> DOWNLOAD v0.9.6***](https://github.com/Krunklehorn/io-scene-gzrs2/releases/tag/v0.9.6)

* NEW: Object types! .rs and .elu import overhaul!
  * Artist friendly UI panels, no more string tags!
  * Empties, meshes, lights, cameras and more!
  * Content imported from previous versions will NOT be compatible, sorry!
  * Look for more 'Realspace' panels to see what controls are available!
* NEW: Light overhaul
  * Removed 'tweaks' and simplified
  * Dynamic lights hidden from render by default
  * New translation layer retains Realspace values in preparation for .rs export
  * Added UI controls for lightmap mix, mod4 fix and light recalculation
  * Phased out light drivers in favor of a UI panel for light translation, fog and other global settings
* NEW: Automatic material ID handling!
  * IDs and sub-IDs are now abstracted behind 'Priority', all of which you can safely ignore
  * Material type, base/sub distinctions are now implied by things like slot order and parent-child relationships
  * Don't panic if warnings appear in the material panel, just follow their instructions
  * Many, many checks are in place to help guide you and you can always message Krunk#6051 for support
* NEW: Better texture path controls, no more labeling image texture nodes!
* NEW: flag.xml and smoke.xml support
* Exposed shader emission and renamed 'Power' to 'Exponent'
* Converted occlusion planes to image dummies
* Fixed data directory processing for Linux paths
* Fixed lightmap uvs for atlased lightmaps (Citadel)
* Fixed .elu power values
* Phased out lightmap export atlasing, better to just increase texture resolution
* Phased out isEffects and UV layer 3
* Other minor fixes


# Current Import Features

* Fully supported filetypes: .elu, .ani, .col, .cl2, .nav
* Mostly supported filetypes: .rs, .lm
* Partially supported filetypes: .scene.xml, .prop.xml

<!-- -->

* Displays world geometry, collision and navigation data using mesh objects
* Displays bsptree and octree bounding boxes, occlusion planes, sounds, spawns, powerups and other dummies using empties
* Approximates fog using a volume scatter or volume absorption shader
* Reinterprets light data to be useful in Blender
* Displays lightmaps using a linked node group for quick toggling


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

### Material Parameters & Presets

Materials have changed! No more node wrangling, it's all handled by presets! =)

The plugin adds a custom "Realspace" panel in the Material Properties view. (see above) The panel provides a live report on what data will be written if exported. To modify the overall look of a material, use the "Change Preset" button.

Some parameters can be configured for special behavior:

| Parameter | Controlled By | Details |
| :---: | :---: | :---: |
| Texture / Alpha Path | Override Texpath / Write Directory ||
| Twosided | Material Properties -> Viewport Display -> Backface Culling ||
| Additive | Change Preset -> Additive ||
| Alphatest | Change Preset -> Tested | Configure the Threshold value of the Math: Greater Than node |
| Use Opacity | Change Preset -> Blended | Must have a valid texture in the Image Texture node |
| Is Animated | File name of the connected texture ||
| Frame Count / Frame Speed / Frame Gap | File name of the connected texture ||

### Notes on texture paths, labels and valid data subdirectories...

RealSpace2's .elu format references textures using relative file paths. Paths are either relative to the .elu or relative to GunZ.exe.

The Override Texpath and Write Directory switches give you control over what path is written during export.
If Write Directory is disabled, only the file name of the image is written which RealSpace2 interprets as .elu relative.

The plugin will automatically truncate and verify the result for you. It will also remove double extensions (tex.bmp.dds -> tex.bmp) and sanitize double dds errors. (tex.dds.dds -> tex.dds)

Advanced users can still use the Maiet Character Viewer (MCV) to modify material paths after exporting.

### Examples of valid path labels:
- "model\woman\shoes.tga"
- "Documents\My Custom Gunz Content\SFX\fireball.bmp.dds"

### Examples of invalid path labels:
- "shoes.tga" -> just omit the label entirely
- "Documents\My Custom Gunz Content\fireball.bmp.dds" -> double check your working directory in addon preferences then relocate your image to somewhere inside it


## Navmesh Export (.nav)

* Automatically triangulates quads and ngons
  * For best results, user should do so manually
* Selected mesh must be manifold


## Lightmap Export (.lm)

* overwrite only
* supports image data as well as UVs
  * requires a GunZ 1 .rs file for the same map in the same directory
  * UV export requires an active mesh object with valid UVs in channel 2
* includes experimental "version 4" for bugfixes and DXT1 support (thanks to DeffJay)
  * version 4 lightmaps take less space and load faster, resolutions up to 8k are now viable
  * for private servers only, v4 lightmaps do not work with vanilla GunZ
  * contact Krunk#6051 for information on how to implement this


# Planned Features

* GunZ 1: alpha .elu versions: 0x11, 0x5001, 0x5002 and 0x5003
* GunZ 1: lightmap export UV generation

<!-- -->

* GunZ 2: .env.xml support
* GunZ 2: embedded scene hierarchies (ex: props with attached lights)
* GunZ 2: texture composition layers (terrain)


# Known Issues

* GunZ 1: handful of .elus with improper bone weights (woman-parts_eola)
* GunZ 1: some elus with reversed winding-order/flipped normals (woman-parts27, woman-parts_sum08, woman-parts_santa, etc.)
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
Ennui<br>
bastardgoose<br>
Menotso<br>
Milanor<br>
Sunrui<br>