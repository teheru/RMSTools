Description
-----------

**RMSTools** is a small collection (currently consisting of a single tool :) ) to ease the work with RMS (Random Map Script) files of the game Age of Empires II.

Tools
-----

**mappacker.py**: Removes a lot of content from RMS files, which wont be used by the game anyways. This includes removing whitespace and comments but also random cases which never can be reached (for example if they have a percent chance of 0) and conditions which never can be reached. This is useful for maps which are created using a map pack by setting one percent_chance to 100 and the others one to 0.
It also can create random map packs of multiple maps which in the resulting map occur with (almost) the same probability.
This tool currently has some problems if the map has an uneven number of if/endif or start_random/end_random what often will result in broken maps. If this happens, you have to manually fix the RMS file. This is not a fault of the tool but of the map maker, so blame him, not me :) .

Licence
-------

**Modified BSD Licence**; see [copying.md](copying.md) .
