using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

/// 命令行场景生成与构建（headless 可用）。
/// 用法：
///   Unity.exe -batchmode -quit -nographics -projectPath <工程> -executeMethod BuildScene.Generate
///   Unity.exe -batchmode -quit -nographics -projectPath <工程> -executeMethod BuildScene.BuildWindows
public static class BuildScene
{
    const string SceneDir = "Assets/Scenes";
    const string ScenePath = "Assets/Scenes/Sandbox.unity";

    [MenuItem("VRMathWorld/生成沙盒场景")]
    public static void Generate()
    {
        Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

        // 世界：地面 + 光照 + 展品
        var world = new GameObject("World");
        var exhibit = world.AddComponent<ExhibitScene>();
        exhibit.Build();                       // 编辑器里 Awake 不会跑，所以显式调用

        // 玩家：曲面行走控制器（能走上莫比乌斯带、能跳、能切视角规格）
        var player = new GameObject("Player");
        player.transform.position = new Vector3(9f, 7.7f, 46f);   // 站在可走莫比乌斯带上
        var walker = player.AddComponent<SurfaceWalker>();
        walker.teleportTargets = new[]
        {
            world.transform.Find("Exhibit_Surface"),
            world.transform.Find("Exhibit_WalkableMobius"),
            world.transform.Find("Exhibit_Mobius"),
            world.transform.Find("Teleport_Math"),        // 按 4：数学区（落在彩色地砖上，面朝图版）
        };
        // 注意：不要再挂 FirstPersonWalker / CharacterController ——
        // 那是"平面简化版"，没有跳跃、视角规格与曲面吸附。Verify() 会检查这一点。

        // 玩家身体：现在是我们的吉祥物（第三人称/正面视角能看见自己）。
        // 将来换成你的 VRM 化身即可 —— SurfaceWalker 会按视高自动缩放它。
        var body = MascotBody.Create("Body", player.transform, 0.78f,
            new Color(0.34f, 0.58f, 0.95f), new Color(0.92f, 0.96f, 1f));
        var bodySwim = body.AddComponent<MascotSwim>();
        bodySwim.spout = false;          // 身体不喷水（那是吉祥物的表演）
        bodySwim.tailAmplitude = 14f;

        var camGo = new GameObject("Camera");
        camGo.transform.SetParent(player.transform, false);
        camGo.transform.localPosition = new Vector3(0f, 0f, 0f);   // SurfaceWalker 直接控制相机朝向
        var cam = camGo.AddComponent<Camera>();
        cam.tag = "MainCamera";
        cam.nearClipPlane = 0.05f;
        cam.farClipPlane = 500f;
        camGo.AddComponent<AudioListener>();

        Directory.CreateDirectory(SceneDir);
        EditorSceneManager.MarkSceneDirty(scene);
        EditorSceneManager.SaveScene(scene, ScenePath);
        AssetDatabase.Refresh();
        Debug.Log("[BuildScene] 场景已生成: " + ScenePath);
    }

    public static void BuildWindows()
    {
        if (!File.Exists(ScenePath)) Generate();
        var opts = new BuildPlayerOptions
        {
            scenes = new[] { ScenePath },
            locationPathName = "Build/VRMathWorld.exe",
            target = BuildTarget.StandaloneWindows64,
            options = BuildOptions.None,
        };
        var report = BuildPipeline.BuildPlayer(opts);
        Debug.Log("[BuildScene] 构建结果: " + report.summary.result
                  + "  大小 " + (report.summary.totalSize / 1024 / 1024) + " MB");
        if (report.summary.result != UnityEditor.Build.Reporting.BuildResult.Succeeded)
            EditorApplication.Exit(1);
    }

