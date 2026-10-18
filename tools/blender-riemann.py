"""Blender: 生成黎曼面（√z 的双层螺旋）+ 渲染转台动画帧。

用法（命令行）：
  blender -b -P tools/blender-riemann.py -- --frames 96 --out C:\tmp\riemann\f_

生成的每一帧是 PNG（1920x1080），后面用 ffmpeg 合成 mp4。
"""
import argparse
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=96)
    ap.add_argument("--out", default=os.path.join(os.environ.get("TEMP", "."), "riemann", "f_"))
    ap.add_argument("--res", type=int, default=1080)
    return ap.parse_args(argv)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def build_riemann(name="Riemann", turns=2.0, n_r=48, n_t=240, R=2.0):
    """√z 的黎曼面：极坐标 (r, θ) → 高度 = 半角，绕两圈才回到原处。"""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    verts = []
    faces = []
    total_th = turns * 2 * math.pi          # turns=2 → 4π，绕两圈才回到原处
    S = 2.4                                # 平面缩放
    Hh = 2.0                               # 每圈的高度（拉高才看得出螺旋）
    for i in range(n_r + 1):
        r = R * 0.55 + (R - R * 0.55) * i / n_r   # 只取外圈 → 变成一条带子
        for j in range(n_t + 1):           # 多一列，方便首尾相接（不做闭合，保留接口）
            th = total_th * j / n_t
            rr = math.sqrt(r)
            x = rr * math.cos(th / 2) * S
            z = rr * math.sin(th / 2) * S
            y = (th / (2 * math.pi)) * Hh - Hh   # 居中
            verts.append((x, y, z))
    stride = n_t + 1
    for i in range(n_r):
        for j in range(n_t):
            a = i * stride + j
            b = a + 1
            c = (i + 1) * stride + j
            d = c + 1
            faces.append((a, b, d, c))
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    for p in mesh.polygons:
        p.use_smooth = True
    return obj


def make_material(obj, name="Mat"):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    # 用"位置 → 色相"做一个彩色的渐变，像复平面色图
    tex = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.9, 0.25, 0.25, 1)
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (0.25, 0.75, 1.0, 1)
    mid = ramp.color_ramp.elements.new(0.5)
    mid.color = (0.35, 0.95, 0.55, 1)
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 2.0
    nt.links.new(tex.outputs["Object"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 0.35
    bsdf.inputs["Roughness"].default_value = 0.35
    bsdf.inputs["Metallic"].default_value = 0.25
    obj.data.materials.append(mat)


def setup_scene(res):
    scene = bpy.context.scene
    scene.render.resolution_x = 1920
    scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True   # 透明底，方便叠到 2D 视频上
    scene.world = bpy.data.worlds.new("W")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.02, 0.03, 0.06, 1)
    bg.inputs[1].default_value = 1.0
    # 引擎：优先 EEVEE（快），退回 Workbench
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        try:
            scene.render.engine = "BLENDER_EEVEE"
        except TypeError:
            scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"

    cam_data = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = (9.5, 4.5, 9.5)
    cam_data.lens = 35
    scene.camera = cam
    track = cam.constraints.new(type="TRACK_TO")
    empty = bpy.data.objects.new("Target", None)
    bpy.context.collection.objects.link(empty)
    empty.location = (0, 0, 0)
    track.target = empty
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"

    light_data = bpy.data.lights.new("Key", type="AREA")
    light_data.energy = 800
    light_data.size = 6
    light = bpy.data.objects.new("Key", light_data)
    bpy.context.collection.objects.link(light)
    light.location = (4, 5, 4)

    return cam


def main():
    args = parse_args()
    clear_scene()
    cam = setup_scene(args.res)

    obj = build_riemann()
    make_material(obj)

    # 自动取景：按物体包围盒算相机距离（之前手写距离老是贴脸）
    bpy.context.view_layer.update()
    dims = obj.dimensions
    extent = max(dims.x, dims.y, dims.z)
    dist = max(6.0, extent * 2.4)
    print("EXTENT", tuple(round(v, 2) for v in dims), "dist", round(dist, 2))
    globals()["CAM_DIST"] = dist
    cam.location = (dist * 0.72, dist * 0.42, dist * 0.72)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = args.frames
    for i in range(1, args.frames + 1):
        ang = 2 * math.pi * (i - 1) / args.frames
        D = globals().get('CAM_DIST', 12.0)
        cam.location = (D * 0.72 * math.cos(ang), D * 0.42, D * 0.72 * math.sin(ang))
        scene.frame_set(i)
        scene.render.filepath = f"{args.out}{i:04d}.png"
        bpy.ops.render.render(write_still=True)
    print("DONE", args.frames, "frames ->", args.out)


if __name__ == "__main__":
    main()
