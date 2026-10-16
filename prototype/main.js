// VR Math World · PC prototype（第一人称走动 + 数学展品）
// 目标：跑通「场景 + 移动 + 数学可视化」这条最小链；WebXR 接入留到 VR 设备到位后。
import * as THREE from 'three';

// ---------- 诊断（?diag=1 时把渲染信息画在页面上，方便无头截图排查） ----------
const qs = new URLSearchParams(location.search);
const diag = document.createElement('div');
diag.style.cssText = 'position:fixed;right:12px;top:12px;z-index:9;text-align:right;white-space:pre;'
  + 'color:#9fe6ff;font:12px/1.55 ui-monospace,Consolas,monospace;text-shadow:0 1px 3px #000;pointer-events:none';
if (qs.get('diag')) document.body.appendChild(diag);
addEventListener('error', ev => {
  diag.textContent = 'JS ERROR: ' + ev.message + '\n' + (ev.filename || '') + ':' + ev.lineno;
  diag.style.color = '#ff9090';
  document.body.appendChild(diag);
});

// ---------- 展品布局 ----------
const EXHIBITS = [
  { key: 'surface', title: '函数曲面  z = sin(x²+z²)/r²', pos: new THREE.Vector3(0, 0, -20) },
  { key: 'solids',  title: '柏拉图立体（五种正多面体）',   pos: new THREE.Vector3(-24, 0, 6) },
  { key: 'mobius',  title: '莫比乌斯带（只有一个面）',     pos: new THREE.Vector3(24, 0, 6) },
];

// 相机预设（?view=1..4）—— 用于自动化截图验证
const VIEWS = {
  1: { pos: [2, 20, 46],  look: [-4, 3, -4] },   // 全景
  2: { pos: [0, 5, -6],   look: [0, 3, -20] },   // 函数曲面
  3: { pos: [-24, 4, 17], look: [-24, 3, 6] },   // 柏拉图立体
  4: { pos: [24, 4, 17],  look: [24, 3, 6] },    // 莫比乌斯带
};

// ---------- 基础三件套 ----------
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0b1020);
scene.fog = new THREE.Fog(0x0b1020, 60, 190);

const camera = new THREE.PerspectiveCamera(70, innerWidth / innerHeight, 0.1, 800);
camera.position.set(0, 1.7, 30);

const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
document.body.appendChild(renderer.domElement);

// ---------- 灯光 ----------
scene.add(new THREE.HemisphereLight(0x9fc6ff, 0x0a0f1c, 0.9));
const sun = new THREE.DirectionalLight(0xffffff, 1.6);
sun.position.set(28, 44, 22);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.left = -70; sun.shadow.camera.right = 70;
sun.shadow.camera.top = 70;   sun.shadow.camera.bottom = -70;
scene.add(sun);
scene.add(new THREE.AmbientLight(0x223355, 0.6));

// ---------- 地面 ----------
const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(400, 400),
  new THREE.MeshStandardMaterial({ color: 0x121a2e, roughness: 0.95, metalness: 0.0 })
);
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

const grid = new THREE.GridHelper(400, 160, 0x2e4a7a, 0x1a2740);
grid.position.y = 0.01;
scene.add(grid);

// 星点背景（便宜的氛围）
(() => {
  const g = new THREE.BufferGeometry(), n = 1200, p = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    const r = 220 + Math.random() * 260, t = Math.random() * Math.PI * 2, u = Math.random() * 0.7 + 0.12;
    p[i*3] = r * Math.cos(t) * Math.sin(u); p[i*3+1] = r * Math.cos(u) * 0.8 + 60; p[i*3+2] = r * Math.sin(t) * Math.sin(u);
  }
  g.setAttribute('position', new THREE.BufferAttribute(p, 3));
  scene.add(new THREE.Points(g, new THREE.PointsMaterial({ color: 0x9fd8ff, size: 1.6, sizeAttenuation: false })));
})();

// ---------- 文字标签（canvas 贴图，不依赖字体文件） ----------
function makeLabel(text, color = '#bfe6ff', scale = 6) {
  const pad = 24, fs = 42;
  const c = document.createElement('canvas'), x = c.getContext('2d');
  x.font = `${fs}px system-ui, "Microsoft YaHei", sans-serif`;
  const w = Math.ceil(x.measureText(text).width) + pad * 2;
  c.width = w; c.height = fs + pad * 1.4;
  const g = c.getContext('2d');
  g.font = `${fs}px system-ui, "Microsoft YaHei", sans-serif`;
  g.fillStyle = 'rgba(8,14,28,0.72)';
  g.fillRect(0, 0, c.width, c.height);
  g.strokeStyle = 'rgba(120,180,255,0.35)'; g.lineWidth = 3; g.strokeRect(1.5, 1.5, c.width - 3, c.height - 3);
  g.fillStyle = color; g.textBaseline = 'middle';
  g.fillText(text, pad, c.height / 2);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false }));
  const k = scale / 6;
  sp.scale.set((c.width / c.height) * k, k, 1);
  return sp;
}

