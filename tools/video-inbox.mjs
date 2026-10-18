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
