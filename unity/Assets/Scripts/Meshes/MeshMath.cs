// 纯 C# 网格数学：不引用 UnityEngine，因此可以在引擎外直接用 dotnet 编译测试。
// （见 tools/meshmath-test —— 装 Unity 之前就能验证几何算得对不对）
using System;

namespace Vmw.Meshes
{
    public struct MeshData
    {
        public float[] Vertices;   // 每 3 个一组 xyz
        public int[] Triangles;    // 每 3 个一组索引
        /// 可选 UV：每 2 个一组 (u,v)。没有就是 null（老调用方不受影响）。
        /// 曲面（如黎曼面带）必须自带 UV —— 用平面投影铺 UV 会把绕圈的参数抹平。
        public float[] Uvs;

        public MeshData(float[] vertices, int[] triangles) { Vertices = vertices; Triangles = triangles; Uvs = null; }
        public MeshData(float[] vertices, int[] triangles, float[] uvs) { Vertices = vertices; Triangles = triangles; Uvs = uvs; }
        public int VertexCount => Vertices.Length / 3;
        public int TriangleCount => Triangles.Length / 3;
    }

    public static class MeshMath
    {
        /// 函数曲面 z = f(x, y)：规则网格三角化（返回顶点与索引）
        public static MeshData ParametricSurface(Func<float, float, float> f, float size, int segments)
        {
            if (segments < 1) throw new ArgumentOutOfRangeException(nameof(segments));
            int n = segments + 1;
            var verts = new float[n * n * 3];
            for (int i = 0; i < n; i++)
            {
                float y = -size * 0.5f + size * i / segments;
                for (int j = 0; j < n; j++)
                {
                    float x = -size * 0.5f + size * j / segments;
                    int k = (i * n + j) * 3;
                    verts[k] = x;
                    verts[k + 1] = f(x, y);
                    verts[k + 2] = y;          // 世界坐标：XZ 为地平面，Y 为高度
                }
            }
            var tris = new int[segments * segments * 6];
            int t = 0;
            for (int i = 0; i < segments; i++)
            for (int j = 0; j < segments; j++)
            {
                int a = i * n + j, b = a + n;
                tris[t++] = a; tris[t++] = b; tris[t++] = a + 1;
                tris[t++] = b; tris[t++] = b + 1; tris[t++] = a + 1;
            }
            return new MeshData(verts, tris);
        }

        /// 竖直图版：XY 平面上的规则网格（z = 0），**法线朝 +Z**（也就是"正面面朝入口"）。
        /// 用来挂复变函数的颜色贴图：+X 是实部、+Y 是虚部，正好是高斯平面的朝向。
        /// 顶点索引与 ParametricSurface 同构（a = i*n + j，这里 i 沿 +X、j 沿 +Y），
        /// 于是法线 = (b-a)×((a+1)-a) = (+X)×(+Y) = +Z —— 测试里会把这条断言钉死，
        /// 免得以后改了索引顺序、图版从背面看不见（那种 bug 只能靠肉眼发现）。
        public static MeshData PanelXY(float size, int segments)
        {
            if (segments < 1) throw new ArgumentOutOfRangeException(nameof(segments));
            int n = segments + 1;
            var verts = new float[n * n * 3];
            for (int i = 0; i < n; i++)
            {
                float x = -size * 0.5f + size * i / segments;
                for (int j = 0; j < n; j++)
                {
                    float y = -size * 0.5f + size * j / segments;
                    int k = (i * n + j) * 3;
                    verts[k] = x;
                    verts[k + 1] = y;
                    verts[k + 2] = 0f;
                }
            }
            var tris = new int[segments * segments * 6];
            int t = 0;
            for (int i = 0; i < segments; i++)
            for (int j = 0; j < segments; j++)
            {
                int a = i * n + j, b = a + n;
                tris[t++] = a; tris[t++] = b; tris[t++] = a + 1;
                tris[t++] = b; tris[t++] = b + 1; tris[t++] = a + 1;
            }
            return new MeshData(verts, tris);
        }

