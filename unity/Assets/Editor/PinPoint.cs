using System.IO;
using System.Net;
using System.Text;
using UnityEditor;
using UnityEngine;

/// 一键"钉标记点"：把选中物体（或场景视图焦点）的世界坐标写进文件 + 发给大肥鱼。
///
/// 为什么要它：靠嘴报坐标经常念错/听错（2026-10-18 连错三次）。
/// 用法：菜单 **VRMathWorld → 钉标记点（发给我）**
///   - 选中任意物体 → 记它的世界坐标
///   - 没选东西 → 用 Scene 视图当前焦点（相机 pivot）
public static class PinPoint
{
    const string LogFile = @"C:\Users\nb666\Documents\deepseek-harness\default-workspace\study-space\pins.log";
    const string Endpoint = "http://127.0.0.1:7891/diag";

    [MenuItem("VRMathWorld/钉标记点（发给我）")]
    public static void Pin()
    {
        Vector3 p;
        string what;

        if (Selection.activeTransform != null)
        {
            p = Selection.activeTransform.position;
            what = Selection.activeTransform.name;
        }
        else
        {
            var sv = SceneView.lastActiveSceneView;
            if (sv == null) { Debug.LogWarning("[PinPoint] 没有选中物体，也没有打开 Scene 视图"); return; }
            p = sv.pivot;
            what = "(scene-view-pivot)";
        }

        string line = string.Format("pin {0} pos=({1:F3}, {2:F3}, {3:F3}) at={4}",
            what, p.x, p.y, p.z, System.DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"));

        try
        {
            File.AppendAllText(LogFile, line + "\n", Encoding.UTF8);
        }
        catch (System.Exception e)
        {
            Debug.LogWarning("[PinPoint] 写文件失败：" + e.Message);
        }

        try
        {
            using (var wc = new WebClient())
            {
                wc.Encoding = Encoding.UTF8;
                wc.UploadString(Endpoint, "POST", line);
            }
        }
        catch (System.Exception e)
        {
            Debug.LogWarning("[PinPoint] 发送失败（不影响记录）：" + e.Message);
        }

        Debug.Log("[PinPoint] " + line);
    }
}
