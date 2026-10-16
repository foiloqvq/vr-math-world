using UnityEngine;
using Vmw.Meshes;
using Complex = System.Numerics.Complex;

/// 把整个原型场景一键搭出来，并且**能在运行时补齐缺的东西**。
///
/// 为什么要"补齐"：场景里只存了 World / Player 这些容器，其余内容由代码生成。
/// 一旦代码新增了组件（对话、同伴控制…），旧场景里就没有它们 ——
/// 以前必须手动重新生成场景，反复坑人。现在 Awake 会检查并只补缺失部分，
/// 于是改完代码直接按 Play 就行。
public class ExhibitScene : MonoBehaviour
{
    [Header("空间")]
    public bool buildGround = true;
    public bool buildLights = true;
    public bool spawnExhibits = true;
    public bool buildHud = true;
    public bool buildMascots = true;
    public bool buildCompanion = true;
    public bool buildDistricts = true;

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
    public float markerHeight = 1.8f;

    /// 复变函数颜色映射（数学区 Slot_1）的全部参数。
    /// **幂次是运行时可变的**：按 `Q` 在 `z, √z, z², z³, z⁴` 之间循环，图版与地砖立刻重算。
    ///
    /// 眼睛能直接数出来的差别：
    ///   · 整数幂 z^n —— 绕原点走一圈，颜色绕 **n 圈**（n=1 一圈、2 两圈、3 三圈）
    ///   · 平方根 √z —— 颜色只绕 **半圈**，而且在**负实轴**上撕开一道**分支切**：
    ///     同一条轴的两侧颜色不同（arg 从 +π 跳到 -π，开方后是 +π/2 与 -π/2）
    ///
    /// 幂次表用「分子/分母」表示：1/1、1/2、2/1、3/1、4/1。
    /// 默认取第 2 项（1/2 = √z）—— 这是最值得先看见的那一件。
    public static readonly int[] ComplexPowNumerators = { 1, 1, 2, 3, 4 };
    public static readonly int[] ComplexPowDenominators = { 1, 2, 1, 1, 1 };
    public const int ComplexPowerDefault = 2;   // 表的第几项（1 基，2 = √z）

    public KeyCode complexCycleKey = KeyCode.Q;
    /// 当前是幂次表里的第几项（1 基）。真身只在这里，函数与贴图都从它派生。
    public int complexPower = ComplexPowerDefault;
    /// 展品的函数：z^(num/den)。幂函数本体在 **ComplexColor.PowFraction**
    /// （纯数学、可在引擎外被测），这里只是接成委托，好让它运行时能变。
    public System.Func<Complex, Complex> ComplexExhibitFn
    {
        get
        {
            int idx = Mathf.Clamp(complexPower, 1, ComplexPowNumerators.Length) - 1;
            return ComplexColor.PowFractionFunc(ComplexPowNumerators[idx], ComplexPowDenominators[idx]);
        }
    }
    /// 贴图缓存：每个幂次一张，按需生成（第一次切换付一次 ~40ms，之后瞬切）
    Texture2D[] complexTexCache;
    Material complexPanelMat;
    Material complexFloorMat;
    /// 定义域边长（米）与贴图像素（越大越细腻；Awake 里只算一次，测试里有耗时数字）
    public const float ComplexMapSize = 5.2f;
    public const int ComplexMapPixels = 512;
    /// 图版与地砖的自发光强度（0 = 只吃环境光）。这一项是给 foilo 调"亮不亮"的旋钮。
    public float complexMapGlow = 0.85f;

    /// 数学区原点与四个展位的 X 坐标 —— 唯一真相：
    /// 地皮、展位台子、摆在台子上的展品都从这里取，免得三处各写一份坐标、改一处忘两处。
    public static readonly Vector3 MathDistrictOrigin = new Vector3(0f, 0f, -46f);
    public static readonly float[] MathSlotX = { -11.25f, -3.75f, 3.75f, 11.25f };
    public const float MathSlotLocalZ = -6f;
    public const float MathSlotTopY = 0.95f;   // 展位台面高度（台子本身见 BuildMathDistrict）

