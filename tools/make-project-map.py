#!/usr/bin/env python3
"""把项目结构扫成一张"导图"：输出 Markdown 树 + 单文件交互式 HTML。

做法：扫目录 → 按规则分类 → 每个 md 文件取第一行标题当简介 → 生成树。
用法：python make-project-map.py [--out 目录]
"""
import argparse
import html
import json
import os
import re

WS = r"C:\Users\nb666\Documents\deepseek-harness\default-workspace"
REPOS = ["vr-math-world", "study-space", "My_Library"]
SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "dist", "build", "Library", "Temp",
             "obj", "venv", "ready", "screenshots"}

# 目录 → 一句话说明（没有就走"自动推断"）
DIR_NOTE = {
    "vr-math-world": "主项目：可以走进去的数学世界（Unity）+ 子项目",
    "vr-math-world/docs": "文档：角色设定、视频脚本、参考分析、进度",
    "vr-math-world/docs/character": "我的形象设定与立绘",
    "vr-math-world/docs/video": "视频：每集脚本、配音、发布记录、风格指南",
    "vr-math-world/docs/video/reference": "参考视频封面与片头抽帧",
    "vr-math-world/tools": "工具脚本（视频渲染/审片/ASR/B站自动化/3D）",
    "vr-math-world/subprojects": "子项目（每个都是一个独立作品）",
    "vr-math-world/subprojects/dsh-live-voice": "DSH 语音插件：通话/常听/看网页/截屏/传视频/闹钟",
    "vr-math-world/site": "作品站（GitHub Pages）",
    "vr-math-world/assets": "素材（3D 帧、图）",
    "study-space": "私库：记忆、日记、队列、工具、安全自查",
    "study-space/tools": "通用工具（见/看屏/读X/存储/TTS看门狗）",
    "study-space/journal": "日记（按场记）",
    "My_Library": "公开学习资料",
}


