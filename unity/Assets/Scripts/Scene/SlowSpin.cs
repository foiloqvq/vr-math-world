using UnityEngine;

/// 慢慢自转（黑洞吸积盘那种）。挂在物体上即可。
public class SlowSpin : MonoBehaviour
{
    public Vector3 axis = Vector3.up;
    public float degreesPerSecond = 6f;

    void Update()
    {
        if (degreesPerSecond != 0f)
            transform.Rotate(axis, degreesPerSecond * Time.deltaTime, Space.Self);
    }
}