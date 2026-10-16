using UnityEngine;

/// 极简第一人称走动：WASD + 鼠标环视 + Shift 快跑。
/// 用的是 Unity 传统输入（Input.GetAxis），工程若只启用了新 Input System，
/// 需要把 Player Settings → Active Input Handling 设成 Both 或 Old（见 unity/docs/setup.md）。
[RequireComponent(typeof(CharacterController))]
public class FirstPersonWalker : MonoBehaviour
{
    public float walkSpeed = 6f;
    public float runSpeed = 14f;
    public float mouseSensitivity = 2.2f;
    public bool lockCursorOnStart = true;

    CharacterController cc;
    float pitch;

    void Awake()
    {
        cc = GetComponent<CharacterController>();
        if (lockCursorOnStart) { Cursor.lockState = CursorLockMode.Locked; Cursor.visible = false; }
    }

    void Update()
    {
        float mx = Input.GetAxis("Mouse X") * mouseSensitivity;
        float my = Input.GetAxis("Mouse Y") * mouseSensitivity;
        transform.Rotate(0f, mx, 0f);
        pitch = Mathf.Clamp(pitch - my, -85f, 85f);
        Camera cam = GetComponentInChildren<Camera>();
        if (cam != null) cam.transform.localRotation = Quaternion.Euler(pitch, 0f, 0f);

        float speed = (Input.GetKey(KeyCode.LeftShift) || Input.GetKey(KeyCode.RightShift)) ? runSpeed : walkSpeed;
        float h = Input.GetAxisRaw("Horizontal");
        float v = Input.GetAxisRaw("Vertical");
        Vector3 dir = (transform.right * h + transform.forward * v).normalized;
        cc.SimpleMove(dir * speed);   // SimpleMove 自带重力
    }
}