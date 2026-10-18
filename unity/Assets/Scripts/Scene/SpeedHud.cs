using UnityEngine;

/// 屏幕角上的信息：速度、视角规格、吉祥物状态、操作提示。
/// 用 OnGUI —— 不依赖 UI 包也不依赖 TextMeshPro，任何渲染管线都能显示。
///
/// 2026-10-18 改版：字号改成按分辨率缩放（1080p 基准），加半透明底板，
/// 调试行（上向量 / 吉祥物自我报告）默认收起 —— 之前 14~17px 的绝对字号
/// 在 2560 宽屏上糊成一大片，挡住了半个场景。
public class SpeedHud : MonoBehaviour
{
    public SurfaceWalker walker;
    public bool showPosition = true;
    public bool showMascots = true;

    /// 调试行（上向量 / 输入轴 / 吉祥物内部状态）。按 F1 切换。
    public bool verbose = false;

    /// 复变展品的当前幂次说明（由 ExhibitScene 写）。静态字符串是刻意的：
    /// HUD 与展品之间不用互相持有引用，重建世界时也不会留下坏引用。
    public static string ComplexStatus = "";

    Vector3 lastPos;
    float speed;
    MascotFollow[] mascots;

    GUIStyle styleMain;
    GUIStyle styleDim;
    Texture2D panelTex;

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

        if (Input.GetKeyDown(KeyCode.F1)) verbose = !verbose;
    }

    void EnsureStyles()
    {
        // 以 1080p 为基准缩放：1366 宽的老屏也不至于挤成一条线
        float k = Mathf.Clamp(Screen.height / 1080f, 0.75f, 2f);
        int mainSize = Mathf.RoundToInt(13f * k);
        int dimSize = Mathf.RoundToInt(11f * k);

        if (styleMain == null)
        {
            styleMain = new GUIStyle(GUI.skin.label) { fontSize = mainSize, richText = true };
            styleMain.normal.textColor = new Color(0.88f, 0.94f, 1f);
            styleMain.padding = new RectOffset(10, 10, 6, 6);
        }
        else if (styleMain.fontSize != mainSize)
        {
            styleMain.fontSize = mainSize;
        }

        if (styleDim == null)
        {
            styleDim = new GUIStyle(GUI.skin.label) { fontSize = dimSize, richText = true };
            styleDim.normal.textColor = new Color(0.62f, 0.74f, 0.92f);
            styleDim.padding = new RectOffset(10, 10, 2, 6);
        }
        else if (styleDim.fontSize != dimSize)
        {
            styleDim.fontSize = dimSize;
        }

        if (panelTex == null)
        {
            panelTex = new Texture2D(1, 1);
            panelTex.SetPixel(0, 0, new Color(0.03f, 0.05f, 0.09f, 0.62f));
            panelTex.Apply();
        }

        styleMain.normal.background = panelTex;
        styleDim.normal.background = panelTex;
    }

    void OnGUI()
    {
        EnsureStyles();

        float k = Mathf.Clamp(Screen.height / 1080f, 0.75f, 2f);
        float pad = 14f * k;
        float lineH = (styleMain.fontSize + 8f) * 1.35f;
        float width = Mathf.Min(Screen.width * 0.62f, 900f * k);

        // ---- 第一块：状态（左上角）----
        string line1 = string.Format("<b>{0,4:F1}</b> m/s", speed);
        if (showPosition && walker != null)
        {
            Vector3 p = walker.transform.position;
            line1 += string.Format("   ·   x {0,4:F0}  y {1,3:F0}  z {2,4:F0}", p.x, p.y, p.z);
        }

        string line2 = "WASD 走 · Shift 跑 · 空格跳 · C 蹲 · Z 趴 · E 说话 · R 停 · 1-4 传送 · 鼠标环视";
        if (walker != null)
            line2 += string.Format("\n视角 [{0}] {1:F2}m · 姿态 [{2}] · 相机 [{3}]",
                walker.CurrentPresetName, walker.CurrentEyeHeight, walker.PostureName, walker.CurrentCamModeName);

        Rect r1 = new Rect(pad, pad, width, lineH);
        GUI.Label(r1, line1, styleMain);
        Rect r2 = new Rect(pad, pad + lineH - 2f, width, lineH * 1.6f);
        GUI.Label(r2, line2, styleDim);

        // ---- 第二块：这一区的"试这件事" + 复变状态（左下角）----
        float bottomY = Screen.height - pad - lineH * (verbose ? 6f : 3.2f);
        Rect r3 = new Rect(pad, bottomY, width, lineH * 1.4f);
        GUI.Label(r3, "试这件事：按 2 走上莫比乌斯带，沿中线绕一圈 —— 回来时上下会翻过来", styleDim);

        if (!string.IsNullOrEmpty(ComplexStatus))
        {
            Rect r4 = new Rect(pad, bottomY + lineH * 1.5f, width, lineH * 1.2f);
            GUI.Label(r4, ComplexStatus, styleDim);
        }

        if (!verbose) return;

        // ---- 调试区（F1）----
        float y = bottomY - lineH * 2.2f;
        if (walker != null && !string.IsNullOrEmpty(walker.DebugLine))
        {
            GUI.Label(new Rect(pad, y, width, lineH), walker.DebugLine, styleDim);
            y -= lineH;
        }
        if (showMascots && mascots != null)
        {
            foreach (var m in mascots)
            {
                if (m == null) continue;
                GUI.Label(new Rect(pad, y, width, lineH), "吉祥物 " + m.name + " : " + m.DebugLine, styleDim);
                y -= lineH;
            }
        }
    }
}
