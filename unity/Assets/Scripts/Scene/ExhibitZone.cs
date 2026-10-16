using UnityEngine;

/// 展品的"感知框"：平时几乎看不见（只在地面留一圈地标），
/// 人一走进来就发亮，再按 E 就出讲解。
///
/// 判定用包围盒自己算，不依赖物理触发器 —— 玩家身上没有碰撞体，
/// 触发器不会触发；而给玩家加碰撞体又可能干扰曲面吸附的射线。
public class ExhibitZone : MonoBehaviour
{
    public string exhibitName = "";
    public Vector3 halfSize = new Vector3(10f, 6f, 10f);
    public float fadeSpeed = 5f;
    public bool playerInside;
    public float glow;

    Material barMaterial;
    float phase;

    public void Setup(string name, Vector3 half)
    {
        exhibitName = name;
        halfSize = half;
    }

    void Awake()
    {
        foreach (Transform c in transform)
        {
            if (c.name == "GlowBar")
            {
                var r = c.GetComponent<Renderer>();
                if (r != null) { barMaterial = r.sharedMaterial; break; }
            }
        }
        SetGlow(0.08f);
    }

    /// 世界坐标是否在框内（只看水平范围，不看高低）
    public bool Contains(Vector3 worldPos)
    {
        Vector3 local = transform.InverseTransformPoint(worldPos);
        return Mathf.Abs(local.x) <= halfSize.x && Mathf.Abs(local.z) <= halfSize.z;
    }

    void Update()
    {
        float target = playerInside ? 1f : 0.08f;
        glow = Mathf.MoveTowards(glow, target, fadeSpeed * Time.deltaTime);
        phase += Time.deltaTime;
        float pulse = playerInside ? (0.8f + 0.2f * Mathf.Sin(phase * 6f)) : 1f;
        SetGlow(glow * pulse);
    }

    void SetGlow(float v)
    {
        if (barMaterial == null) return;
        Color c = new Color(0.45f, 0.85f, 1f, Mathf.Clamp01(v * 0.9f));
        if (barMaterial.HasProperty("_BaseColor")) barMaterial.SetColor("_BaseColor", c);
        if (barMaterial.HasProperty("_Color")) barMaterial.SetColor("_Color", c);
        if (barMaterial.HasProperty("_EmissionColor")) barMaterial.SetColor("_EmissionColor", c * 2f);
    }
}