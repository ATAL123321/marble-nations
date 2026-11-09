"""Blender (Cycles) quality test: instrument wall like the reference channel, one still frame.
Run: blender -b -P blender/still.py -- out.png
"""
import bpy, math, sys, random
from mathutils import Vector

out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp/still.png"
random.seed(4)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 96
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 720, 1280
sc.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in bpy.types.ColorManagedViewSettings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
sc.view_settings.look = "None"

def mat(name, color, metal=0.0, rough=0.4, coat=0.0, trans=0.0, ior=1.45):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Metallic"].default_value = metal
    p.inputs["Roughness"].default_value = rough
    for k in ("Coat Weight", "Clearcoat"):
        if k in p.inputs: p.inputs[k].default_value = coat
    for k in ("Transmission Weight", "Transmission"):
        if k in p.inputs: p.inputs[k].default_value = trans
    p.inputs["IOR"].default_value = ior
    return m

def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)

def bevel(o, w=2, seg=4):
    b = o.modifiers.new("bev", "BEVEL"); b.width = w; b.segments = seg
    bpy.context.view_layer.objects.active = o; bpy.ops.object.shade_smooth()

def link(o, m): o.data.materials.append(m); return o

SC = 0.01   # 1 unit = 100 "pixels" of the 2D layout
WALL = mat("wall", srgb("#9a8dcf"), rough=0.92)
GOLD = mat("gold", srgb("#e3b04b"), metal=1, rough=0.22)
SILVER = mat("silver", srgb("#d9dbe0"), metal=1, rough=0.25)
WOOD = mat("wood", srgb("#8b4a2b"), rough=0.5, coat=0.4)
BLACK = mat("black", srgb("#141416"), rough=0.5)
BLUE = mat("blue", srgb("#2546d6"), rough=0.32, coat=0.6)

bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0)); link(bpy.context.object, WALL)

def pin(x, y, z):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=z, location=(x, y, z / 2)); link(bpy.context.object, SILVER)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.06, location=(x, y, 0.02)); link(bpy.context.object, SILVER)

def trumpet(x, y, ang):
    z = 0.8
    prof = [(0.09 + 0.34 * (u / 20) ** 3.2, -0.7 + 0.7 * u / 20) for u in range(21)]
    verts = []; faces = []; N = 48
    for i, (r, h) in enumerate(prof):
        for k in range(N):
            a = 2 * math.pi * k / N; verts.append((r * math.cos(a), h, r * math.sin(a)))
    for i in range(len(prof) - 1):
        for k in range(N):
            a, b = i * N + k, i * N + (k + 1) % N; faces.append((a, b, b + N, a + N))
    me = bpy.data.meshes.new("bell"); me.from_pydata(verts, [], faces); me.update()
    ob = bpy.data.objects.new("bell", me); bpy.context.collection.objects.link(ob)
    s = ob.modifiers.new("sol", "SOLIDIFY"); s.thickness = 0.015
    link(ob, GOLD); bpy.context.view_layer.objects.active = ob; ob.select_set(True); bpy.ops.object.shade_smooth()
    parts = [ob]
    bpy.ops.mesh.primitive_cylinder_add(radius=0.06, depth=1.2, location=(0, -1.25, 0)); parts.append(link(bpy.context.object, GOLD))
    bpy.ops.mesh.primitive_torus_add(major_radius=0.26, minor_radius=0.05, location=(0.26, -1.85, 0), rotation=(math.pi / 2, 0, 0)); parts.append(link(bpy.context.object, GOLD))
    for k in range(3):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.07, depth=0.34, location=(0.26, -1.05 - k * 0.18, 0), rotation=(0, math.pi / 2, 0)); parts.append(link(bpy.context.object, GOLD))
        bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=0.08, location=(0.48, -1.05 - k * 0.18, 0), rotation=(0, math.pi / 2, 0)); parts.append(link(bpy.context.object, SILVER))
    for p in parts: bpy.context.view_layer.objects.active = p; p.select_set(True)
    bpy.ops.object.shade_smooth()
    empty = bpy.data.objects.new("tr", None); bpy.context.collection.objects.link(empty)
    for p in parts: p.parent = empty
    empty.location = (x, y, z); empty.rotation_euler = (0.3, 0, ang); empty.scale = (0.8, 0.8, 0.8)
    pin(x, y - 0.4, z)

