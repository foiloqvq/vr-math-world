#!/usr/bin/env node
/**
 * 大肥鱼的 MCP 服务器（零依赖，stdio 传输）。
 *
 * 作用：把已经写好的 PowerShell 工具，注册成标准的 MCP 工具，
 * 让 DSH（或任何 MCP 客户端）能直接调用，而不用每次拼命令行。
 *
 * 启动：node mcp-server.mjs        （MCP 客户端会用 stdio 跟它说话）
 *
 * 协议要点（MCP stdio 传输）：
 *   · 每条消息是**一行 JSON-RPC 2.0**（换行分隔，不是 Content-Length 帧）
 *   · 客户端发 initialize → 我们回 serverInfo + capabilities
 *   · 之后 tools/list、tools/call
 */
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import path from 'node:path'
import process from 'node:process'

const WS = 'C:\\Users\\nb666\\Documents\\deepseek-harness\\default-workspace'
const PS = 'C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe'
const TOOLS_DIR = path.join(WS, 'study-space', 'tools')

/** 跑一个 PowerShell 脚本，返回 stdout（超时会杀掉） */
function runPs(script, args = [], timeoutMs = 120000) {
  return new Promise((resolve) => {
    const p = spawn(PS, ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', path.join(TOOLS_DIR, script), ...args],
      { windowsHide: true })
    let out = ''
    let err = ''
    const timer = setTimeout(() => { try { p.kill() } catch {} }, timeoutMs)
    p.stdout.on('data', (d) => { out += d.toString('utf8') })
    p.stderr.on('data', (d) => { err += d.toString('utf8') })
    p.on('close', (code) => {
      clearTimeout(timer)
      resolve({ code, stdout: out.trim(), stderr: err.trim() })
    })
    p.on('error', (e) => { clearTimeout(timer); resolve({ code: -1, stdout: '', stderr: String(e) }) })
  })
}

const TOOLS = [
  {
    name: 'see_web',
    description: '打开一个网页并读取：返回整页截图路径 + 页面可读文字。需要登录态的站点（B站/YouTube）传 profile=dsh-see-profile-x。',
    inputSchema: {
      type: 'object',
      properties: {
        url: { type: 'string', description: '要打开的网址' },
        profile: { type: 'string', description: '登录态目录名，可选：dsh-see-profile（B站）或 dsh-see-profile-x（X/YouTube）' },
        maxChars: { type: 'number', description: '最多返回多少字，默认 1200' },
      },
      required: ['url'],
    },
  },
  {
    name: 'capture_screen',
    description: '截取当前屏幕（连拍 N 张），返回截图文件路径。用于看用户在做什么、读游戏/报错界面。',
    inputSchema: {
      type: 'object',
      properties: {
        shots: { type: 'number', description: '连拍张数，默认 3' },
        interval: { type: 'number', description: '间隔秒数，默认 1' },
        tag: { type: 'string', description: '标记，便于识别，默认 mcp' },
      },
    },
  },
  {
    name: 'read_x_post',
    description: '读取一条 X/Twitter 帖子：返回正文、图片与动图路径（动图会自动抽帧）。不走无头浏览器，抗反爬。',
    inputSchema: {
      type: 'object',
      properties: { url: { type: 'string', description: 'X 帖子链接' } },
      required: ['url'],
    },
  },
  {
    name: 'tts_speak',
    description: '用本机八千代 TTS 把一段中文合成成 wav，返回文件路径。',
    inputSchema: {
      type: 'object',
      properties: {
        text: { type: 'string', description: '要念的文字（中文）' },
        out: { type: 'string', description: '输出 wav 路径（可选）' },
      },
      required: ['text'],
    },
  },
]

const SCRIPTS = {
  see_web: async (a) => {
    const args = ['-Url', String(a.url || '')]
    if (a.profile) args.push('-ProfileDir', String(a.profile))
    if (a.maxChars) args.push('-MaxChars', String(a.maxChars))
    const r = await runPs('see.ps1', args, 180000)
    return `[exit ${r.code}]\n${r.stdout}${r.stderr ? '\n[stderr]\n' + r.stderr : ''}`
  },
  capture_screen: async (a) => {
    const args = ['-Shots', String(a.shots ?? 3), '-Interval', String(a.interval ?? 1), '-Tag', String(a.tag || 'mcp')]
    const r = await runPs('capture.ps1', args, 180000)
    return `[exit ${r.code}]\n${r.stdout}${r.stderr ? '\n[stderr]\n' + r.stderr : ''}`
  },
  read_x_post: async (a) => {
    const r = await runPs('read-x.ps1', ['-Url', String(a.url || '')], 180000)
    return `[exit ${r.code}]\n${r.stdout}${r.stderr ? '\n[stderr]\n' + r.stderr : ''}`
  },
  tts_speak: async (a) => {
    const text = String(a.text || '')
    if (!text) return '错误：text 为空'
    const out = a.out || path.join(process.env.TEMP || '.', 'mcp-tts-' + Date.now() + '.wav')
    const body = JSON.stringify({ text })
    const res = await fetch('http://127.0.0.1:7880/api/v1/tts/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
      signal: AbortSignal.timeout(120000),
    })
    if (!res.ok) return `错误：TTS HTTP ${res.status}`
    const buf = Buffer.from(await res.arrayBuffer())
    const { writeFileSync } = await import('node:fs')
    writeFileSync(out, buf)
    return `已合成：${out}（${buf.length} 字节）`
  },
}

function reply(id, result) {
  process.stdout.write(JSON.stringify({ jsonrpc: '2.0', id, result }) + '\n')
}
function replyError(id, message) {
  process.stdout.write(JSON.stringify({ jsonrpc: '2.0', id, error: { code: -32603, message } }) + '\n')
}

async function handle(msg) {
  const { id, method, params } = msg
  if (method === 'initialize') {
    reply(id, {
      protocolVersion: '2025-06-18',
      capabilities: { tools: {} },
      serverInfo: { name: 'dafeiyu-tools', version: '0.1.0' },
    })
    return
  }
  if (method === 'notifications/initialized') return
  if (method === 'tools/list') {
    reply(id, { tools: TOOLS })
    return
  }
  if (method === 'tools/call') {
    const name = params && params.name
    const args = (params && params.arguments) || {}
    const fn = SCRIPTS[name]
    if (!fn) return replyError(id, '未知工具: ' + name)
    try {
      const text = await fn(args)
      reply(id, { content: [{ type: 'text', text }] })
    } catch (e) {
      replyError(id, e && e.message ? e.message : String(e))
    }
    return
  }
  // 其它请求统一回空结果，避免客户端卡住
  if (id !== undefined) reply(id, {})
}

let buf = ''
process.stdin.setEncoding('utf8')
process.stdin.on('data', (chunk) => {
  buf += chunk
  let idx
  while ((idx = buf.indexOf('\n')) >= 0) {
    const line = buf.slice(0, idx).trim()
    buf = buf.slice(idx + 1)
    if (!line) continue
    let msg
    try { msg = JSON.parse(line) } catch { continue }
    handle(msg).catch((e) => {
      if (msg && msg.id !== undefined) replyError(msg.id, String(e))
    })
  }
})
process.stdin.on('end', () => process.exit(0))
