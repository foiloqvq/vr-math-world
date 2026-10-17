using UnityEditor;
using UnityEngine;

/// 美术资产的导入设置（一次性、幂等）。
///
/// 为什么需要它：Blender 是 Z 轴朝上，Unity 是 Y 轴朝上。FBX 导出后如果不勾
/// 「Bake Axis Conversion」，Unity 会原样导入 —— 于是圆柱**躺倒**（轴从 Y 变成 Z），
/// 视觉上就是"圆盘立起来了"（2026-10-17 foilo 在 Play 里看到的那个）。
///
/// 这里在编辑器加载时检查一遍：凡是 Art 目录下需要修正的模型，把 bakeAxisConversion 打开并重导入。
/// 只改一次（已经是 true 就跳过），所以不会每次启动都重导入。
[InitializeOnLoad]
public static class ArtImportSettings
{
    static readonly string[] NeedBake =
    {
        "Assets/Resources/Art/SlotPedestal.fbx",
    };

    static ArtImportSettings()
    {
        // 延迟到资源导入完成后再跑，避免和首次导入抢锁
        EditorApplication.delayCall += EnsureBake;
    }

    static void EnsureBake()
    {
        int fixedCount = 0;
        foreach (string path in NeedBake)
        {
            var importer = AssetImporter.GetAtPath(path) as ModelImporter;
            if (importer == null) continue;                 // 还没导入 / 文件不存在，跳过
            if (importer.bakeAxisConversion) continue;       // 已经正确
            importer.bakeAxisConversion = true;
            importer.SaveAndReimport();
            fixedCount++;
            Debug.Log("[ArtImportSettings] 已开启 Bake Axis Conversion: " + path);
        }
        if (fixedCount > 0)
            Debug.Log("[ArtImportSettings] 共修正 " + fixedCount + " 个美术资产（Y 轴朝上）");
    }
}
