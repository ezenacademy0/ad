import bpy
import math
import random
from mathutils import Matrix, Vector

S = bpy.context.scene
for old in list(bpy.data.objects):
    bpy.data.objects.remove(old, do_unlink=True)
for old in list(bpy.data.collections):
    bpy.data.collections.remove(old)
S.name = "KIRSCH HOME | A room for color"
S.unit_settings.system = 'METRIC'
S.render.fps = 24
S.frame_start, S.frame_end = 1, 576
S.render.resolution_x, S.render.resolution_y = 1280, 720
S.render.resolution_percentage = 100
S.render.engine = 'BLENDER_EEVEE' if bpy.app.version >= (5, 0, 0) else 'BLENDER_EEVEE_NEXT'
S.eevee.taa_render_samples = 12
S.render.image_settings.file_format = 'PNG'
S.view_settings.view_transform = 'AgX'
S.view_settings.look = 'AgX - Medium High Contrast'

def collection(name):
    coll = bpy.data.collections.new(name)
    S.collection.children.link(coll)
    return coll

CAB = collection("01 · CABIN / timber shell and door")
SET = collection("02 · INTERIOR / wood, linen and objects")
BED = collection("03 · HERO / the color bed")
GARDEN = collection("04 · WOODLAND / path and canopy")
ACT = collection("05 · ACTOR / woman and heart")
SHOT = collection("06 · CAMERA / shot sequence")
LIGHT = collection("07 · LIGHTING / sun and window")
END = collection("08 · END CARD / brand lettering")

def linear(v):
    return v / 12.92 if v < .04045 else ((v + .055) / 1.055) ** 2.4

def rgba(hexcode):
    return tuple(linear(int(hexcode[i:i+2], 16) / 255) for i in (0, 2, 4)) + (1.0,)

