import bpy
import math
import random
from mathutils import Matrix, Quaternion, Vector
S = bpy.context.scene
CAB, SET, BED, GARDEN, ACT, SHOT, LIGHT, END = [next(c for c in S.collection.children if c.name.startswith("%02d " % i)) for i in range(1, 9)]
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

unit_box = bpy.data.meshes["Unit box"]
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

ellipsoid = bpy.data.meshes["Smooth sphere"]
stone_mesh = bpy.data.meshes["River pebble"]
trunk_mesh = bpy.data.meshes["Pine trunk"]
pine_mesh = bpy.data.meshes["Fir crown"]

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

O = bpy.data.objects
M = bpy.data.materials
bed = O["HERO_bed / dimensions in meters"]
hinge = O["RIG_door hinge"]
trim = M["Cabin | honeyed trim"]
beam = M["Cabin | dark oak structure"]
warm = M["Bed | unbleached linen"]
brass = M["Hardware | brushed brass"]
cream = M.get("Interior | rug piping") or mat("Interior | rug piping", "DEC5A1", .82)
skin = M["Actor | warm terracotta skin"]
knit = M["Actor | vanilla knit"]
denim = M["Actor | dusk-blue overalls"]
hair = M["Actor | chestnut hair"]
blush = M["Heart | raspberry velvet"]
roof = [M.get("Roof | clay shingles "+str(i+1)) or mat("Roof | clay shingles "+str(i+1),color,.75) for i,color in enumerate(("795045","875449","8E5B49","8E584C","9C624D"))]
leaf = [M["Forest | fir "+str(i+1)] for i in range(5)]
grass = [M.get("Ground | meadow "+str(i+1)) or mat("Ground | meadow "+str(i+1),color,.93) for i,color in enumerate(("5F795D","6D8964","778B63","829165","59785F"))]
rnd = random.Random(260)

for o in list(S.objects):
    if o.name.startswith("BLOCKOUT_"):
        O.remove(o, do_unlink=True)

def rounded_points(w, h, r, count=8):
    r = min(r,w/2-.0001,h/2-.0001)
    return [(cx+r*math.cos(math.radians(start)+k*math.pi/2/count),cy+r*math.sin(math.radians(start)+k*math.pi/2/count))
        for cx,cy,start in ((w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180),(w/2-r,-h/2+r,270))
        for k in range(count+1)]

def upholstered(name, rings):
    lines = [rounded_points(w,l,r) for z,w,l,r in rings]
    n = len(lines[0])
    verts = [(x,y,rings[j][0]) for j,row in enumerate(lines) for x,y in row]
    faces = [tuple(range(n-1,-1,-1))]
    for j in range(len(lines)-1):
        for i in range(n):
            a,b=j*n+i,j*n+(i+1)%n
            faces.append((a,b,b+n,a+n))
    faces.append(tuple((len(lines)-1)*n+i for i in range(n)))
    d = mesh(name, verts, faces, True)
    d.polygons[0].use_smooth = d.polygons[-1].use_smooth = False
    return d

def loop_curve(name, points, width, material, coll, parent):
    o = tube(name, points, width, material, coll, parent)
    o.data.splines[0].use_cyclic_u = True
    return o

def glow(name, color, power=1):
    m = mat(name,color,.60)
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Emission Color"].default_value = rgba(color)
    p.inputs["Emission Strength"].default_value = power
    return m

def soften_wood(m):
    n = m.node_tree.nodes
    link = m.node_tree.links
    p = n.get("Principled BSDF")
    uv = n.new('ShaderNodeTexCoord')
    scale = n.new('ShaderNodeVectorMath')
    scale.operation = 'MULTIPLY'
    scale.inputs[1].default_value = (2.8,13.0,120.0)
    grain = n.new('ShaderNodeTexNoise')
    grain.inputs["Scale"].default_value = 3.0
    grain.inputs["Detail"].default_value = 2.0
    mix = n.new('ShaderNodeValToRGB')
    for k,f in enumerate((.86,1.095)):
        mix.color_ramp.elements[k].color = tuple(min(v*f,1) for v in m.diffuse_color[:3])+(1,)
    link.new(uv.outputs["Generated"],scale.inputs[0])
    link.new(scale.outputs[0],grain.inputs["Vector"])
    link.new(grain.outputs["Fac"],mix.inputs[0])
    link.new(mix.outputs[0],p.inputs["Base Color"])

for m in M:
    if m.name.startswith("Interior | wide-plank"):
        soften_wood(m)

base_mesh = upholstered("Upholstered platform profile",[
    (.166,1.88,2.11,.17),(.188,1.98,2.21,.18),(.231,2.035,2.256,.20),(.365,2.035,2.256,.20),
    (.409,1.987,2.216,.185),(.438,1.903,2.140,.16)])
board_mesh = upholstered("Arched headboard profile",[
    (-.106,1.945,1.178,.20),(-.091,2.030,1.243,.222),(-.055,2.085,1.282,.238),
    (.054,2.085,1.282,.238),(.087,2.029,1.244,.220),(.104,1.944,1.177,.194)])
duvet_mesh = upholstered("Padded quilt loft",[
    (.493,1.84,1.595,.170),(.525,1.964,1.708,.192),(.583,2.050,1.767,.210),
    (.636,2.050,1.766,.208),(.676,1.992,1.712,.190),(.700,1.866,1.612,.164),
    (.710,1.714,1.501,.142)])
pillow_mesh = upholstered("Linen pillow loft",[
    (-.080,.56,.335,.100),(-.064,.690,.415,.120),(-.030,.750,.462,.131),
    (.021,.750,.469,.133),(.068,.692,.432,.125),(.090,.558,.365,.112),(.097,.385,.260,.094)])
for i in range(2):
    o=O["HERO_linen pillow %d"%i]
    o.modifiers.clear()
    o.data=pillow_mesh
    if not pillow_mesh.materials:
        pillow_mesh.materials.append(warm)
    o.location = ((-.44,.44)[i],.728,.644)
    o.rotation_euler = (math.radians(11),0,math.radians((-7,6)[i]))
    loop_curve("HERO_linen piping %d"%i,[(x,y,.021) for x,y in rounded_points(.752,.471,.132)],.008,warm,BED,o)

