using UnityEngine;

/// 能在任意曲面上行走的第一人称控制器（马里奥银河那种）。
///
/// 核心：这里没有"世界坐标的下"。重力方向是「当前脚下曲面的法线反方向」，
/// 相机的上方向也等于法线。于是——走莫比乌斯带绕一整圈后，你会发现自己
/// 从"背面"回来了：没跨过任何边缘，但上下已经翻转 180°。
/// （这个 180° 是几何本身的性质，见 tools/meshmath-test 里的不变量断言。）
public class SurfaceWalker : MonoBehaviour
{
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

    [Header("视角规格（参照 VRChat 的视高概念：小 / 矮 / 中 / 高）")]
    public string[] presetNames = { "小（萝莉）", "矮", "中", "高" };
    public float[] presetEyeHeights = { 1.05f, 1.35f, 1.62f, 1.85f };
    public float[] presetNearClips = { 0.025f, 0.035f, 0.05f, 0.07f };
    public int presetIndex = 2;
    public float minEyeHeight = 0.5f;    // 视高下限
    public float maxEyeHeight = 2.2f;    // 视高上限（"高视角"的限制）
    public KeyCode cyclePresetKey = KeyCode.V;

    [Header("体感反馈（VR 里建议关掉头部起伏，容易晕）")]
    public bool enableHeadBob = true;
    public float bobAmplitude = 0.05f;
    public float bobFrequency = 8.5f;
    public bool enableRunFov = true;
    public float baseFov = 70f;
    public float runFov = 78f;

    [Header("传送（1/2/3）")]
    public Transform[] teleportTargets;

    Vector3 up = Vector3.up;
    Vector3 fwd = Vector3.forward;
    Vector3 velocity;
    float pitch;
    float bobPhase;
    float moving01;
    float playerHeight = 1.62f;       // 当前视高（由规格决定）
    bool airborne;
    bool grounded;
    Camera cam;

    void Awake()
    {
        cam = GetComponentInChildren<Camera>();
        // 单面网格也要能被射线打到背面，否则走到"另一面"会掉下去
        Physics.queriesHitBackfaces = true;
        ApplyPreset();
        if (lockCursor) { Cursor.lockState = CursorLockMode.Locked; Cursor.visible = false; }
    }

    public string CurrentPresetName
    {
        get
        {
            if (presetNames == null || presetNames.Length == 0) return "-";
            int i = Mathf.Clamp(presetIndex, 0, presetNames.Length - 1);
            return presetNames[i];
        }
    }

    public float CurrentEyeHeight => playerHeight;

    /// 应用当前视角规格：视高 + 近裁剪面
    public void ApplyPreset()
    {
        if (presetEyeHeights == null || presetEyeHeights.Length == 0) return;
        int i = Mathf.Clamp(presetIndex, 0, presetEyeHeights.Length - 1);
        playerHeight = Mathf.Clamp(presetEyeHeights[i], minEyeHeight, maxEyeHeight);
        if (cam != null && presetNearClips != null && presetNearClips.Length > i)
            cam.nearClipPlane = presetNearClips[i];
    }

