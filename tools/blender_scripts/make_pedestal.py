# 生成「展位台子」—— 美术流水线的**参考实现**（大肥鱼写的，foilo 以后手做对照）
#
# 用法（无界面跑，Blender 5.x）：
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b -P tools\blender_scripts\make_pedestal.py -- <输出.glb>
#
# 关键约定（和 docs/art-plan.md 一致）：
#   · 尺寸用米：直径 3.6 m（半径 1.8）、高 0.5 m —— 与 Unity 里 Slot 的台子一致
#   · 低多边形 + 硬边 + 一圈倒角（倒角是"硬边看起来不廉价"的关键）
#   · 导出 glTF 2.0 (.glb)，Y 轴向上（Unity 自动转换）
import bpy
import sys

def main():
    out_path = sys.argv[-1]
    if not out_path.lower().endswith(".fbx"):
        print("[make_pedestal] 最后一个参数应是 .fbx 输出路径，实际:", out_path)
        sys.exit(2)

    # 清空默认场景（立方体/相机/灯）
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # 圆柱：半径 1.8 m、高 0.5 m、48 边（低多边形但足够圆）
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=48, radius=1.8, depth=0.5, end_fill_type='NGON', location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = "SlotPedestal"

    # 顶部收边：把顶面稍微缩一点，看起来像"台面"而不是"柱子"
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    # 选中顶面（z 最大的一圈面）——用 bmesh 更稳
    import bmesh
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    top = max(bm.faces, key=lambda f: f.calc_center_median().z)
    top_scale = 0.92
    c = top.calc_center_median()
    for v in top.verts:
        v.co.x = c.x + (v.co.x - c.x) * top_scale
        v.co.y = c.y + (v.co.y - c.y) * top_scale
    bm.to_mesh(me)
    bm.free()

    # 倒角：宽 0.03、3 段 —— 硬边保住，但高光会顺着倒角走
    bev = obj.modifiers.new(name="Bevel", type='BEVEL')
    bev.width = 0.03
    bev.segments = 3
    bev.limit_method = 'ANGLE'
    bev.angle_limit = 0.61
    bpy.ops.object.modifier_apply(modifier=bev.name)

    # 平面着色（低多边形风格）：不加平滑
    for poly in obj.data.polygons:
        poly.use_smooth = False

    # 导出 FBX（不是 glb！）
    # 为什么：Unity **原生不导入 glTF/glb**（会当成 DefaultImporter 的普通文件，
    # Resources.Load 拿不到模型）—— 除非额外装 glTFast 之类的包。
    # FBX 是 Unity 原生支持的，Blender 也自带导出器，所以这条流水线走 FBX。
    bpy.ops.export_scene.fbx(
        filepath=out_path,
        use_selection=False,
        apply_scale_options='FBX_SCALE_ALL',   # 缩放烘进模型，Unity 里尺寸就是米
        axis_forward='-Z',
        axis_up='Y',
        object_types={'MESH'},
        use_mesh_modifiers=True,
    )
    print("[make_pedestal] 已导出:", out_path)
    print("[make_pedestal] 顶点数:", len(obj.data.vertices), " 面数:", len(obj.data.polygons))

main()
