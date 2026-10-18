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
import { appendFileSync, createWriteStream, existsSync, mkdirSync, readdirSync, readFileSync, statSync } from 'node:fs'
import path from 'node:path'

const PORT = 7891
const DEST = 'C:\\Users\\nb666\\Videos\\大肥鱼作品\\剪辑'
const DIAG_LOG = 'C:\\Users\\nb666\\Videos\\大肥鱼作品\\剪辑\\diag.log'
const OK_EXT = new Set(['.mp4', '.mov', '.mkv', '.webm', '.avi', '.gif', '.png', '.jpg', '.jpeg'])

if (!existsSync(DEST)) mkdirSync(DEST, { recursive: true })

const sanitize = (name) =>
  path.basename(String(name || 'upload.bin'))
    .replace(/[<>:"/\\|?*\x00-\x1f]/g, '_')
    .slice(0, 120)

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

  if (req.method === 'POST' && req.url === '/upload') {
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

server.listen(PORT, '127.0.0.1', () => {
  console.log(`[video-inbox] listening http://127.0.0.1:${PORT}  ->  ${DEST}`)
})