state_info = [
    ("01 Cherry", "BB2C4B", "95263D", "D75769"),
    ("02 Apricot", "E97434", "BE5026", "F89A55"),
    ("03 Butter", "EFBC48", "C18C32", "F6D57B"),
    ("04 Meadow", "3B8D68", "2E6C55", "73AA81"),
]
cloth_roots = []
for i,(name,main,deep,piping) in enumerate(state_info):
    upholstery = mat("HERO | "+name+" upholstery",main,.77,sheen=.25)
    shadow = mat("HERO | "+name+" seams",deep,.88,sheen=.14)
    thread = mat("HERO | "+name+" piping",piping,.79,sheen=.12)
    root = empty("COLOR_"+name,BED,parent=bed)
    cloth_roots.append(root)
    object_from(base_mesh,"HERO_"+name+" upholstered platform",BED,parent=root,material=upholstery)
    o = object_from(board_mesh,"HERO_"+name+" arched headboard",BED,(0,1.123,.762),root,upholstery)
    o.rotation_euler.x = math.pi/2
    loop_curve("HERO_"+name+" headboard welt",[(x,y,.088) for x,y in rounded_points(2.035,1.250,.218)],.009,thread,BED,o)
    for j,x in enumerate((-.69,-.46,-.23,0,.23,.46,.69)):
        tube("HERO_"+name+" headboard seam %d"%j,[(x,1.016,z) for z in (.62,.82,1.06,1.30)],.0046,shadow,BED,root)
    duvet = object_from(duvet_mesh,"HERO_"+name+" cotton quilt",BED,(0,-.263,0),root,upholstery)
    loop_curve("HERO_"+name+" duvet welt",[(x,y,.589) for x,y in rounded_points(2.054,1.770,.207)],.009,thread,BED,duvet)
    for j,x in enumerate((-.755,-.50,-.25,0,.25,.50,.755)):
        tube("HERO_"+name+" stitched quilt channel %d"%j,[(x,-.722,.708),(x,-.55,.713),(x,-.15,.714),(x,.26,.714),(x,.645,.710)],.0047,shadow,BED,duvet,True)
    for j,y in enumerate((-.65,.61)):
        tube("HERO_"+name+" cross stitch %d"%j,[(-.85,y,.707),(-.42,y,.715),(0,y,.715),(.42,y,.715),(.85,y,.707)],.0055,thread,BED,duvet,True)
    tube("HERO_"+name+" base top welt",[(x,-1.13,.373) for x in (-.90,-.5,0,.5,.90)],.0068,thread,BED,root)

for i in range(13):
    for side in (-1,1):
        z=.223
        x=.17+side*1.585
        y=1.52+i*.267
        tube("SET_rug border %d %d"%(side,i),[(x-.018,y,z),(x+.017,y+.13,z)],.006,M["Interior | rug piping"],SET)
for i in range(29):
    x=-1.38+i*.111
    tube("SET_rug tassel %02d"%i,[(x,1.39,.217),(x+.009,1.285,.209)],.0051,M["Interior | rug piping"],SET)

for side in (-1,1):
    for ix in range(10):
        ax0,ax1=ix*.371+.018,(ix+1)*.371-.012
        ax0,ax1=(ax0,ax1) if side>0 else (-ax1,-ax0)
        start=-.485-(ix%2)*.43
        for iy in range(9):
            y0,y1=max(-.49,start+iy*.846),min(6.062,start+(iy+1)*.846-.017)
            if y1-y0<.023:
                continue
            if side>0 and ax0<2.86 and ax1>.61 and y0<3.12 and y1>.94:
                segments=[(ax0,min(.61,ax1),y0,y1),(max(2.86,ax0),ax1,y0,y1),
                          (max(.61,ax0),min(2.86,ax1),y0,min(.94,y1)),(max(.61,ax0),min(2.86,ax1),max(3.12,y0),y1)]
            else:
                segments=[(ax0,ax1,y0,y1)]
            for j,(a,b,c,d) in enumerate(segments):
                if b-a<.025 or d-c<.025:
                    continue
                x=(a+b)/2
                o=box("CAB_shingle %d.%d.%d.%d"%(side,ix,iy,j),(x,(c+d)/2,4.64-.433*abs(x)+.050),((b-a)*1.09,d-c,.048),rnd.choice(roof),CAB)
                o.rotation_euler.y = math.atan(.433)*side

for y in (.30,.87,3.25,4.10,5.12):
    for side in (-1,1):
        x=side*1.62
        a,b=(.2,3.32) if side>0 else (-3.32,-.2)
        o=box("CAB_visible rafter %.2f %d"%(y,side),(x,y,4.64-.433*abs(x)-.139),((b-a)*1.09,.13,.13),beam,CAB,.012)
        o.rotation_euler.y = math.atan(.433)*side

shade = glow("Interior | woven lamp shade","F4D8A2",.34)
lampwood = mat("Interior | dark walnut lamp","6F5544",.56)
pottery = mat("Interior | oyster ceramic","D9C3A4",.38)
pot_green = mat("Interior | sage ceramic","7A947F",.43)
blue = mat("Interior | dusk blue print","526C71",.78)
cream = M["Interior | rug piping"]
clay = mat("Interior | terra cotta planter","AF6954",.83)
def pottery_body(name,loc,profile,m,coll):
    return object_from(ring_mesh(name+" profile",[(z,r,r) for z,r in profile],32),name,coll,loc,material=m)

for x,y,w in ((-1.53,4.15,.53),(1.88,4.24,.57)):
    box("SET_drawer face %+.2f"%x,(x,y-.265,.572),(w*.91,.049,.237),trim,SET,.033)
    box("SET_drawer brass pull %+.2f"%x,(x,y-.297,.581),(.158,.040,.032),brass,SET,.016)
    for dx in (-.18,.18):
        box("SET_table foot %+.2f %.2f"%(x,dx),(x+dx,y,.232),(.083,.42,.071),beam,SET,.022)
pottery_body("SET_lamp base",(-1.53,4.15,.742),[(0,.159),(.031,.153),(.10,.083),(.217,.059),(.249,.067)],pot_green,SET)
pottery_body("SET_lamp shade",(-1.53,4.15,.961),[(0,.208),(.015,.208),(.255,.121),(.275,.121)],shade,SET)
light("LGT_lamp practical", 'POINT',(-1.52,4.12,1.20),21,(1,.69,.36),.23)
for i,(m,rx) in enumerate(((blue,-.04),(cream,.056))):
    o=box("SET_book %d"%i,(1.80,4.25,.762+i*.045),(.324,.236,.043),m,SET,.010)
    o.rotation_euler.z=rx
pottery_body("SET_bud vase",(2.02,4.23,.75),[(0,.09),(.042,.112),(.151,.093),(.209,.047),(.243,.045),(.252,.058)],pottery,SET)
plant = mat("Interior | olive stems","536C4A",.80)
petal = mat("Interior | dried stems","D5935D",.87)
for i in range(5):
    x=2.02+rnd.uniform(-.13,.12)
    y=4.23+rnd.uniform(-.07,.08)
    z=1.17+rnd.random()*.14
    tube("SET_vase stem %d"%i,[(2.02,4.23,.98),(x*.5+1.01,y,z-.10),(x,y,z)],.0045,plant,SET, smooth=True)
    oval("SET_dried bud %d"%i,(x,y,z),(.022,.018,.032),petal,SET)

