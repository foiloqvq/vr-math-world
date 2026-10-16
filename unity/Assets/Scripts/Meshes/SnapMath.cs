using System;

namespace Vmw.Meshes
{
    /// 曲面贴合的纯数学（不引用 UnityEngine，可在引擎外测试）。
    public static class SnapMath
    {
        /// 沿法线把点修正到"距曲面 height"处。
        /// 只沿法线移动 —— 若改成"直接贴到射线命中点再抬起 height"，切向坐标会被
        /// 命中的偏差带走，表现就是站着不动也慢慢滑走（真实踩过的 bug）。
        public static void CorrectAlongNormal(
            float px, float py, float pz,
            float hx, float hy, float hz,
            float nx, float ny, float nz,
            float height,
            out float ox, out float oy, out float oz)
        {
            float gap = (px - hx) * nx + (py - hy) * ny + (pz - hz) * nz - height;
            ox = px - nx * gap;
            oy = py - ny * gap;
            oz = pz - nz * gap;
        }

        /// 旧写法（会漂移），保留下来做对照测试。
        public static void CorrectToHitPoint(
            float hx, float hy, float hz,
            float nx, float ny, float nz, float height,
            out float ox, out float oy, out float oz)
        {
            ox = hx + nx * height;
            oy = hy + ny * height;
            oz = hz + nz * height;
        }

        /// 射线与平面 n·x = 0 求交：o + t·d。返回是否有交点。
        public static bool RayPlane(
            float ox, float oy, float oz,
            float dx, float dy, float dz,
            float nx, float ny, float nz,
            out float hx, out float hy, out float hz)
        {
            float denom = nx * dx + ny * dy + nz * dz;
            if (Math.Abs(denom) < 1e-9f) { hx = hy = hz = 0f; return false; }
            float t = -(nx * ox + ny * oy + nz * oz) / denom;
            hx = ox + dx * t; hy = oy + dy * t; hz = oz + dz * t;
            return true;
        }
    }
}