using UnityEngine;

/// 吉祥物行为：跟随 / 自由漫游 / 原地停下，三种状态。
///
/// 「自由漫游」是它的灵魂感来源：放开之后它自己在附近挑个点游过去，
/// 到了就待一会儿、看看四周，再挑下一个 —— 你不管它，它也在过日子。
///
/// 注意：旋转必须每帧整体赋值。曾经写成 transform.rotation *= 摆动，
/// 方向向量退化时"转向目标"那句被跳过、而 *= 仍在乘，结果原地转圈。
public class MascotFollow : MonoBehaviour
{
    public enum Mode { Follow = 0, Wander = 1, Stay = 2 }

    public Transform target;                 // 留空则运行时自动找玩家
    public Mode mode = Mode.Follow;

    [Header("跟随")]
    public float followDistance = 5f;
    public float followHeight = 1.3f;        // 与主角相近的高度，不再飘在天上
    public float followLerp = 2.0f;
    public float turnSpeed = 140f;

    [Header("自由漫游")]
    public float wanderRadius = 14f;
    public float wanderSpeed = 3.2f;
    public float cruiseHeight = 1.3f;
    public float wanderPauseMin = 1.5f;
    public float wanderPauseMax = 5f;

    [Header("通用")]
    public float bobAmplitude = 0.14f;
    public float bobFrequency = 1.0f;
    public float bodyRoll = 8f;

    /// 说话时看向的目标（由对话系统临时设置）
    public Transform lookAtOverride;

    /// AI 待机区（站台）中心。ExhibitScene 建模时写入；按 M 时所有跟班飞回这里。
    public static Vector3 StationPoint = new Vector3(18f, 1.5f, -40f);

    /// 各自的分站位（避免两只叠在一起）
    public Vector3 homeStation;
    public bool hasHome;

    /// 停靠省电：回到站台并站定后，关掉朝向计算 / 呼吸 / 游泳动画（2026-10-18 foilo 要的）
    public bool dockedIdle = true;
    MascotSwim swim;

    float bobPhase;
    Vector3 lastPos;
    float lastSpeed;
    Vector3 wanderTarget;
    float wanderPause;
    bool hasWanderTarget;

    public string ModeName
    {
        get { return mode == Mode.Follow ? "跟随中" : (mode == Mode.Wander ? "自由漫游" : "已停下"); }
    }

    /// 回站台待机（不进 Follow，也不乱跑）
    public void GoHome(Vector3 station)
    {
        homeStation = station;
        hasHome = true;
        mode = Mode.Stay;
    }

    /// 重新跟着玩家
    public void ResumeFollow()
    {
        hasHome = false;
        mode = Mode.Follow;
    }

    public void CycleMode() { mode = (Mode)(((int)mode + 1) % 3); if (mode == Mode.Wander) hasWanderTarget = false; }

    /// 供 HUD 显示的一行自我报告
    public string DebugLine { get; private set; } = "尚未开始";

    void Start()
    {
        if (target == transform) target = null;
        if (target == null)
        {
            var walker = Object.FindFirstObjectByType<SurfaceWalker>();
            if (walker != null) target = walker.transform;
        }
        swim = GetComponent<MascotSwim>();
        bobPhase = Random.value * 6.28f;
        lastPos = transform.position;
    }

    void PickWanderTarget()
    {
        Vector2 c = Random.insideUnitCircle * wanderRadius;
        Vector3 home = target != null ? target.position : transform.position;
        wanderTarget = new Vector3(home.x + c.x, home.y + cruiseHeight, home.z + c.y);
        hasWanderTarget = true;
    }

