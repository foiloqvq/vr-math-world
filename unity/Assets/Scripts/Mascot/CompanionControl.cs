using UnityEngine;

/// 同伴控制：
///   R —— 循环三种状态：跟随 → 自由漫游 → 原地停下
///   E —— 在展品旁按一下听讲解（逐句推进）；空地上则闲聊
/// 屏幕上显示状态、交互提示与自我报告（按键是否收到、找到几只同伴）。
public class CompanionControl : MonoBehaviour
{
    [Header("按键")]
    public KeyCode talkKey = KeyCode.E;
    public KeyCode stopKey = KeyCode.R;

    [Header("距离")]
    public float promptRange = 4.5f;      // 能和同伴说话的最近距离
    public float narrationRange = 22f;    // 站得多近算"在展品旁边"（按水平距离，不看高低）

    [Header("调试显示")]
    public bool showDebug = true;

    static readonly string[] ExhibitNames =
    {
        "Exhibit_Surface", "Exhibit_Mobius", "Exhibit_WalkableMobius", "Exhibit_BlackHole"
    };

    SurfaceWalker player;
    MascotFollow[] follows;
    MascotDialogue[] dialogues;
    Transform[] exhibits;
    MascotDialogue nearest;
    float nearestDist = float.MaxValue;
    string nearExhibit;
    Transform nearExhibitTransform;
    string lastKey = "—";
    float lastKeyUntil;
    int stopCount;

    void Start() { Rescan(); }

    void Rescan()
    {
        player = Object.FindFirstObjectByType<SurfaceWalker>();
        follows = Object.FindObjectsByType<MascotFollow>(FindObjectsSortMode.None);
        dialogues = Object.FindObjectsByType<MascotDialogue>(FindObjectsSortMode.None);
        exhibits = new Transform[ExhibitNames.Length];
        for (int i = 0; i < ExhibitNames.Length; i++)
        {
            var go = GameObject.Find(ExhibitNames[i]);
            exhibits[i] = go != null ? go.transform : null;
        }
    }

    void Update()
    {
        if (player == null || follows == null || follows.Length == 0 || dialogues == null || dialogues.Length == 0)
            Rescan();

        // R：切换状态
        if (Input.GetKeyDown(stopKey))
        {
            lastKey = "R"; lastKeyUntil = Time.time + 3f; stopCount++;
            string state = "?";
            if (follows != null)
                foreach (var f in follows)
                    if (f != null) { f.CycleMode(); state = f.ModeName; }
            Debug.Log("[CompanionControl] R 收到 → " + state);
        }

        // 找最近的同伴
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

        // 找最近的展品（用于讲解）
        nearExhibit = null; nearExhibitTransform = null;
        float exDist = float.MaxValue;
        if (player != null && exhibits != null)
        {
            for (int i = 0; i < exhibits.Length; i++)
            {
                if (exhibits[i] == null) continue;
                // 只看水平距离：展品在高处（比如黑洞）也照样能触发
                Vector3 a = player.transform.position, b = exhibits[i].position;
                float dist = new Vector2(a.x - b.x, a.z - b.z).magnitude;
                if (dist < exDist) { exDist = dist; nearExhibit = ExhibitNames[i]; nearExhibitTransform = exhibits[i]; }
            }
            if (exDist > narrationRange) { nearExhibit = null; nearExhibitTransform = null; }
        }

        // E：优先讲解展品，其次闲聊
        if (Input.GetKeyDown(talkKey))
        {
            lastKey = "E"; lastKeyUntil = Time.time + 3f;
            bool done = false;
            if (nearest != null && nearExhibit != null && nearExhibitTransform != null)
                done = nearest.SpeakExhibit(nearExhibit, nearExhibitTransform);
            if (!done && nearest != null && nearestDist <= promptRange) nearest.Speak();
            if (!done && (nearest == null || nearestDist > promptRange))
                Debug.Log("[CompanionControl] 按了 E，但附近没有可对话的同伴（最近 " + nearestDist.ToString("F1") + "m）");
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

        string line = null;
        if (nearExhibit != null && nearest != null)
            line = string.Format("按 E 听讲解：{0}（{1} 会讲）   ·   按 R 切换 跟随 / 自由漫游 / 停下",
                ShortName(nearExhibit), nearest.name);
        else if (nearest != null && nearestDist <= promptRange)
            line = string.Format("按 E 和 {0} 说话（{1:F1}m）   ·   按 R 切换 跟随 / 自由漫游 / 停下", nearest.name, nearestDist);

        if (line != null)
        {
            var rect = new Rect(0f, Screen.height - 252f, Screen.width, 26f);
            GUI.Label(new Rect(rect.x + 1.5f, rect.y + 1.5f, rect.width, rect.height), line, shadow);
            GUI.Label(rect, line, prompt);
        }

        if (showDebug)
        {
            string modes = "";
            if (follows != null)
                foreach (var f in follows)
                    if (f != null) modes += (modes.Length > 0 ? " / " : "") + f.ModeName;
            string dbg = string.Format("同伴 {0} 只 [{1}] · 对话 {2} 个 · 最近按键 {3} · R 触发 {4} 次",
                follows != null ? follows.Length : 0, modes,
                dialogues != null ? dialogues.Length : 0,
                Time.time < lastKeyUntil ? lastKey : "—", stopCount);
            GUI.Label(new Rect(16f, 148f, 1300f, 22f), dbg, small);
        }
    }

    static string ShortName(string exhibit)
    {
        switch (exhibit)
        {
            case "Exhibit_Surface": return "函数曲面";
            case "Exhibit_Mobius": return "小莫比乌斯带";
            case "Exhibit_WalkableMobius": return "可走的莫比乌斯带";
            case "Exhibit_BlackHole": return "黑洞";
            default: return exhibit;
        }
    }
}