// ---------- 展品 1：函数曲面 ----------
function buildSurface() {
  const g = new THREE.PlaneGeometry(22, 22, 160, 160);
  const pos = g.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i), y = pos.getY(i);
    const r2 = x * x + y * y, r = Math.sqrt(r2) || 1e-6;
    pos.setZ(i, (Math.sin(r) / r) * 6.5);
  }
  g.computeVertexNormals();
  g.rotateX(-Math.PI / 2);

  const grp = new THREE.Group();
  const solid = new THREE.Mesh(g, new THREE.MeshStandardMaterial({
    color: 0x4aa3ff, roughness: 0.35, metalness: 0.15, side: THREE.DoubleSide,
    transparent: true, opacity: 0.92, flatShading: false,
  }));
  solid.castShadow = true;
  grp.add(solid);
  const wire = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ color: 0x9fd8ff, wireframe: true, transparent: true, opacity: 0.18 }));
  wire.position.y = 0.02;
  grp.add(wire);
  return grp;
}

// ---------- 展品 2：五种柏拉图立体 ----------
function buildSolids() {
  const grp = new THREE.Group();
  const defs = [
    ['正四面体', new THREE.TetrahedronGeometry(1.5)],
    ['正六面体',        new THREE.BoxGeometry(2.2, 2.2, 2.2)],
    ['正八面体',  new THREE.OctahedronGeometry(1.7)],
    ['正十二面体',    new THREE.DodecahedronGeometry(1.6)],
    ['正二十面体',     new THREE.IcosahedronGeometry(1.6)],
  ];
  defs.forEach(([name, geo], i) => {
    const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({
      color: new THREE.Color().setHSL(0.55 + i * 0.055, 0.7, 0.6), roughness: 0.28, metalness: 0.35, flatShading: true,
    }));
    m.position.set((i - 2) * 7, 2.0, 0);
    m.castShadow = true; m.name = 'solid-' + i; m.userData.spin = 0.25 + i * 0.06;
    grp.add(m);
    const ped = new THREE.Mesh(new THREE.CylinderGeometry(1.15, 1.35, 0.8, 24),
      new THREE.MeshStandardMaterial({ color: 0x1b2740, roughness: 0.9 }));
    ped.position.set((i - 2) * 7, 0.4, 0); ped.receiveShadow = true; grp.add(ped);
    const lb = makeLabel(name, '#bfe6ff', 3.2); lb.position.set((i - 2) * 7, 4.8, 0); grp.add(lb);
  });
  return grp;
}

// ---------- 展品 3：莫比乌斯带 ----------
function buildMobius(R = 3.4, halfW = 1.15, segU = 240, segV = 12) {
  const g = new THREE.BufferGeometry();
  const verts = [], idx = [];
  for (let i = 0; i <= segU; i++) {
    const u = (i / segU) * Math.PI * 2;
    for (let j = 0; j <= segV; j++) {
      const v = (j / segV - 0.5) * 2 * halfW;
      verts.push((R + v * Math.cos(u / 2)) * Math.cos(u), v * Math.sin(u / 2), (R + v * Math.cos(u / 2)) * Math.sin(u));
    }
  }
  for (let i = 0; i < segU; i++) for (let j = 0; j < segV; j++) {
    const a = i * (segV + 1) + j, b = a + segV + 1;
    idx.push(a, b, a + 1, b, b + 1, a + 1);
  }
  g.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3));
  g.setIndex(idx); g.computeVertexNormals();

  const grp = new THREE.Group();
  const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({
    color: 0x8be0ff, roughness: 0.3, metalness: 0.4, side: THREE.DoubleSide, flatShading: true,
  }));
  m.castShadow = true;
  m.position.y = 3.4;
  grp.add(m);
  const lb = makeLabel('莫比乌斯带', '#d6f2ff', 3.2);
  lb.position.set(0, 6.6, 0); grp.add(lb);
  return grp;
}

// ---------- 装配 ----------
const built = {};
EXHIBITS.forEach(e => {
  let obj;
  if (e.key === 'surface') obj = buildSurface();
  else if (e.key === 'solids') obj = buildSolids();
  else obj = buildMobius();
  obj.position.copy(e.pos);
  obj.userData = { key: e.key, title: e.title };
  scene.add(obj);
  built[e.key] = obj;
  const lb = makeLabel(e.title, '#eaf6ff', 3.5);   // 展品总标题
  lb.position.copy(e.pos).add(new THREE.Vector3(0, e.key === 'surface' ? 10.5 : 9.5, 0));
  scene.add(lb);
});