    void Update()
    {
        // ---- 视角规格切换 ----
        if (Input.GetKeyDown(cyclePresetKey) && presetNames != null && presetNames.Length > 0)
        {
            presetIndex = (presetIndex + 1) % presetNames.Length;
            ApplyPreset();
        }

        // ---- 视角：左右绕"上"转，上下做俯仰 ----
        fwd = Quaternion.AngleAxis(Input.GetAxis("Mouse X") * mouseSensitivity, up) * fwd;
        pitch = Mathf.Clamp(pitch - Input.GetAxis("Mouse Y") * mouseSensitivity, -85f, 85f);

        // ---- 找脚下曲面 ----
        Vector3 origin = transform.position + up * 0.2f;
        grounded = Physics.Raycast(origin, -up, out RaycastHit hit,
                                   playerHeight + snapDistance, surfaceMask, QueryTriggerInteraction.Ignore);
        if (grounded)
        {
            Vector3 n = hit.normal;
            if (Vector3.Dot(n, up) < 0f) n = -n;         // 从背面打过来时法线翻向自己
            if (!airborne) up = Vector3.Slerp(up, n, Mathf.Clamp01(Time.deltaTime * 8f)).normalized;
        }

        // ---- 移动：切线平面内的位移（空中也能微调方向） ----
        fwd = Vector3.ProjectOnPlane(fwd, up);
        if (fwd.sqrMagnitude < 1e-6f) fwd = Vector3.ProjectOnPlane(Vector3.forward, up);
        if (fwd.sqrMagnitude < 1e-6f) fwd = Vector3.Cross(up, Vector3.right);
        fwd.Normalize();
        Vector3 right = Vector3.Cross(up, fwd);

        float speed = (Input.GetKey(KeyCode.LeftShift) || Input.GetKey(KeyCode.RightShift)) ? runSpeed : walkSpeed;
        Vector3 wish = (fwd * Input.GetAxisRaw("Vertical") + right * Input.GetAxisRaw("Horizontal")).normalized * speed;
        transform.position += wish * Time.deltaTime;

        // ---- 跳跃：贴着曲面时给一个沿法线的冲量 ----
        if (grounded && !airborne && Input.GetKeyDown(jumpKey))
        {
            airborne = true;
            velocity += up * jumpSpeed;
        }

        // ---- 重力：朝着曲面（-up）拉 ----
        velocity += -up * gravity * Time.deltaTime;
        transform.position += velocity * Time.deltaTime;

        // ---- 贴地 / 落地 ----
        Vector3 probe = transform.position + up * 0.2f;
        if (Physics.Raycast(probe, -up, out RaycastHit ground,
                            playerHeight + snapDistance, surfaceMask, QueryTriggerInteraction.Ignore))
        {
            Vector3 gn = ground.normal;
            if (Vector3.Dot(gn, up) < 0f) gn = -gn;
            float gap = Vector3.Dot(transform.position - ground.point, gn) - playerHeight;
            bool falling = Vector3.Dot(velocity, gn) <= 0.5f;

            if (!airborne || (falling && gap <= landSnapGap))
            {
                // 落地或贴地：吸附并把"撞向地面"的速度分量去掉
                transform.position = ground.point + gn * playerHeight;
                velocity = Vector3.ProjectOnPlane(velocity, gn);
                airborne = false;
                up = Vector3.Slerp(up, gn, Mathf.Clamp01(Time.deltaTime * 10f)).normalized;
            }
        }
        else if (velocity.magnitude > 60f)
        {
            velocity = velocity.normalized * 60f;   // 掉落限速，防止穿地
        }

        // ---- 姿态与体感 ----
        if (cam != null)
        {
            bool moving = wish.sqrMagnitude > 0.01f && !airborne;
            moving01 = Mathf.Lerp(moving01, moving ? 1f : 0f, Mathf.Clamp01(Time.deltaTime * 6f));
            bobPhase += Time.deltaTime * bobFrequency * moving01;

            cam.transform.rotation = Quaternion.LookRotation(fwd, up) * Quaternion.Euler(pitch, 0f, 0f);
            float bob = enableHeadBob ? Mathf.Sin(bobPhase) * bobAmplitude * moving01 : 0f;
            cam.transform.localPosition = new Vector3(0f, bob, 0f);
            if (enableRunFov)
            {
                bool running = (Input.GetKey(KeyCode.LeftShift) || Input.GetKey(KeyCode.RightShift)) && moving;
                cam.fieldOfView = Mathf.Lerp(cam.fieldOfView, running ? runFov : baseFov, Mathf.Clamp01(Time.deltaTime * 4f));
            }
        }

        // ---- 1/2/3 传送到展品 ----
        if (teleportTargets != null)
        {
            for (int i = 0; i < teleportTargets.Length && i < 3; i++)
            {
                if (Input.GetKeyDown(KeyCode.Alpha1 + i) && teleportTargets[i] != null)
                {
                    transform.position = teleportTargets[i].position + Vector3.up * (playerHeight + 0.3f);
                    up = Vector3.up;
                    velocity = Vector3.zero;
                    fwd = Vector3.forward;
                    pitch = -10f;
                    airborne = true;      // 让吸附逻辑把你放到展品脚下的地面上
                }
            }
        }
    }
}