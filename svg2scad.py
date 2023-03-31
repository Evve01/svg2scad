import re, sys
import numpy as np

rot_matrix = np.array([[0, -1],[1, 0]])

resolution = 1e-6

print("svg2scad v0.2.0")

layers = int(input("Please input number of layers (maximum 2): "))

if layers == 1:
    source_file = input("Please input source file address: ")
else:
    top_file = input("Please input top file address: ")
    bottom_file = input("Please input bottom file address: ")

output_file = input("Please input output file address: ")

trace_width = 1
hole_radius = 0.5

dimensions = input("Please input dimensions x,y in mm: ").strip().split(',')
[width, height] = [float(dimensions[0]), float(dimensions[1])]

scad_file = open(output_file, 'w')

if layers == 1:
    svg_file = open(source_file).read()
else:
    svg_top_file = open(top_file).read()
    svg_bottom_file = open(bottom_file).read()



def circles_analyze(x, y, r):
    x *= resolution
    y *= resolution
    r = hole_radius
    return(((x, y), r))



def lines_analyze(x0, y0, x1, y1):
    x0 *= resolution
    y0 *= resolution
    x1 *= resolution
    y1 *= resolution

    u0 = np.array([x0, y0]).T
    u1 = np.array([x1, y1]).T

    direction = u1 - u0
    normal = (trace_width / 2)*(rot_matrix@direction) / (np.linalg.norm(direction))

    return([(u0 + normal).tolist(), (u0 - normal).tolist(), (u1 - normal).tolist(), (u1 + normal).tolist()])



def decode_file(svg):
    svg = svg.split('<g')                           #Split in such a way that each element in the list represents a g object

    for n in range(len(svg)):
        svg[n] = svg[n].strip()                     #remove leading and trailing whitespace
        svg[n] = svg[n].replace('</g>', '')         #Remove closing tag

    for n in range(len(svg)):
            svg[n] = svg[n].split('<')              #Split each list element into separate list elements, each containing one graphic element  

    for n in range(len(svg)):
        for m in range(len(svg[n])):
            svg[n][m] = svg[n][m].split(' ')    #Split each graphic element string into separate words

    for n in range(len(svg)):
        for m in range(len(svg[n])):
            for i in range(len(svg[n][m])):
                try:
                    svg[n][m][i] = re.sub(r".*fill.*", '', svg[n][m][i])            #Remove each 'fill'-command, since these commands aren't relevant for this purpose 
                except:
                    pass
                try:
                    svg[n][m][i] = re.sub(r"stroke-opacity.*", '', svg[n][m][i])    #Remove irrelevant 'stroke'-commands
                    svg[n][m][i] = re.sub(r"stroke-linecap.*", '', svg[n][m][i])
                    svg[n][m][i] = re.sub(r"stroke-linejoin.*", '', svg[n][m][i])
                except:
                    pass
                try:
                    svg[n][m][i] = svg[n][m][i].replace('/>', '')                   #Remove closing tag
                except:
                    pass
            try:
                while("" in svg[n][m]):
                    svg[n][m].remove('')                                            #Remove all empty charachters
            except:
                pass

    for n in range(len(svg)):
        for m in range(len(svg[n])):
            try:
                svg[n][m] = list(filter(None, svg[n][m]))                           #Remove all empty lists
            except:
                pass

    svg.pop(0)                                                                      #Remove first and last elements, as these only contain irrelevant meta data
    svg.pop(-1)

    popable = []

    for n in range(len(svg)):
        if len(svg[n]) == 1:
            popable.append(n)                                                       #Create list of g objects without graphical objects in them

    for n in range(len(popable)):
        svg.pop(popable[n] - n)                                                     #Remove saide g objects

    circles = []                                                                    #list of all circles. Each item will be of form [x location for centre in mm, 
    lines = []
    polygons = []

    for n in range(len(svg)):
        for m in range(len(svg[n])):
            if svg[n][m][0] == "circle":
                x = float(svg[n][m][1][4:-1])
                y = float(svg[n][m][2][4:-1])
                r = float(svg[n][m][3][3:-1])
                circles.append(circles_analyze(x, y, r))
            elif svg[n][m][0] == "path":
                if svg[n][m][1][1:7] == "stroke":
                    polygon = svg[n][m][5][:-3].replace('\n', ',')
                    polygon = polygon.split(',')
                    coords = []
                    for i in range(int(len(polygon) / 2)):
                        coords.append([float(polygon[2*i])*resolution, float(polygon[2*i + 1])*resolution])
                    polygons.append(coords)
                else:
                    line = []
                    for i in range(len(svg[n][m])):
                        if len(svg[n][m][i]) > 1:
                            line.append(svg[n][m][i].replace('\n',''))
                    line = line[1:]
                    line[0] = line[0][4:]
                    line[-1] = line[-1][:-1]
                    line[1] = line[1].split('L')
                    [x0, y0, x1, y1] = [float(line[0]), float(line[1][0]), float(line[1][1]), float(line[2])]
                    lines.append(lines_analyze(x0, y0, x1, y1))

    return(circles, polygons, lines)



def circles_to_scad(list_of_circles):
    set_of_circles = set()
    circle_code = []
    for n in list_of_circles:
        set_of_circles.add(n)
    for n in set_of_circles:
        circle_code.append("translate([" + str(n[0][0]) + ", " + str(n[0][1]) + ", 0])\n")
        circle_code.append("\tcircle(r = " + str(n[1]) + ");\n")
    return(circle_code)