box("SET_art walnut frame",(.26,5.503,2.046),(1.018,.052,.608),beam,SET,.023)
box("SET_art linen ground",(.26,5.471,2.046),(.931,.019,.525),warm,SET,.015)
oval("SET_art amber sun",(.476,5.451,2.130),(.095,.007,.095),petal,SET)
for j,points in enumerate((
    [(-.158,1.960),(.013,2.007),(.185,1.977),(.365,2.041),(.664,1.998)],
    [(-.158,1.909),(.011,1.946),(.268,1.910),(.480,1.973),(.664,1.934)])):
    tube("SET_art horizon %d"%j,[(x,5.448,z) for x,z in points],.014,blue,SET,smooth=True)

fern_data = mesh("Potted lanceolate leaf",[(0,0,0),(.10,-.054,.10),(.24,-.060,.165),(.39,0,.225),(.23,.062,.180),(.088,.055,.12),(.158,0,.151)],[(0,1,6),(1,2,6),(2,3,6),(3,4,6),(4,5,6),(5,0,6)],True)
for n,(x,y,ss) in enumerate(((2.69,4.62,1.0),(-2.61,2.84,.78),(2.83,-.52,.89),(-2.75,-.48,.63))):
    coll=SET if y>0 else GARDEN
    z=.2 if y>0 else -.03
    p=empty("SET_planter group %d"%n,coll,(x,y,z))
    p.scale=(ss,ss,ss)
    box("SET_planter soil %d"%n,(0,0,.271),(.302,.302,.034),beam,coll,.060,p)
    body=pottery_body("SET_planter pot %d"%n,(0,0,0),[(0,.129),(.020,.145),(.253,.187),(.273,.193),(.288,.183)],clay,coll)
    body.parent=p
    for j in range(9):
        o=object_from(fern_data,"SET_planter %d leaf %d"%(n,j),coll,(0,0,.267+(j%3)*.095),p,leaf[j%4])
        o.rotation_euler.z=j*2.40
        o.rotation_euler.y=rnd.uniform(-.83,-.17)
        o.scale=(1.2,1.25,1.55)

lantern_glass=glow("Porch | glowing honey glass","FFD69B",.8)
box("CAB_porch lantern back",(-.389,-.125,1.86),(.155,.052,.242),beam,CAB,.028)
box("CAB_porch lantern diffuser",(-.389,-.255,1.811),(.138,.134,.224),lantern_glass,CAB,.029)
for z in (1.685,1.943):
    box("CAB_porch lantern band %.2f"%z,(-.389,-.251,z),(.180,.171,.042),beam,CAB,.013)
for x in (-.453,-.325):
    box("CAB_porch lantern rail %.2f"%x,(x,-.327,1.811),(.016,.016,.242),beam,CAB,.004)

# Repeated grass and flower geometry is batched by material.
def meadow_patch(label, positions, material):
    verts,faces=[],[]
    for x,y,h,theta in positions:
        u,v=math.cos(theta),math.sin(theta)
        k=len(verts)
        verts.extend([(x-v*.025,y+u*.025,-.028),(x+v*.025,y-u*.025,-.028),
                      (x+u*h*.30+v*.018,y+v*h*.30-u*.018,h*.58),
                      (x+u*h*.65,y+v*h*.65,h), (x+u*h*.28-v*.014,y+v*h*.28+u*.014,h*.55)])
        faces.extend([(k,k+1,k+2,k+4),(k+4,k+2,k+3)])
    object_from(mesh(label+" mesh",verts,faces),label,GARDEN,material=material)

for j in range(3):
    positions=[]
    for i in range(250):
        x,y=rnd.uniform(-9.8,10.2),rnd.uniform(-7.5,9.6)
        if (-3.6<x<3.6 and -.58<y<5.99) or (-2.03<x<-.78 and y<-.57):
            continue
        for k in range(2):
            positions.append((x+rnd.uniform(-.12,.12),y+rnd.uniform(-.09,.09),rnd.uniform(.08,.28),rnd.uniform(0,math.tau)))
    meadow_patch("ENV_grass patch %d"%j,positions,grass[(j+2)%len(grass)])

flower_mat=mat("Woodland | pale yellow wildflowers","E9C76D",.80)
stem_mat=mat("Woodland | flowering stem","5D754B",.78)
flower_data=ring_mesh("Wildflower dot",[(-1,.36,.36),(-.48,.82,.82),(.20,1,1),(.90,.57,.57)],8,True)
for j,(cx,cy) in enumerate(((-.45,-2.8),(-2.27,-3.97),(-.45,-4.98),(-2.45,-1.79),(3.72,-2.39),(4.56,.34),(-3.30,-2.13))):
    for k in range(7):
        x,y,h=cx+rnd.uniform(-.31,.31),cy+rnd.uniform(-.31,.31),rnd.uniform(.12,.34)
        tube("ENV_flower stem %d.%d"%(j,k),[(x,y,-.026),(x-.008,y,h)],.008,stem_mat,GARDEN)
        for i in range(3):
            t=i*math.tau/3
            oval("ENV_flower %d.%d.%d"%(j,k,i),(x+.025*math.sin(t),y+.025*math.cos(t),h),(.032,.032,.022),flower_mat,GARDEN,data=flower_data)

cloud = glow("Sky | powder clouds","D9E6DE",.21)
for j,(x,y,z,s) in enumerate(((-7,16,9.0,1.85),(-13,12.7,8.2,1.62),(.2,20.5,9.9,1.92),(-4.5,23.0,7.4,1.50),(5.7,18.1,9.4,1.90))):
    for i,(dx,dy,dz,sx,sy,sz) in enumerate(((-.95,0,-.03,.88,.32,.30),(-.29,.06,.11,.91,.39,.42),(.45,0,-.09,.78,.36,.25),(1.0,.12,-.12,.42,.33,.19))):
        oval("ENV_soft cloud %d.%d"%(j,i),(x+dx*s,y+dy*s,z+dz*s),(sx*s,sy*s,sz*s),cloud,GARDEN)
