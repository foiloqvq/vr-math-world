using UnityEngine;
using Vmw.Meshes;

/// 莫比乌斯带：双面显示（side = DoubleSided 由材质决定），走一圈可看出只有一个面。
[RequireComponent(typeof(MeshFilter), typeof(MeshRenderer))]
public class MobiusStrip : MonoBehaviour
{
    public float radius = 3.4f;
    public float halfWidth = 1.15f;
    [Range(24, 480)] public int segmentsU = 240;
    [Range(2, 40)] public int segmentsV = 12;

    void Awake() => Rebuild();

    public void Rebuild()
    {
        MeshData data = MeshMath.MobiusStrip(radius, halfWidth, segmentsU, segmentsV);
        var mesh = new Mesh { name = "MobiusStrip" };
        if (data.VertexCount > 65000)
            mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
        var v = new Vector3[data.VertexCount];
        for (int i = 0; i < v.Length; i++)
            v[i] = new Vector3(data.Vertices[i * 3], data.Vertices[i * 3 + 1], data.Vertices[i * 3 + 2]);
        mesh.vertices = v;
        mesh.triangles = data.Triangles;
        mesh.RecalculateNormals();
        mesh.RecalculateBounds();
        GetComponent<MeshFilter>().sharedMesh = mesh;
    }
}