    /// 大鱼台词（顺便当展品导览）
    public static readonly string[] BigLines =
    {
        "我是大肥鱼。那条小鱼是我妹妹，她跟得慢，你别笑她。",
        "前面那个曲面是 z 等于 sin(r) 除以 r —— 中间那根尖峰，是 r 趋近 0 时它自己冒出来的。",
        "右边那条带子只有一个面。你走一整圈回到起点，会发现自己上下翻了，却没跨过任何边缘。",
        "再往前有个黑洞。它不咬人，只是把光拦住了。",
        "按 R 可以让我停下来，停在哪里都行 —— 你回来的时候我还在。",
    };

    /// 小鱼台词
    public static readonly string[] SmallLines =
    {
        "……姐姐让我跟着你。",
        "那个圆圆的洞，掉进去会到哪里呀？",
        "你走快了我就追不上啦，等等我嘛。",
        "姐姐懂好多数学，我只会跟着她。",
    };

    void Awake()
    {
        // 内容全部由代码定义，场景只当容器 —— 所以每次开始运行都清掉旧内容重建。
        // 这样改了代码（哪怕只是给某件展品加了个台子）也不必手动重新生成场景。
        // 踩过的坑：以前是"只补缺的东西"，于是对已有展品的改动永远不会生效。
        ClearGenerated();
        Build();
        SetComplexPower(complexPower);   // 展品建好后按当前幂次贴一次 + 写 HUD 小字
    }

    /// 清掉本节点下由代码生成的子物体（不动场景里手放的 Player 等）
    void ClearGenerated()
    {
        for (int i = transform.childCount - 1; i >= 0; i--)
        {
            var child = transform.GetChild(i).gameObject;
            if (Application.isPlaying) Destroy(child); else DestroyImmediate(child);
        }
    }

    /// 只做一件事：按 Q 换幂次。
    /// 不在这里做别的逻辑 —— 生成全在 Awake，运行时只换"函数 + 贴图"。
    void Update()
    {
        if (complexCycleKey != KeyCode.None && Input.GetKeyDown(complexCycleKey))
            CycleComplexPower();
    }

    /// 幂次表里往后走一项，走到头回到第一项。
    public void CycleComplexPower()
    {
        int next = complexPower % ComplexPowNumerators.Length + 1;
        SetComplexPower(next);
    }

    /// 换幂次：重算/取缓存贴图，同时更新图版与地砖（两处共用同一张，永远同步）。
    public void SetComplexPower(int item)
    {
        complexPower = Mathf.Clamp(item, 1, ComplexPowNumerators.Length);
        if (complexTexCache == null) return;   // 还没生成过展品（编辑器里没 Build）
        Texture2D tex = ComplexTextureFor(complexPower);
        if (complexPanelMat != null) MaterialKit.SetMainTexture(complexPanelMat, tex, 1f);
        if (complexFloorMat != null) MaterialKit.SetMainTexture(complexFloorMat, tex, 1f);
        if (complexPanelMat != null) MaterialKit.SetEmissionTexture(complexPanelMat, tex, complexMapGlow);
        if (complexFloorMat != null) MaterialKit.SetEmissionTexture(complexFloorMat, tex, complexMapGlow);
        UpdateComplexHud();
    }

    /// 幂次表第 item 项对应的贴图；缓存里没有就现算一张（并缓存，下次瞬切）。
    Texture2D ComplexTextureFor(int item)
    {
        int idx = Mathf.Clamp(item, 1, ComplexPowNumerators.Length);
        if (complexTexCache[idx] == null)
        {
            int num = ComplexPowNumerators[idx - 1];
            int den = ComplexPowDenominators[idx - 1];
            complexTexCache[idx] = MakeComplexTexture(
                ComplexColor.PowFractionFunc(num, den), ComplexMapSize, ComplexMapPixels);
        }
        return complexTexCache[idx];
    }

    /// 展品当前的幂次写法（给 HUD / 讲解用）：1/1 写 "z"，1/2 写 "z^(1/2)"，其余写 "z^n"
    public string ComplexPowerLabel()
    {
        int idx = Mathf.Clamp(complexPower, 1, ComplexPowNumerators.Length) - 1;
        int num = ComplexPowNumerators[idx], den = ComplexPowDenominators[idx];
        if (den == 1) return num == 1 ? "z" : "z^" + num;
        return "z^(" + num + "/" + den + ")";
    }

