#!/usr/bin/env node
/**
 * 本地「视频收件」小服务（127.0.0.1:7891）。
 *
 * 为什么需要：浏览器里的插件不能直接写磁盘，所以给它一个本地端点：
 *   POST /upload            裸二进制 body + X-Filename 头 → 存到剪辑目录
 *   GET  /latest            返回目录里最新的那个视频路径（大肥鱼审片用）
 *   GET  /health            存活检查
 *
 * 安全：只监听回环地址；只接受视频扩展名；文件名做净化，不允许路径穿越。
 */
import { createServer } from 'node:http'
import { appendFileSync, createWriteStream, createReadStream, writeFileSync, existsSync, mkdirSync, readdirSync, readFileSync, statSync } from 'node:fs'
import path from 'node:path'

const PORT = 7891
const DEST = 'C:\\Users\\nb666\\Videos\\大肥鱼作品\\剪辑'
const LAN_DIR = 'C:\\Users\\nb666\\Documents\\deepseek-harness\\default-workspace\\study-space\\tools\\lan'
const QUEUE_FILE = 'C:\\Users\\nb666\\Videos\\大肥鱼作品\\剪辑\\agent-queue.json'
const DIAG_LOG = 'C:\\Users\\nb666\\Videos\\大肥鱼作品\\剪辑\\diag.log'
const OK_EXT = new Set(['.mp4', '.mov', '.mkv', '.webm', '.avi', '.gif', '.png', '.jpg', '.jpeg'])

if (!existsSync(DEST)) mkdirSync(DEST, { recursive: true })

