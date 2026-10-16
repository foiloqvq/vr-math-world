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
        };
        // 注意：不要再挂 FirstPersonWalker / CharacterController ——
        // 那是"平面简化版"，没有跳跃、视角规格与曲面吸附。Verify() 会检查这一点。

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
        Debug.Log("[BuildScene] Verify: roots=" + scene.rootCount + " objects=" + allObjects + " meshes=" + meshes
                  + " World=" + (world != null) + " Player=" + (player != null)
                  + " SurfaceWalker=" + (walker != null) + " Camera=" + (cam != null)
                  + (walker != null ? (" preset=" + walker.CurrentPresetName + " eye=" + walker.CurrentEyeHeight.ToString("F2")) : ""));
        if (world == null || player == null || meshes < 2)
        { Debug.LogError("[BuildScene] Verify FAILED: 场景内容不全"); EditorApplication.Exit(1); return; }
        // 下面两条是专门防"控制器挂错"这类事故的：曾经因为字符串替换静默失败，
        // 场景里挂的一直是旧的 FirstPersonWalker，导致跳跃 / 视角规格 / 传送全部无效。
        if (walker == null)
        { Debug.LogError("[BuildScene] Verify FAILED: Player 上没有 SurfaceWalker"); EditorApplication.Exit(1); return; }
        if (stale != null)
        { Debug.LogError("[BuildScene] Verify FAILED: 场景里残留旧的 FirstPersonWalker"); EditorApplication.Exit(1); return; }
        Debug.Log("[BuildScene] Verify OK");
    }}