using System.Collections;
using UnityEngine;

/// 让吉祥物"游"起来：尾巴左右摆、胸鳍划水、偶尔从喷水孔喷一下水。
/// 靠名字找子部件（FlukeL/FlukeR/FinL/FinR/Blowhole），不需要额外引用。
public class MascotSwim : MonoBehaviour
{
    [Header("摆动")]
    public float tailAmplitude = 20f;      // 尾巴摆幅（度）
    public float tailFrequency = 1.5f;     // 每秒摆动次数
    public float finAmplitude = 16f;
    public float finFrequency = 1.5f;
    public float finPhase = 0.35f;         // 胸鳍比尾巴慢半拍的相位差

    [Header("喷水")]
    public bool spout = true;
    public float spoutInterval = 7f;
    public float spoutSpeed = 4.0f;

    Transform tailL, tailR, finL, finR, blowhole;
    Quaternion tailL0, tailR0, finL0, finR0;
    float t, spoutTimer;
    Material dropMat;

    void Start()
    {
        tailL = transform.Find("FlukeL");
        tailR = transform.Find("FlukeR");
        finL = transform.Find("FinL");
        finR = transform.Find("FinR");
        blowhole = transform.Find("Blowhole");
        if (tailL != null) tailL0 = tailL.localRotation;
        if (tailR != null) tailR0 = tailR.localRotation;
        if (finL != null) finL0 = finL.localRotation;
        if (finR != null) finR0 = finR.localRotation;

        spoutTimer = Random.value * spoutInterval;   // 错开喷水，两只不会同时喷
        dropMat = MaterialKit.MakeMaterial(new Color(0.72f, 0.90f, 1f), 0.8f, 0f);
    }

    void Update()
    {
        t += Time.deltaTime;

        // 尾巴：整体左右摆（两片同相，看起来是一条尾巴在摆）
        float s = Mathf.Sin(t * tailFrequency * Mathf.PI * 2f);
        if (tailL != null) tailL.localRotation = tailL0 * Quaternion.Euler(0f, s * tailAmplitude, 0f);
        if (tailR != null) tailR.localRotation = tailR0 * Quaternion.Euler(0f, s * tailAmplitude, 0f);

        // 胸鳍：上下划水，左右反相
        float sf = Mathf.Sin((t * finFrequency + finPhase) * Mathf.PI * 2f);
        if (finL != null) finL.localRotation = finL0 * Quaternion.Euler(0f, 0f, sf * finAmplitude * 0.5f);
        if (finR != null) finR.localRotation = finR0 * Quaternion.Euler(0f, 0f, -sf * finAmplitude * 0.5f);

        // 喷水
        if (spout && blowhole != null)
        {
            spoutTimer -= Time.deltaTime;
            if (spoutTimer <= 0f)
            {
                StartCoroutine(SpoutRoutine());
                spoutTimer = spoutInterval * (0.7f + Random.value * 0.6f);
            }
        }
    }

    IEnumerator SpoutRoutine()
    {
        int count = 3 + Random.Range(0, 3);
        for (int i = 0; i < count; i++)
        {
            var drop = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            drop.name = "SpoutDrop";
            var col = drop.GetComponent<Collider>();
            if (col != null) Destroy(col);
            drop.transform.position = blowhole.position;
            drop.transform.localScale = Vector3.one * 0.12f * Mathf.Max(0.5f, transform.lossyScale.x);
            drop.GetComponent<MeshRenderer>().sharedMaterial = dropMat;
            StartCoroutine(DropRoutine(drop.transform, spoutSpeed * (0.85f + Random.value * 0.3f)));
            yield return new WaitForSeconds(0.07f);
        }
    }

    IEnumerator DropRoutine(Transform drop, float vy)
    {
        float life = 0f;
        while (life < 2.0f && drop != null)
        {
            vy -= 9.8f * Time.deltaTime;
            drop.position += Vector3.up * vy * Time.deltaTime;
            life += Time.deltaTime;
            yield return null;
        }
        if (drop != null) Destroy(drop.gameObject);
    }
}