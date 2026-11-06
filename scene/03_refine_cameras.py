import bpy, math
from mathutils import Vector
S=bpy.context.scene
O=bpy.data.objects
SHOT=next(c for c in S.collection.children if c.name.startswith("06 "))
CAM_A, CAM_B, CAM_C, CAM_D, CAM_E = [next(o for o in SHOT.objects if o.name.startswith("CAM_%02d" % i)) for i in range(1,6)]
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

main_action=None

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

shot_keys(CAM_B,[(71,(-2.49,-3.08,1.52)),(86,(-2.01,-2.32,1.53)),(100,(-1.51,-1.82,1.57)),
                 (113,(-1.39,-.73,1.62)),(125,(-1.24,-.04,1.68)),(144,(-.98,.46,1.71))],
          [(71,(-1.29,.32,1.32)),(89,(-1.08,.52,1.32)),(107,(-.83,1.82,1.28)),
           (125,(-.64,2.95,1.29)),(144,(-.51,3.31,1.21))],26)
shot_keys(CAM_C,[(145,(3.065,.38,2.17)),(389,(2.982,.56,2.12))],
          [(145,(.39,3.44,1.01)),(389,(.44,3.45,.99))],31.8,step=8,ease=.72)
shot_keys(CAM_D,[(390,(3.08,.30,1.73)),(415,(3.10,.27,1.59)),(430,(3.10,.34,1.54)),
                 (450,(3.05,.32,1.65)),(461,(2.99,.44,1.93)),(476,(2.58,1.10,3.53))],
          [(390,(.57,1.75,1.04)),(415,(1.39,1.83,1.015)),(430,(1.48,1.79,.61)),
           (450,(1.46,1.89,1.12)),(461,(1.43,1.92,1.59)),(476,(1.44,1.95,3.77))],26.0)
shot_keys(CAM_E,[(477,(6.37,-2.13,5.54)),(490,(5.83,-1.85,5.94)),(508,(5.36,-1.54,6.16)),(526,(5.05,-1.58,6.55))],
          [(477,(1.41,1.95,4.09)),(490,(1.41,2.00,5.32)),(508,(1.38,2.13,6.52)),(526,(1.38,2.18,6.82))],44)
for o in S.objects:
    if o.name.startswith("ENV_granite") and -.65<o.location.y<6.20 and abs(o.location.x)-o.scale.x<3.48:
        o.location.x=math.copysign(3.71+o.scale.x, o.location.x)
S.frame_set(1)
S.camera=CAM_A
result={"adjusted_cameras":[o.name for o in (CAM_B,CAM_C,CAM_D,CAM_E)],"frame_range":[S.frame_start,S.frame_end],
        "fps":S.render.fps,"name":S.name}
