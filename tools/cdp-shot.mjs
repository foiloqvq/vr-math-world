/**
 * 截"真窗口"的图（Chrome 调试端口 CDP）。
 *
 * 用途：无头浏览器会被反爬拦（X、B 站投稿页都拦），但对**你开着的真实窗口**截屏没问题。
 * 所以：先 ensureChrome 打开带 --remote-debugging-port=9222 的窗口，再用这个脚本截图。
 *
 * 用法：
 *   node tools/cdp-shot.mjs --match member.bilibili.com --out C:\temp\shot.png
 *   node tools/cdp-shot.mjs --match x.com --out shot.png --eval "document.title"
 */
import http from 'node:http'
import { writeFileSync } from 'node:fs'

const PORT = Number(process.env.CDP_PORT || 9222)
const args = process.argv.slice(2)
const opt = { match: '', out: 'cdp-shot.png', eval: '', full: false }
for (let i = 0; i < args.length; i++) {
  const a = args[i]
  if (a === '--match') opt.match = args[++i]
  else if (a === '--out') opt.out = args[++i]
  else if (a === '--eval') opt.eval = args[++i]
  else if (a === '--full') opt.full = true
}

const getJson = (url) => new Promise((resolve, reject) => {
  http.get(url, (res) => {
    let d = ''
    res.on('data', (c) => (d += c))
    res.on('end', () => { try { resolve(JSON.parse(d)) } catch (e) { reject(e) } })
  }).on('error', reject)
})

class Cdp {
  constructor(ws) { this.ws = ws; this.id = 0; this.waiting = new Map() }
  static async connect(url) {
    const ws = new WebSocket(url)
    const c = new Cdp(ws)
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej })
    ws.onmessage = (ev) => {
      let m; try { m = JSON.parse(ev.data) } catch { return }
      if (m.id && c.waiting.has(m.id)) {
        const { resolve, reject } = c.waiting.get(m.id); c.waiting.delete(m.id)
        m.error ? reject(new Error(JSON.stringify(m.error))) : resolve(m.result)
      }
    }
    return c
  }
  send(method, params = {}) {
    const id = ++this.id
    this.ws.send(JSON.stringify({ id, method, params }))
    return new Promise((resolve, reject) => {
      this.waiting.set(id, { resolve, reject })
      setTimeout(() => { if (this.waiting.has(id)) { this.waiting.delete(id); reject(new Error('timeout ' + method)) } }, 60000)
    })
  }
}

const main = async () => {
  const list = await getJson(`http://127.0.0.1:${PORT}/json/list`)
  const pages = list.filter((t) => t.type === 'page')
  const page = opt.match ? pages.find((p) => p.url.includes(opt.match)) : pages[pages.length - 1]
  if (!page) {
    console.log('没找到匹配的页面。现有页面：')
    pages.forEach((p) => console.log(' -', p.url))
    process.exit(1)
  }
  const cdp = await Cdp.connect(page.webSocketDebuggerUrl)
  if (opt.eval) {
    const r = await cdp.send('Runtime.evaluate', { expression: opt.eval, returnByValue: true, awaitPromise: true })
    console.log('eval:', JSON.stringify(r.result && r.result.value))
  }
  const shot = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: !!opt.full })
  writeFileSync(opt.out, Buffer.from(shot.data, 'base64'))
  console.log('已保存:', opt.out, ' 页面:', page.url)
  setTimeout(() => process.exit(0), 200)
}

main().catch((e) => { console.error('失败:', e.message); process.exit(1) })