    void LateUpdate()
    {
        float dt = Time.deltaTime;

        // ---- 停靠省电：在站台站定后，不做朝向 / 呼吸 / 游泳，几乎不耗 CPU ----
        if (dockedIdle && mode == Mode.Stay && hasHome && lookAtOverride == null)
        {
            bool arrived = Vector3.Distance(transform.position, homeStation) < 0.25f;
            if (arrived)
            {
                if (swim != null && swim.enabled) swim.enabled = false;
                DebugLine = string.Format("站台待机（省电）· 目标 {0}", homeStation);
                return;
            }
        }
        else if (swim != null && !swim.enabled)
        {
            swim.enabled = true;              // 离开站台，恢复游泳动画
        }

        bobPhase += dt * bobFrequency * Mathf.PI * 2f;
        Vector3 before = transform.position;

        bool speaking = lookAtOverride != null;

        if (mode == Mode.Follow)
        {
            if (target != null && !speaking)
            {
                Vector3 desired = target.position
                                + Vector3.up * followHeight
                                - target.forward * followDistance
                                + Vector3.up * (Mathf.Sin(bobPhase) * bobAmplitude);
                float k = 1f - Mathf.Exp(-followLerp * Mathf.Max(dt, 1e-4f));
                transform.position = Vector3.Lerp(transform.position, desired, k);
            }
        }
        else if (mode == Mode.Wander)
        {
            if (!speaking)
            {
                if (wanderPause > 0f)
                {
                    wanderPause -= dt;                       // 到了就待一会儿
                }
                else
                {
                    if (!hasWanderTarget) PickWanderTarget();
                    Vector3 flat = wanderTarget - transform.position;
                    flat.y = 0f;
                    if (flat.magnitude < 0.8f)
                    {
                        hasWanderTarget = false;
                        wanderPause = Random.Range(wanderPauseMin, wanderPauseMax);
                    }
                    else
                    {
                        Vector3 step = flat.normalized * wanderSpeed * dt;
                        transform.position += step;
                    }
                    // 高度慢慢贴到巡游高度
                    Vector3 p = transform.position;
                    p.y = Mathf.Lerp(p.y, (target != null ? target.position.y : 0f) + cruiseHeight, dt * 1.2f);
                    transform.position = p;
                }
            }
        }
        else if (mode == Mode.Stay && hasHome)
        {
            // 回自己的站位，站定后只剩呼吸
            Vector3 dockPos = homeStation + Vector3.up * (Mathf.Sin(bobPhase) * bobAmplitude * 0.5f);
            float k = 1f - Mathf.Exp(-1.6f * Mathf.Max(dt, 1e-4f));
            transform.position = Vector3.Lerp(transform.position, dockPos, k);
        }
        // Stay（没有站位）：什么都不做，只保留呼吸与摆动

        // ---- 朝向：说话时看讲解目标，否则看移动方向/目标 ----
        Vector3 face, dir;
        if (lookAtOverride != null)
        {
            face = lookAtOverride.position;
            dir = face - transform.position;
        }
        else if (mode == Mode.Wander && hasWanderTarget)
        {
            dir = wanderTarget - transform.position;
        }
        else if (target != null)
        {
            dir = target.position - transform.position;
        }
        else
        {
            dir = transform.forward;
        }
        dir.y = 0f;
        Vector3 fwd = dir.sqrMagnitude > 0.01f ? dir.normalized : transform.forward;
        if (fwd.sqrMagnitude < 1e-4f) fwd = Vector3.forward;
        float roll = Mathf.Sin(bobPhase * 0.5f) * bodyRoll;
        Quaternion want = Quaternion.LookRotation(fwd, Vector3.up) * Quaternion.Euler(0f, 0f, roll);
        transform.rotation = Quaternion.RotateTowards(transform.rotation, want, turnSpeed * dt);

        // ---- 自我报告 ----
        lastSpeed = dt > 0f ? Vector3.Distance(transform.position, before) / dt : 0f;
        lastPos = transform.position;
        string tgt = target != null ? target.name : "无";
        DebugLine = string.Format("{0} · 目标 {1} · 距离 {2:F1}m · 高度 {3:F1}m · 移动 {4:F1}m/s",
            ModeName, tgt, target != null ? Vector3.Distance(transform.position, target.position) : 0f,
            transform.position.y, lastSpeed);
    }
}