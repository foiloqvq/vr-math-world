using UnityEngine;
using Vmw.Meshes;

/// 能在任意曲面上行走的第一人称/第三人称控制器。
///
/// 核心：这里没有"世界坐标的下"。重力方向是「当前脚下曲面的法线反方向」，
/// 相机的上方向也等于法线。于是走莫比乌斯带绕一整圈后，你会从"背面"回来：
/// 没跨过任何边缘，但上下已经翻转 180°（几何性质，见 tools/meshmath-test 的断言）。
///
/// 相机模式参考 Minecraft 的 F5：第一人称 → 第三人称（背后） → 第三人称（正面看自己）。
/// 相机距离随「视角规格」的视高缩放 —— 体型大，参考尺度就大。
public class SurfaceWalker : MonoBehaviour
{
    public enum CamMode { FirstPerson = 0, ThirdBack = 1, ThirdFront = 2 }

    [Header("移动")]
    public float walkSpeed = 6f;
    public float runSpeed = 12f;
    public float mouseSensitivity = 2.2f;

    [Header("跳跃")]
    public KeyCode jumpKey = KeyCode.Space;
    public float jumpSpeed = 7.5f;
    public float landSnapGap = 0.25f;

    [Header("曲面吸附")]
    public float gravity = 22f;
    public float snapDistance = 3f;
    public LayerMask surfaceMask = ~0;
    public bool lockCursor = true;

    [Header("视角规格（参照 VRChat：小 / 矮 / 中 / 高）")]
    public string[] presetNames = { "小（萝莉）", "矮", "中", "高" };
    public float[] presetEyeHeights = { 1.05f, 1.35f, 1.62f, 1.85f };
    public float[] presetNearClips = { 0.025f, 0.035f, 0.05f, 0.07f };
    public int presetIndex = 2;
    public float minEyeHeight = 0.5f;
    public float maxEyeHeight = 2.2f;
    public KeyCode cyclePresetKey = KeyCode.V;

    [Header("相机模式（F5 循环）")]
    public CamMode camMode = CamMode.FirstPerson;
    public KeyCode cycleCamModeKey = KeyCode.F5;
    public float thirdDistanceScale = 3.6f;    // 相机距离 = 视高 × 这个值
    public float thirdHeightScale = 0.35f;     // 相机抬高 = 视高 × 这个值
    public string bodyName = "Body";           // 身体节点名（第三人称时显示）

    [Header("体感反馈（VR 里建议关掉头部起伏）")]
    public bool enableHeadBob = true;
    public float bobAmplitude = 0.05f;
    public float bobFrequency = 8.5f;
    public bool enableRunFov = true;
    public float baseFov = 70f;
    public float runFov = 78f;

    [Header("传送（1/2/3/4）")]
    public Transform[] teleportTargets;
    // 场景内容每次运行都会重建，序列化的引用会指向已销毁对象 —— 所以按键时按名字重解析
    public string[] teleportTargetNames = { "Exhibit_Surface", "Exhibit_WalkableMobius", "Exhibit_Mobius", "Teleport_Math" };

    Vector3 up = Vector3.up;
    Vector3 fwd = Vector3.forward;
    Vector3 velocity;
    float pitch;
    float bobPhase;
    float moving01;
    float playerHeight = 1.62f;
    bool airborne;
    bool grounded;
    Camera cam;
    Transform body;

    void Awake()
    {
        cam = GetComponentInChildren<Camera>();
        body = transform.Find(bodyName);
        Physics.queriesHitBackfaces = true;   // 单面网格也要能打到背面，否则走到"另一面"会掉下去
        ApplyPreset();
        ApplyCamMode();
        if (lockCursor) { Cursor.lockState = CursorLockMode.Locked; Cursor.visible = false; }
    }

    public string CurrentPresetName
    {
        get
        {
            if (presetNames == null || presetNames.Length == 0) return "-";
            return presetNames[Mathf.Clamp(presetIndex, 0, presetNames.Length - 1)];
        }
    }

    public float CurrentEyeHeight => playerHeight;

    public string CurrentCamModeName
    {
        get
        {
            switch (camMode)
            {
                case CamMode.ThirdBack: return "第三人称·背后";
                case CamMode.ThirdFront: return "第三人称·正面";
                default: return "第一人称";
            }
        }
    }