def mat(name, hexcode, rough=.58, metal=0, sheen=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = rgba(hexcode)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = m.diffuse_color
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Sheen Weight"].default_value = sheen
    return m

def object_from(data, name, coll, loc=(0, 0, 0), parent=None, material=None):
    o = bpy.data.objects.new(name, data)
    coll.objects.link(o)
    o.parent = parent
    o.location = loc
    if material:
        if not data.materials:
            data.materials.append(material)
        o.material_slots[0].link = 'OBJECT'
        o.material_slots[0].material = material
    return o

def empty(name, coll, loc=(0, 0, 0), parent=None):
    o = object_from(None, name, coll, loc, parent)
    o.empty_display_size = .22
    return o

def mesh(name, verts, faces, smooth=False):
    d = bpy.data.meshes.new(name)
    d.from_pydata(verts, [], faces)
    d.update()
    if smooth:
        for face in d.polygons:
            face.use_smooth = True
    return d

unit_box = mesh("Unit box", [(-.5,-.5,-.5),(.5,-.5,-.5),(.5,.5,-.5),(-.5,.5,-.5),(-.5,-.5,.5),(.5,-.5,.5),(.5,.5,.5),(-.5,.5,.5)],
    [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
box_cache = {}

def box(name, loc, size, material, coll, radius=0, parent=None):
    if radius:
        key = tuple(round(v, 5) for v in size)
        if key not in box_cache:
            d = unit_box.copy()
            d.name = name + " profile"
            d.transform(Matrix.Diagonal((*size, 1)))
            box_cache[key] = d
        o = object_from(box_cache[key], name, coll, loc, parent, material)
        bevel = o.modifiers.new("Rounded edge", 'BEVEL')
        bevel.width, bevel.segments = radius, 3
        bevel.harden_normals = True
        weighted = o.modifiers.new("Weighted normals", 'WEIGHTED_NORMAL')
        weighted.keep_sharp = True
    else:
        o = object_from(unit_box, name, coll, loc, parent, material)
        o.scale = size
    return o

def ring_mesh(name, profile, sides=24, smooth=True):
    verts = [(rx*math.cos(a*math.tau/sides), ry*math.sin(a*math.tau/sides), z)
             for z, rx, ry in profile for a in range(sides)]
    faces = [tuple(range(sides-1, -1, -1))]
    for j in range(len(profile)-1):
        for i in range(sides):
            a, b = j*sides+i, j*sides+(i+1)%sides
            faces.append((a, b, b+sides, a+sides))
    faces.append(tuple((len(profile)-1)*sides+i for i in range(sides)))
    return mesh(name, verts, faces, smooth)

ellipsoid = ring_mesh("Smooth sphere",
    [(math.sin(t*math.pi/16)*.999, max(.005,math.cos(t*math.pi/16)), max(.005,math.cos(t*math.pi/16))) for t in range(-8,9)], 24)
stone_mesh = ring_mesh("River pebble", [(-.8,.24,.30),(-.40,.82,.94),(.16,1,1),(.55,.73,.79),(.77,.27,.32)], 9, False)
trunk_mesh = ring_mesh("Pine trunk", [(0,1,1),(.72,.64,.63),(1,.27,.27)], 9, False)
pine_mesh = ring_mesh("Fir crown", [(0,.67,.67),(.08,1,1),(.27,.70,.70),(.52,.43,.43),(.76,.23,.23),(1,.012,.012)], 11, False)

def oval(name, loc, scale, material, coll, parent=None, data=ellipsoid):
    o = object_from(data, name, coll, loc, parent, material)
    o.scale = scale
    return o

def tube(name, points, width, material, coll, parent=None, smooth=False, radius=None):
    d = bpy.data.curves.new(name, 'CURVE')
    d.dimensions = '3D'
    d.resolution_u = 10
    d.bevel_depth = width
    d.bevel_resolution = 3
    d.use_fill_caps = True
    if smooth:
        spl = d.splines.new('BEZIER')
        spl.bezier_points.add(len(points)-1)
        for j, (p, xyz) in enumerate(zip(spl.bezier_points, points)):
            p.co = xyz
            p.handle_left_type = p.handle_right_type = 'AUTO'
            if radius:
                p.radius = radius[j]
    else:
        spl = d.splines.new('POLY')
        spl.points.add(len(points)-1)
        for j, (p, xyz) in enumerate(zip(spl.points, points)):
            p.co = (*xyz, 1)
            if radius:
                p.radius = radius[j]
    return object_from(d, name, coll, parent=parent, material=material)

def aim(obj, at):
    obj.rotation_euler = (Vector(at) - obj.location).to_track_quat('-Z', 'Y').to_euler()

def camera(name, loc, at, lens):
    d = bpy.data.cameras.new(name)
    d.lens, d.clip_end = lens, 135
    o = object_from(d, name, SHOT, loc)
    aim(o, at)
    return o

def light(name, kind, loc, power, color, softness, at=None):
    d = bpy.data.lights.new(name, kind)
    d.energy, d.color = power, color
    if kind == 'SUN':
        d.angle = softness
    else:
        d.shadow_soft_size = softness
    o = object_from(d, name, LIGHT, loc)
    if at:
        aim(o, at)
    return o

S.world = bpy.data.worlds.new("Soft blue woodland sky")
S.world.use_nodes = True
bg = S.world.node_tree.nodes.get("Background")
bg.inputs["Color"].default_value = rgba("A3C6CC")
bg.inputs["Strength"].default_value = .74
keylight = light("LGT_sun • late afternoon", 'SUN', (2.8,-4,8), 2.4, (1,.86,.68), .14, (0,2,0))
outfill = light("LGT_exterior fill", 'POINT', (1.8,-4.6,4.6), 390, (.69,.83,1), 2.3)
windowkey = light("LGT_skylight • warm", 'POINT', (2.25,2.25,3.12), 215, (1,.87,.69), .78)
fill = light("LGT_bedroom bounce", 'POINT', (-1.95,1.30,2.52), 135, (1,.91,.80), .68)
CAM_A = camera("CAM_01 • Approach", (5.8,-10.2,3.47), (-.31,-.4,1.88), 34)
CAM_B = camera("CAM_02 • Threshold", (-2.5,-3.18,1.54), (-1.11,.78,1.39), 29)
CAM_C = camera("CAM_03 • Bed colors", (2.88,.64,2.10), (.10,3.52,1.03), 35)
CAM_D = camera("CAM_04 • Heart cushion", (2.87,.39,1.68), (.50,1.84,1.10), 32)
CAM_E = camera("CAM_05 • Sky", (6.35,-2.04,5.30), (1.35,1.9,4.35), 45)
S.camera = CAM_A

trim = mat("Cabin | honeyed trim", "B47A4E", .57)
beam = mat("Cabin | dark oak structure", "653D33", .68)
boards = [mat("Cabin | cedar " + str(i+1), c, .68) for i,c in enumerate(("AD7350","A66B47","B47A51","B57950","AE6C46"))]
inside = [mat("Interior | sanded pine " + str(i+1), c, .72) for i,c in enumerate(("BF926A","C49A70","C89B74","BB8E66","C09370"))]
floor = [mat("Interior | wide-plank oak " + str(i+1), c, .66) for i,c in enumerate(("9D6F51","A37352","A87856","AF7C55","AB7859"))]
roof = [mat("Roof | clay shingles " + str(i+1), c, .75) for i,c in enumerate(("795045","875449","8E5B49","8E584C","9C624D"))]
stone = [mat("Ground | riverstone " + str(i+1), c, .91) for i,c in enumerate(("7C8271","899180","A0A18B","747968"))]
soil = mat("Ground | warm clay", "9D8059", .91)
grass = [mat("Ground | meadow " + str(i+1), c, .93) for i,c in enumerate(("5F795D","6D8964","778B63","829165","59785F"))]
leaf = [mat("Forest | fir " + str(i+1), c, .86) for i,c in enumerate(("395D54","4B705D","557865","6B8866","3B6A5C"))]
bark = mat("Forest | bark", "624C3E", .89)
warm = mat("Bed | unbleached linen", "EFE0C9", .80, sheen=.18)
red = mat("Bed | 01 Cherry", "B92E4B", .76, sheen=.22)
rug = mat("Interior | straw weave", "AD946A", .87)
cream = mat("Interior | rug piping", "DEC5A1", .82)
brass = mat("Hardware | brushed brass", "BE8B4B", .29, .65)
doorwood = mat("Cabin | painted olive door", "526B54", .63)
doortrim = mat("Cabin | painted olive molding", "5D7A62", .60)
glass = mat("Window | morning blue", "799C9F", .32)
rnd = random.Random(173)

box("ENV_meadow base", (0,5,-.16), (53,49,.25), grass[1], GARDEN)
box("CAB_foundation", (0,2.8,.065), (6.76,5.67,.19), beam, CAB, .055)
for i in range(26):
    x = -3.275 + i*.262
    box("SET_floorboard %02d" % (i+1), (x,2.8,.172), (.258,5.57,.054), rnd.choice(floor), SET, .006)
for i in range(11):
    box("CAB_porch plank %02d" % (i+1), (-2.51+i*.211,-.44,.149), (.207,.91,.087), rnd.choice(boards), CAB, .012)
box("CAB_porch lower step", (-1.455,-1.03,.058), (2.42,.32,.14), beam, CAB, .033)
box("CAB_porch step tread", (-1.455,-1.01,.127), (2.50,.37,.045), trim, CAB, .020)

def clad(label, direction, const, starts, int_skin=False):
    for k in range(14):
        lo = .205+k*.203
        hi = lo+.198
        spans = starts(lo+.099)
        for j,(a,b) in enumerate(spans):
            if b-a < .004:
                continue
            center = (a+b)/2
            matl = rnd.choice(boards)
            p = (center,const,lo+.099) if direction == 'X' else (const,center,lo+.099)
            dim = (b-a,.158,.198) if direction == 'X' else (.158,b-a,.198)
            box("CAB_"+label+" course %02d.%d" % (k+1,j+1), p, dim, matl, CAB, .008)
            if int_skin:
                side = 1 if const <= .01 else -1
                q = (center,const+side*.086,lo+.099) if direction == 'X' else (const+side*.086,center,lo+.099)
                dim = (b-a,.017,.197) if direction == 'X' else (.017,b-a,.197)
                box("SET_"+label+" lining %02d.%d" % (k+1,j+1), q, dim, rnd.choice(inside), SET)

clad("front wall", 'X', 0, lambda z: [(-3.28,-2.12),(-.70,.62),(2.53,3.28)] if 1.16<z<2.41 else ([(-3.28,-2.12),(-.70,3.28)] if z<2.44 else [(-3.28,3.28)]))
clad("back wall", 'X', 5.60, lambda z: [(-3.28,-2.76),(-1.09,3.28)] if 1.34<z<2.58 else [(-3.28,3.28)], True)
clad("west wall", 'Y', -3.32, lambda z: [(0,5.60)], True)
clad("east wall", 'Y', 3.32, lambda z: [(0,2.53),(4.36,5.60)] if 1.17<z<2.60 else [(0,5.60)], True)

for x in (-3.29,3.29):
    for y in (-.025,5.61):
        box("CAB_corner post %+.1f %+.1f" % (x,y), (x,y,1.68), (.203,.214,3.02), trim, CAB, .019)
for y in (.033,5.58):
    box("CAB_gable sill %+.1f" % y, (0,y,3.045), (6.85,.21,.20), beam, CAB, .016)
    verts = [(-3.35,y+dy,3.10) for dy in (-.074,.074)] + [(3.35,y+dy,3.10) for dy in (-.074,.074)] + [(0,y+dy,4.56) for dy in (-.074,.074)]
    gd = mesh("Gable prism", verts, [(0,2,4),(5,3,1),(0,1,3,2),(2,3,5,4),(4,5,1,0)])
    object_from(gd, "CAB_gable infill %+.1f" % y, CAB, material=boards[2])
    for i,x in enumerate([-2.65,-2.15,-1.65,-1.15,-.65,0,.65,1.15,1.65,2.15,2.65]):
        h = (4.52-.429*abs(x))-3.10
        box("CAB_gable batten %+.1f.%02d" % (y,i), (x,y-.086,3.10+h/2), (.036,.026,h), trim, CAB, .005)

def roof_rect(name, a, b, y1, y2, height, material, thickness=.10):
    x = (a+b)/2
    o = box(name, (x,(y1+y2)/2,4.64-.433*abs(x)+height), ((b-a)*1.09,y2-y1,thickness), material, CAB, min(.018,thickness/4))
    o.rotation_euler.y = math.atan(.433) * (1 if x>=0 else -1)
    return o

hole = (.61,2.86,.94,3.12)
a,b,c,d = hole
roof_sections = [(-3.72,-.01,-.49,6.06),(.01,a,-.49,6.06),(b,3.72,-.49,6.06),(a,b,-.49,c),(a,b,d,6.06)]
for i,(x1,x2,y1,y2) in enumerate(roof_sections):
    roof_rect("CAB_roof deck %d" % i,x1,x2,y1,y2,-.045,roof[0],.14)
for i,side in enumerate((-1,1)):
    for y in (-.50,6.06):
        lo,hi = (-3.74,-.008) if side<0 else (.008,3.74)
        roof_rect("CAB_rake fascia %d %.1f" % (i,y),lo,hi,y-.06,y+.06,-.032,beam,.19)
    x = side*3.67
    box("CAB_eave fascia %d" % i, (x,2.79,3.025), (.15,6.61,.19), beam, CAB, .022)
box("CAB_ridge cap", (0,2.78,4.691), (.18,6.64,.12), roof[1], CAB, .040)
for x in (a-.055,b+.055):
    roof_rect("CAB_skylight longitudinal %.1f" % x,x-.055,x+.055,c-.085,d+.085,.065,trim,.14)
for y in (c-.050,d+.050):
    roof_rect("CAB_skylight crossbeam %.1f" % y,a-.10,b+.10,y-.05,y+.05,.065,trim,.14)

hinge = empty("RIG_door hinge", CAB, (-2.105,-.013,.199))
box("CAB_door solid leaf", (.681,0,1.086), (1.362,.102,2.172), doorwood, CAB, .035, hinge)
for x in (-2.175,-.643):
    box("CAB_door jamb %.2f" % x,(x,-.032,1.33),(.133,.208,2.31),trim,CAB,.021)
box("CAB_door lintel",(-1.41,-.032,2.425),(1.665,.224,.149),trim,CAB,.024)
for y in (-.062,.060):
    for i in range(5):
        box("CAB_door inset board %d %.2f" % (i,y),(.145+i*.265,y,1.088),(.248,.036,1.985),doortrim,CAB,.014,hinge)
    for z in (.28,1.88):
        box("CAB_door cross rail %.2f %.2f" % (y,z),(.682,y*1.48,z),(1.275,.044,.122),doorwood,CAB,.017,hinge)
    oval("CAB_door brass knob %.2f" % y,(1.226,y*2.45,.965),(.052,.045,.052),brass,CAB,hinge)
    box("CAB_door knob plate %.2f" % y,(1.226,y*1.53,.966),(.077,.025,.191),brass,CAB,.014,hinge)

def window(name, direction, const, a, b, z1, z2):
    def insert(suffix, u, z, width, height, depth, material, offset=0):
        loc = (u,const+offset,z) if direction=='X' else (const+offset,u,z)
        dims = (width,depth,height) if direction=='X' else (depth,width,height)
        box("CAB_window "+name+" "+suffix,loc,dims,material,CAB,.013)
    for u,tag in ((a,"left"),(b,"right")):
        insert(tag,u,(z1+z2)/2,.112,z2-z1+.10,.244,trim)
    for z,tag in ((z1,"sill"),(z2,"header")):
        insert(tag,(a+b)/2,z,b-a+.22,.105,.302,trim)
    insert("vertical muntin",(a+b)/2,(z1+z2)/2,.047,z2-z1,.130,beam)
    insert("cross muntin",(a+b)/2,(z1+z2)/2,b-a,.047,.130,beam)

window("front", 'X', -.015, .62,2.53,1.19,2.43)
window("back", 'X', 5.60, -2.76,-1.09,1.41,2.58)
window("east", 'Y', 3.32, 2.53,4.36,1.20,2.63)

bed = empty("HERO_bed / dimensions in meters", BED, (.15,3.54,.20))
box("HERO_bed oak plinth", (0,0,.135), (1.96,2.24,.21), beam, BED, .075, bed)
for x in (-.75,.75):
    for y in (-.89,.89):
        box("HERO_bed support %+.2f %+.2f" % (x,y), (x,y,.07),(.17,.17,.14),trim,BED,.039,bed)
box("HERO_bed linen mattress", (0,-.012,.445), (1.982,2.19,.265), warm, BED, .106, bed)
hero_base = box("BLOCKOUT_bed base", (0,0,.299), (2.025,2.257,.27), red,BED,.108,bed)
hero_head = box("BLOCKOUT_bed headboard", (0,1.127,.771),(2.10,.195,1.27),red,BED,.092,bed)
hero_duvet = box("BLOCKOUT_bed quilt", (0,-.28,.595),(2.07,1.73,.20),red,BED,.094,bed)
for i,x in enumerate((-.45,.45)):
    o = box("HERO_linen pillow %d" % i,(x,.70,.643),(.76,.49,.20),warm,BED,.092,bed)
    o.rotation_euler.x = math.radians(10)
box("SET_woven floor rug",(.17,3.13,.211),(3.27,3.61,.023),rug,SET,.011)
box("SET_left bedside plinth",(-1.53,4.15,.47),(.53,.52,.55),trim,SET,.060)
box("SET_right bedside plinth",(1.88,4.24,.47),(.57,.51,.55),trim,SET,.060)

for i in range(14):
    y = -1.28-i*.405
    x = -1.46+.13*math.sin(i*.75)+rnd.uniform(-.12,.12)
    o=oval("ENV_stepping stone %02d" % i,(x,y,.008), (rnd.uniform(.33,.49),rnd.uniform(.17,.25),.079), rnd.choice(stone),GARDEN,data=stone_mesh)
    o.rotation_euler.z = rnd.uniform(-.3,.3)
for i in range(14):
    side = -1 if i%2 else 1
    oval("ENV_granite %02d" % i,(side*rnd.uniform(2.9,9),rnd.uniform(-6,10),.095),(rnd.uniform(.24,.75),rnd.uniform(.21,.51),rnd.uniform(.14,.36)),rnd.choice(stone),GARDEN,data=stone_mesh)
def tree(i,x,y,h):
    p = empty("ENV_fir %02d" % i,GARDEN,(x,y,-.03))
    p.rotation_euler.z = rnd.uniform(0,math.tau)
    oval("Fir %02d • trunk" % i,(0,0,0),(.13*h/3,.13*h/3,h*.84),bark,GARDEN,p,trunk_mesh)
    for k in range(3):
        r = h*(.23-k*.046)
        crown = oval("Fir %02d • crown %d" % (i,k+1),(0,0,h*(.21+k*.185)),(r,r,h*.50),leaf[(i+k)%len(leaf)],GARDEN,p,pine_mesh)
        crown.rotation_euler.z = k*.27
tree_coords=[(-6.20,-1.92,5.9),(-5.4,1.0,5.4),(-4.3,3.2,5.1),(-5.9,4.9,6.4),(-7.7,-.4,6.9),(6.1,3.0,5.0),(7.3,.9,5.9),(8.6,3.4,6.25),(5.6,6,5.9),(4.08,6.68,5.0),(2.53,7.7,6.0),(.5,8.15,6.8),(-1.8,7.9,5.7),(-3.5,7.5,6.9),(-7.5,7.0,5.6),(8.6,7,6.9)]
tree_coords += [(x+rnd.uniform(-.36,.36),y+rnd.uniform(-.6,.6),rnd.uniform(4.2,7.8)) for y in (10.3,13.9,18) for x in range(-12,13,3)]
for i,(x,y,h) in enumerate(tree_coords):
    tree(i,x,y,h)

skin = mat("Actor | warm terracotta skin", "D78E6D", .57)
knit = mat("Actor | vanilla knit", "E8C598", .83, sheen=.20)
denim = mat("Actor | dusk-blue overalls", "49606A", .83, sheen=.21)
hair = mat("Actor | chestnut hair", "51352F", .56)
blush = mat("Heart | raspberry velvet", "C63D64", .81, sheen=.27)
proxy = empty("BLOCKOUT_actor root", ACT, (-1.38,-5.66,.04))
oval("BLOCKOUT_actor coat", (0,0,1.04), (.22,.135,.28), knit, ACT, proxy)
oval("BLOCKOUT_actor head", (0,.01,1.49), (.135,.119,.171), skin, ACT, proxy)
oval("BLOCKOUT_actor hair", (0,-.035,1.53), (.146,.115,.178), hair, ACT, proxy)
for i,x in enumerate((-.10,.10)):
    oval("BLOCKOUT_actor leg %d" % i,(x,0,.515),(.081,.076,.40),denim,ACT,proxy)
    oval("BLOCKOUT_actor shoe %d" % i,(x,.038,.08),(.085,.144,.074),hair,ACT,proxy)
oval("BLOCKOUT_heart cushion", (1.64,1.53,.279),(.252,.204,.070),blush,ACT)

result = {"objects":len(S.objects),"cameras":[o.name for o in SHOT.objects],"bed_m":[2.025,2.257,1.406],"door":"RIG_door hinge","roof_opening_m":[b-a,d-c]}
