# 章节生产线（SOP）

> 目的：**每章照表填，不再每次重新设计。** 一章的成本从"想 + 做"降到"填 + 跑"。
> 定稿：2026-10-18 深夜（foilo：「要有一个稳定的节奏，不用随便乱生成」）

---

## 一、一章 = 固定五件产物

| # | 产物 | 放哪 | 谁生成 |
| --- | --- | --- | --- |
| 1 | 课程条目 | `vr-math-world/docs/CURRICULUM.md` 表格一行 | 手填 |
| 2 | **一图流** | `My_Library/.../img/<章>-<主题>.png` | `tools/make-chapter.py`（模板） |
| 3 | **VR 展品** | `ExhibitScene.cs` 里 `Build<章>Wall()` + 至少一个可走件 | 代码 |
| 4 | **两份笔记** | 公开 `My_Library/.../<章>-笔记.md`；私库 `study-space/notes/<章>-速查.md` | 手写（套结构） |
| 5 | **自测题** | 笔记末尾 + 图右下角 | 手写 3 道 |

> 少一件不算完成。**判据**：一个没学过的人，看完图 → 走进 VR 走一遍 → 做对 3 道自测。

---

## 二、命名规范（别再发明）

```
图：      <章号>-<主题>.png          例：01-集合-交并补.png
脚本：    make-chapter-<章号>.py      例：make-chapter-01.py
VR 根节点：Exhibit_C<章号>_<主题>     例：Exhibit_C01_Venn
VR 贴图：  Resources/Art/C<章号>_<主题>.png
笔记：    公开 <章>-笔记.md   ｜ 私库 <章>-速查.md
```

---

## 三、跑一图的固定动作

```powershell
$py = "C:\Users\nb666\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
$env:PYTHONUTF8="1"
& $py "study-space\tools\make-chapter-01.py"      # 生成图
# 看图（必须自己先读一遍，别直接交付）
```

**图形铁律（踩过的坑）**
1. 一定 `from math_diagram_util import draw_mixed` —— 雅黑没有 ∈ ∅ ∩ ∪ ⊆ 字形，会变方框
2. 不要用中文引号写进字符串
3. 多行文本用 `\n` + 逐行绘制，不要塞给 `textlength`
4. Venn 类图要**蒙版上色**（ImageChops），描边三张会一样
5. 每张图右下/底部必须有一条**自测**

---

## 四、VR 展品的固定动作

```powershell
# 1) 贴图进 Resources/Art/
# 2) ExhibitScene.cs 加 Build<章>Wall()，照抄 BuildMethodWall（U 翻转 = (1-u, v)）
# 3) 编辑器必须关闭
Unity.exe -batchmode -quit -projectPath unity -executeMethod BuildScene.Generate
Unity.exe -batchmode -quit -projectPath unity -executeMethod BuildScene.Verify
# 4) 复核坐标
python tools\read-scene-pos.py --match <节点名>
```

**验收数字**：`Verify OK`，且 `objects` / `meshes` 比上次增加（增量记在提交信息里）。

---

## 五、笔记固定结构（照抄即可）

```markdown
# <章名>

> 一句话：这章在讲什么、为什么要学它

![一图流](img/xxx.png)

## 为什么要有这一章
## 核心内容（3~6 条）
## 三个易错点
## 例题（答案用 <details> 折叠）
## 三条自测
## 下一章
```

---

## 六、提交固定格式

```
feat(<章号>): <章名> —— 图/VR/笔记/自测
```

提交信息里必须带：**图文件名 + VR 节点名 + Verify 增量数字**（否则以后查不回来）。

---

## 七、每个阶段收口标准（对应 CURRICULUM 四阶段）

- **S1 收口**：第 0 章 + 第 1 章走完整五件套，且自测能过
- 之后每章照此复制，**不再改流程**；流程要改必须写进本文件并说明原因

---

## 八、待办模板（复制粘贴用）

```markdown
### 第 N 章 <章名>
- [ ] CURRICULUM 加一行
- [ ] `make-chapter-NN.py` 出一图流（含自测）
- [ ] 读图自检（符号/排版/是否说清）
- [ ] VR：`Build<章>Wall()` + 一个可走件
- [ ] Generate + Verify + read-scene-pos 复核
- [ ] 公开笔记 + 私库速查
- [ ] 三条自测
- [ ] 提交（带增量数字）+ 更新 CURRICULUM 状态
```
