using UnityEngine;
using Vmw.Meshes;

/// 把整个原型场景一键搭出来。
/// 用法：新建空场景 → 建一个空 GameObject → 挂上这个脚本 → 按 Play。
/// 不依赖任何渲染管线特性（Built-in / URP / HDRP 都能跑），材质统一走 MaterialKit。
public class ExhibitScene : MonoBehaviour
{
    [Header("空间")]
    public bool buildGround = true;
    public bool buildLights = true;
    public bool spawnExhibits = true;
    public bool buildHud = true;
    public bool buildMascots = true;

    [Header("脚下网格（给运动提供参照）")]
    public int gridCellsPerTile = 8;
    public float gridUnitsPerCell = 2f;
    public float groundSize = 400f;

    [Header("可走莫比乌斯带")]
    public float walkRadius = 9f;
    public float walkHalfWidth = 2.5f;
    public int walkSegU = 320;
    public int walkSegV = 16;
    public int markerCount = 24;
    public float markerHeight = 1.8f;   // 用户反馈"参照物太矮看不全"，加高

    void Awake() { if (transform.childCount == 0) Build(); }

    public void Build()
    {
        if (buildGround) BuildGround();
        if (buildLights) BuildLights();
        if (spawnExhibits) BuildExhibits();
        if (buildHud) BuildHud();
        if (buildMascots) BuildMascots();
    }

    void BuildGround()
    {
        var ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
        ground.name = "Ground";
        ground.transform.SetParent(transform, false);
        ground.transform.localScale = new Vector3(groundSize / 10f, 1f, groundSize / 10f);

        var mat = MaterialKit.MakeMaterial(new Color(0.075f, 0.105f, 0.185f), 0.12f);
        var tex = MaterialKit.MakeGridTexture(256, gridCellsPerTile);
        // 平铺次数 = 总格数 / 每图格数，让每格约等于 gridUnitsPerCell 个单位
        float tiles = groundSize / (gridUnitsPerCell * gridCellsPerTile);
        MaterialKit.SetMainTexture(mat, tex, tiles);
        ground.GetComponent<MeshRenderer>().sharedMaterial = mat;
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
        RenderSettings.fogStartDistance = 70f;
        RenderSettings.fogEndDistance = 260f;
    }

    void BuildExhibits()
    {
        // 展品 1：函数曲面
        var surface = new GameObject("Exhibit_Surface");
        surface.transform.SetParent(transform, false);
        surface.transform.localPosition = new Vector3(0f, 0f, -20f);
        surface.AddComponent<ParametricSurface>().Rebuild();
        surface.GetComponent<MeshRenderer>().sharedMaterial =
            MaterialKit.MakeMaterial(new Color(0.29f, 0.64f, 1f), 0.35f, 0.15f);

        // 展品 2：展示用的小莫比乌斯带
        var mobius = new GameObject("Exhibit_Mobius");
        mobius.transform.SetParent(transform, false);
        mobius.transform.localPosition = new Vector3(24f, 3.4f, 6f);
        mobius.AddComponent<MobiusStrip>().Rebuild();
        mobius.GetComponent<MeshRenderer>().sharedMaterial =
            MaterialKit.MakeMaterial(new Color(0.55f, 0.88f, 1f), 0.30f, 0.40f);

        // 展品 3：能走上去的莫比乌斯带（真的能站上去走一圈）
        var walk = new GameObject("Exhibit_WalkableMobius");
        walk.transform.SetParent(transform, false);
        walk.transform.localPosition = new Vector3(0f, 6f, 46f);
        var wm = walk.AddComponent<MobiusStrip>();
        wm.radius = walkRadius;
        wm.halfWidth = walkHalfWidth;
        wm.segmentsU = walkSegU;
        wm.segmentsV = walkSegV;
        wm.Rebuild();
        walk.GetComponent<MeshRenderer>().sharedMaterial =
            MaterialKit.MakeMaterial(new Color(0.62f, 0.86f, 1f), 0.25f, 0.30f);
        var wcol = walk.AddComponent<MeshCollider>();
        wcol.sharedMesh = walk.GetComponent<MeshFilter>().sharedMesh;

        BuildLoopMarkers(walk.transform);

        // 展品 4：黑洞（黑球 + 倾斜的发光圆环）—— 远处就能认出来的地标
        var bh = new GameObject("Exhibit_BlackHole");
        bh.transform.SetParent(transform, false);
        bh.transform.localPosition = new Vector3(-46f, 18f, 34f);

        var core = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        core.name = "Core";
        core.transform.SetParent(bh.transform, false);
        core.transform.localScale = Vector3.one * 9f;
        core.GetComponent<MeshRenderer>().sharedMaterial =
            MaterialKit.MakeMaterial(new Color(0.01f, 0.01f, 0.015f), 0f);
        var coreCol = core.GetComponent<Collider>();
        if (coreCol != null) { if (Application.isPlaying) Destroy(coreCol); else DestroyImmediate(coreCol); }

        var ring = MeshUtil.Spawn("AccretionRing", MeshMath.Torus(13.5f, 1.5f, 160, 24),
            MaterialKit.MakeMaterial(new Color(1f, 0.55f, 0.16f), 0.45f, 0.2f), bh.transform);
        ring.transform.localRotation = Quaternion.Euler(74f, 0f, 0f);
        ring.AddComponent<SlowSpin>();

        // 展品 5（待办）：五种柏拉图立体 —— 需要各自的网格生成器，下一轮加
    }

