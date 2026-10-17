/**
 * 通过 Chrome DevTools Protocol 把视频"塞进" B 站投稿页。
 *
 * 为什么用 CDP 而不是无头浏览器：无头会被 B 站风控；而且投稿需要**已登录的真实窗口**。
 * 所以流程是：先用真窗口（专用配置）打开投稿页，再用 CDP 连上去操作它 —— 相当于
 * "我伸一只手到你开着的那个浏览器里"，不需要模拟登录。
 *
 * 用法：
 *   node tools/bili-upload.mjs --file "C:\path\video.mp4" --title "标题" --desc "简介"
 *   node tools/bili-upload.mjs --file ... --dry      # 只看能不能找到投稿页/控件
 *
 * 注意：
 *   · 需要先启动带 --remote-debugging-port=9222 的 Chrome（脚本里会自动开）
 *   · **最后一步「发布」不会自动点** —— 这一步必须人按（账号责任在人）
 */
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import http from 'node:http'

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
const PROFILE = process.env.LOCALAPPDATA + '\\dsh-see-profile'
const UPLOAD_URL = 'https://member.bilibili.com/platform/upload/video/frame'
const PORT = 9222

const args = process.argv.slice(2)
const opt = { file: '', title: '', desc: '', dry: false, timeout: 60000 }
for (let i = 0; i < args.length; i++) {
  const a = args[i]
  if (a === '--file') opt.file = args[++i]
  else if (a === '--title') opt.title = args[++i]
  else if (a === '--desc') opt.desc = args[++i]
  else if (a === '--dry') opt.dry = true
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let data = ''
      res.on('data', (c) => (data += c))
      res.on('end', () => {
        try { resolve(JSON.parse(data)) } catch (e) { reject(e) }
      })
    }).on('error', reject)
  })
}

async function ensureChrome() {
  try {
    await getJson(`http://127.0.0.1:${PORT}/json/version`)
    return 'already-running'
  } catch {}
  spawn(CHROME, [`--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE}`,
                 '--no-first-run', '--no-default-browser-check', UPLOAD_URL],
        { detached: true, stdio: 'ignore' }).unref()
  for (let i = 0; i < 30; i++) {
    await sleep(500)
    try { await getJson(`http://127.0.0.1:${PORT}/json/version`); return 'started' } catch {}
  }
  throw new Error('Chrome 调试端口没起来（可能被别的实例占用）')
}

class Cdp {
  constructor(ws) { this.ws = ws; this.id = 0; this.waiting = new Map() }
  static async connect(wsUrl) {
    const ws = new WebSocket(wsUrl)
    const c = new Cdp(ws)
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej })
    ws.onmessage = (ev) => {
      let msg
      try { msg = JSON.parse(ev.data) } catch { return }
      if (msg.id && c.waiting.has(msg.id)) {
        const { resolve, reject } = c.waiting.get(msg.id)
        c.waiting.delete(msg.id)
        if (msg.error) reject(new Error(JSON.stringify(msg.error)))
        else resolve(msg.result)
      }
    }
    return c
  }
  send(method, params = {}) {
    const id = ++this.id
    this.ws.send(JSON.stringify({ id, method, params }))
    return new Promise((resolve, reject) => {
      this.waiting.set(id, { resolve, reject })
      setTimeout(() => {
        if (this.waiting.has(id)) {
          this.waiting.delete(id)
          reject(new Error('CDP 超时: ' + method))
        }
      }, opt.timeout)
    })
  }
}

async function main() {
  if (!opt.file) throw new Error('缺少 --file')
  if (!existsSync(opt.file)) throw new Error('文件不存在: ' + opt.file)

  console.log('启动/复用 Chrome …', await ensureChrome())
  await sleep(1500)

  let targets = await getJson(`http://127.0.0.1:${PORT}/json/list`)
  let page = targets.find((t) => t.type === 'page' && /member\.bilibili\.com/.test(t.url))
  if (!page) {
    // 没有投稿页就开一个新的
    const created = await getJson(`http://127.0.0.1:${PORT}/json/new?${encodeURIComponent(UPLOAD_URL)}`)
    page = created
    await sleep(6000)
  }
  console.log('目标页面:', page.url)

  const cdp = await Cdp.connect(page.webSocketDebuggerUrl)
  await cdp.send('DOM.enable')
  await cdp.send('Runtime.enable')
  await sleep(2500)

  // 等页面上的 file input 出现（B 站是隐藏的 input）
  let nodeId = 0
  for (let i = 0; i < 20; i++) {
    const doc = await cdp.send('DOM.getDocument', { depth: -1, pierce: true })
    const q = await cdp.send('DOM.querySelector', { nodeId: doc.root.nodeId, selector: 'input[type=file]' })
    if (q.nodeId) { nodeId = q.nodeId; break }
    await sleep(1000)
  }
  if (!nodeId) throw new Error('找不到 input[type=file]（页面没加载好，或被登录页挡住）')
  console.log('找到文件输入框 nodeId=', nodeId)

  if (opt.dry) { console.log('（dry：不设置文件）'); return }

  await cdp.send('DOM.setFileInputFiles', { nodeId, files: [opt.file] })
  console.log('已设置文件:', opt.file)

  // 等上传开始（B 站的进度条/表单出现）
  await sleep(6000)

  // 填标题/简介：找可编辑的输入框
  const fill = await cdp.send('Runtime.evaluate', {
    expression: `(() => {
      const setNative = (el, v) => {
        const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype
        const setter = Object.getOwnPropertyDescriptor(proto, 'value').set
        setter.call(el, v)
        el.dispatchEvent(new Event('input', { bubbles: true }))
        el.dispatchEvent(new Event('change', { bubbles: true }))
      }
      const inputs = [...document.querySelectorAll('input[type=text], input:not([type]), textarea')]
      const titleEl = inputs.find(e => (e.placeholder||'').includes('标题')) || inputs[0]
      const descEl = [...document.querySelectorAll('textarea')].find(e => (e.placeholder||'').includes('简介'))
        || [...document.querySelectorAll('textarea')].pop()
      let t = false, d = false
      if (titleEl) { setNative(titleEl, ${JSON.stringify(opt.title || '')}); t = true }
      if (descEl) { setNative(descEl, ${JSON.stringify(opt.desc || '')}); d = true }
      return JSON.stringify({ title: t, desc: d, inputs: inputs.length,
        textareas: document.querySelectorAll('textarea').length })
    })()`,
    returnByValue: true,
  })
  console.log('填表结果:', fill.result.value)
  console.log('')
  console.log('接下来请你：① 检查标题/简介/分区 ② 上传封面 ③ 自己按「发布」')
  console.log('（发布我不代按 —— 账号是你的，责任也是你的）')
}

main().then(() => setTimeout(() => process.exit(0), 300)).catch((e) => { console.error('失败:', e.message); process.exit(1) })
