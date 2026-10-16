using System;
using System.Numerics;
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

        Console.WriteLine("== 体感莫比乌斯：走一圈后上方向翻转 180° ==");
        // 沿线走一圈 u: 0 -> 2π（v 固定在中心线上），曲面法线应当反向
        float R2 = 9f, W2 = 2.5f;
        Func<double, float[]> normalAt = (uu) =>
        {
            const float e = 1e-3f;
            MeshMath.MobiusPoint((float)uu, 0f, R2, W2, out float px, out float py, out float pz);
            MeshMath.MobiusPoint((float)uu + e, 0f, R2, W2, out float ux, out float uy, out float uz);
            MeshMath.MobiusPoint((float)uu, e, R2, W2, out float vx, out float vy, out float vz);
            float dux = ux - px, duy = uy - py, duz = uz - pz;
            float dvx = vx - px, dvy = vy - py, dvz = vz - pz;
            float nx = duy * dvz - duz * dvy, ny = duz * dvx - dux * dvz, nz = dux * dvy - duy * dvx;
            float len = (float)Math.Sqrt(nx * nx + ny * ny + nz * nz);
            if (len < 1e-9f) len = 1f;
            return new[] { nx / len, ny / len, nz / len };
        };
        var n0 = normalAt(0.0);
        var nHalf = normalAt(Math.PI);
        var nFull = normalAt(Math.PI * 2);
        float dotFull = n0[0] * nFull[0] + n0[1] * nFull[1] + n0[2] * nFull[2];
        float dotHalf = n0[0] * nHalf[0] + n0[1] * nHalf[1] + n0[2] * nHalf[2];
        Check(dotFull < -0.999f, "绕一整圈后法线反向（上方向翻转 180°）", $"dot = {dotFull:F4}");
        Check(Math.Abs(dotHalf) < 0.01f, "半圈时法线转过 90°", $"dot = {dotHalf:F4}");
        Console.WriteLine("== 圆环面（黑洞吸积盘用） ==");
        float bigR = 13.5f, smallR = 1.5f;
        var tor = MeshMath.Torus(bigR, smallR, 160, 24);
        Check(tor.VertexCount == 161 * 25, "顶点数 = (segU+1)*(segV+1)", tor.VertexCount.ToString());
        Check(tor.TriangleCount == 160 * 24 * 2, "三角形数 = segU*segV*2", tor.TriangleCount.ToString());
        Check(MeshMath.IndicesValid(tor), "索引全部合法");
        MeshMath.Bounds(tor, out float tdx, out float tdy, out float tdz);
        Check(Math.Abs(tdx - 2f * (bigR + smallR)) < 1e-2f, "外径 = 2(R+r)", $"{tdx:F2}");
        Check(Math.Abs(tdy - 2f * smallR) < 1e-2f, "厚度 = 2r", $"{tdy:F2}");
        Console.WriteLine("== 单位椭球（吉祥物积木） ==");
        var ell = MeshMath.Ellipsoid(48, 24);
        Check(ell.VertexCount == 49 * 25, "顶点数 = (segU+1)*(segV+1)", ell.VertexCount.ToString());
        Check(MeshMath.IndicesValid(ell), "索引全部合法");
        MeshMath.Bounds(ell, out float edx, out float edy, out float edz);
        Check(Math.Abs(edx - 2f) < 1e-3f && Math.Abs(edy - 2f) < 1e-3f && Math.Abs(edz - 2f) < 1e-3f,
              "包围盒 = 2（单位半径）", $"{edx:F3} x {edy:F3} x {edz:F3}");
        Console.WriteLine("== 曲面贴合：站着不动不能自己漂移 ==");
        // 倾斜 30° 的平面（法线在 y-z 面内）。玩家站在平面上方 H 处。
        // 射线方向用 up=(0,1,0)（落后于真法线）—— 漂移就来自这个偏差。
        float deg30 = 30f * (float)Math.PI / 180f;
        float cnx = 0f, cny = (float)Math.Cos(deg30), cnz = -(float)Math.Sin(deg30);
        const float HH = 1.62f;
        float upx2 = 0f, upy2 = 1f, upz2 = 0f;
        float qx0 = 3f, qz0 = 5f;                          // 平面上一点（满足 n·q = 0）
        float qy0 = -(cnx * qx0 + cnz * qz0) / cny;
        float pax = qx0 + cnx * HH, pay = qy0 + cny * HH, paz = qz0 + cnz * HH;
        float obx = pax, oby = pay, obz = paz;
        float driftNew2 = 0f, driftOld2 = 0f;
        Func<float, float, float, float> tang = (ax, ay, az) =>
        {
            float dx = ax - qx0, dy = ay - qy0, dz = az - qz0;
            float dn = dx * cnx + dy * cny + dz * cnz;
            dx -= cnx * dn; dy -= cny * dn; dz -= cnz * dn;
            return (float)Math.Sqrt(dx * dx + dy * dy + dz * dz);
        };
        for (int i = 0; i < 300; i++)
        {
            pax -= cnx * 0.02f; pay -= cny * 0.02f; paz -= cnz * 0.02f;
            if (SnapMath.RayPlane(pax + upx2 * 0.2f, pay + upy2 * 0.2f, paz + upz2 * 0.2f,
                                  -upx2, -upy2, -upz2, cnx, cny, cnz, out float hx, out float hy, out float hz))
            {
                SnapMath.CorrectAlongNormal(pax, pay, paz, hx, hy, hz, cnx, cny, cnz, HH,
                                            out float nxa, out float nya, out float nza);
                pax = nxa; pay = nya; paz = nza;
                driftNew2 = Math.Max(driftNew2, tang(pax, pay, paz));
            }
            obx -= cnx * 0.02f; oby -= cny * 0.02f; obz -= cnz * 0.02f;
            if (SnapMath.RayPlane(obx + upx2 * 0.2f, oby + upy2 * 0.2f, obz + upz2 * 0.2f,
                                  -upx2, -upy2, -upz2, cnx, cny, cnz, out float kx, out float ky, out float kz))
            {
                SnapMath.CorrectToHitPoint(kx, ky, kz, cnx, cny, cnz, HH,
                                           out float nxb, out float nyb, out float nzb);
                obx = nxb; oby = nyb; obz = nzb;
                driftOld2 = Math.Max(driftOld2, tang(obx, oby, obz));
            }
        }
        Check(driftNew2 < 1e-3f, "新写法：300 帧切向零漂移", string.Format("{0:E2}", driftNew2));
        Check(driftOld2 > 0.05f, "旧写法：确实会漂（对照）", string.Format("{0:F3} m", driftOld2));

        Console.WriteLine("== 复变函数的颜色映射（数学区 Slot_1 的展品） ==");
        // 展品本体：w = z²。下面每条断言都对应"你在图版上能看见的一件事"。
        Func<Complex, Complex> sq = z => z * z;

        // 0) 幂次 z^n（按 Q 循环的就是 n=1/2/3/4）：辐角必须正好翻 n 倍
        for (int exp = 1; exp <= 4; exp++)
        {
            Func<Complex, Complex> pow = ComplexColor.PowFunc(exp);
            Complex w = pow(Complex.ImaginaryOne);          // z=i，辐角 90°
            double gotDeg = Math.Atan2(w.Imaginary, w.Real) * 180.0 / Math.PI;
            double expectedDeg = 90.0 * exp;
            double diff = Math.Abs(((gotDeg - expectedDeg + 540.0) % 360.0) - 180.0);
            Check(diff < 1e-6, $"z^{exp} 在 z=i 处辐角应为 {expectedDeg:F0}°", $"{gotDeg:F3}°（差 {diff:E3}）");
        }
        // n=2 必须与手写的 z*z 逐位一致（换实现不许改变已有展品的颜色）
        {
            Complex z0 = new Complex(0.37, -1.24);
            Complex a = ComplexColor.Pow(z0, 2), b = z0 * z0;
            Check(a.Real == b.Real && a.Imaginary == b.Imaginary, "z^2 与 z*z 逐位一致", $"{a} vs {b}");
        }

        // 0b) 平方根 √z（主值支）—— 幂次表里的 "1/2" 那一项
        {
            // ① 远离分支切处：开方再平方必须回到自己
            Complex z0 = new Complex(2.0, 0.5);
            Complex root = ComplexColor.PowFraction(z0, 1, 2);
            Complex back = root * root;
            Check(Math.Abs(back.Real - z0.Real) < 1e-12 && Math.Abs(back.Imaginary - z0.Imaginary) < 1e-12,
                  "√z 再平方 = z（远离分支切处）", $"{back} vs {z0}");

            // ② 分支切落在负实轴上：正上方与正下方趋近，结果必须**不同**（就是那道缝）
            Complex justAbove = ComplexColor.PowFraction(new Complex(-1.0, 1e-9), 1, 2);
            Complex justBelow = ComplexColor.PowFraction(new Complex(-1.0, -1e-9), 1, 2);
            double gap = (justAbove - justBelow).Magnitude;
            Check(gap > 1.9, "负实轴上有分支切：两侧 √z 的值差约 2i", $"|差|={gap:F6}");
            Check(justAbove.Imaginary > 0.9 && justBelow.Imaginary < -0.9,
                  "分支切两侧分别是 +i 与 -i（arg 从 +π 跳到 -π 的一半）",
                  $"上={justAbove:F4} 下={justBelow:F4}");

            // ③ 绕半圈时辐角只转 π/2 —— 这就是"√z 的颜色只绕半圈"的来源
            Complex one = ComplexColor.PowFraction(Complex.One, 1, 2);
            double dArg = Math.Atan2(justAbove.Imaginary, justAbove.Real)
                        - Math.Atan2(one.Imaginary, one.Real);
            Check(Math.Abs(dArg - Math.PI / 2) < 1e-6, "从 arg 0 到 arg π，√z 的辐角只转 π/2", $"{dArg:F6} rad");
        }

        // 1) 辐角 → 色相
        ComplexColor.RgbForZ(sq, 1f, 0f, out float r1, out float g1, out float b1);
        Check(r1 > g1 && b1 < 0.02f, "z=1 → w=1（辐角 0）取红", $"rgb=({r1:F3},{g1:F3},{b1:F3})");
        ComplexColor.RgbForZ(sq, 0f, 1f, out float r2, out float g2, out float b2);
        Check(g2 > r2 + 0.05f && b2 > r2 + 0.05f, "z=i → w=-1（辐角 π）取青", $"rgb=({r2:F3},{g2:F3},{b2:F3})");

        // 2) 平方让色环绕两圈：z=1 与 z=-1 必须同色；对照 f=z 时它们是互补色
        ComplexColor.RgbForZ(sq, -1f, 0f, out float rn, out float gn, out float bn);
        Check(Math.Abs(rn - r1) < 1e-4f && Math.Abs(bn - b1) < 1e-4f,
              "f=z²：z=-1 与 z=1 同色（辐角翻倍 → 色环绕两圈）", $"|Δr|={Math.Abs(rn - r1):E2}");
        ComplexColor.RgbForZ(z => z, -1f, 0f, out float ir, out float ig, out float ib);
        Check(ib > ir + 0.05f, "对照 f=z：z=-1 是青（对面）—— 所以上一条不是凑巧", $"rgb=({ir:F3},{ig:F3},{ib:F3})");

        // 3) 模 → 明度：越亮的地方模越大；零点最黑
        ComplexColor.RgbForZ(sq, 0f, 0f, out float rz, out float gz, out float bz);
        Check(Math.Max(rz, Math.Max(gz, bz)) < 0.10f, "z=0 → w=0：零点最黑", $"max={Math.Max(rz, Math.Max(gz, bz)):F3}");
        ComplexColor.RgbForZ(z => z, 1.2f, 0f, out float rb, out _, out _);
        ComplexColor.RgbForZ(z => z, 3.0f, 0f, out float rc, out _, out _);
        Check(rc > rb, "同一射线上 |w| 越大越亮", $"{rb:F3} → {rc:F3}");

        // 4) 等模环：|w| 正好等于 1（log2=0，环上）应比 |w|=1.2 更暗
        ComplexColor.RgbForZ(z => z, 1.0f, 0f, out float ring, out _, out _);
        Check(ring < rb, "|w|=1 落在等模环上（被压暗）", $"{ring:F3} < {rb:F3}");

        // 5) 取色顺序：BuildGrid 第 0 行 = 虚部最小、第 0 列 = 实部最小
        //    （写反了图就上下颠倒，而这种错只能靠肉眼发现 —— 所以在这里钉死）
        float[] grid = ComplexColor.BuildGrid(sq, 2f, 4);
        Check(grid[1] > grid[0] && grid[1] > grid[2],
              "第 0 行第 0 列 = z=-1-i → w=2i：绿（行 0 是虚部最小）",
              $"rgb=({grid[0]:F3},{grid[1]:F3},{grid[2]:F3})");

        // 6) 竖直图版：法线必须朝 +Z，否则"正面看不见、只能从背面看"
        var panel = MeshMath.PanelXY(5.2f, 96);
        Check(panel.VertexCount == 97 * 97, "图版顶点数 = (seg+1)^2", panel.VertexCount.ToString());
        Check(panel.TriangleCount == 96 * 96 * 2, "图版三角形数 = seg^2*2", panel.TriangleCount.ToString());
        Check(MeshMath.IndicesValid(panel), "图版索引全部合法");
        MeshMath.Bounds(panel, out float pdx, out float pdy, out float pdz);
        Check(Math.Abs(pdx - 5.2f) < 1e-3f && Math.Abs(pdy - 5.2f) < 1e-3f && Math.Abs(pdz) < 1e-6f,
              "图版尺寸 = 5.2 × 5.2 × 0", $"{pdx:F3} x {pdy:F3} x {pdz:F3}");
        int flipped = 0;
        for (int t = 0; t + 2 < panel.Triangles.Length; t += 3)
        {
            int a = panel.Triangles[t] * 3, b = panel.Triangles[t + 1] * 3, c = panel.Triangles[t + 2] * 3;
            float e1x = panel.Vertices[b] - panel.Vertices[a];
            float e1y = panel.Vertices[b + 1] - panel.Vertices[a + 1];
            float e2x = panel.Vertices[c] - panel.Vertices[a];
            float e2y = panel.Vertices[c + 1] - panel.Vertices[a + 1];
            float nz = e1x * e2y - e1y * e2x;      // 与 Unity RecalculateNormals 同一套叉积
            if (nz <= 0f) flipped++;
        }
        Check(flipped == 0, $"全部 {panel.TriangleCount} 个三角形法线朝 +Z", $"反例 {flipped}");

        var swTex = System.Diagnostics.Stopwatch.StartNew();
        ComplexColor.BuildGrid(sq, 5.2f, 512);
        swTex.Stop();
        Console.WriteLine($"  [信息] 512×512 取色耗时 {swTex.ElapsedMilliseconds} ms（Awake 里每次只算一次）");

        Console.WriteLine();
        Console.WriteLine(fail == 0 ? "全部通过：网格数学可用 ✓" : $"{fail} 项失败 ✗");
        return fail == 0 ? 0 : 1;
    }
}