def tube(x, y, ang, hexcol):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.2, depth=1.9, location=(x, y, 0.8), rotation=(0, math.pi / 2, ang))
    o = bpy.context.object; s = o.modifiers.new("sol", "SOLIDIFY"); s.thickness = 0.02
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="DESELECT"); bpy.ops.object.mode_set(mode="OBJECT")
    link(o, mat("tube" + hexcol, srgb(hexcol), rough=0.35, coat=0.5)); bevel(o, 0.02, 3); pin(x, y, 0.8)

def recorder(x, y, ang):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.14, depth=2.1, location=(x, y, 0.8), rotation=(0, math.pi / 2, ang)); o = bpy.context.object
    link(o, WOOD); bevel(o, 0.02, 3)
    d = Vector((math.cos(ang), math.sin(ang), 0))
    bpy.ops.mesh.primitive_cylinder_add(radius=0.16, depth=0.14, location=Vector((x, y, 0.8)) - d * 1.0, rotation=(0, math.pi / 2, ang)); link(bpy.context.object, SILVER)
    for k in range(6):
        p = Vector((x, y, 0.94)) + d * (-0.5 + k * 0.22)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.035, depth=0.05, location=p); link(bpy.context.object, BLACK)
    pin(x, y, 0.8)

def speaker(x, y, ang):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, 0.75), rotation=(0.15, 0, ang)); o = bpy.context.object
    o.scale = (0.96, 0.96, 0.8); link(o, BLUE); bevel(o, 0.08, 6)
    bpy.ops.mesh.primitive_cone_add(radius1=0.36, radius2=0.08, depth=0.16, location=(x, y + 0.05, 1.12), rotation=(math.pi, 0, 0)); link(bpy.context.object, BLACK)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.37, minor_radius=0.04, location=(x, y + 0.05, 1.18)); link(bpy.context.object, SILVER)
    pin(x, y, 0.4)

def marble(x, y):
    g = mat("glass", srgb("#1aa39b"), rough=0.02, trans=1.0, ior=1.5)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3, location=(x, y, 0.85), segments=64, ring_count=32); o = bpy.context.object; link(o, g)
    bpy.ops.object.shade_smooth()
    bpy.ops.mesh.primitive_torus_add(major_radius=0.25, minor_radius=0.05, location=(x, y, 0.85), rotation=(1.2, 0.3, 0)); link(bpy.context.object, mat("band", srgb("#ffd23a"), rough=0.3))
    bpy.ops.object.shade_smooth()

# layout (2D: y down -> blender y up)
for k in range(4): trumpet(-1.6, 3.2 - k * 1.25, -0.25)
for k in range(4): trumpet(1.6, 2.6 - k * 1.25, math.pi + 0.25)
cols = ["#ff4d6d", "#ffb020", "#ffe34d", "#3ddc84", "#3fa9ff", "#9b5cff", "#ff6fd0"]
for k in range(4): tube(-1.3, -2.6 - k * 0.9, 0.9, cols[k])
for k in range(4): tube(1.3, -3.0 - k * 0.9, -0.9, cols[k + 3])
marble(0.15, 0.1)

# lights: warm sun from the upper right + soft sky
bpy.ops.object.light_add(type="SUN", location=(5, 8, 10)); sun = bpy.context.object
sun.data.energy = 4.5; sun.data.angle = math.radians(9); sun.data.color = (1.0, 0.9, 0.78)
sun.rotation_euler = (math.radians(35), math.radians(28), math.radians(150))
world = bpy.data.worlds.new("w"); sc.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.78, 0.75, 0.95, 1); world.node_tree.nodes["Background"].inputs[1].default_value = 0.9

bpy.ops.object.camera_add(location=(0.1, -0.4, 21), rotation=(0, 0, 0)); cam = bpy.context.object
cam.data.lens = 80; sc.camera = cam
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print("WROTE", out)
