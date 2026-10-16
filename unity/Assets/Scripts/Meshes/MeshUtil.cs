using UnityEngine;
using Vmw.Meshes;

/// 把 MeshMath 的输出变成 Unity 的 Mesh 并挂到 GameObject 上。
/// 网格生成逻辑与引擎解耦，这里只做"翻译"。
public static class MeshUtil
{
    public static Mesh MakeMesh(MeshData data, string name)
    {
        var mesh = new Mesh { name = name };
        if (data.VertexCount > 65000)
            mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
        var v = new Vector3[data.VertexCount];
        for (int i = 0; i < v.Length; i++)
            v[i] = new Vector3(data.Vertices[i * 3], data.Vertices[i * 3 + 1], data.Vertices[i * 3 + 2]);
        mesh.vertices = v;
        mesh.triangles = data.Triangles;
        mesh.RecalculateNormals();
        mesh.RecalculateBounds();
        return mesh;
    }

    /// 按平面投影给网格铺 UV（0..1）。
    /// 为什么需要它：MakeMesh 建出来的网格**没有 UV**（一直是纯色材质，所以从没暴露过），
    /// 直接挂贴图的话所有顶点都取 (0,0)，整块面只显示一个像素的颜色 —— 看起来像"贴图没生效"。
    /// uAxis / vAxis 取 0=X、1=Y、2=Z：竖直图版用 (0,1)，水平地面用 (0,2)。
    public static void SetPlanarUVs(Mesh mesh, int uAxis, int vAxis)
    {
        if (mesh == null) return;
        mesh.RecalculateBounds();
        Vector3[] verts = mesh.vertices;
        Bounds b = mesh.bounds;
        Vector3 min = b.min, size = b.size;
        var uv = new Vector2[verts.Length];
        for (int i = 0; i < verts.Length; i++)
        {
            Vector3 p = verts[i];
            uv[i] = new Vector2(
                size[uAxis] > 1e-6f ? (p[uAxis] - min[uAxis]) / size[uAxis] : 0f,
                size[vAxis] > 1e-6f ? (p[vAxis] - min[vAxis]) / size[vAxis] : 0f);
        }
        mesh.uv = uv;
    }

    public static GameObject Spawn(string name, MeshData data, Material mat, Transform parent)
    {
        var go = new GameObject(name);
        go.transform.SetParent(parent, false);
        go.AddComponent<MeshFilter>().sharedMesh = MakeMesh(data, name);
        go.AddComponent<MeshRenderer>().sharedMaterial = mat;
        return go;
    }
}