        /// 黎曼面（√z 的那两片叶子）用**一条绕两圈的螺旋带**来呈现。
        ///
        /// 参数：u ∈ [0, turns·2π]（绕角，同时决定高度）、v ∈ [0,1]（半径比例）。
        ///   P(u,v) = ( R(v)·cos u , h·u/(2π) , R(v)·sin u )，R(v) = rIn + (rOut-rIn)·v
        /// 于是绕一圈高度升 h；绕**两圈**回到同一个 (x,z)，但高了 2h ——
        /// 正好对上 √z：绕一圈换到另一片叶子，绕两圈才回到原来那片。
        ///
        /// UV：u 归一化到 [0,1]（沿色带）、v 归一化到 [0,1]（沿半径）。
        /// 之所以要自带 UV：绕圈的参数一旦被"平面投影"抹平，颜色接缝就对不上了。
        public static MeshData RiemannHelix(float rIn, float rOut, float heightPerTurn, int turns, int segU, int segV)
        {
            if (turns < 1) throw new ArgumentOutOfRangeException(nameof(turns));
            if (segU < 1) throw new ArgumentOutOfRangeException(nameof(segU));
            if (segV < 1) throw new ArgumentOutOfRangeException(nameof(segV));

            int nu = segU + 1, nv = segV + 1;
            var verts = new float[nu * nv * 3];
            var uvs = new float[nu * nv * 2];
            float span = turns * 2f * (float)Math.PI;

            for (int i = 0; i < nu; i++)
            {
                float u = span * i / segU;
                float cu = (float)Math.Cos(u), su = (float)Math.Sin(u);
                for (int j = 0; j < nv; j++)
                {
                    float t = (float)j / segV;
                    float r = rIn + (rOut - rIn) * t;
                    int k = (i * nv + j);
                    verts[k * 3] = r * cu;
                    verts[k * 3 + 1] = heightPerTurn * u / (float)(2 * Math.PI);
                    verts[k * 3 + 2] = r * su;
                    uvs[k * 2] = u / span;
                    uvs[k * 2 + 1] = t;
                }
            }

            var tris = new int[segU * segV * 6];
            int p = 0;
            for (int i = 0; i < segU; i++)
            for (int j = 0; j < segV; j++)
            {
                int a = i * nv + j;
                int b = (i + 1) * nv + j;
                int c = i * nv + j + 1;
                int d = (i + 1) * nv + j + 1;
                // 顺序让法线大致朝 +Y（从上面看得见、能站上去）
                tris[p++] = a; tris[p++] = b; tris[p++] = c;
                tris[p++] = b; tris[p++] = d; tris[p++] = c;
            }
            return new MeshData(verts, tris, uvs);
        }

        /// 莫比乌斯带的参数方程（唯一真相：网格生成与曲面法线都用它）        /// P(u,v) = ((R + v·cos(u/2))·cos u, v·sin(u/2), (R + v·cos(u/2))·sin u)
        public static void MobiusPoint(float u, float v, float radius, float halfWidth, out float x, out float y, out float z)
        {
            double r = radius + v * Math.Cos(u * 0.5);
            x = (float)(r * Math.Cos(u));
            y = (float)(v * Math.Sin(u * 0.5));
            z = (float)(r * Math.Sin(u));
        }

        /// 莫比乌斯带：参数曲面手工建网格（只有一个面，走一圈会翻到背面）
        public static MeshData MobiusStrip(float radius, float halfWidth, int segU, int segV)
        {
            if (segU < 3 || segV < 1) throw new ArgumentOutOfRangeException(nameof(segU));
            int nv = segV + 1;
            var verts = new float[(segU + 1) * nv * 3];
            for (int i = 0; i <= segU; i++)
            {
                float u = (float)(i / (double)segU * Math.PI * 2.0);
                for (int j = 0; j <= segV; j++)
                {
                    float v = (j / (float)segV - 0.5f) * 2f * halfWidth;
                    int k = (i * nv + j) * 3;
                    MobiusPoint(u, v, radius, halfWidth, out verts[k], out verts[k + 1], out verts[k + 2]);
                }
            }
            var tris = new int[segU * segV * 6];
            int t = 0;
            for (int i = 0; i < segU; i++)
            for (int j = 0; j < segV; j++)
            {
                int a = i * nv + j, b = a + nv;
                tris[t++] = a; tris[t++] = b; tris[t++] = a + 1;
                tris[t++] = b; tris[t++] = b + 1; tris[t++] = a + 1;
            }
            return new MeshData(verts, tris);
        }