// ---------- 第一人称控制 ----------
const keys = Object.create(null);
let yaw = 0, pitch = 0, locked = false;
const startEl = document.getElementById('start');
startEl.addEventListener('click', () => renderer.domElement.requestPointerLock());
document.addEventListener('pointerlockchange', () => {
  locked = document.pointerLockElement === renderer.domElement;
  startEl.style.display = locked ? 'none' : 'flex';
});
document.addEventListener('mousemove', e => {
  if (!locked) return;
  yaw -= e.movementX * 0.0022;
  pitch = Math.max(-1.45, Math.min(1.45, pitch - e.movementY * 0.0022));
});
addEventListener('keydown', e => {
  keys[e.code] = true;
  const n = { Digit1: 'surface', Digit2: 'solids', Digit3: 'mobius' }[e.code];
  if (n) { camera.position.copy(built[n].position).add(new THREE.Vector3(0, 1.7, 12)); yaw = 0; pitch = -0.06; }
});
addEventListener('keyup', e => { keys[e.code] = false; });
addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

// 移动（带一点惯性，走起来不那么生硬）
const vel = new THREE.Vector3();
function move(dt) {
  if (!locked) return;
  const fwd = new THREE.Vector3(-Math.sin(yaw), 0, -Math.cos(yaw));
  const right = new THREE.Vector3(Math.cos(yaw), 0, -Math.sin(yaw));
  const wish = new THREE.Vector3();
  if (keys.KeyW) wish.add(fwd);
  if (keys.KeyS) wish.sub(fwd);
  if (keys.KeyD) wish.add(right);
  if (keys.KeyA) wish.sub(right);
  const speed = (keys.ShiftLeft || keys.ShiftRight) ? 22 : 9;
  if (wish.lengthSq() > 0) wish.normalize().multiplyScalar(speed);
  vel.lerp(wish, Math.min(1, dt * 9));
  camera.position.addScaledVector(vel, dt);
  camera.position.y = 1.7;
}

// ---------- 主循环 ----------
const nearEl = document.getElementById('near');
const clock = new THREE.Clock();
let focus = null, t = 0;

function frame() {
  const dt = Math.min(0.05, clock.getDelta());
  t += dt;
  move(dt);

  camera.rotation.set(pitch, yaw, 0, 'YXZ');

  // 展品轻微自转
  built.solids.children.forEach(c => { if (c.userData.spin) c.rotation.y += dt * c.userData.spin; });
  built.mobius.children[0].rotation.y += dt * 0.15;
  built.surface.children[0].material.emissive = new THREE.Color(0x000000);

  // 靠近哪个展品 → HUD 提示 + 该展品高亮
  let best = null, bestD = 1e9;
  EXHIBITS.forEach(e => {
    const d = camera.position.distanceTo(e.pos);
    if (d < bestD) { bestD = d; best = e; }
  });
  if (best && bestD < 16) {
    if (focus !== best.key) focus = best.key;
    nearEl.textContent = `你正站在「${best.title}」旁边 · ${(bestD).toFixed(1)} m`;
  } else { focus = null; nearEl.textContent = ''; }

  if (qs.get('diag')) {
    const gl = renderer.getContext();
    diag.textContent = [
      'WebGL: ' + gl.getParameter(gl.VERSION),
      'GPU: ' + (gl.getParameter(gl.RENDERER) || '?'),
      'canvas: ' + renderer.domElement.width + 'x' + renderer.domElement.height,
      'children: ' + scene.children.length,
      'calls: ' + renderer.info.render.calls,
      'tris: ' + renderer.info.render.triangles,
      'cam: ' + camera.position.toArray().map(n => n.toFixed(1)).join(','),
      'fps: ' + (1 / Math.max(dt, 1e-4)).toFixed(0),
    ].join('\n');
  }
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}

// ---------- 自动化截图支持：?view=1..4 固定机位（免交互） ----------
const vm = qs.get('view');
if (vm && VIEWS[vm]) {
  const v = VIEWS[vm];
  camera.position.set(...v.pos);
  const dir = new THREE.Vector3(...v.look).sub(camera.position).normalize();
  yaw = Math.atan2(-dir.x, -dir.z);
  pitch = Math.asin(Math.max(-1, Math.min(1, dir.y)));
  startEl.style.display = 'none';
}
frame();   // 始终走持续渲染循环（无头截图需要"活帧"）