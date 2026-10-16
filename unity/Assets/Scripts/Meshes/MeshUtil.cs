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

    public static GameObject Spawn(string name, MeshData data, Material mat, Transform parent)
    {
        var go = new GameObject(name);
        go.transform.SetParent(parent, false);
        go.AddComponent<MeshFilter>().sharedMesh = MakeMesh(data, name);
        go.AddComponent<MeshRenderer>().sharedMaterial = mat;
        return go;
    }
}