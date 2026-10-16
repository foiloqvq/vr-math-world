using System.Collections.Generic;

/// 展品讲解词。按展品名字索引，走近展品按 E 就会念出来（带语音）。
/// 原则：先说"你眼前看到的东西"，再说它背后的数学，最后给一个能带走的直觉。
public static class Narration
{
    public static readonly Dictionary<string, string[]> ByExhibit = new Dictionary<string, string[]>
    {
        ["Exhibit_Surface"] = new[]
        {
            "这个曲面是 z 等于 sin(r) 除以 r。r 是到中心的距离。",
            "看中间那根尖峰：当 r 趋近 0，sin(r) 除以 r 趋近 1，所以它在那里最高，正好 6.5。",
            "外面一圈圈的水波是 sin(r) 的周期；振幅被 1 除以 r 压小，所以越远越平。",
            "这个函数在物理里到处都是：衍射、傅里叶变换、贝塞尔函数，都是它的亲戚。",
        },
        ["Exhibit_WalkableMobius"] = new[]
        {
            "这条带子只有一个面、一条边。你绕着中线走一整圈，回到起点时会发现自己上下翻了，却没跨过任何边缘。",
            "数学上这叫不可定向：走一圈，局部的上变成了下。",
            "那个 180 度不是我做的动画，是参数方程自己算出来的。",
        },
        ["Exhibit_Mobius"] = new[]
        {
            "这条小的也是莫比乌斯带，做出来给你对比看的。",
            "你可以把它想成一张纸拧半圈再粘起来 —— 从此它只有一个面。",
        },
        ["MathDistrict"] = new[]
        {
            "这里是数学区。你脚下这块地和这一圈框，就是它的格位。",
            "右边那条带子只有一个面；左前方那件曲面是 z 等于 sin(r) 除以 r。",
            "后面那几个空着的展位，是用来摆下一件数学的 —— 一件一件搬进来就行。",
        },
        ["Slot_1"] = new[] { "这个展位还空着。等我们把下一件数学搬进来。" },
        ["Slot_2"] = new[] { "这个展位还空着。你有什么想摆进来的？" },
        ["Slot_3"] = new[] { "这个展位还空着。位置都留好了。" },
        ["Slot_4"] = new[] { "这个展位还空着。以后每加一门学科，就多一块这样的地。" },
        ["Exhibit_BlackHole"] = new[]
        {
            "那是黑洞。它自己不发光，我们看见的是它背后和周围的光被折弯的样子。",
            "中间那个黑球是事件视界：进去的东西，连光也出不来。",
            "外面那圈亮环是吸积盘：物质被撕开、互相摩擦发热，越靠里转得越快。",
            "顺便说一句：广义相对论里引力不是力，是时空的弯曲 —— 掉进去的其实是直线。",
        },
    };

    /// 取某件展品的讲解词；没有就返回空数组
    public static string[] For(string exhibitName)
    {
        if (exhibitName != null && ByExhibit.TryGetValue(exhibitName, out var lines)) return lines;
        return new string[0];
    }
}