root = empty("RIG_woman • world and flight",ACT,(-1.42,-5.34,.055))
torso = empty("RIG_woman • torso",ACT,(0,0,.817),root)
head = empty("RIG_woman • head",ACT,(0,.003,.551),torso)
skin_hi=mat("Actor | blush rose","D87A70",.74)
skin_deep=mat("Actor | contour warm","BF715E",.73)
hair_hi=mat("Actor | chestnut highlights","71483C",.59)
hair_mid=mat("Actor | chestnut ribbon","613D35",.59)
denim_deep=mat("Actor | blue tailoring","3B525E",.87)
denim_seam=mat("Actor | overalls stitching","799097",.77)
boot_mat=mat("Actor | cinnamon leather","875541",.58)
sole=mat("Actor | umber soles","523F3B",.75)
cuff=mat("Actor | vanilla cuffs","E5C29A",.83,sheen=.14)
eye_ivory=mat("Actor | eye whites","FAEEDF",.45)
eye_dark=mat("Actor | dark cocoa pupils","332A29",.39)
mouth_dark=mat("Actor | smile","7D4141",.58)
teeth=mat("Actor | smile highlight","F0D5BB",.65)

def tailored(name, profile, matl, parent):
    return object_from(ring_mesh(name+" profile",profile,26),name,ACT,parent=parent,material=matl)

tailored("ACT_overalls waist and hips",[(-.131,.129,.078),(-.103,.176,.109),(-.015,.193,.129),(.073,.175,.115),(.144,.147,.107)],denim,torso)
tailored("ACT_knit sweater",[(-.015,.157,.110),(.071,.156,.115),(.177,.155,.113),(.268,.178,.124),
                            (.338,.180,.116),(.382,.143,.099),(.411,.100,.085),(.417,.070,.067)],knit,torso)
tailored("ACT_knit collar",[(.399,.077,.075),(.419,.078,.077),(.438,.071,.069)],cuff,torso)
oval("ACT_neck",(0,.001,.460),(.057,.061,.088),skin,ACT,torso)
bib_data=upholstered("Overalls front bib profile",[(-.017,.195,.206,.037),(0,.230,.229,.047),(.021,.231,.229,.050),(.029,.197,.190,.042)])
bib=object_from(bib_data,"ACT_tailored front bib",ACT,(0,.101,.230),torso,denim)
bib.rotation_euler.x=-math.pi/2
for sign in (-1,1):
    x=sign*.103
    tag="L" if sign<0 else "R"
    tube("ACT_"+tag+" suspender",[(x,.129,.288),(x,.103,.359),(x,.036,.409),(x,-.049,.390),(x,-.100,.281),(x,-.106,.165)],.023,denim_deep,ACT,torso,True)
    oval("ACT_"+tag+" brass button",(x,.144,.285),(.016,.009,.016),brass,ACT,torso)
tube("ACT_bib patch seam",[(-.062,.135,.215),(-.053,.144,.179),(0,.148,.169),(.054,.143,.179),(.061,.135,.215)],.0036,denim_seam,ACT,torso,True)

face = oval("ACT_face",(0,.001,.024),(.131,.119,.165),skin,ACT,head)
oval("ACT_nose",(0,.121,.019),(.025,.022,.028),skin,ACT,head)
oval("ACT_nose tip",(0,.139,.010),(.018,.010,.014),skin,ACT,head)
hairverts, hairfaces = [], []
around, steps = 64, 19
for k in range(steps+1):
    t=k/steps
    for j in range(around):
        phi=j*math.tau/around
        front = (math.sin(phi)+1)/2
        theta_end = 2.33-1.29*front**3+.13*math.cos(phi+.36)*front**2
        theta=.012+(theta_end-.012)*t
        x=.145*math.sin(theta)*math.cos(phi)
        y=.139*math.sin(theta)*math.sin(phi)-.006
        z=.057+.174*math.cos(theta)
        hairverts.append((x,y,z))
hairfaces.append(tuple(range(around)))
for k in range(steps):
    for j in range(around):
        a,b=k*around+j,k*around+(j+1)%around
        hairfaces.append((a,a+around,b+around,b))
hairfaces.append(tuple(steps*around+j for j in range(around-1,-1,-1)))
object_from(mesh("Sculpted chestnut hair cap",hairverts,hairfaces,True),"ACT_sculpted bob",ACT,parent=head,material=hair)
for j,phi in enumerate((.18,.55,.82,1.12,1.43,1.73,2.06,2.41,2.80,3.27,3.70,4.14,4.66,5.17,5.60)):
    points=[]
    front=(math.sin(phi)+1)/2
    limit=2.32-1.29*front**3+.13*math.cos(phi+.36)*front**2
    for k in range(6):
        t=k/5
        theta=.34+t*(limit-.43)
        ang=phi+(.42-.42*t)*math.sin(phi-1.25)
        points.append((.146*math.sin(theta)*math.cos(ang),.140*math.sin(theta)*math.sin(ang)-.006,.057+.176*math.cos(theta)))
    tube("ACT_hair swept lock %02d"%j,points,.0055,hair_hi if j%4==1 else hair_mid,ACT,head,True,[.12,.60,.97,.83,.54,.08])
for side in (-1,1):
    tag="L" if side<0 else "R"
    x=.049*side
    oval("ACT_"+tag+" ear",(side*.123,.006,.006),(.025,.031,.042),skin,ACT,head)
    oval("ACT_"+tag+" warm cheek",(side*.072,.099,-.010),(.030,.010,.018),skin_hi,ACT,head)
    tube("ACT_"+tag+" eyebrow",[(x-.025,.098,.078),(x,.106,.088),(x+.025,.099,.081)],.0043,hair,ACT,head,True)
eyes = []
for side in (-1,1):
    tag="L" if side<0 else "R"
    x=.049*side
    e=empty("RIG_woman • "+tag+" eyelid",ACT,(x,.106,.055),head)
    eyes.append(e)
    oval("ACT_"+tag+" eye",(0,0,0),(.027,.015,.019),eye_ivory,ACT,e)
    oval("ACT_"+tag+" cocoa iris",(-.002,.013,.001),(.013,.006,.013),eye_dark,ACT,e)
    oval("ACT_"+tag+" eye glint",(-.006,.018,.006),(.004,.002,.004),eye_ivory,ACT,e)
    tube("ACT_"+tag+" upper lash",[(-.025,.004,.004),(-.014,.008,.016),(0,.011,.018),(.016,.007,.012),(.025,.004,.003)],.0032,hair,ACT,e,True)

smile = empty("RIG_woman • smile",ACT,(0,.115,-.032),head)
outline=[(-.039,.010),(-.027,.008),(-.012,.005),(.011,.005),(.027,.008),(.039,.011),(.030,-.005),(.018,-.014),(0,-.017),(-.019,-.013),(-.033,-.004)]
object_from(mesh("Happy smile silhouette",[(x,-.003*(abs(x)/.04)**2,z) for x,z in outline],[tuple(range(len(outline)))],True),
            "ACT_smile interior",ACT,parent=smile,material=mouth_dark)
