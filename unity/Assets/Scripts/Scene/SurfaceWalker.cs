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

    [Header("曲面吸附")]
    public float gravity = 22f;
    public float snapDistance = 3f;       // 射线找地面的距离，超出就坠落
    public float playerHeight = 1.7f;
    public LayerMask surfaceMask = ~0;
    public bool lockCursor = true;

    [Header("传送（1/2/3）")]
    public Transform[] teleportTargets;
    public float teleportDistance = 14f;

    Vector3 up = Vector3.up;              // 当前的"上"，会随曲面法线旋转
    Vector3 fwd = Vector3.forward;        // 当前的"前"，始终切于曲面
    Vector3 velocity;
    float pitch;
    Camera cam;

    void Awake()
    {
        cam = GetComponentInChildren<Camera>();
        // 单面网格也要能被射线打到背面，否则走到"另一面"会掉下去
        Physics.queriesHitBackfaces = true;
        if (lockCursor) { Cursor.lockState = CursorLockMode.Locked; Cursor.visible = false; }
    }

    void Update()
    {
        // ---- 视角：左右绕"上"转，上下做俯仰 ----
        fwd = Quaternion.AngleAxis(Input.GetAxis("Mouse X") * mouseSensitivity, up) * fwd;
        pitch = Mathf.Clamp(pitch - Input.GetAxis("Mouse Y") * mouseSensitivity, -85f, 85f);

        // ---- 找脚下曲面 ----
        Vector3 origin = transform.position + up * 0.2f;
        bool hitSurface = Physics.Raycast(origin, -up, out RaycastHit hit,
                                          playerHeight + snapDistance, surfaceMask, QueryTriggerInteraction.Ignore);
        if (hitSurface)
        {
            Vector3 n = hit.normal;
            if (Vector3.Dot(n, up) < 0f) n = -n;        // 从背面打过来时法线要翻向自己
            up = Vector3.Slerp(up, n, Mathf.Clamp01(Time.deltaTime * 8f)).normalized;
        }

        // ---- 移动：切线平面内的位移 ----
        fwd = Vector3.ProjectOnPlane(fwd, up);
        if (fwd.sqrMagnitude < 1e-6f) fwd = Vector3.ProjectOnPlane(Vector3.forward, up);
        if (fwd.sqrMagnitude < 1e-6f) fwd = Vector3.Cross(up, Vector3.right);
        fwd.Normalize();
        Vector3 right = Vector3.Cross(up, fwd);

        float speed = (Input.GetKey(KeyCode.LeftShift) || Input.GetKey(KeyCode.RightShift)) ? runSpeed : walkSpeed;
        Vector3 wish = (fwd * Input.GetAxisRaw("Vertical") + right * Input.GetAxisRaw("Horizontal")).normalized * speed;
        transform.position += wish * Time.deltaTime;

        // ---- 重力：朝着曲面（-up）拉 ----
        velocity += -up * gravity * Time.deltaTime;
        transform.position += velocity * Time.deltaTime;

        // ---- 吸附到曲面 ----
        origin = transform.position + up * 0.2f;
        if (Physics.Raycast(origin, -up, out RaycastHit ground,
                            playerHeight + snapDistance, surfaceMask, QueryTriggerInteraction.Ignore))
        {
            Vector3 gn = ground.normal;
            if (Vector3.Dot(gn, up) < 0f) gn = -gn;
            transform.position = ground.point + gn * playerHeight;
            velocity = Vector3.ProjectOnPlane(velocity, gn);   // 去掉撞向地面的分量
            up = Vector3.Slerp(up, gn, Mathf.Clamp01(Time.deltaTime * 10f)).normalized;
        }
        else if (velocity.magnitude > 40f)
        {
            velocity = velocity.normalized * 40f;              // 掉落限速，防止穿地
        }

        // ---- 姿态 ----
        if (cam != null)
            cam.transform.rotation = Quaternion.LookRotation(fwd, up) * Quaternion.Euler(pitch, 0f, 0f);

        // ---- 1/2/3 传送到展品 ----
        if (teleportTargets != null)
        {
            for (int i = 0; i < teleportTargets.Length && i < 3; i++)
            {
                if (Input.GetKeyDown(KeyCode.Alpha1 + i) && teleportTargets[i] != null)
                {
                    transform.position = teleportTargets[i].position + Vector3.up * (playerHeight - 0.4f);
                    up = Vector3.up;
                    velocity = Vector3.zero;
                    fwd = Vector3.forward;
                    pitch = -10f;
                }
            }
        }
    }
}