def polygons_to_scad(list_of_polygons):
    polygons_code = []
    for n in list_of_polygons:
        polygons_code.append("polygon(" + str(n) +");\n")
    return(polygons_code)



def lines_to_scad(list_of_lines):
    lines_code = []
    for n in list_of_lines:
        lines_code.append("polygon(" + str(n) + ");\n")
    return(lines_code)



def code_single_layer(svg, scad):
    [circles, polygons, lines] = decode_file(svg)
    [holes_code, polygons_code, lines_code] = [circles_to_scad(circles), polygons_to_scad(polygons), lines_to_scad(lines)]

    scad.write("module PCB() {\n")
    scad.write("\tdifference() {\n")
    scad.write("\t\tcube([" + str(width) + ", "+ str(height) + ", 2]);\n")
    scad.write("\t\tunion() {\n")

    scad.write("\t\t\t//code to generate circles:\n")
    scad.write("\t\t\ttranslate([0, 0, -0.5]) {\n")
    scad.write("\t\t\t\tlinear_extrude(3) {\n")
    for n in holes_code:
        scad.write("\t\t\t\t\t" + n)
    scad.write("\t\t\t\t}\n")
    scad.write("\t\t\t}\n")


    scad.write("\n\t\t\t//code to generate various polygons:\n")
    scad.write("\t\t\ttranslate([0, 0, 1.2]) {\n")
    scad.write("\t\t\t\tlinear_extrude(1) {\n")
    for n in polygons_code:
        scad.write("\t\t\t\t\t" + n)
    scad.write("\t\t\t\t}\n")
    scad.write("\t\t\t}")

    scad.write("\n\t\t\t//code to generate traces:\n")
    scad.write("\t\t\ttranslate([0, 0, 1.2]) {\n")
    scad.write("\t\t\t\tlinear_extrude(1) {\n")
    scad.write("\t\t\t\t\tunion() {\n")
    for n in lines_code:
        scad.write("\t\t\t\t\t\t" + n)
    scad.write("\t\t\t\t\t}\n")
    scad.write("\t\t\t\t}\n")
    scad.write("\t\t\t}\n")

    scad.write("\t\t}\n")
    scad.write("\t}\n")
    scad.write("};")



def code_double_layer(svg_top, svg_bottom, scad):
    [circles_top, polygons_top, lines_top] = decode_file(svg_top)
    [circles_bottom, polygons_bottom, lines_bottom] = decode_file(svg_bottom)
    holes = circles_top
    for n in circles_bottom:
        holes.append(n)
    [hole_code, polygons_top_code, lines_top_code] = [circles_to_scad(holes), polygons_to_scad(polygons_top), lines_to_scad(lines_top)]
    [polygons_bottom_code, lines_bottom_code] = [polygons_to_scad(polygons_bottom), lines_to_scad(lines_bottom)]

    scad.write("module PCB() {\n")
    scad.write("\tdifference() {\n")
    scad.write("\t\tcube([" + str(width) + ", "+ str(height) + ", 2]);\n")
    scad.write("\t\tunion() {\n")

    scad.write("\t\t\t//code to generate holes:\n")
    scad.write("\t\t\ttranslate([0, 0, -0.5]) {\n")
    scad.write("\t\t\t\tlinear_extrude(3) {\n")
    for n in holes_code:
        scad.write("\t\t\t\t" + n)
    scad.write("\t\t\t\t}\n")
    scad.write("\t\t\t}\n")

    scad.write("\t\t\t//TOP LAYER\n")

    scad.write("\n\t\t\t//code to generate various polygons:\n")
    scad.write("\t\t\ttranslate([0, 0, 1.2]) {\n")
    scad.write("\t\t\t\tlinear_extrude(1) {\n")
    for n in polygons_top_code:
        scad.write("\t\t\t\t\t" + n)
    scad.write("\t\t\t\t}\n")
    scad.write("\t\t\t}")

    scad.write("\n\t\t\t//code to generate traces:\n")
    scad.write("\t\t\ttranslate([0, 0, 1.2]) {\n")
    scad.write("\t\t\t\tlinear_extrude(1) {\n")
    scad.write("\t\t\t\t\tunion() {\n")
    for n in lines_top_code:
        scad.write("\t\t\t\t\t\t" + n)
    scad.write("\t\t\t\t\t}\n")
    scad.write("\t\t\t\t}\n")
    scad.write("\t\t\t}\n")

    scad.write("\t\t\t//BOTTOM LAYER\n")

    scad.write("\n\t\t\t//code to generate various polygons:\n")
    scad.write("\t\t\ttranslate([0, 0, -.2]) {\n")
    scad.write("\t\t\t\tlinear_extrude(1) {\n")
    for n in polygons_bottom_code:
        scad.write("\t\t\t\t\t" + n)
    scad.write("\t\t\t\t}\n")
    scad.write("\t\t\t}")

    scad.write("\n\t\t\t//code to generate traces:\n")
    scad.write("\t\t\ttranslate([0, 0, -.2]) {\n")
    scad.write("\t\t\t\tlinear_extrude(1) {\n")
    scad.write("\t\t\t\t\tunion() {\n")
    for n in lines_bottom_code:
        scad.write("\t\t\t\t\t\t" + n)
    scad.write("\t\t\t\t\t}\n")
    scad.write("\t\t\t\t}\n")
    scad.write("\t\t\t}\n")

    scad.write("\t\t}\n")
    scad.write("\t}\n")
    scad.write("};")

if layers == 1:
    code_single_layer(svg_file, scad_file)
else:
    code_double_layer(svg_top_file, svg_bottom_file, scad_file)
