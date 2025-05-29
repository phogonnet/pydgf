# PyDGF

A tool for reading/writing Data General formats.

> This started as a project to relearn python along in addition to Gtk.

## Features
* Reading Files
    * DSK images in either big/little endian format.
    * 9TRK with automatic attempts at `dump`ing files.
    * DP files as `dump` files.
* Writing Files
    * DSK images as 6030 `(616 sectors or 315KB)` in big endian format
        * If using [simh](https://github.com/open-simh/simh), you will need to `dd conv=swab`
    * DSK images as 4048 `(12180 sectors or 6MB)` in big endian format
        * If using [simh](https://github.com/open-simh/simh), you will need to `dd conv=swab`
* Drag and Drop support
    * Between other PyDGF disk windows.
    * Import from file system to PyDGF.

## Current Limitations
    * Directories with lots of files may cause problems with saving.
    * Not all user input is validated yet, things may get truncated/changed unexpectedly.
    * _MANY_ other assumptions made that may be wrong (DG Documentation is obviously light and something even wrong)!