    /// 沿带子中心线摆一圈路标（颜色绕色相环变化）。
    /// 作用有两个：看得出自己绕了多少、以及"走着走着上下翻过来"这件事是渐变的。
    void BuildLoopMarkers(Transform strip)
    {
        var root = new GameObject("LoopMarkers");
        root.transform.SetParent(strip, false);

        for (int i = 0; i < markerCount; i++)
        {
            float u = i / (float)markerCount * Mathf.PI * 2f;
            const float e = 0.01f;
            MeshMath.MobiusPoint(u, 0f, walkRadius, walkHalfWidth, out float cx, out float cy, out float cz);
            MeshMath.MobiusPoint(u + e, 0f, walkRadius, walkHalfWidth, out float ux, out float uy, out float uz);
            MeshMath.MobiusPoint(u, e, walkRadius, walkHalfWidth, out float vx, out float vy, out float vz);

            Vector3 p = new Vector3(cx, cy, cz);
            Vector3 du = new Vector3(ux - cx, uy - cy, uz - cz);
            Vector3 dv = new Vector3(vx - cx, vy - cy, vz - cz);
            Vector3 n = Vector3.Cross(du, dv).normalized;

            var post = GameObject.CreatePrimitive(PrimitiveType.Cube);
            post.name = "Marker_" + i.ToString("00");
            post.transform.SetParent(root.transform, false);
            post.transform.localPosition = p + n * (markerHeight * 0.5f);
            post.transform.localRotation = Quaternion.LookRotation(du.normalized, n);
            post.transform.localScale = new Vector3(0.16f, markerHeight, 0.16f);

            // 路标不能挡射线（会干扰曲面吸附），去掉碰撞体
            var col = post.GetComponent<Collider>();
            if (col != null)
            {
                if (Application.isPlaying) Destroy(col);
                else DestroyImmediate(col);
            }

            post.GetComponent<MeshRenderer>().sharedMaterial =
                MaterialKit.MakeMaterial(Color.HSVToRGB(i / (float)markerCount, 0.55f, 0.95f), 0.3f);
        }
    }

    /// 两只吉祥物：大鱼跟着玩家，小鱼跟着大鱼（妹妹跟着姐姐）
    void BuildMascots()
    {
        var big = MascotBody.Create("Mascot_BigFish", transform, 1.25f,
            new Color(0.30f, 0.56f, 0.92f), new Color(0.90f, 0.95f, 1f));
        big.transform.localPosition = new Vector3(0f, 8.6f, 40f);
        var bigFollow = big.AddComponent<MascotFollow>();
        bigFollow.followDistance = 5.5f;
        bigFollow.followHeight = 1.9f;

        var small = MascotBody.Create("Mascot_SmallFish", transform, 0.62f,
            new Color(0.58f, 0.82f, 1f), new Color(1f, 0.97f, 0.99f));
        small.transform.localPosition = new Vector3(1.4f, 7.6f, 37f);
        var smallFollow = small.AddComponent<MascotFollow>();
        smallFollow.target = big.transform;      // 妹妹跟着姐姐
        smallFollow.followDistance = 3.0f;
        smallFollow.followHeight = -0.15f;
        smallFollow.followLerp = 1.6f;           // 慢半拍更可爱
        smallFollow.bobFrequency = 1.3f;

        // 让它们游起来：大鱼慢一点，小鱼快一点，看起来是两条活鱼
        var bigSwim = big.AddComponent<MascotSwim>();
        bigSwim.tailFrequency = 1.3f;
        bigSwim.finFrequency = 1.3f;
        var smallSwim = small.AddComponent<MascotSwim>();
        smallSwim.tailFrequency = 1.9f;
        smallSwim.finFrequency = 1.9f;
        smallSwim.spoutInterval = 5f;
    }

    void BuildHud()
    {
        var hud = new GameObject("HUD");
        hud.transform.SetParent(transform, false);
        hud.AddComponent<SpeedHud>();   // 会在运行时自己找到 SurfaceWalker
    }
}