tube("ACT_smile ivory highlight",[(-.021,.001,.004),(0,.002,.001),(.021,.001,.004)],.0028,teeth,ACT,smile,True)

def segment_data(name,length,radii):
    a,b,c = radii
    p = [(-.064,a*.60,a*.63),(-.034,a*.93,a*.96),(0,a,a),(.20*length,a*.98,a*.99),
        (.50*length,b,b),(.83*length,c*1.06,c*1.06),(length,c,c),(length+.021,c*.60,c*.60)]
    return ring_mesh(name,p,22)

segments = {
    "thigh": segment_data("Tailored tapered thigh",.398,(.092,.084,.068)),
    "shin": segment_data("Tailored tapered shin",.410,(.071,.064,.052)),
    "sleeve": segment_data("Knitted upper sleeve",.237,(.071,.066,.054)),
    "forearm": segment_data("Knitted lower sleeve",.219,(.055,.049,.040)),
}
limbs = {}
for side in (-1,1):
    tag="L" if side<0 else "R"
    leg=object_from(segments["thigh"],"ACT_"+tag+" thigh",ACT,parent=root,material=denim)
    shin=object_from(segments["shin"],"ACT_"+tag+" shin",ACT,parent=root,material=denim)
    arm=object_from(segments["sleeve"],"ACT_"+tag+" upper sleeve",ACT,parent=root,material=knit)
    fore=object_from(segments["forearm"],"ACT_"+tag+" lower sleeve",ACT,parent=root,material=knit)
    cuff_obj=oval("ACT_"+tag+" cuff",(0,0,.210),(.046,.047,.030),cuff,ACT,fore)
    hand=empty("RIG_woman • "+tag+" hand",ACT,parent=root)
    oval("ACT_"+tag+" mitten hand",(0,0,.006),(.038,.039,.052),skin,ACT,hand)
    oval("ACT_"+tag+" thumb",(-side*.029,.017,.015),(.021,.024,.027),skin,ACT,hand)
    foot=empty("RIG_woman • "+tag+" boot",ACT,parent=root)
    box("ACT_"+tag+" boot sole",(0,.042,-.068),(.138,.249,.034),sole,ACT,.015,foot)
    oval("ACT_"+tag+" boot vamp",(0,.049,-.022),(.067,.121,.047),boot_mat,ACT,foot)
    oval("ACT_"+tag+" boot ankle",(0,-.007,.025),(.061,.064,.086),boot_mat,ACT,foot)
    tube("ACT_"+tag+" boot seam",[(-.050,.066,.011),(0,.078,.024),(.050,.066,.011)],.0038,sole,ACT,foot,True)
    limbs[side]=(leg,shin,arm,fore,hand,foot)

def heart_xy(phi,width,height):
    x=math.sin(phi)**3
    z=(13*math.cos(phi)-5*math.cos(2*phi)-2*math.cos(3*phi)-math.cos(4*phi)+2.35)/16
    return (x*width*.5,z*height*.55)

def heart_mesh(name,w,h,depth):
    num=96
    profile=[(-depth,.27),(-depth*.93,.62),(-depth*.66,.87),(-depth*.32,.98),(0,1),
        (depth*.32,.98),(depth*.66,.87),(depth*.93,.62),(depth,.27)]
    verts = [(x*fac,y,z*fac) for y,fac in profile for x,z in [heart_xy(j*math.tau/num,w,h) for j in range(num)]]
    faces=[tuple(range(num-1,-1,-1))]
    for k in range(len(profile)-1):
        for j in range(num):
            a,b=k*num+j,k*num+(j+1)%num
            faces.append((a,b,b+num,a+num))
    faces.append(tuple((len(profile)-1)*num+j for j in range(num)))
    d=mesh(name,verts,faces,True)
    d.polygons[0].use_smooth=d.polygons[-1].use_smooth=False
    return d

heart = empty("RIG_heart cushion • floor to embrace",ACT,(1.694,1.622,.297))
heart_width, heart_height = .455,.421
object_from(heart_mesh("Velvet heart cushion profile",heart_width,heart_height,.073),"HERO_heart cushion velvet",ACT,parent=heart,material=blush)
heartthread=mat("Heart | pink cord piping","E9879E",.84,sheen=.12)
loop_curve("HERO_heart cushion piping",[(x,0,z) for x,z in [heart_xy(j*math.tau/96,heart_width,heart_height) for j in range(96)]],.0062,heartthread,ACT,heart)
label=mat("Heart | cotton seam label","EACBB4",.79)
o=box("HERO_heart cotton tag",(.122,.004,-.145),(.047,.018,.055),label,ACT,.006,heart)
o.rotation_euler.y=-.59
CAM_A, CAM_B, CAM_C, CAM_D, CAM_E = [next(o for o in SHOT.objects if o.name.startswith("CAM_%02d" % i)) for i in range(1,6)]
cam_end = camera("CAM_06 • White end card",(0,2.12,-1.03),(0,2.12,-2.2),50)
cam_end.data.type='ORTHO'
cam_end.data.ortho_scale=5.30
cam_end.data.clip_end=3

def flat(name, hexcode, strength=1, animated_alpha=False):
    m=mat(name,hexcode)
    nodes=m.node_tree.nodes
    links=m.node_tree.links
    nodes.clear()
    out=nodes.new('ShaderNodeOutputMaterial')
    emission=nodes.new('ShaderNodeEmission')
    emission.inputs["Color"].default_value=rgba(hexcode)
    emission.inputs["Strength"].default_value=strength
    if animated_alpha:
        trans=nodes.new('ShaderNodeBsdfTransparent')
        mix=nodes.new('ShaderNodeMixShader')
        links.new(trans.outputs[0],mix.inputs[1])
        links.new(emission.outputs[0],mix.inputs[2])
        links.new(mix.outputs[0],out.inputs[0])
        m.surface_render_method = 'BLENDED'
        return m,mix.inputs[0]
    links.new(emission.outputs[0],out.inputs[0])
    return m

