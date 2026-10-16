using UnityEngine;

/// 同伴控制：让吉祥物停下 / 继续跟随（R），走近了和它说话（E）。
/// 停下之后它会一直待在原地 —— 停在哪里都行，你回来时它还在。
public class CompanionControl : MonoBehaviour
{
    [Header("按键")]
    public KeyCode talkKey = KeyCode.E;
    public KeyCode stopKey = KeyCode.R;

    [Header("交互距离")]
    public float promptRange = 4.5f;

    SurfaceWalker player;
    MascotFollow[] follows;
    MascotDialogue[] dialogues;
    MascotDialogue nearest;
    float nearestDist = float.MaxValue;

    void Start()
    {
        player = Object.FindFirstObjectByType<SurfaceWalker>();
        follows = Object.FindObjectsByType<MascotFollow>(FindObjectsSortMode.None);
        dialogues = Object.FindObjectsByType<MascotDialogue>(FindObjectsSortMode.None);
    }

    void Update()
    {
        if (follows == null || follows.Length == 0)
            follows = Object.FindObjectsByType<MascotFollow>(FindObjectsSortMode.None);
        if (dialogues == null || dialogues.Length == 0)
            dialogues = Object.FindObjectsByType<MascotDialogue>(FindObjectsSortMode.None);
        if (player == null) player = Object.FindFirstObjectByType<SurfaceWalker>();

        // R：全体停下 / 继续跟随
        if (Input.GetKeyDown(stopKey))
            foreach (var f in follows) if (f != null) f.ToggleFollow();

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

        if (nearest != null && nearestDist <= promptRange && Input.GetKeyDown(talkKey))
            nearest.Speak();
    }

    void OnGUI()
    {
        if (nearest == null || nearestDist > promptRange) return;
        var style = new GUIStyle(GUI.skin.label) { fontSize = 18, alignment = TextAnchor.MiddleCenter };
        style.normal.textColor = new Color(1f, 0.96f, 0.7f);
        var shadow = new GUIStyle(style);
        shadow.normal.textColor = new Color(0f, 0f, 0f, 0.8f);
        string text = string.Format("按 E 和 {0} 说话   ·   按 R 让它停下 / 继续跟随", nearest.name);
        var rect = new Rect(0f, Screen.height - 250f, Screen.width, 26f);
        GUI.Label(new Rect(rect.x + 1.5f, rect.y + 1.5f, rect.width, rect.height), text, shadow);
        GUI.Label(rect, text, style);
    }
}