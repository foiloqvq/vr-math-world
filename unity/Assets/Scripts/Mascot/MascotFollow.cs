using UnityEngine;

/// 吉祥物跟随：平滑地飘在目标身后，带轻微上下呼吸，并转头看向目标。
/// 大鱼的目标是玩家，小鱼的目标是大鱼（妹妹跟着姐姐）。
///
/// 注意：旋转必须**每帧整体赋值**。曾经写成 transform.rotation *= 摆动，
/// 当方向向量退化（离目标太近）时"转向目标"那句被跳过，而 *= 还在乘，
/// 结果就是原地转圈 —— 这是本文件唯一需要小心的地方。
public class MascotFollow : MonoBehaviour
{
    public Transform target;                 // 留空则运行时自动找 SurfaceWalker（玩家）
    public float followDistance = 5f;
    public float followHeight = 2.2f;
    public float followLerp = 2.0f;          // 越小越"慢半拍"，越可爱
    public float turnSpeed = 140f;
    public float bobAmplitude = 0.14f;
    public float bobFrequency = 1.0f;
    public float bodyRoll = 8f;              // 游动时左右轻摆（度）

    /// 是否正在跟随。false = 停在原地（停在哪里都行，你回来时它还在）
    public bool following = true;
    public void ToggleFollow() { following = !following; }
    public bool IsFollowing => following;

    float bobPhase;
    Vector3 lastPos;
    float lastSpeed;

    /// 供 HUD 显示的一行自我报告
    public string DebugLine { get; private set; } = "尚未开始";

    void Start()
    {
        if (target == transform) target = null;          // 防呆：别追自己
        if (target == null)
        {
            var walker = Object.FindFirstObjectByType<SurfaceWalker>();
            if (walker != null) target = walker.transform;
        }
        bobPhase = Random.value * 6.28f;
        lastPos = transform.position;
    }

    void LateUpdate()
    {
        if (target == null) { DebugLine = "没有目标"; return; }

        float dt = Time.deltaTime;
        bobPhase += dt * bobFrequency * Mathf.PI * 2f;

        if (following)
        {
            Vector3 desired = target.position
                            + Vector3.up * followHeight
                            - target.forward * followDistance
                            + Vector3.up * (Mathf.Sin(bobPhase) * bobAmplitude);

            float k = 1f - Mathf.Exp(-followLerp * Mathf.Max(dt, 1e-4f));
            transform.position = Vector3.Lerp(transform.position, desired, k);
        }

        // 朝向：把摆动合进目标旋转，再整体 RotateTowards —— 绝不 *= 累积
        Vector3 dir = target.position - transform.position;
        dir.y = 0f;
        Vector3 fwd = dir.sqrMagnitude > 0.01f ? dir.normalized : transform.forward;
        if (fwd.sqrMagnitude < 1e-4f) fwd = Vector3.forward;
        float roll = Mathf.Sin(bobPhase * 0.5f) * bodyRoll;
        Quaternion want = Quaternion.LookRotation(fwd, Vector3.up) * Quaternion.Euler(0f, 0f, roll);
        transform.rotation = Quaternion.RotateTowards(transform.rotation, want, turnSpeed * dt);

        // 自我报告
        lastSpeed = dt > 0f ? Vector3.Distance(transform.position, lastPos) / dt : 0f;
        lastPos = transform.position;
        Vector3 toTarget = target.position - transform.position;
        DebugLine = string.Format("{4} · 目标 {0} · 距离 {1:F1}m · 高度差 {2:F1}m · 移动 {3:F1}m/s",
            target.name, toTarget.magnitude, transform.position.y - target.position.y, lastSpeed, following ? "跟随中" : "已停下");
    }
}