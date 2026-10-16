using UnityEngine;

/// 把整个原型场景一键搭出来：地面 + 光照 + 两件展品。
/// 用法：新建空场景 → 建一个空 GameObject → 挂上这个脚本 → 按 Play。
/// 不依赖任何渲染管线特性（Built-in / URP / HDRP 都能跑），材质用属性探测兼容。
public class ExhibitScene : MonoBehaviour
{
    [Header("空间")]
    public bool buildGround = true;
    public bool buildLights = true;
    public bool spawnExhibits = true;

    static Material MakeMaterial(Color color, float smoothness = 0.25f, float metallic = 0f)
    {
        Shader sh = Shader.Find("Universal Render Pipeline/Lit")
                 ?? Shader.Find("Standard")
                 ?? Shader.Find("HDRP/Lit")
                 ?? Shader.Find("Sprites/Default");
        var m = new Material(sh);
        // 不同管线属性名不同，探测着设，避免"粉色材质"
        if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", color);
        if (m.HasProperty("_Color")) m.SetColor("_Color", color);
        if (m.HasProperty("_Smoothness")) m.SetFloat("_Smoothness", smoothness);
        if (m.HasProperty("_Glossiness")) m.SetFloat("_Glossiness", smoothness);
        if (m.HasProperty("_Metallic")) m.SetFloat("_Metallic", metallic);
        return m;
    }

    // 场景里已经搭好了就不重复生成（编辑器生成的场景 + 按 Play 时 Awake 都会走这里）
    void Awake() { if (transform.childCount == 0) Build(); }

    public void Build()
    {
        if (buildGround) BuildGround();
        if (buildLights) BuildLights();
        if (spawnExhibits) BuildExhibits();
    }

    void BuildGround()
    {
        var ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
        ground.name = "Ground";
        ground.transform.SetParent(transform, false);
        ground.transform.localScale = new Vector3(40f, 1f, 40f);   // 400x400
        ground.GetComponent<MeshRenderer>().sharedMaterial =
            MakeMaterial(new Color(0.07f, 0.10f, 0.18f), 0.1f);
    }

    void BuildLights()
    {
        var sunGo = new GameObject("Sun");
        sunGo.transform.SetParent(transform, false);
        sunGo.transform.rotation = Quaternion.Euler(48f, 35f, 0f);
        var sun = sunGo.AddComponent<Light>();
        sun.type = LightType.Directional;
        sun.intensity = 1.6f;
        sun.color = Color.white;
        sun.shadows = LightShadows.Soft;

        RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
        RenderSettings.ambientSkyColor = new Color(0.30f, 0.42f, 0.62f);
        RenderSettings.ambientEquatorColor = new Color(0.16f, 0.20f, 0.30f);
        RenderSettings.ambientGroundColor = new Color(0.05f, 0.06f, 0.10f);
        RenderSettings.fog = true;
        RenderSettings.fogColor = new Color(0.04f, 0.06f, 0.12f);
        RenderSettings.fogMode = FogMode.Linear;
        RenderSettings.fogStartDistance = 60f;
        RenderSettings.fogEndDistance = 190f;
    }

    void BuildExhibits()
    {
        // 展品 1：函数曲面（和网页原型同一个函数与尺寸）
        var surface = new GameObject("Exhibit_Surface");
        surface.transform.SetParent(transform, false);
        surface.transform.localPosition = new Vector3(0f, 0f, -20f);
        var ps = surface.AddComponent<ParametricSurface>();
        ps.Rebuild();
        surface.GetComponent<MeshRenderer>().sharedMaterial =
            MakeMaterial(new Color(0.29f, 0.64f, 1f), 0.35f, 0.15f);

        // 展品 2：莫比乌斯带
        var mobius = new GameObject("Exhibit_Mobius");
        mobius.transform.SetParent(transform, false);
        mobius.transform.localPosition = new Vector3(24f, 3.4f, 6f);
        var ms = mobius.AddComponent<MobiusStrip>();
        ms.Rebuild();
        mobius.GetComponent<MeshRenderer>().sharedMaterial =
            MakeMaterial(new Color(0.55f, 0.88f, 1f), 0.30f, 0.40f);

        // 展品 3：可走上去的莫比乌斯带（半径与宽度都放大，够人走在上面）
        // 走一圈后你会从"背面"回来：没跨过边缘，但上下翻转 180°
        var walk = new GameObject("Exhibit_WalkableMobius");
        walk.transform.SetParent(transform, false);
        walk.transform.localPosition = new Vector3(0f, 6f, 46f);
        var wm = walk.AddComponent<MobiusStrip>();
        wm.radius = 9f;
        wm.halfWidth = 2.5f;
        wm.segmentsU = 320;
        wm.segmentsV = 16;
        wm.Rebuild();
        walk.GetComponent<MeshRenderer>().sharedMaterial =
            MakeMaterial(new Color(0.62f, 0.86f, 1f), 0.25f, 0.30f);
        var wcol = walk.AddComponent<MeshCollider>();
        wcol.sharedMesh = walk.GetComponent<MeshFilter>().sharedMesh;

        // 展品 4（待办）：五种柏拉图立体 —— 需要各自的网格生成器，下一轮加
        // 说明见 unity/README.md 的 TODO
    }
}