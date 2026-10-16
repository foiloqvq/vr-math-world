using UnityEngine;

/// 材质与贴图的统一出口。
/// 不同渲染管线的属性名不同（URP: _BaseColor/_BaseMap，Built-in: _Color/_MainTex），
/// 集中在这里处理，免得别处写出"粉色材质"。
public static class MaterialKit
{
    public static Shader FindLit()
    {
        // 注意：这里用显式 if 而不是 ?? —— Unity 的 Object 重载了 ==，?? 会绕过它的空判断
        Shader sh = Shader.Find("Universal Render Pipeline/Lit");
        if (sh == null) sh = Shader.Find("Standard");
        if (sh == null) sh = Shader.Find("HDRP/Lit");
        if (sh == null) sh = Shader.Find("Sprites/Default");
        return sh;
    }

    public static Material MakeMaterial(Color color, float smoothness = 0.25f, float metallic = 0f)
    {
        var m = new Material(FindLit());
        SetColor(m, color);
        SetFirstFloat(m, new[] { "_Smoothness", "_Glossiness" }, smoothness);
        SetFirstFloat(m, new[] { "_Metallic" }, metallic);
        return m;
    }

    public static void SetColor(Material m, Color c)
    {
        if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", c);
        if (m.HasProperty("_Color")) m.SetColor("_Color", c);
    }

    static void SetFirstFloat(Material m, string[] names, float v)
    {
        foreach (string n in names) { if (m.HasProperty(n)) { m.SetFloat(n, v); return; } }
    }

    /// 程序化网格贴图（棋盘 + 细线）。
    /// 存在的理由：没有纹理和近物时，人眼没有运动视差，走起来"感觉没动"。
    public static Texture2D MakeGridTexture(int size = 256, int cells = 8,
                                           Color? bg = null, Color? line = null, Color? checker = null)
    {
        var tex = new Texture2D(size, size, TextureFormat.RGBA32, true);
        Color cBg = bg ?? new Color(0.07f, 0.10f, 0.18f);
        Color cLine = line ?? new Color(0.30f, 0.50f, 0.80f);
        Color cCheck = checker ?? new Color(0.105f, 0.145f, 0.245f);
        int cell = Mathf.Max(1, size / cells);
        for (int y = 0; y < size; y++)
        for (int x = 0; x < size; x++)
        {
            Color c = (((x / cell) + (y / cell)) % 2 == 0) ? cCheck : cBg;
            if (x % cell == 0 || y % cell == 0) c = cLine;
            tex.SetPixel(x, y, c);
        }
        tex.Apply();
        tex.wrapMode = TextureWrapMode.Repeat;
        tex.filterMode = FilterMode.Bilinear;
        return tex;
    }

    public static void SetMainTexture(Material m, Texture t, float tiling)
    {
        var scale = new Vector2(tiling, tiling);
        if (m.HasProperty("_BaseMap")) { m.SetTexture("_BaseMap", t); m.SetTextureScale("_BaseMap", scale); }
        if (m.HasProperty("_MainTex")) { m.SetTexture("_MainTex", t); m.SetTextureScale("_MainTex", scale); }
    }

    /// 让贴图自发光 —— 颜色映射那块图版当"屏幕"用：环境光偏暗时，纯反射的贴图会发灰。
    /// Standard 与 URP Lit 都是 _EmissionMap + _EmissionColor + _EMISSION 关键字，两家通用。
    /// intensity 放了个旋钮给 foilo 调"亮不亮"（那是他的活儿，不是我的）。
    public static void SetEmissionTexture(Material m, Texture t, float intensity = 0.85f)
    {
        if (m.HasProperty("_EmissionMap")) m.SetTexture("_EmissionMap", t);
        if (m.HasProperty("_EmissionColor")) m.SetColor("_EmissionColor", Color.white * Mathf.Max(0f, intensity));
        m.EnableKeyword("_EMISSION");
    }
}