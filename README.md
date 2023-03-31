# svg2scad
This is a simple python script to translate from svg to scad, for the purposes of creating a "custom perf board". Essentially, if you've ever thought "I have this project which would be great on a perf board, but I can't find one of the right size and/or with holes in the proper places" then this is the script for you!

The script takes an svg file designed in Kicad (or similar, but I've only tested on Kicad files), extracts information about where holes and traces go and outputs this information into an output file in the form of scad code.