    /// 应用视角规格：视高 + 近裁剪面 + 身体随视高缩放
    public void ApplyPreset()
    {
        if (presetEyeHeights != null && presetEyeHeights.Length > 0)
        {
            int i = Mathf.Clamp(presetIndex, 0, presetEyeHeights.Length - 1);
            playerHeight = Mathf.Clamp(presetEyeHeights[i], minEyeHeight, maxEyeHeight);
            if (cam != null && presetNearClips != null && presetNearClips.Length > i)
                cam.nearClipPlane = presetNearClips[i];
        }
        if (body != null)
        {
            float s = playerHeight / 1.62f;                       // 以"中"为基准缩放身体
            body.localScale = Vector3.one * s;
            body.localPosition = new Vector3(0f, -playerHeight * 0.45f, 0f);
        }
    }

    public void ApplyCamMode() { if (body != null) body.gameObject.SetActive(camMode != CamMode.FirstPerson); }

    /// 按名字重新解析传送目标（内容重建后老引用会失效）
    public void ResolveTeleportTargets()
    {
        var list = new System.Collections.Generic.List<Transform>();
        if (teleportTargetNames != null)
            foreach (string n in teleportTargetNames)
            {
                var go = GameObject.Find(n);
                if (go != null) list.Add(go.transform);
            }
        if (list.Count == 0 && teleportTargets != null)
            foreach (var tr in teleportTargets) if (tr != null) list.Add(tr);
        teleportTargets = list.ToArray();
    }