    /// 屏幕上的小字：当前函数 + 怎么换 + 这次该看什么。给 SpeedHud 显示。
    void UpdateComplexHud()
    {
        int idx = Mathf.Clamp(complexPower, 1, ComplexPowNumerators.Length) - 1;
        bool half = ComplexPowDenominators[idx] != 1;
        SpeedHud.ComplexStatus = string.Format(
            "复变展品：f(z) = {0}   —— 按 {1} 换（z → √z → z² → z³ → z⁴）· {2}",
            ComplexPowerLabel(), complexCycleKey,
            half
                ? "√z：绕原点只转半圈，而且负实轴上有道分支切 —— 那条缝两侧颜色不一样"
                : string.Format("绕原点走一圈，颜色绕 {0} 圈", ComplexPowNumerators[idx]));
    }

    public void Build()
    {
        if (transform.childCount > 0) ClearGenerated();   // 保证与代码一致，不会叠加
        if (buildGround) BuildGround();
        if (buildLights) BuildLights();
        if (spawnExhibits) BuildExhibits();
        if (buildDistricts) BuildMathDistrict();
        if (buildMascots) BuildMascots();
        if (buildCompanion) BuildCompanion();
        if (buildHud) BuildHud();
    }

    /// 运行时补齐：缺什么建什么。改了代码不用重新生成场景。
    public void EnsureRuntimeParts()
    {
        if (buildGround && transform.Find("Ground") == null) BuildGround();
        if (buildLights && transform.Find("Sun") == null) BuildLights();
        if (spawnExhibits && transform.Find("Exhibit_Surface") == null) BuildExhibits();

        var mascots = Object.FindObjectsByType<MascotFollow>(FindObjectsSortMode.None);
        if (mascots.Length == 0)
        {
            if (buildMascots) BuildMascots();
        }
        else
        {
            foreach (var m in mascots)
            {
                if (m == null) continue;
                if (m.GetComponent<MascotSwim>() == null) m.gameObject.AddComponent<MascotSwim>();
                var d = m.GetComponent<MascotDialogue>();
                if (d == null) d = m.gameObject.AddComponent<MascotDialogue>();
                if (d.lines == null || d.lines.Length == 0)
                    d.lines = m.name.ToLower().Contains("small") ? SmallLines : BigLines;
            }
        }

        if (buildCompanion && Object.FindFirstObjectByType<CompanionControl>() == null) BuildCompanion();
        if (buildHud && Object.FindFirstObjectByType<SpeedHud>() == null) BuildHud();
        if (transform.Find("Ground") != null && transform.Find("Sun") == null && buildLights) BuildLights();
    }

