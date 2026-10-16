using UnityEngine;

/// 同伴控制：让吉祥物停下 / 继续跟随（R），走近了和它说话（E）。
/// 停下之后它会一直待在原地 —— 停在哪里都行，你回来时它还在。
///
/// 屏幕上会显示「最近收到的按键」与找到的同伴数量：
/// 按键没反应时，一眼能分清是"按键没进游戏"还是"代码没响应"。
public class CompanionControl : MonoBehaviour
{
    [Header("按键")]
    public KeyCode talkKey = KeyCode.E;
    public KeyCode stopKey = KeyCode.R;

    [Header("交互距离")]
    public float promptRange = 4.5f;

    [Header("调试显示")]
    public bool showDebug = true;

    SurfaceWalker player;
    MascotFollow[] follows;
    MascotDialogue[] dialogues;
    MascotDialogue nearest;
    float nearestDist = float.MaxValue;
    string lastKey = "—";
    float lastKeyUntil;
    int stopCount;

    void Start() { Rescan(); }

    void Rescan()
    {
        player = Object.FindFirstObjectByType<SurfaceWalker>();
        follows = Object.FindObjectsByType<MascotFollow>(FindObjectsSortMode.None);
        dialogues = Object.FindObjectsByType<MascotDialogue>(FindObjectsSortMode.None);
    }

    void Update()
    {
        if (player == null || follows == null || follows.Length == 0 || dialogues == null || dialogues.Length == 0)
            Rescan();

        // R：全体停下 / 继续跟随
        if (Input.GetKeyDown(stopKey))
        {
            lastKey = "R（停下/继续）"; lastKeyUntil = Time.time + 3f; stopCount++;
            if (follows != null)
                foreach (var f in follows)
                    if (f != null) f.ToggleFollow();
            Debug.Log("[CompanionControl] R 收到，已切换跟随状态（第 " + stopCount + " 次）");
        }

        if (Input.GetKeyDown(talkKey))
        {
            lastKey = "E（说话）"; lastKeyUntil = Time.time + 3f;
            if (nearest != null && nearestDist <= promptRange) nearest.Speak();
            else Debug.Log("[CompanionControl] 按了 E，但附近没有可对话的同伴（最近 " + nearestDist.ToString("F1") + "m）");
        }

        // 找最近的一只作为交互对象
        nearest = null; nearestDist = float.MaxValue;
        if (player != null && dialogues != null)
        {
            foreach (var d in dialogues)
            {
                if (d == null) continue;
                float dist = Vector3.Distance(player.transform.position, d.transform.position);
                if (dist < nearestDist) { nearestDist = dist; nearest = d; }
            }
        }
    }

    void OnGUI()
    {
        var small = new GUIStyle(GUI.skin.label) { fontSize = 14 };
        small.normal.textColor = new Color(0.72f, 0.84f, 1f);
        var prompt = new GUIStyle(GUI.skin.label) { fontSize = 19, alignment = TextAnchor.MiddleCenter };
        prompt.normal.textColor = new Color(1f, 0.96f, 0.7f);
        var shadow = new GUIStyle(prompt);
        shadow.normal.textColor = new Color(0f, 0f, 0f, 0.8f);

        if (nearest != null && nearestDist <= promptRange)
        {
            string text = string.Format("按 E 和 {0} 说话（{1:F1}m）   ·   按 R 让它停下 / 继续跟随", nearest.name, nearestDist);
            var rect = new Rect(0f, Screen.height - 252f, Screen.width, 26f);
            GUI.Label(new Rect(rect.x + 1.5f, rect.y + 1.5f, rect.width, rect.height), text, shadow);
            GUI.Label(rect, text, prompt);
        }

        if (showDebug)
        {
            string dbg = string.Format("同伴系统：找到 {0} 只跟随 / {1} 个对话   ·   最近按键 {2}   ·   R 已触发 {3} 次",
                follows != null ? follows.Length : 0,
                dialogues != null ? dialogues.Length : 0,
                Time.time < lastKeyUntil ? lastKey : "—",
                stopCount);
            GUI.Label(new Rect(16f, 148f, 1300f, 22f), dbg, small);
        }
    }
}