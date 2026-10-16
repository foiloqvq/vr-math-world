using UnityEngine;
using Vmw.Meshes;

/// 在 Unity 里把 MeshMath 的函数曲面变成实际网格。
/// 默认函数选 z = sin(r)/r —— 那圈涟漪和中央尖峰就是它的形状。
[RequireComponent(typeof(MeshFilter), typeof(MeshRenderer))]
public class ParametricSurface : MonoBehaviour
{
    public float size = 22f;
    [Range(8, 400)] public int segments = 160;
    public float amplitude = 6.5f;

    void Awake() => Rebuild();

    public void Rebuild()
    {
        MeshData data = MeshMath.ParametricSurface((x, y) =>
        {
            float r = Mathf.Sqrt(x * x + y * y);
            if (r < 1e-4f) return amplitude;             // r→0 时 sin(r)/r → 1
            return Mathf.Sin(r) / r * amplitude;
        }, size, segments);

        var mesh = new Mesh { name = "ParametricSurface" };
        if (data.VertexCount > 65000)
            mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
        mesh.vertices = ToVector3(data.Vertices);
        mesh.triangles = data.Triangles;
        mesh.RecalculateNormals();
        mesh.RecalculateBounds();
        GetComponent<MeshFilter>().sharedMesh = mesh;
    }

    static Vector3[] ToVector3(float[] flat)
    {
        var v = new Vector3[flat.Length / 3];
        for (int i = 0; i < v.Length; i++)
            v[i] = new Vector3(flat[i * 3], flat[i * 3 + 1], flat[i * 3 + 2]);
        return v;
    }
}