    void Update()
    {
        // ---- 视角规格 / 相机模式 切换 ----
        if (Input.GetKeyDown(cyclePresetKey) && presetNames != null && presetNames.Length > 0)
        {
            presetIndex = (presetIndex + 1) % presetNames.Length;
            ApplyPreset();
        }
        if (Input.GetKeyDown(cycleCamModeKey))
        {
            camMode = (CamMode)(((int)camMode + 1) % 3);
            ApplyCamMode();
        }

        // ---- 视角：左右绕"上"转，上下俯仰 ----
        fwd = Quaternion.AngleAxis(Input.GetAxis("Mouse X") * mouseSensitivity, up) * fwd;
        pitch = Mathf.Clamp(pitch - Input.GetAxis("Mouse Y") * mouseSensitivity, -85f, 85f);

        // ---- 找脚下曲面 ----
        Vector3 origin = transform.position + up * 0.2f;
        grounded = Physics.Raycast(origin, -up, out RaycastHit hit, playerHeight + snapDistance, surfaceMask, QueryTriggerInteraction.Ignore);
        if (grounded)
        {
            Vector3 n = hit.normal;
            if (Vector3.Dot(n, up) < 0f) n = -n;
            if (!airborne) up = Vector3.Slerp(up, n, Mathf.Clamp01(Time.deltaTime * 8f)).normalized;
        }

        // ---- 移动 ----
        fwd = Vector3.ProjectOnPlane(fwd, up);
        if (fwd.sqrMagnitude < 1e-6f) fwd = Vector3.ProjectOnPlane(Vector3.forward, up);
        if (fwd.sqrMagnitude < 1e-6f) fwd = Vector3.Cross(up, Vector3.right);
        fwd.Normalize();
        Vector3 right = Vector3.Cross(up, fwd);

        float speed = (Input.GetKey(KeyCode.LeftShift) || Input.GetKey(KeyCode.RightShift)) ? runSpeed : walkSpeed;
        Vector3 wish = (fwd * Input.GetAxisRaw("Vertical") + right * Input.GetAxisRaw("Horizontal")).normalized * speed;
        transform.position += wish * Time.deltaTime;

        // 关键：把朝向写进 transform。否则「跟在你身后」用的还是世界默认方向，
        // 吉祥物就会卡在固定方位、甚至挡在你面前。
        transform.rotation = Quaternion.LookRotation(fwd, up);

        // ---- 跳跃 ----
        if (grounded && !airborne && Input.GetKeyDown(jumpKey))
        {
            airborne = true;
            velocity += up * jumpSpeed;
        }

        // ---- 重力 ----
        velocity += -up * gravity * Time.deltaTime;
        transform.position += velocity * Time.deltaTime;

        // ---- 贴地 / 落地 ----
        Vector3 probe = transform.position + up * 0.2f;
        if (Physics.Raycast(probe, -up, out RaycastHit ground, playerHeight + snapDistance, surfaceMask, QueryTriggerInteraction.Ignore))
        {
            Vector3 gn = ground.normal;
            if (Vector3.Dot(gn, up) < 0f) gn = -gn;
            float gap = Vector3.Dot(transform.position - ground.point, gn) - playerHeight;
            bool falling = Vector3.Dot(velocity, gn) <= 0.5f;
            if (!airborne || (falling && gap <= landSnapGap))
            {
                // 只沿法线修正（切向绝不动），否则站在斜面上会自己滑走
                if (Mathf.Abs(gap) > 0.002f)
                {
                    SnapMath.CorrectAlongNormal(
                        transform.position.x, transform.position.y, transform.position.z,
                        ground.point.x, ground.point.y, ground.point.z,
                        gn.x, gn.y, gn.z, playerHeight,
                        out float cx, out float cy, out float cz);
                    transform.position = new Vector3(cx, cy, cz);
                }
                // 静摩擦：没有移动输入时把速度归零。
                // 否则重力每帧加上去、只投影掉法线分量，切向分量会残留并累积 ——
                // 站在斜面/曲面上就会慢慢往下滑（"站着不动自己移动"）。
                if (wish.sqrMagnitude < 0.01f && !Input.GetKey(jumpKey))
                    velocity = Vector3.zero;
                else
                    velocity = Vector3.ProjectOnPlane(velocity, gn);
                airborne = false;
                up = Vector3.Slerp(up, gn, Mathf.Clamp01(Time.deltaTime * 10f)).normalized;
            }
        }
        else
        {
            // 掉出曲面范围（例如从带子边缘走出去）：把"上"慢慢拉回世界正上方，
            // 否则会一直带着"倒挂"的取向，最后卡在地面底下
            up = Vector3.Slerp(up, Vector3.up, Mathf.Clamp01(Time.deltaTime * 1.5f)).normalized;
            if (velocity.magnitude > 60f) velocity = velocity.normalized * 60f;
        }

        // ---- 相机 ----
        if (cam != null)
        {
            bool moving = wish.sqrMagnitude > 0.01f && !airborne;
            moving01 = Mathf.Lerp(moving01, moving ? 1f : 0f, Mathf.Clamp01(Time.deltaTime * 6f));
            bobPhase += Time.deltaTime * bobFrequency * moving01;
            float bob = enableHeadBob ? Mathf.Sin(bobPhase) * bobAmplitude * moving01 : 0f;

            if (camMode == CamMode.FirstPerson)
            {
                cam.transform.localPosition = new Vector3(0f, bob, 0f);
                cam.transform.localRotation = Quaternion.Euler(pitch, 0f, 0f);
            }
            else
            {
                // 距离与抬高都随视高缩放：体型多大，参考尺度就多大
                float dist = playerHeight * thirdDistanceScale;
                float dy = playerHeight * thirdHeightScale;
                Vector3 back = (camMode == CamMode.ThirdBack) ? -fwd : fwd;
                Vector3 camPos = transform.position + back * dist + up * dy;
                Vector3 lookAt = transform.position + up * (playerHeight * 0.30f);
                cam.transform.position = camPos;
                cam.transform.rotation = Quaternion.LookRotation(lookAt - camPos, up);
            }

            if (enableRunFov)
            {
                bool running = (Input.GetKey(KeyCode.LeftShift) || Input.GetKey(KeyCode.RightShift)) && moving;
                cam.fieldOfView = Mathf.Lerp(cam.fieldOfView, running ? runFov : baseFov, Mathf.Clamp01(Time.deltaTime * 4f));
            }
        }

        // ---- 1/2/3/4 传送 ----
        bool k1 = Input.GetKeyDown(KeyCode.Alpha1);
        bool k2 = Input.GetKeyDown(KeyCode.Alpha2);
        bool k3 = Input.GetKeyDown(KeyCode.Alpha3);
        bool k4 = Input.GetKeyDown(KeyCode.Alpha4);
        if (k1 || k2 || k3 || k4) ResolveTeleportTargets();

        if (teleportTargets != null)
        {
            for (int i = 0; i < teleportTargets.Length && i < 4; i++)
            {
                bool pressed = (i == 0 && k1) || (i == 1 && k2) || (i == 2 && k3) || (i == 3 && k4);
                if (pressed && teleportTargets[i] != null)
                {
                    transform.position = teleportTargets[i].position + Vector3.up * (playerHeight + 0.3f);
                    up = Vector3.up;
                    velocity = Vector3.zero;
                    // 目标自己朝哪儿，落地就往哪儿看 —— 这样放个空物体转个身就能决定"到达时的第一眼"。
                    // （数学区的传送点是转过 180° 的，落地正好面朝 Slot_1 那块图版，而不是背对着它。）
                    fwd = teleportTargets[i].forward;
                    if (fwd.sqrMagnitude < 0.5f) fwd = Vector3.forward;
                    pitch = -10f;
                    airborne = true;
                }
            }
        }
    }
}