#!/usr/bin/env python3
"""读 Unity 场景 YAML，列出指定（或全部）物体的坐标。

为什么要它：foilo 喜欢在编辑器里手动摆位置，而场景是脚本生成的 —— 两边会打架。
流程改成：**他摆 + Ctrl+S 保存 → 我读场景 → 把坐标回填进生成脚本**。

用法：
  python read-scene-pos.py                # 只列关键物体
  python read-scene-pos.py --all          # 列全部有 Transform 的物体
  python read-scene-pos.py --match AI_Station StationRing
"""
import argparse
import os
import re

DEFAULT_SCENE = (
    r"C:\Users\nb666\Documents\deepseek-harness\default-workspace"
    r"\vr-math-world\unity\Assets\Scenes\Sandbox.unity"
)

KEY = [
    "Player", "AI_Station", "StationBase", "StationRingOuter", "StationRingCenter",
    "Mascot_BigFish", "Mascot_SmallFish", "Exhibit_ProjectMap", "Exhibit_Surface",
    "Exhibit_ComplexMap", "Exhibit_RiemannSqrt", "Exhibit_Fractions", "Exhibit_Slopes",
    "District_Math", "Teleport_Math",
]


def parse(scene_path):
    """返回 [(字典序号, 物体名, 父物体序号, localPos, localScale)]"""
    with open(scene_path, encoding="utf-8", errors="replace") as f:
        text = f.read()

    docs = re.split(r"^--- !u!(\d+) &(\d+).*$", text, flags=re.M)
    # docs: [前导, class, fileID, 正文, class, fileID, 正文, ...]
    go_name = {}          # fileID -> name
    go_comp = {}          # fileID -> Transform fileID
    tr_info = {}          # transform fileID -> (goId, fatherId, localPos, localScale)

    i = 1
    while i + 2 < len(docs):
        cls, fid, body = docs[i], docs[i + 1], docs[i + 2]
        if cls == "1":    # GameObject
            m = re.search(r"m_Name:\s*(.*)", body)
            if m:
                go_name[fid] = m.group(1).strip()
        elif cls == "4":  # Transform
            m_go = re.search(r"m_GameObject:\s*\{fileID:\s*(\d+)", body)
            m_fa = re.search(r"m_Father:\s*\{fileID:\s*(\d+)", body)
            m_p = re.search(r"m_LocalPosition:\s*\{x:\s*([-\d.eE]+),\s*y:\s*([-\d.eE]+),\s*z:\s*([-\d.eE]+)\}", body)
            m_s = re.search(r"m_LocalScale:\s*\{x:\s*([-\d.eE]+),\s*y:\s*([-\d.eE]+),\s*z:\s*([-\d.eE]+)\}", body)
            if m_go:
                tr_info[fid] = (
                    m_go.group(1),
                    m_fa.group(1) if m_fa else "0",
                    tuple(float(x) for x in m_p.groups()) if m_p else (0, 0, 0),
                    tuple(float(x) for x in m_s.groups()) if m_s else (1, 1, 1),
                )
        i += 3

    rows = []
    for tr_id, (go_id, father, pos, scale) in tr_info.items():
        name = go_name.get(go_id, f"<{go_id}>")
        rows.append((name, father, pos, scale, go_id))
    return rows, tr_info


def build_chain(tr_info):
    """transform fileID -> (go_id, father_transform_id, pos, scale)"""
    return {tr: (go, father, pos, scale) for tr, (go, father, pos, scale) in tr_info.items()}


def world_pos(go_id, by_go, tr_info):
    """沿 Transform 的 m_Father 链累加 localPosition（父链是 Transform id，不是 GameObject id）。"""
    total = [0.0, 0.0, 0.0]
    # 先找到该 GameObject 的 Transform id
    tr_of_go = {v[0]: k for k, v in tr_info.items()}
    cur_tr = tr_of_go.get(go_id)
    guard = 0
    while cur_tr and guard < 64:
        guard += 1
        info = tr_info.get(cur_tr)
        if not info:
            break
        _, father_tr, pos, _ = info
        total = [total[k] + pos[k] for k in range(3)]
        if not father_tr or father_tr == "0":
            break
        cur_tr = father_tr
    return tuple(total)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default=DEFAULT_SCENE)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--match", nargs="*", default=None)
    args = ap.parse_args()

    rows, tr_info = parse(args.scene)
    by_go = {r[4]: r for r in rows}

    if args.match:
        wanted = args.match
        picked = [r for r in rows if any(w.lower() in r[0].lower() for w in wanted)]
    elif args.all:
        picked = rows
    else:
        picked = [r for r in rows if r[0] in KEY]

    print(f"场景: {os.path.basename(args.scene)} · 共 {len(rows)} 个 Transform\n")
    for name, father, pos, scale, go_id in picked:
        w = world_pos(go_id, by_go, tr_info)
        print(f"{name:<24} 世界({w[0]:8.3f}, {w[1]:7.3f}, {w[2]:8.3f})   "
              f"local({pos[0]:8.3f}, {pos[1]:7.3f}, {pos[2]:8.3f})   "
              f"scale({scale[0]:.3f}, {scale[1]:.3f}, {scale[2]:.3f})")


if __name__ == "__main__":
    main()
