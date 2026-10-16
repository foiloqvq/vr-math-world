using UnityEngine;
using Vmw.Meshes;

/// 「大肥鱼」吉祥物：全部用程序化几何拼出来（一个椭球当积木，缩放/旋转/平移）。
/// 坐标约定：+Z 向前，符合 Unity 习惯，方便直接用 LookRotation 转向。
public static class MascotBody
{
    static Mesh sharedEllipsoid;

    static Mesh UnitEllipsoid()
    {
        if (sharedEllipsoid == null)
            sharedEllipsoid = MeshUtil.MakeMesh(MeshMath.Ellipsoid(48, 24), "UnitEllipsoid");
        return sharedEllipsoid;
    }

    /// 造一只吉祥物。size ≈ 身长（米）。返回根节点。
    public static GameObject Create(string name, Transform parent, float size, Color bodyColor, Color bellyColor)
    {
        var root = new GameObject(name);
        root.transform.SetParent(parent, false);

        var bodyMat = MaterialKit.MakeMaterial(bodyColor, 0.45f, 0.05f);
        var bellyMat = MaterialKit.MakeMaterial(bellyColor, 0.6f, 0f);
        var finMat = MaterialKit.MakeMaterial(bodyColor * 0.85f, 0.5f, 0f);
        var eyeMat = MaterialKit.MakeMaterial(new Color(0.05f, 0.06f, 0.09f), 0.85f, 0f);
        var glintMat = MaterialKit.MakeMaterial(new Color(1f, 1f, 1f), 0.9f, 0f);

        // 身体：沿 +Z 拉长的胖椭球（叫大肥鱼，得肥）
        Part(root.transform, "Body", Vector3.zero, new Vector3(0.75f, 0.92f, 1.55f) * size, Quaternion.identity, bodyMat);
        // 肚子：略小的浅色椭球，从下前方顶出来
        Part(root.transform, "Belly", new Vector3(0f, -0.34f, 0.18f) * size, new Vector3(0.6f, 0.62f, 1.2f) * size, Quaternion.identity, bellyMat);
        // 尾鳍：两片压扁的椭球向后展开
        Part(root.transform, "FlukeL", new Vector3(-0.38f, 0.05f, -1.5f) * size, new Vector3(0.42f, 0.1f, 0.6f) * size, Quaternion.Euler(12f, 22f, 0f), finMat);
        Part(root.transform, "FlukeR", new Vector3(0.38f, 0.05f, -1.5f) * size, new Vector3(0.42f, 0.1f, 0.6f) * size, Quaternion.Euler(12f, -22f, 0f), finMat);
        // 胸鳍：两侧各一片
        Part(root.transform, "FinL", new Vector3(-0.62f, -0.24f, 0.3f) * size, new Vector3(0.5f, 0.1f, 0.36f) * size, Quaternion.Euler(0f, 0f, 22f), finMat);
        Part(root.transform, "FinR", new Vector3(0.62f, -0.24f, 0.3f) * size, new Vector3(0.5f, 0.1f, 0.36f) * size, Quaternion.Euler(0f, 0f, -22f), finMat);
        // 眼睛 + 高光
        Part(root.transform, "EyeL", new Vector3(-0.42f, 0.2f, 0.95f) * size, Vector3.one * 0.14f * size, Quaternion.identity, eyeMat);
        Part(root.transform, "EyeR", new Vector3(0.42f, 0.2f, 0.95f) * size, Vector3.one * 0.14f * size, Quaternion.identity, eyeMat);
        Part(root.transform, "GlintL", new Vector3(-0.46f, 0.25f, 1.01f) * size, Vector3.one * 0.05f * size, Quaternion.identity, glintMat);
        Part(root.transform, "GlintR", new Vector3(0.46f, 0.25f, 1.01f) * size, Vector3.one * 0.05f * size, Quaternion.identity, glintMat);
        // 头顶喷水孔
        Part(root.transform, "Blowhole", new Vector3(0f, 0.62f, 0.5f) * size, new Vector3(0.12f, 0.1f, 0.2f) * size, Quaternion.identity, finMat);

        return root;
    }

    static void Part(Transform parent, string name, Vector3 localPos, Vector3 localScale, Quaternion localRot, Material mat)
    {
        var go = new GameObject(name);
        go.transform.SetParent(parent, false);
        go.transform.localPosition = localPos;
        go.transform.localRotation = localRot;
        go.transform.localScale = localScale;
        go.AddComponent<MeshFilter>().sharedMesh = UnitEllipsoid();
        go.AddComponent<MeshRenderer>().sharedMaterial = mat;
    }
}