white = flat("End card | white","FFFFFF",24)
wipe_mat,wipe_alpha = flat("Transition | soft white fade","FFFFFF",24,True)
wipe = box("FX_white fade plate",(0,0,-.51),(1.70,1.14,.003),wipe_mat,END,parent=CAM_E)
endcard = empty("END_white card / 키르시홈",END,(0,2.12,-2.03))
box("END_white background",(0,0,0),(6.0,3.50,.019),white,END,parent=endcard)
wordmark = empty("END_키르시홈 | temporary wordmark",END,(0,0,.035),endcard)
wordmark["status"] = "임시 워드마크. 공식 로고 파일 제공 시 교체."
brand, brand_alpha = flat("End card | cherry ink","961D41",.82,True)
lettering = [
    [[(.06,.53),(.38,.53),(.37,.33),(.33,.16)],[(.067,.348),(.367,.348)],[(.556,.55),(.556,.039)]],
    [[(.108,.54),(.503,.54),(.503,.414),(.134,.414),(.134,.285),(.533,.285)],[(.063,.099),(.571,.099)]],
    [[(.063,.175),(.189,.267),(.274,.427),(.279,.527)],[(.273,.423),(.325,.296),(.433,.192)],[(.560,.55),(.560,.039)]],
    [[(.224,.570),(.418,.570)],[(.114,.493),(.516,.493)],[(.325,.260),(.325,.206)],[(.058,.203),(.580,.203)],
     [(.135,.128),(.506,.128),(.506,.018),(.135,.018),(.135,.128)]],
]
for i,strokes in enumerate(lettering):
    origin=-1.421+i*.741
    for j,st in enumerate(strokes):
        points=[(origin+x,y-.449,0) for x,y in st]
        tube("END_hangul stroke %d.%d"%(i,j),points,.027,brand,END,wordmark)
        for k,(x,y,z) in enumerate(points):
            oval("END_hangul join %d.%d.%d"%(i,j,k),(x,y,z),(.027,.027,.027),brand,END,wordmark)
for j in range(32):
    t=j*math.tau/32
    if j==0: points=[]
    points.append((.139*math.cos(t),.359+.053*math.sin(t),0))
loop_curve("END_hangul hom circle",[(x+.985,y-.449,z) for x,y,z in points],.025,brand,END,wordmark)
emblem_points=[heart_xy(j*math.tau/100,.317,.288) for j in range(100)]
symbol=mesh("Cherry heart glyph",[(x,z+.504,.004) for x,z in emblem_points],[tuple(range(len(emblem_points)))])
object_from(symbol,"END_cherry heart emblem",END,parent=wordmark,material=brand)

def blend(a,b,u):
    if isinstance(a,(tuple,list)):
        return tuple(aa+(bb-aa)*u for aa,bb in zip(a,b))
    return a+(b-a)*u

def smooth(u):
    u=min(1,max(0,u))
    return u*u*(3-2*u)

def track(f,keys,ease=0):
    if f<=keys[0][0]:
        return keys[0][1]
    for (t0,a),(t1,b) in zip(keys,keys[1:]):
        if f<=t1:
            u=(f-t0)/(t1-t0)
            return blend(a,b,blend(u,smooth(u),ease))
    return keys[-1][1]

def ramp(f,a,b):
    return smooth((f-a)/(b-a))

main_action=bpy.data.actions.new("Kirsch Home | 24-second 3D spot") if hasattr(bpy.types,'ActionSlot') else None

def insert(o, path, f):
    if main_action is not None and isinstance(o,bpy.types.Object):
        ad=o.animation_data_create()
        if ad.action is None:
            ad.action=main_action
            ad.action_slot=main_action.slots.new('OBJECT',o.name)
    o.keyframe_insert(data_path=path,frame=f,group=o.name if isinstance(o,bpy.types.Object) else "Shot")

def interp(o, style, prop=None):
    ad=o.animation_data
    if ad is None or ad.action is None:
        return
    act=ad.action
    if hasattr(act,'slots') and ad.action_slot is not None:
        curves=[curve for layer in act.layers for strip in layer.strips for bag in [strip.channelbag(ad.action_slot)] if bag is not None for curve in bag.fcurves]
    else:
        curves=act.fcurves
    for curve in curves:
        if prop is None or curve.data_path==prop:
            for key in curve.keyframe_points:
                key.interpolation=style

for k, o in enumerate(cloth_roots):
    for f,state in ((1,0),(216,0),(217,1),(288,1),(289,2),(360,2),(361,3),(576,3)):
        v=1.0 if k==state else .0001
        o.scale=(v,v,v)
        insert(o,"scale",f)
    interp(o,'CONSTANT')

def hinge_angle(f):
    return math.radians(track(f,[(1,0),(85,0),(90,13),(96,51),(103,79),(110,77),(576,77)],.77))

for f in (1,85,87,90,92,96,100,103,107,110,576):
    hinge.rotation_euler.z=hinge_angle(f)
    insert(hinge,"rotation_euler",f)
interp(hinge,'BEZIER')

def shot_keys(cam, positions, targets, lens, step=3, ease=.40):
    start,end=positions[0][0],positions[-1][0]
    fs=sorted(set(range(start,end+1,step))|{end}|{f for f,p in positions}|{f for f,p in targets})
    cam.rotation_mode='QUATERNION'
    last=None
    for f in fs:
        cam.location=track(f,positions,ease)
        at=Vector(track(f,targets,ease))
        q=(at-cam.location).to_track_quat('-Z','Y')
        if last is not None and last.dot(q)<0:
            q.negate()
        cam.rotation_quaternion=q
        last=q.copy()
        insert(cam,"location",f)
        insert(cam,"rotation_quaternion",f)
    cam.data.lens=lens
    interp(cam,'LINEAR')

shot_keys(CAM_A,[(1,(5.53,-10.94,3.55)),(70,(5.30,-9.86,3.37))],
          [(1,(-.78,-.54,1.77)),(70,(-.55,-.24,1.81))],32)
shot_keys(CAM_B,[(71,(-2.49,-3.08,1.52)),(86,(-2.01,-2.32,1.53)),(100,(-1.48,-1.74,1.55)),
                 (113,(-1.38,-.53,1.59)),(125,(-1.40,.48,1.62)),(144,(-2.49,1.02,1.63))],
          [(71,(-1.29,.32,1.32)),(89,(-1.08,.52,1.32)),(107,(-.83,1.82,1.28)),
           (125,(-.45,2.93,1.24)),(144,(-.34,3.27,1.15))],28)
shot_keys(CAM_C,[(145,(2.96,.50,2.14)),(389,(2.79,.63,2.08))],
          [(145,(.19,3.40,.98)),(389,(.17,3.43,.96))],31.5,step=8,ease=.72)
shot_keys(CAM_D,[(390,(2.92,.40,1.67)),(415,(2.96,.38,1.57)),(430,(2.97,.46,1.49)),
                 (450,(2.91,.39,1.61)),(461,(2.75,.55,1.76)),(476,(2.40,.97,2.70))],
          [(390,(.47,1.71,1.02)),(415,(1.22,1.83,1.04)),(430,(1.43,1.83,.70)),
           (450,(1.46,1.89,1.18)),(461,(1.43,1.92,1.45)),(476,(1.43,1.92,3.59))],30.0)