        /// 圆环面（给黑洞的吸积盘、地标等用）
        public static MeshData Torus(float majorRadius, float minorRadius, int segU, int segV)
        {
            if (segU < 3 || segV < 3) throw new ArgumentOutOfRangeException(nameof(segU));
            int nv = segV + 1;
            var verts = new float[(segU + 1) * nv * 3];
            for (int i = 0; i <= segU; i++)
            {
                double u = i / (double)segU * Math.PI * 2.0;
                double cu = Math.Cos(u), su = Math.Sin(u);
                for (int j = 0; j <= segV; j++)
                {
                    double v = j / (double)segV * Math.PI * 2.0;
                    double r = majorRadius + minorRadius * Math.Cos(v);
                    int k = (i * nv + j) * 3;
                    verts[k] = (float)(r * cu);
                    verts[k + 1] = (float)(minorRadius * Math.Sin(v));
                    verts[k + 2] = (float)(r * su);
                }
            }
            var tris = new int[segU * segV * 6];
            int t = 0;
            for (int i = 0; i < segU; i++)
            for (int j = 0; j < segV; j++)
            {
                int a = i * nv + j, b = a + nv;
                tris[t++] = a; tris[t++] = b; tris[t++] = a + 1;
                tris[t++] = b; tris[t++] = b + 1; tris[t++] = a + 1;
            }
            return new MeshData(verts, tris);
        }
        /// 单位椭球（半径 1，UV 球）。缩放交给 Transform —— 吉祥物的身体、鳍、眼睛都用它拼。
        public static MeshData Ellipsoid(int segU = 48, int segV = 24)
        {
            if (segU < 3 || segV < 2) throw new ArgumentOutOfRangeException(nameof(segU));
            int nv = segV + 1;
            var verts = new float[(segU + 1) * nv * 3];
            for (int i = 0; i <= segU; i++)
            {
                double u = i / (double)segU * Math.PI * 2.0;
                for (int j = 0; j <= segV; j++)
                {
                    double v = j / (double)segV * Math.PI;
                    int k = (i * nv + j) * 3;
                    verts[k] = (float)(Math.Sin(v) * Math.Cos(u));
                    verts[k + 1] = (float)Math.Cos(v);
                    verts[k + 2] = (float)(Math.Sin(v) * Math.Sin(u));
                }
            }
            var tris = new int[segU * segV * 6];
            int t = 0;
            for (int i = 0; i < segU; i++)
            for (int j = 0; j < segV; j++)
            {
                int a = i * nv + j, b = a + nv;
                tris[t++] = a; tris[t++] = b; tris[t++] = a + 1;
                tris[t++] = b; tris[t++] = b + 1; tris[t++] = a + 1;
            }
            return new MeshData(verts, tris);
        }
        /// 包围盒尺寸（用于自检：确认几何形状在预期范围内）
        public static void Bounds(MeshData m, out float dx, out float dy, out float dz)
        {
            float minX = float.MaxValue, minY = float.MaxValue, minZ = float.MaxValue;
            float maxX = float.MinValue, maxY = float.MinValue, maxZ = float.MinValue;
            for (int i = 0; i < m.Vertices.Length; i += 3)
            {
                float x = m.Vertices[i], y = m.Vertices[i + 1], z = m.Vertices[i + 2];
                if (x < minX) minX = x; if (x > maxX) maxX = x;
                if (y < minY) minY = y; if (y > maxY) maxY = y;
                if (z < minZ) minZ = z; if (z > maxZ) maxZ = z;
            }
            dx = maxX - minX; dy = maxY - minY; dz = maxZ - minZ;
        }

        /// 索引是否全部落在顶点范围内（自检用，防越界）
        public static bool IndicesValid(MeshData m)
        {
            int n = m.VertexCount;
            foreach (int idx in m.Triangles) if (idx < 0 || idx >= n) return false;
            return true;
        }
    }
}