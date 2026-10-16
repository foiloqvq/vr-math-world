using UnityEngine;

/// 屏幕角上的信息：速度、视角规格、吉祥物状态、操作提示。
/// 用 OnGUI —— 不依赖 UI 包也不依赖 TextMeshPro，任何渲染管线都能显示。
public class SpeedHud : MonoBehaviour
{
    public SurfaceWalker walker;
    public bool showPosition = true;
    public bool showMascots = true;

    Vector3 lastPos;
    float speed;
    MascotFollow[] mascots;

    void Update()
    {
        if (walker == null) walker = Object.FindFirstObjectByType<SurfaceWalker>();
        if (walker != null)
        {
            float inst = (Time.deltaTime > 0f)
                ? Vector3.Distance(walker.transform.position, lastPos) / Time.deltaTime
                : 0f;
            speed = Mathf.Lerp(speed, inst, 0.15f);
            lastPos = walker.transform.position;
        }
        if (showMascots && (mascots == null || mascots.Length == 0))
            mascots = Object.FindObjectsByType<MascotFollow>(FindObjectsSortMode.None);
    }

    void OnGUI()
    {
        var big = new GUIStyle(GUI.skin.label) { fontSize = 17 };
        big.normal.textColor = new Color(0.86f, 0.93f, 1f);
        var small = new GUIStyle(GUI.skin.label) { fontSize = 14 };
        small.normal.textColor = new Color(0.72f, 0.84f, 1f);

        string line1 = string.Format("速度 {0,5:F1} m/s", speed);
        if (showPosition && walker != null)
        {
            Vector3 p = walker.transform.position;
            line1 += string.Format("    位置 {0,5:F0}, {1,4:F0}, {2,4:F0}", p.x, p.y, p.z);
        }
        GUI.Label(new Rect(16f, 10f, 1000f, 26f), line1, big);

        string line2 = "W A S D 走  ·  Shift 快跑  ·  空格 跳  ·  鼠标环视  ·  1 / 2 / 3 传送";
        if (walker != null)
            line2 += string.Format("    视角 [{0}] {1:F2} m（V 切换）", walker.CurrentPresetName, walker.CurrentEyeHeight);
        GUI.Label(new Rect(16f, 34f, 1300f, 26f), line2, small);

        GUI.Label(new Rect(16f, 56f, 1300f, 26f),
            "试这件事：按 2 走到莫比乌斯带上，沿中线绕一整圈 —— 回到起点时，上下会翻过来", small);

        if (showMascots && mascots != null)
        {
            float y = 80f;
            foreach (var m in mascots)
            {
                if (m == null) continue;
                GUI.Label(new Rect(16f, y, 1300f, 24f), "吉祥物 " + m.name + " : " + m.DebugLine, small);
                y += 22f;
            }
        }
    }
}