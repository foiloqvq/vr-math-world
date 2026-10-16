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

        // 玩家：CharacterController + 第一人称 + 相机
        var player = new GameObject("Player");
        player.transform.position = new Vector3(0f, 1.7f, 12f);
        var cc = player.AddComponent<CharacterController>();
        cc.height = 1.7f; cc.radius = 0.3f; cc.center = new Vector3(0f, 0.85f, 0f);
        player.AddComponent<FirstPersonWalker>();

        var camGo = new GameObject("Camera");
        camGo.transform.SetParent(player.transform, false);
        camGo.transform.localPosition = new Vector3(0f, 0.75f, 0f);
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
}