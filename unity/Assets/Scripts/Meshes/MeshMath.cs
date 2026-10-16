// 纯 C# 网格数学：不引用 UnityEngine，因此可以在引擎外直接用 dotnet 编译测试。
// （见 tools/meshmath-test —— 装 Unity 之前就能验证几何算得对不对）
using System;

namespace Vmw.Meshes
{
    public struct MeshData
    {
        public float[] Vertices;   // 每 3 个一组 xyz
        public int[] Triangles;    // 每 3 个一组索引

        public MeshData(float[] vertices, int[] triangles) { Vertices = vertices; Triangles = triangles; }
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

        /// 莫比乌斯带的参数方程（唯一真相：网格生成与曲面法线都用它）
        /// P(u,v) = ((R + v·cos(u/2))·cos u, v·sin(u/2), (R + v·cos(u/2))·sin u)
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