    /// 打开生成的场景并核对内容（headless 自检用）
    public static void Verify()
    {
        if (!File.Exists(ScenePath)) { Debug.LogError("[BuildScene] scene missing: " + ScenePath); EditorApplication.Exit(1); return; }
        Scene scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
        int allObjects = 0, meshes = 0;
        foreach (GameObject go in Object.FindObjectsByType<GameObject>(FindObjectsSortMode.None))
        {
            allObjects++;
            var mf = go.GetComponent<MeshFilter>();
            if (mf != null && mf.sharedMesh != null) meshes++;
        }
        var world = GameObject.Find("World");
        var player = GameObject.Find("Player");
        var walker = Object.FindFirstObjectByType<SurfaceWalker>();
        var cam = Object.FindFirstObjectByType<Camera>();
        var stale = Object.FindFirstObjectByType<FirstPersonWalker>();
        var mascots = Object.FindObjectsByType<MascotFollow>(FindObjectsSortMode.None);
        var swims = Object.FindObjectsByType<MascotSwim>(FindObjectsSortMode.None);
        Debug.Log("[BuildScene] Verify: roots=" + scene.rootCount + " objects=" + allObjects + " meshes=" + meshes
                  + " World=" + (world != null) + " Player=" + (player != null)
                  + " SurfaceWalker=" + (walker != null) + " Camera=" + (cam != null)
                  + (walker != null ? (" preset=" + walker.CurrentPresetName + " eye=" + walker.CurrentEyeHeight.ToString("F2")) : "")
                  + " 吉祥物=" + mascots.Length + " 游泳=" + swims.Length);
        if (world == null || player == null || meshes < 2)
        { Debug.LogError("[BuildScene] Verify FAILED: 场景内容不全"); EditorApplication.Exit(1); return; }
        // 下面两条是专门防"控制器挂错"这类事故的：曾经因为字符串替换静默失败，
        // 场景里挂的一直是旧的 FirstPersonWalker，导致跳跃 / 视角规格 / 传送全部无效。
        if (walker == null)
        { Debug.LogError("[BuildScene] Verify FAILED: Player 上没有 SurfaceWalker"); EditorApplication.Exit(1); return; }
        if (stale != null)
        { Debug.LogError("[BuildScene] Verify FAILED: 场景里残留旧的 FirstPersonWalker"); EditorApplication.Exit(1); return; }
        if (mascots.Length < 2) { Debug.LogError("[BuildScene] Verify FAILED: 吉祥物不足两只"); EditorApplication.Exit(1); return; }
        if (swims.Length < 2) { Debug.LogError("[BuildScene] Verify FAILED: 吉祥物没挂 MascotSwim"); EditorApplication.Exit(1); return; }

        // 展品：复变函数的颜色映射（数学区 Slot_1 + 可走地砖）。
        // 这里特意把"顶点 / UV / 贴图"三个数字都报出来 —— 展品最容易静默漏掉或被建出来但没贴图，
        // 而"贴图没生效"（网格没有 UV）属于只能靠肉眼发现的 bug，值得用一条硬检查挡住。
        foreach (string name in new[] { "Exhibit_ComplexMap", "Walk_ComplexPlane", "Exhibit_RiemannSqrt", "Exhibit_Fractions" })
        {
            var go = world.transform.Find(name);
            if (go == null)
            { Debug.LogError("[BuildScene] Verify FAILED: 找不到展品 " + name); EditorApplication.Exit(1); return; }
            var mf = go.GetComponentInChildren<MeshFilter>();
            var mr = go.GetComponentInChildren<MeshRenderer>();
            var mesh = mf != null ? mf.sharedMesh : null;
            bool hasUv = mesh != null && mesh.uv.Length == mesh.vertexCount;
            bool hasTex = mr != null && mr.sharedMaterial != null && mr.sharedMaterial.mainTexture != null;
            Debug.Log("[BuildScene] Verify: " + name
                      + " 顶点=" + (mesh != null ? mesh.vertexCount.ToString() : "null")
                      + " UV=" + (mesh != null ? mesh.uv.Length.ToString() : "null")
                      + " 贴图=" + hasTex);
            if (mesh != null && !hasUv)
            { Debug.LogError("[BuildScene] Verify FAILED: " + name + " 的网格没有 UV（贴图只会显示一个像素的颜色）"); EditorApplication.Exit(1); return; }
        }
        // 斜坡展品：三条斜坡都必须有碰撞体（能走上去），数量也要对
        var slopes = world.transform.Find("Exhibit_Slopes");
        if (slopes == null)
        { Debug.LogError("[BuildScene] Verify FAILED: 找不到展品 Exhibit_Slopes"); EditorApplication.Exit(1); return; }
        int slopeCount = 0, slopeColliders = 0;
        foreach (Transform child in slopes)
        {
            slopeCount++;
            if (child.GetComponent<MeshCollider>() != null) slopeColliders++;
        }
        Debug.Log("[BuildScene] Verify: Exhibit_Slopes 斜坡=" + slopeCount + " 带碰撞=" + slopeColliders);
        if (slopeCount != 3 || slopeColliders != 3)
        { Debug.LogError("[BuildScene] Verify FAILED: 斜坡应为 3 条且都带 MeshCollider（否则走不上去）"); EditorApplication.Exit(1); return; }

        // 传送点：数学区（按 4）。落地朝向由 Teleport_Math 自己的 rotation 决定，
        // 所以这里把它的角度也报出来（180° = 面朝 Slot_1 的图版，而不是背对着）。
        // 同时也数一遍传送目标：这条专防"加了键但目标没挂上"（1/2/3 失灵过类似的坑）。
        var teleport = world.transform.Find("Teleport_Math");
        if (teleport == null)
        { Debug.LogError("[BuildScene] Verify FAILED: 找不到数学区传送点 Teleport_Math"); EditorApplication.Exit(1); return; }
        int targets = 0;
        if (walker.teleportTargets != null)
            foreach (var t in walker.teleportTargets) if (t != null) targets++;
        Debug.Log("[BuildScene] Verify: Teleport_Math 位置=" + teleport.position.ToString("F1")
                  + " 朝向=" + teleport.eulerAngles.y.ToString("F0") + "° · 传送目标=" + targets + " 个");
        if (targets < 4)
        { Debug.LogError("[BuildScene] Verify FAILED: 传送目标只有 " + targets + " 个（应为 4）"); EditorApplication.Exit(1); return; }

        Debug.Log("[BuildScene] Verify OK");
    }
}