shot_keys(CAM_E,[(477,(6.38,-2.13,5.74)),(490,(5.83,-1.85,6.20)),(508,(5.15,-1.52,7.07)),(526,(4.98,-1.49,7.37))],
          [(477,(1.41,1.95,4.14)),(490,(1.41,2.00,5.29)),(508,(1.38,2.13,6.45)),(526,(1.38,2.18,6.75))],41)
for marker in list(S.timeline_markers):
    S.timeline_markers.remove(marker)
for f,name,cam in (
    (1,"01 / 숲길 · 나무집으로",CAM_A),
    (71,"02 / 문을 열고 들어가는 순간",CAM_B),
    (145,"03 / 빨강",CAM_C),
    (217,"04 / 주황",CAM_C),
    (289,"05 / 노랑",CAM_C),
    (361,"06 / 초록",CAM_C),
    (390,"07 / 하트 쿠션",CAM_D),
    (451,"08 / 공중으로",CAM_D),
    (477,"09 / 하늘로",CAM_E),
    (510,"10 / 페이드 투 화이트",CAM_E),
    (527,"11 / 키르시홈",cam_end)):
    m=S.timeline_markers.new(name,frame=f)
    m.camera=cam

def front_floor(y):
    return track(y,[(-8,.057),(-1.39,.057),(-1.10,.144),(-.83,.193),(-.13,.193),(.17,.199)],.84)

def body_path(f):
    x,y=track(f,[(1,(-1.43,-5.34)),(23,(-1.41,-3.93)),(45,(-1.44,-2.49)),
                    (66,(-1.41,-1.08)),(77,(-1.37,-.55)),(83,(-1.34,-.455)),(94,(-1.33,-.42)),
                    (101,(-1.32,-.31)),(111,(-1.36,.30)),(124,(-1.45,.98)),(138,(-1.44,1.54)),
                    (151,(-1.42,1.58)),(363,(-1.42,1.58)),(389,(-.91,1.65)),(402,(.28,1.75)),
                    (417,(1.425,1.910)),(451,(1.425,1.910)),(477,(1.435,1.95)),(506,(1.385,2.12)),
                    (526,(1.38,2.20))],.29)
    fly=track(f,[(451,0),(456,.065),(463,.44),(470,1.32),(477,2.48),(486,3.54),(496,4.53),(508,5.38),(526,5.72)],.54)
    return Vector((x,y,front_floor(y)+fly))

def yaw_at(f):
    return math.radians(track(f,[(1,-1),(58,1),(83,-12),(94,-12),(111,4),(128,1),(145,-36),
         (354,-36),(371,-83),(388,-96),(409,-101),(417,-136),(435,-136),(457,-134),(477,-128),(505,-139),(526,-145)],.68))

floor_heart=Vector((1.694,1.622,.297))
floor_rot = Quaternion((0,0,1),-.42) @ Quaternion((1,0,0),math.pi/2)
known_local = Quaternion((0,0,1),-yaw_at(430)) @ (floor_heart-body_path(430))
heart_hug=Vector((.010,.257,1.066))
prev_quats={}

def set_q(o,q):
    o.rotation_mode='QUATERNION'
    if o.name in prev_quats and q.dot(prev_quats[o.name])<0:
        q.negate()
    prev_quats[o.name]=q.copy()
    o.rotation_quaternion=q

def segment(o,a,b,length):
    d=b-a
    o.location=a
    set_q(o,d.to_track_quat('Z','Y'))
    o.scale=(1,1,d.length/length)

def joint(a,b,A,B,pole):
    direction=b-a
    actual=max(.0001,direction.length)
    u=direction/actual
    length=max(abs(A-B)+.001,min(actual,A+B-.001))
    straight=(A*A-B*B+length*length)/(2*length)
    height=math.sqrt(max(0,A*A-straight*straight))
    n=(pole-u*pole.dot(u)).normalized()
    return a+u*straight+n*height

def gait(f,side,pos,yaw):
    walk_y=0
    dist=0
    amp=0
    if f<=85:
        dist=pos.y+5.34
        amp=1-ramp(f,71,83)
    elif 97<=f<=150:
        dist=pos.y+.42
        amp=ramp(f,97,105)*(1-ramp(f,132,146))
    elif 365<=f<=417:
        dist=pos.x+1.42
        amp=ramp(f,365,389)*(1-ramp(f,407,418))
    phase=(dist/1.04+(.0 if side<0 else .5)+.20)%1
    if phase<=.57:
        walk_y=.296-1.04*phase
        lift=0
    else:
        swing=(phase-.57)/.43
        walk_y=blend(-.296,.296,smooth(swing))
        lift=.146*math.sin(swing*math.pi)**1.2
    lean=amp*(1-abs(phase-.5)*4)*.04
    return amp*walk_y,amp*lift,amp,lean