def first_heading(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            for _ in range(12):
                line = f.readline()
                if not line:
                    break
                m = re.match(r"^#{1,3}\s+(.+)", line.strip())
                if m:
                    return m.group(1).strip()[:60]
    except Exception:
        pass
    return ""


def first_docstring(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            text = f.read(1200)
        m = re.search(r'"""(.+?)"""', text, re.S) or re.search(r"'''(.+?)'''", text, re.S)
        if m:
            return m.group(1).strip().split("\n")[0][:70]
        for line in text.split("\n")[:6]:
            if line.strip().startswith("//"):
                return line.strip().lstrip("/").strip()[:70]
    except Exception:
        pass
    return ""


def describe(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".md":
        return first_heading(path)
    if ext in (".py", ".mjs", ".js", ".ps1"):
        return first_docstring(path)
    return ""


def scan(root, rel, depth=0, max_depth=4):
    abs_path = os.path.join(root, rel)
    node = {"name": os.path.basename(abs_path) or rel, "path": rel, "type": "dir", "children": []}
    try:
        entries = sorted(os.listdir(abs_path))
    except Exception:
        return node
    files, dirs = [], []
    for e in entries:
        if e in SKIP_DIRS or e.startswith("."):
            continue
        p = os.path.join(abs_path, e)
        (dirs if os.path.isdir(p) else files).append(e)
    key = rel.replace("\\", "/")
    node["note"] = DIR_NOTE.get(key, "")
    for d in dirs:
        if depth < max_depth:
            node["children"].append(scan(root, os.path.join(rel, d), depth + 1, max_depth))
        else:
            node["children"].append({"name": d + "/", "path": os.path.join(rel, d), "type": "dir", "children": [], "note": ""})
    if len(files) > 15:
        # 同质文件太多（比如 150 帧 png）就折叠成一行，别把导图撑爆
        ext = os.path.splitext(files[0])[1] or ""
        total = sum(os.path.getsize(os.path.join(abs_path, f)) for f in files)
        node["children"].append({
            "name": f"… 共 {len(files)} 个 {ext} 文件", "path": os.path.join(rel, "*"),
            "type": "file", "size": total, "note": "（已折叠）",
        })
        for f in files[:3]:
            fp = os.path.join(abs_path, f)
            node["children"].append({
                "name": f, "path": os.path.join(rel, f), "type": "file",
                "size": os.path.getsize(fp), "note": describe(fp),
            })
    else:
        for f in files:
            fp = os.path.join(abs_path, f)
            node["children"].append({
                "name": f, "path": os.path.join(rel, f), "type": "file",
                "size": os.path.getsize(fp), "note": describe(fp),
            })
    return node


def to_md(node, level=0):
    lines = []
    pad = "  " * level
    note = node.get("note") or ""
    if node["type"] == "dir":
        lines.append(f"{pad}- **{node['name']}/**" + (f" — {note}" if note else ""))
        for c in node["children"]:
            lines.extend(to_md(c, level + 1))
    else:
        size = node.get("size", 0)
        sz = f"{size/1024:.0f}KB" if size < 1024 * 1024 else f"{size/1024/1024:.1f}MB"
        lines.append(f"{pad}- {node['name']} ({sz})" + (f" — {note}" if note else ""))
    return lines


HTML_TPL = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>项目导图 · 大肥鱼</title>
<style>
:root{--bg:#0a0e18;--fg:#dfe9ff;--dim:#8ea0be;--line:#1f2a44;--cy:#6ee6eb;--ye:#ffd060}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.7 system-ui,"Microsoft YaHei",sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:32px 20px 80px}
h1{font-size:26px;margin:0 0 6px}
.sub{color:var(--dim);margin:0 0 22px}
.ctl{display:flex;gap:10px;margin-bottom:18px}
button{background:#141c2c;color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:6px 12px;cursor:pointer}
button:hover{border-color:var(--cy);color:var(--cy)}
ul{list-style:none;padding-left:18px;border-left:1px solid var(--line);margin:4px 0}
li{margin:2px 0}
.dir>span{color:var(--cy);cursor:pointer;font-weight:600}
.file{color:var(--dim)}
.note{color:#7f8ea8;font-size:13px;margin-left:8px}
.sz{color:#5b6b85;font-size:12px;margin-left:6px}
.hide>ul{display:none}
</style></head><body><div class="wrap">
<h1>项目导图</h1>
<p class="sub">自动生成 —— 点目录可折叠。生成脚本：<code>vr-math-world/tools/make-project-map.py</code></p>
<div class="ctl">
  <button onclick="document.querySelectorAll('.dir').forEach(e=>e.classList.remove('hide'))">全部展开</button>
  <button onclick="document.querySelectorAll('.dir').forEach(e=>e.classList.add('hide'))">全部收起</button>
  <button onclick="document.querySelectorAll('.dir').forEach(e=>e.classList.toggle('hide'))">反转</button>
</div>
<div id="tree"></div>
<script>
const DATA = __DATA__;
function el(tag, cls, text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e}
function build(node){
  if(node.type==='file'){
    const li=el('li');
    li.appendChild(el('span','file',node.name));
    if(node.size) li.appendChild(el('span','sz',(node.size/1024|0)+'KB'));
    if(node.note) li.appendChild(el('span','note','— '+node.note));
    return li;
  }
  const li=el('li','dir');
  const s=el('span','',node.name+'/');
  s.onclick=()=>li.classList.toggle('hide');
  li.appendChild(s);
  if(node.note) li.appendChild(el('span','note','— '+node.note));
  const ul=el('ul');
  node.children.forEach(c=>ul.appendChild(build(c)));
  li.appendChild(ul);
  return li;
}
const root=el('ul');DATA.forEach(n=>root.appendChild(build(n)));
document.getElementById('tree').appendChild(root);
</script></div></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(WS, "vr-math-world", "docs"))
    args = ap.parse_args()

    trees = []
    for repo in REPOS:
        p = os.path.join(WS, repo)
        if os.path.isdir(p):
            trees.append(scan(WS, repo))

    md = ["# 项目导图（自动生成）", "",
          f"> 生成时间：自动 · 生成器 `vr-math-world/tools/make-project-map.py`",
          "> 说明：`—` 后面是该文件/目录的第一行说明（从文档标题或脚本注释里读的）", ""]
    for t in trees:
        md.extend(to_md(t))
        md.append("")
    md_path = os.path.join(args.out, "ARCHITECTURE.md")
    os.makedirs(args.out, exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    html_path = os.path.join(args.out, "architecture.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(HTML_TPL.replace("__DATA__", json.dumps(trees, ensure_ascii=False)))

    n_files = sum(1 for t in trees for _ in [0])
    print("Markdown:", md_path)
    print("HTML    :", html_path)
    for t in trees:
        cnt = len([c for c in t["children"]])
        print(f"  {t['name']}: {cnt} 个顶层项")


if __name__ == "__main__":
    main()