    void BuildGround()
    {
        var ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
        ground.name = "Ground";
        ground.transform.SetParent(transform, false);
        ground.transform.localScale = new Vector3(groundSize / 10f, 1f, groundSize / 10f);

        var mat = MaterialKit.MakeMaterial(new Color(0.075f, 0.105f, 0.185f), 0.12f);
        var tex = MaterialKit.MakeGridTexture(256, gridCellsPerTile);
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

    // 注意：这里必须"无条件构建"。
    // 曾经写成按名字检查是否已存在，但 Unity 的 Destroy 延迟到帧末执行 ——
    // 清空后重建时 Find 还能找到那些"待销毁"的旧展品，于是跳过重建，
    // 旧的一销毁，展品就全没了（而吉祥物那部分没有检查，反而变成两份）。
    void BuildExhibits()
    {
        BuildSurface();
        BuildDisplayMobius();
        BuildWalkableMobius();
        BuildBlackHole();
        BuildComplexColorMap();
    }

    /// 感知框：平时几乎隐形，人一进来就发亮
    void BuildZone(string exhibitName, Vector3 center, Vector3 half)
    {
        var root = new GameObject("Zone_" + exhibitName);
        root.transform.SetParent(transform, false);
        root.transform.localPosition = center;
        var z = root.AddComponent<ExhibitZone>();
        z.Setup(exhibitName, half);

        var mat = MaterialKit.MakeMaterial(new Color(0.45f, 0.85f, 1f, 0.08f), 0.6f, 0f);
        if (mat.HasProperty("_Surface")) mat.SetFloat("_Surface", 1f);
        if (mat.HasProperty("_Mode")) mat.SetFloat("_Mode", 3f);

        float hx = half.x, hz = half.z, tt = 0.18f;
        MakeBar(root.transform, mat, new Vector3(0f, -half.y, -hz), new Vector3(hx * 2f, tt, tt));
        MakeBar(root.transform, mat, new Vector3(0f, -half.y, hz), new Vector3(hx * 2f, tt, tt));
        MakeBar(root.transform, mat, new Vector3(-hx, -half.y, 0f), new Vector3(tt, tt, hz * 2f));
        MakeBar(root.transform, mat, new Vector3(hx, -half.y, 0f), new Vector3(tt, tt, hz * 2f));
        MakeBar(root.transform, mat, new Vector3(-hx, half.y, -hz), Vector3.one * tt);
        MakeBar(root.transform, mat, new Vector3(hx, half.y, -hz), Vector3.one * tt);
        MakeBar(root.transform, mat, new Vector3(-hx, half.y, hz), Vector3.one * tt);
        MakeBar(root.transform, mat, new Vector3(hx, half.y, hz), Vector3.one * tt);
    }

    static void MakeBar(Transform parent, Material mat, Vector3 pos, Vector3 scale)
    {
        var b = GameObject.CreatePrimitive(PrimitiveType.Cube);
        b.name = "GlowBar";
        b.transform.SetParent(parent, false);
        b.transform.localPosition = pos;
        b.transform.localScale = scale;
        var col = b.GetComponent<Collider>();
        if (col != null) { if (Application.isPlaying) Destroy(col); else DestroyImmediate(col); }
        b.GetComponent<MeshRenderer>().sharedMaterial = mat;
    }

    void BuildSurface()
    {
        var surface = new GameObject("Exhibit_Surface");
        surface.transform.SetParent(transform, false);
        surface.transform.localPosition = new Vector3(0f, 0f, -20f);
        surface.AddComponent<ParametricSurface>().Rebuild();
        surface.GetComponent<MeshRenderer>().sharedMaterial =
            MaterialKit.MakeMaterial(new Color(0.29f, 0.64f, 1f), 0.35f, 0.15f);
        BuildZone("Exhibit_Surface", new Vector3(0f, 5f, -20f), new Vector3(13f, 5f, 13f));
    }

    void BuildDisplayMobius()
    {
        var mobius = new GameObject("Exhibit_Mobius");
        mobius.transform.SetParent(transform, false);
        mobius.transform.localPosition = new Vector3(24f, 3.4f, 6f);
        mobius.AddComponent<MobiusStrip>().Rebuild();
        mobius.GetComponent<MeshRenderer>().sharedMaterial =
            MaterialKit.MakeMaterial(new Color(0.55f, 0.88f, 1f), 0.30f, 0.40f);
        BuildZone("Exhibit_Mobius", new Vector3(24f, 4.4f, 6f), new Vector3(7f, 4f, 7f));
    }

    void BuildWalkableMobius()
    {
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
        BuildZone("Exhibit_WalkableMobius", new Vector3(0f, 6f, 46f), new Vector3(13f, 4f, 13f));
    }

    void BuildBlackHole()
    {
        var bh = new GameObject("Exhibit_BlackHole");
        bh.transform.SetParent(transform, false);
        bh.transform.localPosition = new Vector3(-46f, 8.5f, 34f);   // 降到抬头能看清的高度

        // 观景台 + 方框围栏（看得见的"框"），正面留 8 米入口
        var deck = GameObject.CreatePrimitive(PrimitiveType.Cube);
        deck.name = "ObservationDeck";
        deck.transform.SetParent(bh.transform, false);
        deck.transform.localPosition = new Vector3(0f, -8.3f, 0f);
        deck.transform.localScale = new Vector3(26f, 0.4f, 26f);
        deck.GetComponent<MeshRenderer>().sharedMaterial =
            MaterialKit.MakeMaterial(new Color(0.13f, 0.17f, 0.26f), 0.15f);

        MakeRail(bh.transform, new Vector3(0f, -7.5f, -12.6f), new Vector3(26f, 1.2f, 0.4f));
        MakeRail(bh.transform, new Vector3(-12.6f, -7.5f, 0f), new Vector3(0.4f, 1.2f, 26f));
        MakeRail(bh.transform, new Vector3(12.6f, -7.5f, 0f), new Vector3(0.4f, 1.2f, 26f));
        MakeRail(bh.transform, new Vector3(-9f, -7.5f, 12.6f), new Vector3(8f, 1.2f, 0.4f));
        MakeRail(bh.transform, new Vector3(9f, -7.5f, 12.6f), new Vector3(8f, 1.2f, 0.4f));
        BuildZone("Exhibit_BlackHole", new Vector3(-46f, 1.5f, 34f), new Vector3(13f, 8f, 13f));

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
    }

    /// 沿带子中心线摆一圈路标（颜色绕色相环变化）
    static void MakeRail(Transform parent, Vector3 localPos, Vector3 localScale)
    {
        var w = GameObject.CreatePrimitive(PrimitiveType.Cube);
        w.name = "Railing";
        w.transform.SetParent(parent, false);
        w.transform.localPosition = localPos;
        w.transform.localScale = localScale;
        w.GetComponent<MeshRenderer>().sharedMaterial =
            MaterialKit.MakeMaterial(new Color(0.42f, 0.62f, 0.92f), 0.3f, 0.1f);
    }

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

            var col = post.GetComponent<Collider>();
            if (col != null) { if (Application.isPlaying) Destroy(col); else DestroyImmediate(col); }

            post.GetComponent<MeshRenderer>().sharedMaterial =
                MaterialKit.MakeMaterial(Color.HSVToRGB(i / (float)markerCount, 0.55f, 0.95f), 0.3f);
        }
    }

    /// 两只吉祥物：大鱼跟着玩家，小鱼跟着大鱼（妹妹跟着姐姐）
    void BuildMascots()
    {
        var big = MascotBody.Create("Mascot_BigFish", transform, 1.25f,
            new Color(0.30f, 0.56f, 0.92f), new Color(0.90f, 0.95f, 1f));
        big.transform.localPosition = new Vector3(0f, 2.6f, 40f);
        var bigFollow = big.AddComponent<MascotFollow>();
        bigFollow.followDistance = 5.5f;
        bigFollow.followHeight = 1.3f;   // 与主角相近高度，不再飘在天上
        var bigSwim = big.AddComponent<MascotSwim>();
        bigSwim.tailFrequency = 1.3f;
        bigSwim.finFrequency = 1.3f;
        var bigTalk = big.AddComponent<MascotDialogue>();
        bigTalk.lines = BigLines;

        var small = MascotBody.Create("Mascot_SmallFish", transform, 0.62f,
            new Color(0.58f, 0.82f, 1f), new Color(1f, 0.97f, 0.99f));
        small.transform.localPosition = new Vector3(1.4f, 2.4f, 37f);
        var smallFollow = small.AddComponent<MascotFollow>();
        smallFollow.target = big.transform;      // 妹妹跟着姐姐
        smallFollow.followDistance = 3.0f;
        smallFollow.followHeight = -0.2f;
        smallFollow.followLerp = 1.6f;
        smallFollow.bobFrequency = 1.3f;
        var smallSwim = small.AddComponent<MascotSwim>();
        smallSwim.tailFrequency = 1.9f;
        smallSwim.finFrequency = 1.9f;
        smallSwim.spoutInterval = 5f;
        var smallTalk = small.AddComponent<MascotDialogue>();
        smallTalk.lines = SmallLines;
    }

    /// 同伴控制节点（E 说话 / R 停下继续）
    void BuildCompanion()
    {
        var go = new GameObject("Companion");
        go.transform.SetParent(transform, false);
        go.AddComponent<CompanionControl>();
    }

    /// 数学区 Slot_1 的第一件新展品：**复变函数的颜色映射**。
    ///
    /// 颜色怎么来的：色相 = f(z) 的辐角、明度 = |f(z)| 的模（详见 ComplexColor，那是唯一真相）。
    /// f 取 z²，所以绕原点走一圈，颜色会绕**两圈** —— 这正是它最值得亲眼看一次的地方。
    ///
    /// 两处共用同一张贴图（同一个函数、同一条生成路径）：
    ///   ① 竖直图版：面朝入口，+X 是实部、+Y 是虚部，正好是高斯平面的朝向
    ///   ② 可走彩色地砖：走到数学区中间那块地上，颜色跟着脚步变 ——
    ///      这是这件展品的**体感锚点**：不用先听懂 arg 和 |f|，走一圈就知道了
    void BuildComplexColorMap()
    {
        // 幂次贴图缓存：4 张按需生成（第一次按 Q 会付一次 ~40ms，之后瞬切）
        if (complexTexCache == null)
            complexTexCache = new Texture2D[ComplexPowNumerators.Length + 1];
        // 重新生成世界时把老贴图丢掉（编辑里反复 Play 不会堆垃圾）
        for (int i = 0; i < complexTexCache.Length; i++)
        {
            if (complexTexCache[i] != null) { Destroy(complexTexCache[i]); complexTexCache[i] = null; }
        }
        Texture2D tex = ComplexTextureFor(complexPower);

        // ---- ① 竖直图版：摆在 Slot_1 的台面上 ----
        var root = new GameObject("Exhibit_ComplexMap");
        root.transform.SetParent(transform, false);
        float sx = MathSlotX[0];
        float sy = MathSlotTopY + ComplexMapSize * 0.5f;
        float sz = MathDistrictOrigin.z + MathSlotLocalZ;
        root.transform.localPosition = new Vector3(sx, sy, sz);

        var panelMat = MaterialKit.MakeMaterial(Color.white, 0.12f, 0f);
        MaterialKit.SetMainTexture(panelMat, tex, 1f);
        MaterialKit.SetEmissionTexture(panelMat, tex, complexMapGlow);
        complexPanelMat = panelMat;   // 记下来：按 Q 换幂次时要换这张贴图
        var panel = MeshUtil.Spawn("ComplexPanel", MeshMath.PanelXY(ComplexMapSize, 96), panelMat, root.transform);
        // 没有这一步，整块面只会显示一个像素的颜色（MakeMesh 不生成 UV）
        MeshUtil.SetPlanarUVs(panel.GetComponent<MeshFilter>().sharedMesh, 0, 1);

        // 一圈细边框：让它看起来是"一件展品"，而不是一张飘着的纸
        var frameMat = MaterialKit.MakeMaterial(new Color(0.30f, 0.55f, 0.85f), 0.45f, 0.2f);
        float h = ComplexMapSize * 0.5f, bar = 0.12f;
        MakeBar(root.transform, frameMat, new Vector3(0f, h, 0f), new Vector3(ComplexMapSize + bar * 2f, bar, bar));
        MakeBar(root.transform, frameMat, new Vector3(0f, -h, 0f), new Vector3(ComplexMapSize + bar * 2f, bar, bar));
        MakeBar(root.transform, frameMat, new Vector3(-h, 0f, 0f), new Vector3(bar, ComplexMapSize, bar));
        MakeBar(root.transform, frameMat, new Vector3(h, 0f, 0f), new Vector3(bar, ComplexMapSize, bar));

        BuildZone("Exhibit_ComplexMap", new Vector3(sx, sy, sz), new Vector3(3.6f, 3.4f, 3.6f));

        // ---- ② 可走彩色地砖：数学区中间的空地 ----
        // 抬到 0.45（地皮顶面 0.40）—— 高 5 厘米是为了不跟地皮 Z 打架。
        // 挂 MeshCollider，人就能站上去（和"可走莫比乌斯带"同一套路）。
        var floorMat = MaterialKit.MakeMaterial(Color.white, 0.10f, 0f);
        MaterialKit.SetMainTexture(floorMat, tex, 1f);
        MaterialKit.SetEmissionTexture(floorMat, tex, complexMapGlow);
        complexFloorMat = floorMat;   // 同上：两处共用一张贴图，换幂次必须一起换
        var floor = MeshUtil.Spawn("Walk_ComplexPlane",
            MeshMath.ParametricSurface((x, y) => 0f, 13f, 128), floorMat, transform);
        floor.transform.localPosition = new Vector3(MathDistrictOrigin.x, 0.45f, -40f);
        var floorMesh = floor.GetComponent<MeshFilter>().sharedMesh;
        MeshUtil.SetPlanarUVs(floorMesh, 0, 2);
        floor.AddComponent<MeshCollider>().sharedMesh = floorMesh;

        BuildZone("Exhibit_ComplexMap", new Vector3(MathDistrictOrigin.x, 1.5f, -40f), new Vector3(6.8f, 3f, 6.8f));

        // 传送点（按 4 到达）：站在彩色地砖当中、面朝 Slot_1 的图版。
        // 这是个转过 180° 的空物体 —— SurfaceWalker 按"目标自己朝哪儿"决定落地朝向，
        // 这样落地第一眼就是图版，而不是背对着它。（数学区离出生点 92 米，走过来的话太久了。）
        var teleport = new GameObject("Teleport_Math");
        teleport.transform.SetParent(transform, false);
        teleport.transform.localPosition = new Vector3(MathDistrictOrigin.x, 0.6f, -40f);
        teleport.transform.localRotation = Quaternion.Euler(0f, 180f, 0f);
    }

    /// 复变函数的颜色 → 一张贴图。
    /// 取色与写入顺序都走 ComplexColor.BuildGrid：于是"图上哪里是红"和测试断言的是同一件事，
    /// 不会出现"函数对了但图上下颠倒"这种只能靠肉眼发现的问题。
    static Texture2D MakeComplexTexture(System.Func<Complex, Complex> f, float size, int pixels)
    {
        float[] rgb = ComplexColor.BuildGrid(f, size, pixels);
        var cols = new Color32[pixels * pixels];
        for (int i = 0; i < cols.Length; i++)
        {
            cols[i] = new Color32(
                (byte)Mathf.Clamp(rgb[i * 3] * 255f + 0.5f, 0f, 255f),
                (byte)Mathf.Clamp(rgb[i * 3 + 1] * 255f + 0.5f, 0f, 255f),
                (byte)Mathf.Clamp(rgb[i * 3 + 2] * 255f + 0.5f, 0f, 255f),
                255);
        }
        var tex = new Texture2D(pixels, pixels, TextureFormat.RGB24, true);
        tex.SetPixels32(cols);
        tex.Apply(true);
        tex.wrapMode = TextureWrapMode.Clamp;   // 不重复：否则边缘的颜色会串到对面去
        tex.filterMode = FilterMode.Bilinear;
        return tex;
    }

    /// 数学区：一块地皮 + 入口框 + 四个空展位（都带感知框，走近会亮）
    /// 以后加一门学科 = 再建一块这样的地 + 往格位上摆展品。
    void BuildMathDistrict()
    {
        var root = new GameObject("District_Math");
        root.transform.SetParent(transform, false);
        root.transform.localPosition = MathDistrictOrigin;

        // 地皮
        var pad = GameObject.CreatePrimitive(PrimitiveType.Cube);
        pad.name = "Pad";
        pad.transform.SetParent(root.transform, false);
        pad.transform.localPosition = new Vector3(0f, 0.2f, 0f);
        pad.transform.localScale = new Vector3(34f, 0.4f, 26f);
        pad.GetComponent<MeshRenderer>().sharedMaterial =
            MaterialKit.MakeMaterial(new Color(0.11f, 0.15f, 0.24f), 0.15f);

        // 入口框（四根立柱 + 顶横梁），走近会亮
        var frameMat = MaterialKit.MakeMaterial(new Color(0.35f, 0.75f, 1f), 0.55f, 0.1f);
        MakeBar(root.transform, frameMat, new Vector3(-7f, 3f, 13.2f), new Vector3(0.35f, 6f, 0.35f));
        MakeBar(root.transform, frameMat, new Vector3(7f, 3f, 13.2f), new Vector3(0.35f, 6f, 0.35f));
        MakeBar(root.transform, frameMat, new Vector3(0f, 6f, 13.2f), new Vector3(14.4f, 0.4f, 0.4f));
        BuildZone("MathDistrict", new Vector3(0f, 2.5f, -32.8f), new Vector3(17f, 5f, 13f));

        // 四个空展位：小台子 + 各自感知框
        for (int i = 0; i < 4; i++)
        {
            float x = MathSlotX[i];
            var slot = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            slot.name = "Slot_" + (i + 1);
            slot.transform.SetParent(root.transform, false);
            slot.transform.localPosition = new Vector3(x, 0.7f, MathSlotLocalZ);
            slot.transform.localScale = new Vector3(2.2f, 0.25f, 2.2f);
            slot.GetComponent<MeshRenderer>().sharedMaterial =
                MaterialKit.MakeMaterial(new Color(0.22f, 0.30f, 0.45f), 0.3f);
            BuildZone("Slot_" + (i + 1), root.transform.localPosition + new Vector3(x, 2.5f, MathSlotLocalZ), new Vector3(3.4f, 3f, 3.4f));
        }
    }

    void BuildHud()
    {
        var hud = new GameObject("HUD");
        hud.transform.SetParent(transform, false);
        hud.AddComponent<SpeedHud>();
    }
}