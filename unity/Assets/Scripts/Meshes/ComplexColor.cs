// 复变函数的颜色映射：纯 C#，不引用 UnityEngine —— 所以能在引擎外测（见 tools/meshmath-test）。
//
// 这是颜色的**唯一真相**：Unity 侧那张贴图和测试里的断言都从这里取色，不许各写一套。
//
// 规则（每一条都能用眼睛数出来）：
//   色相 = f(z) 的辐角 arg → 绕零点走一圈，颜色绕一圈色环（f = z² 就绕两圈）
//   明度 = f(z) 的模 |f(z)| → 零点最黑，模越大越亮
//   等模环：|f(z)| 每翻一倍压暗一条（对数刻度的"等高线"）
//   等辐角射线：每 15° 压暗一条
using System;
using Complex = System.Numerics.Complex;

namespace Vmw.Meshes
{
    public static class ComplexColor
    {
        /// 参考幅度：|f(z)| 到这里就算"最亮"。
        /// 取 16 是因为默认展品用 f = z²、定义域 |z| ≤ 3 → |f| 最大 9，留一点余量。
        public const float ReferenceMagnitude = 16f;

        const float RingDim = 0.45f;   // 等模环压暗到多少
        const float RayDim = 0.55f;    // 等辐角射线压暗到多少

        /// 给一个已经算出来的 w = f(z) 取色（r/g/b 都在 0..1）
        public static void RgbFor(Complex w, out float r, out float g, out float b)
        {
            // System.Numerics.Complex 内部是 double，这里统一转成 float（展品不需要双精度）
            float re = (float)w.Real, im = (float)w.Imaginary;
            float mag = (float)Math.Sqrt(re * re + im * im);
            float arg = (float)Math.Atan2(im, re);

            // 色相：辐角归一化到 0..1（负角也绕回正）
            float hue = arg / (float)(Math.PI * 2.0);
            hue -= (float)Math.Floor(hue);

            // 明度：对数缩放，零点压到最暗
            float t = Log2(1f + mag) / Log2(1f + ReferenceMagnitude);
            float v = 0.05f + 0.95f * Clamp01(t);

            if (mag > 1e-6f)
            {
                float ringT = Frac(Log2(mag));                        // 每 2 倍一条
                if (ringT < 0.05f || ringT > 0.95f) v *= RingDim;

                float rayT = Frac(arg / (float)Math.PI * 12f);        // 每 15° 一条
                if (rayT < 0.04f || rayT > 0.96f) v *= RayDim;
            }

            HsvToRgb(hue, 1f, Clamp01(v), out r, out g, out b);
        }

        /// 直接在复平面点 z 上取色：w = f(z)
        public static void RgbForZ(Func<Complex, Complex> f, float re, float im,
                                   out float r, out float g, out float b)
        {
            RgbFor(f(new Complex(re, im)), out r, out g, out b);
        }

        /// 一个方形定义域 [-size/2, size/2]² 的全部像素颜色：行优先，
        /// **第 0 行 = 虚部最小（最下）**，第 0 列 = 实部最小（最左）。
        /// 返回长度 pixels*pixels*3 的 RGB —— 这个顺序就是 Unity 贴图的写入顺序，
        /// 所以两边共用同一个循环，不会出现"图上下颠倒"这类只能靠肉眼发现的问题。
        public static float[] BuildGrid(Func<Complex, Complex> f, float size, int pixels)
        {
            if (pixels < 2) throw new ArgumentOutOfRangeException(nameof(pixels));
            var rgb = new float[pixels * pixels * 3];
            for (int y = 0; y < pixels; y++)
            {
                float im = -size * 0.5f + size * y / (pixels - 1);
                for (int x = 0; x < pixels; x++)
                {
                    float re = -size * 0.5f + size * x / (pixels - 1);
                    RgbFor(f(new Complex(re, im)), out float r, out float g, out float b);
                    int k = (y * pixels + x) * 3;
                    rgb[k] = r; rgb[k + 1] = g; rgb[k + 2] = b;
                }
            }
            return rgb;
        }

        /// 色相 0..1 绕一圈：0 红 → 1/3 绿 → 2/3 蓝 → 回到红
        public static void HsvToRgb(float h, float s, float v, out float r, out float g, out float b)
        {
            h = Frac(h) * 6f;
            int i = (int)Math.Floor(h);
            float f = h - i;
            float p = v * (1f - s);
            float q = v * (1f - s * f);
            float t = v * (1f - s * (1f - f));
            switch (i % 6)
            {
                case 0: r = v; g = t; b = p; break;
                case 1: r = q; g = v; b = p; break;
                case 2: r = p; g = v; b = t; break;
                case 3: r = p; g = q; b = v; break;
                case 4: r = t; g = p; b = v; break;
                default: r = v; g = p; b = q; break;
            }
        }

        static float Frac(float x) { return x - (float)Math.Floor(x); }
        static float Clamp01(float x) { return x < 0f ? 0f : (x > 1f ? 1f : x); }

        /// 以 2 为底的对数。
        /// **别改成 Math.Log2**：Unity 的 .NET 配置（.NET Standard 2.1）里没有它，
        /// 而引擎外的测试工程是 net8.0、有它 —— 于是"测试全过、Unity 编不过"，
        /// 2026-10-17 真的这么翻车过一次（Unity 报 CS0117，三处）。
        static float Log2(float x) { return (float)(Math.Log(x) / Math.Log(2.0)); }
    }
}