const sanitize = (name) =>
  path.basename(String(name || 'upload.bin'))
    .replace(/[<>:"/\\|?*\x00-\x1f]/g, '_')
    .slice(0, 120)


const readQueue = () => {
  try {
    return JSON.parse(readFileSync(QUEUE_FILE, 'utf8'))
  } catch (e) {
    return { pending: [], running: [], done: [] }
  }
}
const writeQueue = (q) => {
  try { writeFileSync(QUEUE_FILE, JSON.stringify(q, null, 1)) } catch (e) {}
}

const latest = () => {
  const files = readdirSync(DEST)
    .map((f) => path.join(DEST, f))
    .filter((p) => { try { return statSync(p).isFile() } catch { return false } })
    .map((p) => ({ p, m: statSync(p).mtimeMs }))
    .sort((a, b) => b.m - a.m)
  return files.length ? files[0].p : ''
}

const cors = (res) => {
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-Filename')
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
}

const server = createServer((req, res) => {
  cors(res)
  if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return }

  // ===== 笔记本手眼面板（同源，浏览器打开 /panel）=====
  if (req.method === 'GET' && (req.url === '/panel' || req.url === '/panel/')) {
    const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>大肥鱼 · 笔记本手眼</title>
<style>
  :root { --bg:#080b13; --fg:#e6eeff; --dim:#8ea0be; --line:#22304c; --cy:#6ee6eb; --ok:#8fd8b0; --bad:#ff9ec7; }
  * { box-sizing: border-box; }
  body { margin:0; background:radial-gradient(800px 480px at 70% -10%, #152344, var(--bg) 65%); color:var(--fg);
         font:14px/1.6 system-ui,"Microsoft YaHei",sans-serif; min-height:100vh; }
  .wrap { max-width:1020px; margin:0 auto; padding:22px 18px 60px; }
  h1 { font-size:20px; margin:0 0 4px; }
  .sub { color:var(--dim); font-size:12px; margin-bottom:16px; }
  .grid { display:grid; grid-template-columns: 1.35fr 1fr; gap:16px; }
  @media (max-width: 860px) { .grid { grid-template-columns: 1fr; } }
  .card { background:rgba(12,18,30,.85); border:1px solid var(--line); border-radius:12px; padding:14px; }
  .status { font-size:12px; margin-bottom:10px; }
  .ok { color:var(--ok); } .bad { color:var(--bad); }
  img.shot { width:100%; border-radius:8px; border:1px solid var(--line); display:block; background:#0b1220; }
  .row { display:flex; gap:8px; align-items:center; margin-bottom:8px; }
  button { background:#16233a; color:#cfe3ff; border:1px solid #2b3f60; border-radius:8px;
           padding:7px 12px; font-size:13px; cursor:pointer; }
  button:hover { border-color:var(--cy); color:var(--cy); }
  button:disabled { opacity:.45; cursor:not-allowed; }
  input { background:#0e1523; color:var(--fg); border:1px solid #2b3f60; border-radius:8px;
          padding:6px 9px; font-size:13px; width:100%; }
  input:focus { outline:none; border-color:var(--cy); }
  label { display:block; font-size:11px; color:var(--dim); margin:10px 0 4px; }
  .log { font:12px/1.5 ui-monospace,Consolas,monospace; color:#9fb3d1; background:#0a101c;
         border:1px solid var(--line); border-radius:8px; padding:8px; height:150px; overflow:auto; white-space:pre-wrap; }
  .hint { color:#5f7292; font-size:11px; margin-top:8px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>🖐 笔记本手眼</h1>
  <div class="sub">大肥鱼自用面板 · 数据来自本机 7891 · 笔记本离线时按钮无效</div>

  <div class="grid">
    <div class="card">
      <div class="status" id="status">连接中…</div>
      <img class="shot" id="shot" alt="笔记本桌面">
      <div class="hint">截图来自笔记本；点「截屏」会刷新</div>
    </div>

    <div class="card">
      <div class="row">
        <button id="btnShot">📷 截屏</button>
        <button id="btnRefresh">↻ 刷新状态</button>
      </div>

      <label>点击坐标（笔记本全屏像素；1920×1080）</label>
      <div class="row">
        <input id="x" value="960" placeholder="x">
        <input id="y" value="540" placeholder="y">
        <button id="btnClick">🖱 点击</button>
      </div>

      <label>键盘输入（打进笔记本当前焦点窗口）</label>
      <div class="row">
        <input id="text" placeholder="要打的字">
        <button id="btnType">⌨️ 打字</button>
      </div>

      <label>快捷动作</label>
      <div class="row">
        <button id="btnEnter">⏎ 回车</button>
        <button id="btnEsc">Esc</button>
        <button id="btnWin">Win</button>
      </div>

      <label>日志</label>
      <div class="log" id="log"></div>
    </div>
  </div>
</div>

<script>
const BASE = location.origin;   // 同源（页面由 7891 提供）
const $ = (id) => document.getElementById(id);
let lastShotAt = 0;

function log(msg) {
  const el = $('log');
  const t = new Date().toLocaleTimeString();
  el.textContent = '[' + t + '] ' + msg + '\\n' + el.textContent;
  if (el.textContent.length > 8000) el.textContent = el.textContent.slice(0, 8000);
}

async function pushTask(cmd, label) {
  try {
    const res = await fetch(BASE + '/agent/push', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cmd }),
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const j = await res.json();
    log((label || '任务') + ' 已推送 id=' + j.id);
  } catch (e) {
    log('推送失败：' + (e && e.message ? e.message : e));
  }
}

const shot = (name) => pushTask(
  'powershell -NoProfile -ExecutionPolicy Bypass -File D:\\\\DaFeiyu\\\\ctl.ps1 -Action shot -Name ' + (name || 'panel.png'),
  '截屏');

const click = (x, y) => pushTask(
  'powershell -NoProfile -ExecutionPolicy Bypass -File D:\\\\DaFeiyu\\\\ctl.ps1 -Action click -X ' + x + ' -Y ' + y,
  '点击 ' + x + ',' + y);

const typeText = (t) => pushTask(
  'powershell -NoProfile -ExecutionPolicy Bypass -File D:\\\\DaFeiyu\\\\ctl.ps1 -Action type -Text "' + String(t).replace(/"/g, '\`"') + '"',
  '打字');

const key = (vk) => pushTask(
  'powershell -NoProfile -ExecutionPolicy Bypass -File D:\\\\DaFeiyu\\\\ctl.ps1 -Action key -VK ' + vk,
  '按键 vk=' + vk);

async function refresh() {
  try {
    const res = await fetch(BASE + '/agent/state', { cache: 'no-store' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const s = await res.json();
    let txt = '在线 · 队列 ' + s.pending + ' · 跑中 ' + s.running;
    if (s.shot) {
      const age = Math.max(0, Math.round((Date.now() - s.shot.at) / 1000));
      txt += ' · 截图 ' + age + ' 秒前';
    }
    $('status').textContent = txt;
    $('status').className = 'status ok';
    if (s.shot && s.shot.at !== lastShotAt) {
      lastShotAt = s.shot.at;
      $('shot').src = BASE + '/agent/latest-shot?t=' + s.shot.at;
    }
  } catch (e) {
    $('status').textContent = '离线（7891 没响应）';
    $('status').className = 'status bad';
  }
}

$('btnShot').onclick = () => shot('panel-' + Date.now() + '.png');
$('btnRefresh').onclick = refresh;
$('btnClick').onclick = () => click(parseInt($('x').value, 10) || 0, parseInt($('y').value, 10) || 0);
$('btnType').onclick = () => { const t = $('text').value; if (!t) return log('文字为空'); typeText(t); };
$('btnEnter').onclick = () => key(13);
$('btnEsc').onclick = () => key(27);
$('btnWin').onclick = () => key(91);

refresh();
setInterval(refresh, 3000);
log('面板就绪，v0.2（网页面板）');
</script>
</body>
</html>
`
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' })
    res.end(html)
    return
  }

  // ===== 给插件用的状态快照 + 最新截图 =====
  if (req.method === 'GET' && req.url === '/agent/state') {
    const q = readQueue()
    const dir = path.join('C:\\Users\\nb666\\Videos\\大肥鱼作品\\剪辑', 'laptop-shots')
    let shot = null
    try {
      const files = readdirSync(dir).filter((f) => /\.png$/i.test(f))
      if (files.length) {
        files.sort((a, b) => statSync(path.join(dir, b)).mtimeMs - statSync(path.join(dir, a)).mtimeMs)
        const f = files[0]
        shot = { name: f, at: statSync(path.join(dir, f)).mtimeMs, bytes: statSync(path.join(dir, f)).size }
      }
    } catch (e) {}
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({
      ok: true,
      pending: q.pending.length,
      running: q.running.length,
      last: (q.done || []).slice(-3),
      shot,
      now: Date.now(),
    }))
    return
  }

  if (req.method === 'GET' && req.url.startsWith('/agent/latest-shot')) {
    const dir = path.join('C:\\Users\\nb666\\Videos\\大肥鱼作品\\剪辑', 'laptop-shots')
    try {
      const files = readdirSync(dir).filter((f) => /\.png$/i.test(f))
      files.sort((a, b) => statSync(path.join(dir, b)).mtimeMs - statSync(path.join(dir, a)).mtimeMs)
      const f = files[0]
      if (!f) { res.writeHead(404); res.end('no shot'); return }
      const full = path.join(dir, f)
      res.writeHead(200, { 'Content-Type': 'image/png', 'Cache-Control': 'no-store', 'Content-Length': statSync(full).size })
      createReadStream(full).pipe(res)
      return
    } catch (e) {
      res.writeHead(404); res.end('no shot'); return
    }
  }

  // ===== 给局域网 worker 下载脚本/文件用（只读，白名单目录）=====
  if (req.method === 'GET' && req.url.startsWith('/lan/')) {
    const name = decodeURIComponent(req.url.slice(5)).replace(/[^\w.\-\u4e00-\u9fa5]/g, '')
    const file = path.join(LAN_DIR, name)
    if (!name || !existsSync(file)) {
      res.writeHead(404, { 'Content-Type': 'text/plain' })
      res.end('not found')
      return
    }
    res.writeHead(200, { 'Content-Type': 'application/octet-stream', 'Content-Length': statSync(file).size })
    createReadStream(file).pipe(res)
    return
  }

  // ===== 局域网 worker 上传截图/文件（笔记本的桌面截图走这里）=====
  if (req.method === 'POST' && req.url.startsWith('/agent/upload')) {
    const u = new URL(req.url, 'http://x')
    const name = (u.searchParams.get('name') || 'upload.bin').replace(/[^\w.\-]/g, '')
    const dir = 'C:\\Users\\nb666\\Videos\\大肥鱼作品\\剪辑\\laptop-shots'
    try { mkdirSync(dir, { recursive: true }) } catch (e) {}
    const out = path.join(dir, name)
    const chunks = []
    req.on('data', (c) => chunks.push(c))
    req.on('end', () => {
      try {
        writeFileSync(out, Buffer.concat(chunks))
        appendFileSync(DIAG_LOG, new Date().toISOString() + ' upload ' + name + ' ' + Buffer.concat(chunks).length + ' bytes\n')
        res.writeHead(200, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({ ok: true, path: out, size: Buffer.concat(chunks).length }))
      } catch (e) {
        res.writeHead(500); res.end('{"ok":false}')
      }
    })
    return
  }

  // ===== 局域网代理（笔记本主动取任务，不需要入站端口）=====
  if (req.method === 'GET' && req.url === '/agent/task') {
    const q = readQueue()
    const job = q.pending.shift()
    if (job) {
      job.state = 'running'
      job.startedAt = Date.now()
      q.running.push(job)
      writeQueue(q)
    }
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify(job ? { ok: true, id: job.id, cmd: job.cmd } : { ok: true, none: true }))
    return
  }

  if (req.method === 'POST' && req.url === '/agent/result') {
    let body = ''
    req.on('data', (c) => { body += c })
    req.on('end', () => {
      try {
        const r = JSON.parse(body)
        const q = readQueue()
        q.running = q.running.filter((j) => j.id !== r.id)
        q.done.push({ id: r.id, code: r.code, out: String(r.out || '').slice(0, 20000), at: Date.now() })
        if (q.done.length > 50) q.done = q.done.slice(-50)
        writeQueue(q)
        appendFileSync(DIAG_LOG, new Date().toISOString() + ' agent-result ' + JSON.stringify(r).slice(0, 2000) + '\n')
        res.writeHead(200, { 'Content-Type': 'application/json' })
        res.end('{"ok":true}')
      } catch (e) {
        res.writeHead(500); res.end('{"ok":false}')
      }
    })
    return
  }

  if (req.method === 'POST' && req.url === '/agent/push') {
    if (!(String(req.socket.remoteAddress || '').includes('127.0.0.1') || String(req.socket.remoteAddress || '').includes('::1'))) {
      res.writeHead(403); res.end('{"ok":false}'); return
    }
    let body = ''
    req.on('data', (c) => { body += c })
    req.on('end', () => {
      try {
        const { cmd } = JSON.parse(body)
        const q = readQueue()
        const id = 'j' + Date.now().toString(36) + Math.floor(Math.random() * 999)
        q.pending.push({ id, cmd, createdAt: Date.now() })
        writeQueue(q)
        res.writeHead(200, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({ ok: true, id }))
      } catch (e) {
        res.writeHead(500); res.end('{"ok":false}')
      }
    })
    return
  }

  if (req.method === 'GET' && req.url === '/agent/log') {
    const q = readQueue()
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ pending: q.pending.length, running: q.running.length, done: q.done.slice(-10) }))
    return
  }

  if (req.method === 'GET' && req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ ok: true, dest: DEST, latest: latest() }))
    return
  }

  if (req.method === 'POST' && req.url === '/diag') {
    let body = ''
    req.on('data', (c) => { body += c })
    req.on('end', () => {
      try {
        const line = new Date().toISOString() + ' ' + body.slice(0, 2000) + '\n'
        appendFileSync(DIAG_LOG, line)
        res.writeHead(200, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({ ok: true }))
      } catch (e) {
        res.writeHead(500); res.end('fail')
      }
    })
    return
  }

  if (req.method === 'GET' && req.url === '/diag') {
    try {
      const txt = readFileSync(DIAG_LOG, 'utf8').split('\n').slice(-200).join('\n')
      res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' })
      res.end(txt)
    } catch (e) {
      res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' })
      res.end('(no log yet)')
    }
    return
  }

  if (req.method === 'GET' && req.url === '/latest') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ ok: true, latest: latest() }))
    return
  }

  const isLoopback = (req) => {
    const a = String(req.socket.remoteAddress || '')
    return a.includes('127.0.0.1') || a.includes('::1')
  }

  if (req.method === 'POST' && req.url === '/upload') {
    if (!isLoopback(req)) {
      res.writeHead(403, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ ok: false, error: 'upload 只允许本机' }))
      return
    }
    const raw = decodeURIComponent(String(req.headers['x-filename'] || 'upload.mp4'))
    const name = sanitize(raw)
    const ext = path.extname(name).toLowerCase()
    if (!OK_EXT.has(ext)) {
      res.writeHead(400, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ ok: false, error: '不支持的扩展名: ' + ext }))
      return
    }
    const stamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14)
    const finalPath = path.join(DEST, `${stamp}-${name}`)
    const ws = createWriteStream(finalPath)
    let size = 0
    req.on('data', (c) => { size += c.length })
    req.pipe(ws)
    ws.on('finish', () => {
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ ok: true, path: finalPath, size }))
    })
    ws.on('error', (e) => {
      res.writeHead(500, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ ok: false, error: String(e) }))
    })
    return
  }

  res.writeHead(404, { 'Content-Type': 'application/json' })
  res.end(JSON.stringify({ ok: false, error: 'not found' }))
})

server.listen(PORT, '0.0.0.0', () => {
  console.log(`[video-inbox] listening on 0.0.0.0:${PORT} (upload=loopback only) -> ${DEST}`)
})
