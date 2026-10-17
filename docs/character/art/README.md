# 大肥鱼 · 2D 形象（代码绘制）

> 由 `tools/make-mascot-2d.py` 生成，**不依赖画师、版权干净**（纯代码绘制）。
> 设定见 `docs/character/mascot-sheet.md`（方案 A · 水手服）。

| 文件 | 表情 | 用途 |
| --- | --- | --- |
| 大肥鱼-水手服-happy.png | 开心（弯眼 ^ ^） | 默认形象、头像、封面 |
| 大肥鱼-水手服-confused.png | 困惑 | 表情包、报错场景 |
| 大肥鱼-水手服-proud.png | 得意 | 表情包、被夸 |
| 大肥鱼-水手服-shy.png | 害羞 | 表情包 |
| 大肥鱼-水手服-tired.png | 疲惫 | 深夜、收工 |

重新生成（含透明底）：

```powershell
python tools\make-mascot-2d.py --all --dir docs\character\art --transparent
```

规格：1400×1400 PNG；线宽按尺寸自动缩放；配色表见设定表第三节 + 第十七节。