actor_frames=sorted(set(range(1,531,3))|{70,71,83,85,90,94,97,102,115,130,145,217,289,361,389,390,416,417,424,430,431,442,450,451,457,473,476,477,485,508,510,526,576})
for f in actor_frames:
    pos=body_path(f)
    yaw=yaw_at(f)
    body_q=Quaternion((0,0,1),yaw)
    root.location=pos
    set_q(root,body_q)
    crouch=track(f,[(1,0),(417,0),(423,.47),(430,1),(432,.98),(440,.51),(450,0),(576,0)],.56)
    grip=ramp(f,426,434)
    float_on=ramp(f,451,470)
    lift_phase=math.sin((f-454)*.17)
    lean_door=ramp(f,76,85)*(1-ramp(f,90,101))
    walk_amplitude=gait(f,1,pos,yaw)[2]
    gait_bob=(.014*math.cos((pos.y+5.34 if f<365 else pos.x+1.42)*math.tau*2/1.04)) * walk_amplitude
    hip=.818-.472*crouch+gait_bob+.006*math.sin(f*.10)*(1-crouch)
    torso.location=(0,.052*crouch+.028*lean_door,hip)
    tilt=-1.005*crouch-.155*lean_door+.06*float_on
    torso.rotation_euler=(tilt,.026*math.sin(f*.13)*(walk_amplitude+.35*float_on),.019*math.sin(f*.13)*walk_amplitude)
    tr=torso.rotation_euler.to_quaternion()
    head.rotation_euler.x=track(f,[(1,.02),(83,-.10),(101,.03),(131,-.05),(365,-.08),
                                        (407,-.22),(429,.15),(447,-.12),(457,.05),(477,.17),(526,.15)],.73)
    head.rotation_euler.y=track(f,[(1,0),(145,-.057),(355,-.057),(418,.055),(447,.14),(462,.107),(493,-.065),(526,-.12)],.80)
    head.rotation_euler.z=track(f,[(1,-.04),(75,-.13),(97,.085),(138,-.19),(364,-.15),(397,.07),
                                        (430,.05),(446,-.055),(457,-.03),(480,-.12),(526,-.16)],.67)
    opening=.66+.60*ramp(f,438,454)
    smile.scale=(1+.10*ramp(f,438,454),1,opening)
    for e in eyes:
        blink=max(0,max((1-abs(f-center)/3 for center in (57,132,228,328,407,452,486)),default=0))
        e.scale=(1,1,max(.15,1-.91*blink))

    if f<=430:
        pillow_local=body_q.inverted() @ (floor_heart-pos)
        heart.location=floor_heart
        q=floor_rot.copy()
    else:
        f_hold=ramp(f,430,450)
        pillow_local=known_local.lerp(heart_hug,f_hold)
        pillow_local.z+=.018*math.sin((f-430)*math.pi/20)*max(0,1-f_hold) + .007*float_on*lift_phase
        heart.location=pos+body_q @ pillow_local
        q=floor_rot.slerp(body_q @ Quaternion((1,0,0),-.08+.09*float_on*lift_phase),f_hold)
    set_q(heart,q)

    for side,(thigh,shin,sleeve,fore,hand,foot) in limbs.items():
        gy,lift,activity,_=gait(f,side,pos,yaw)
        planar_y=pos.y+math.cos(yaw)*gy+math.sin(yaw)*side*.104
        floor_delta=0 if f>=451 else front_floor(planar_y)-pos.z
        foot_loc=Vector((side*(.111+.014*crouch), gy+.09*crouch+float_on*(-.064+side*.086*math.sin((f-451)*.114)),.087+lift+floor_delta+float_on*(.087+side*.038*lift_phase)))
        thigh_top=Vector((side*.106,.040*crouch,hip-.026))
        knee=joint(thigh_top,foot_loc,.398,.410,Vector((.09*side,1,.03)))
        segment(thigh,thigh_top,knee,.398)
        segment(shin,knee,foot_loc,.410)
        foot.location=foot_loc
        foot.rotation_euler=(.55*lift-.40*float_on+.19*float_on*side*lift_phase,0,-side*.08)
        upper=Vector(torso.location)+tr @ Vector((side*.166,.005,.332))
        wrist=Vector((side*.234,-.63*gy,.746+.05*activity))
        if side==1:
            knob=Vector(hinge.location)+Quaternion((0,0,1),hinge_angle(f)) @ Vector((1.226,-.151,.967))
            knob_rel=body_q.inverted() @ (knob-pos)
            touch=ramp(f,76,84)*(1-ramp(f,89,96))
            wrist=wrist.lerp(knob_rel,touch)
        anticipation=ramp(f,416,429)*(1-ramp(f,430,438))
        target=pillow_local+Vector((side*(.146-.008*grip),-.031+.085*grip,-.012-.029*grip))
        wrist=wrist.lerp(target,max(anticipation,grip))
        elbow=joint(upper,wrist,.237,.219,Vector((side*.72,-.18,-.71)))
        segment(sleeve,upper,elbow,.237)
        segment(fore,elbow,wrist,.219)
        hand.location=wrist
        set_q(hand,(wrist-elbow).to_track_quat('Z','Y'))
        for o in (thigh,shin,sleeve,fore):
            for prop in ("location","rotation_quaternion","scale"):
                insert(o,prop,f)
        for prop in ("location","rotation_euler"):
            insert(foot,prop,f)
        for prop in ("location","rotation_quaternion"):
            insert(hand,prop,f)

    for o, props in ((root,("location","rotation_quaternion")),(torso,("location","rotation_euler")),
                     (head,("rotation_euler",)),(smile,("scale",)),(eyes[0],("scale",)),(eyes[1],("scale",)),
                     (heart,("location","rotation_quaternion"))):
        for prop in props:
            insert(o,prop,f)

for o in [root,torso,head,smile,heart,*eyes,*[o for L in limbs.values() for o in L]]:
    interp(o,'LINEAR')

spark=glow("Flight | soft amber motes","F8D896",1.03)
for i in range(14):
    theta=i*2.39996
    radius=.49+(i%4)*.13
    dot=oval("FX_levitation mote %02d"%i,(0,0,-.1),(.016,.016,.020),spark,ACT)
    start=448+(i*7)%31
    finish=min(514,start+27+i%12)
    for f in sorted({1,start,start+6,(start+finish)//2,finish,576}):
        base=body_path(f)
        t=theta+(f-start)*.033
        dot.location=(base.x+radius*math.cos(t),base.y+radius*math.sin(t),base.z+.28+(i%5)*.23)
        alpha=ramp(f,start,start+5)*(1-ramp(f,finish-8,finish))
        dot.scale=tuple(v*max(.0001,alpha)*(1+(i%3)*.27) for v in (.013,.013,.018))
        insert(dot,"location",f)
        insert(dot,"scale",f)
    interp(dot,'LINEAR')

for f,val in ((1,0),(510,0),(518,.43),(526,1),(576,1)):
    wipe_alpha.default_value=val
    wipe_alpha.keyframe_insert(data_path="default_value",frame=f)
for f,val in ((1,.0001),(509,.0001),(510,1),(526,1),(527,.0001),(576,.0001)):
    wipe.scale=(val,val,val)
    insert(wipe,"scale",f)
interp(wipe,'CONSTANT')
for f,val in ((1,0),(527,0),(530,.07),(540,1),(576,1)):
    brand_alpha.default_value=val
    brand_alpha.keyframe_insert(data_path="default_value",frame=f)

O["ENV_fir 02"].location.x=-4.97
O["ENV_fir 09"].location.y+=.58
S.world.color=(.36,.54,.61)
S.world.node_tree.nodes["Background"].inputs["Strength"].default_value=.98
S.render.resolution_x, S.render.resolution_y = 1280,720
S.render.resolution_percentage=100
S.eevee.taa_render_samples=16
S.frame_set(1)
S.camera=CAM_A
for o in bpy.context.selected_objects:
    o.select_set(False)
S["brief"]="키르시홈 침대 광고 샘플 | 숲속 나무집 · 하트 쿠션 · 하늘"
S["color_change_seconds"]="06.0 red / 09.0 orange / 12.0 yellow / 15.0 green"
S["logo_note"]="임시 키르시홈 워드마크"
result={"objects":len(S.objects),"fps":S.render.fps,"frame_range":[S.frame_start,S.frame_end],
        "camera":S.camera.name,"color_frames":[145,217,289,361],"door_open_frame":103,
        "cushion_pickup":430,"sky_shot":477,"end_card":527,
        "cameras":[m.camera.name for m in S.timeline_markers if m.camera]}
