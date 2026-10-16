using UnityEngine;

/// 吉祥物跟随：平滑地飘在目标身后，带轻微上下呼吸，并转头看向目标。
/// 大鱼的目标是玩家，小鱼的目标是大鱼（妹妹跟着姐姐）。
public class MascotFollow : MonoBehaviour
{
    public Transform target;                 // 留空则运行时自动找 SurfaceWalker（玩家）
    public float followDistance = 5f;
    public float followHeight = 2.2f;
    public float followLerp = 2.0f;          // 越小越"慢半拍"，越可爱
    public float turnSpeed = 140f;
    public float bobAmplitude = 0.14f;
    public float bobFrequency = 1.0f;
    public float bodyRoll = 8f;

    float bobPhase;

    void Start()
    {
        if (target == null)
        {
            var walker = Object.FindFirstObjectByType<SurfaceWalker>();
            if (walker != null) target = walker.transform;
        }
        bobPhase = Random.value * 6.28f;
    }

    void LateUpdate()
    {
        if (target == null) return;

        bobPhase += Time.deltaTime * bobFrequency * Mathf.PI * 2f;

        Vector3 desired = target.position
                        + Vector3.up * followHeight
                        - target.forward * followDistance
                        + Vector3.up * (Mathf.Sin(bobPhase) * bobAmplitude);

        float k = 1f - Mathf.Exp(-followLerp * Time.deltaTime);
        transform.position = Vector3.Lerp(transform.position, desired, k);

        Vector3 dir = target.position - transform.position;
        dir.y = 0f;
        if (dir.sqrMagnitude > 0.01f)
        {
            Quaternion want = Quaternion.LookRotation(dir.normalized, Vector3.up);
            transform.rotation = Quaternion.RotateTowards(transform.rotation, want, turnSpeed * Time.deltaTime);
        }

        if (bodyRoll != 0f)
            transform.rotation *= Quaternion.Euler(0f, 0f, Mathf.Sin(bobPhase * 0.5f) * bodyRoll);
    }
}