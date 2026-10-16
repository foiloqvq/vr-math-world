using System;
using Vmw.Meshes;

// 在引擎外验证网格数学：装 Unity 之前就能确认几何算对了
class Program
{
    static int fail = 0;

    static void Check(bool ok, string what, string detail = "")
    {
        Console.WriteLine($"  [{(ok ? "OK" : "FAIL")}] {what} {detail}");
        if (!ok) fail++;
    }

    static int Main()
    {
        Console.WriteLine("== 函数曲面 z = sin(r)/r * 6.5 ==");
        const float size = 22f; const int seg = 160; const float amp = 6.5f;
        var s = MeshMath.ParametricSurface((x, y) =>
        {
            float r = (float)Math.Sqrt(x * x + y * y);
            return r < 1e-4f ? amp : (float)(Math.Sin(r) / r) * amp;
        }, size, seg);

        int n = seg + 1;
        Check(s.VertexCount == n * n, "顶点数 = (seg+1)^2", $"{s.VertexCount} vs {n * n}");
        Check(s.TriangleCount == seg * seg * 2, "三角形数 = seg^2*2", $"{s.TriangleCount}");
        Check(MeshMath.IndicesValid(s), "索引全部合法（无越界）");
        MeshMath.Bounds(s, out float dx, out float dy, out float dz);
        Check(Math.Abs(dx - size) < 1e-3f && Math.Abs(dz - size) < 1e-3f, "XZ 尺寸 = size", $"{dx:F3} x {dz:F3}");
        // 分别验证最高与最低：sin(r)/r 在 r=0 取 1（中心尖峰 6.5），在 r≈4.493 取 ≈-0.217（约 -1.41）
        float maxY = float.MinValue, minY = float.MaxValue;
        for (int i = 1; i < s.Vertices.Length; i += 3) { float y = s.Vertices[i]; if (y > maxY) maxY = y; if (y < minY) minY = y; }
        Check(Math.Abs(maxY - amp) < 1e-3f, "中心尖峰高度 = 6.5", $"max = {maxY:F3}");
        Check(Math.Abs(minY - (-0.2172f * amp)) < 0.01f, "最低涟漪 ≈ -1.41", $"min = {minY:F3}");
        Check(Math.Abs(dy - (maxY - minY)) < 1e-3f, "高度差 = max - min", $"dy = {dy:F3}");

        Console.WriteLine("== 莫比乌斯带 ==");
        const float R = 3.4f, W = 1.15f; const int su = 240, sv = 12;
        var m = MeshMath.MobiusStrip(R, W, su, sv);
        Check(m.VertexCount == (su + 1) * (sv + 1), "顶点数 = (segU+1)*(segV+1)", $"{m.VertexCount}");
        Check(m.TriangleCount == su * sv * 2, "三角形数 = segU*segV*2", $"{m.TriangleCount}");
        Check(MeshMath.IndicesValid(m), "索引全部合法（无越界）");

        // 不变量：绕 u 一圈后，同一条 v 线会接到对面的 -v（这就是"只有一个面"）
        int nv = sv + 1;
        bool closes = true; float worst = 0f;
        for (int j = 0; j <= sv; j++)
        {
            int a = (0 * nv + j) * 3;                 // u = 0,  v = v_j
            int b = ((su) * nv + (sv - j)) * 3;       // u = 2π, v = -v_j（索引镜像）
            for (int k = 0; k < 3; k++)
            {
                float d = Math.Abs(m.Vertices[a + k] - m.Vertices[b + k]);
                if (d > worst) worst = d;
                if (d > 1e-3f) closes = false;
            }
        }
        Check(closes, "绕一圈闭合到 -v 侧（单面性）", $"最大偏差 {worst:E2}");

        Console.WriteLine();
        Console.WriteLine(fail == 0 ? "全部通过：网格数学可用 ✓" : $"{fail} 项失败 ✗");
        return fail == 0 ? 0 : 1;
    }
}