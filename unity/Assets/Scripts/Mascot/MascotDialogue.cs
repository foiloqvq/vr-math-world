using System.Collections;
using UnityEngine;
using UnityEngine.Networking;

/// 对话与讲解：走近按 E。
/// - 展品旁边：念该展品的讲解（多句，按 E 逐句推进），并转头看向它
/// - 空地：说自己的固定台词
/// 语音走本机桥接（默认 http://127.0.0.1:7880）。服务不在也不影响功能 ——
/// 只显示字幕，并把错误显示出来。
public class MascotDialogue : MonoBehaviour
{
    [Header("闲聊台词（固定词，按顺序循环）")]
    [TextArea] public string[] lines;

    [Header("语音服务")]
    public string ttsUrl = "http://127.0.0.1:7880/api/v1/tts/tasks";
    public string textLang = "zh";
    public bool useTts = true;

    [Header("字幕")]
    public float minSubtitleSeconds = 2.5f;
    public float secondsPerChar = 0.18f;

    AudioSource src;
    MascotFollow follow;
    int lineIndex;
    string subtitle = "";
    float subtitleUntil;
    string lastError = "";
    bool speaking;

    string[] queue;
    int queueIndex;
    string queueExhibit;
    Transform lookTarget;

    [System.Serializable]
    class TtsRequest { public string text; public string text_lang; }

    public bool IsSpeaking => speaking;
    public string Subtitle => Time.time < subtitleUntil ? subtitle : "";
    public string LastError => lastError;

    void Awake()
    {
        src = gameObject.AddComponent<AudioSource>();
        src.spatialBlend = 1f;            // 3D 音源：声音从它所在位置传过来
        src.rolloffMode = AudioRolloffMode.Linear;
        src.minDistance = 2f;
        src.maxDistance = 40f;
        src.playOnAwake = false;
        follow = GetComponent<MascotFollow>();
    }

    void Update()
    {
        // 字幕结束后，把"看向展品"收回来（讲解时才有这个动作）
        if (follow != null && Time.time >= subtitleUntil && follow.lookAtOverride != null)
            follow.lookAtOverride = null;
    }

    /// 闲聊一句
    public void Speak()
    {
        if (lines == null || lines.Length == 0) return;
        queueExhibit = null;
        SpeakLine(lines[lineIndex % lines.Length]);
        lineIndex++;
    }

    /// 讲解某件展品（多句，连续按 E 逐句推进），并转头看向它
    public bool SpeakExhibit(string exhibitName, Transform exhibit)
    {
        var text = Narration.For(exhibitName);
        if (text.Length == 0) return false;
        if (queueExhibit != exhibitName) { queue = text; queueIndex = 0; queueExhibit = exhibitName; }
        if (queueIndex >= queue.Length) queueIndex = 0;      // 一轮念完，从头再来
        lookTarget = exhibit;
        SpeakLine(queue[queueIndex]);
        queueIndex++;
        return true;
    }

    void SpeakLine(string line)
    {
        subtitle = line;
        subtitleUntil = Time.time + Mathf.Max(minSubtitleSeconds, line.Length * secondsPerChar);
        if (follow != null) follow.lookAtOverride = lookTarget;   // 说话时看向展品
        if (useTts && !speaking) StartCoroutine(TtsRoutine(line));
    }

    IEnumerator TtsRoutine(string line)
    {
        speaking = true;
        string json = JsonUtility.ToJson(new TtsRequest { text = line, text_lang = textLang });
        var req = new UnityWebRequest(ttsUrl, "POST");
        req.uploadHandler = new UploadHandlerRaw(System.Text.Encoding.UTF8.GetBytes(json));
        var audio = new DownloadHandlerAudioClip(ttsUrl, AudioType.WAV);
        req.downloadHandler = audio;
        req.SetRequestHeader("Content-Type", "application/json");
        req.timeout = 180;

        yield return req.SendWebRequest();

        if (req.result == UnityWebRequest.Result.Success)
        {
            var clip = audio.audioClip;
            if (clip != null) { src.PlayOneShot(clip); lastError = ""; }
            else lastError = "返回的不是可播放音频";
        }
        else
        {
            lastError = "语音服务不可用：" + req.error;
            Debug.LogWarning("[MascotDialogue] " + lastError);
        }
        req.Dispose();
        speaking = false;
    }

    void OnGUI()
    {
        string text = Subtitle;
        if (string.IsNullOrEmpty(text)) return;

        float k = Mathf.Clamp(Screen.height / 1080f, 0.75f, 2f);
        var style = new GUIStyle(GUI.skin.label) { fontSize = Mathf.RoundToInt(16f * k), alignment = TextAnchor.MiddleCenter, wordWrap = true };
        style.normal.textColor = new Color(0.95f, 0.98f, 1f);
        var shadow = new GUIStyle(style);
        shadow.normal.textColor = new Color(0f, 0f, 0f, 0.75f);

        float w = Mathf.Min(Screen.width - 80f, 1000f);
        var rect = new Rect((Screen.width - w) * 0.5f, Screen.height - 210f, w, 96f);
        GUI.Label(new Rect(rect.x + 2f, rect.y + 2f, rect.width, rect.height), text, shadow);
        GUI.Label(rect, text, style);
    }
}