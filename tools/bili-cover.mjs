/**
 * 给 B 站投稿页设置封面。
 *
 * 为什么单独写：B 站的封面不是页面里现成的 file input —— 要点「添加封面」弹出对话框后
 * 才出现 image 类型的 input（2026-10-17 实测：原来那 4 个 input 全是视频/.txt/.zip）。
 */
import http from 'node:http'
import { existsSync } from 'node:fs'

const PORT = Number(process.env.CDP_PORT || 9222)
const args = process.argv.slice(2)
let cover = ''
for (let i = 0; i < args.length; i++) if (args[i] === '--cover') cover = args[++i]
if (!cover || !existsSync(cover)) { console.error('缺少 --cover 或文件不存在'); process.exit(1) }

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const getJson = (url) => new Promise((resolve, reject) => {
  http.get(url, (res) => { let d = ''; res.on('data', (c) => (d += c)); res.on('end', () => { try { resolve(JSON.parse(d)) } catch (e) { reject(e) } }) }).on('error', reject)
})

class Cdp {
  constructor(ws) { this.ws = ws; this.id = 0; this.waiting = new Map() }
  static async connect(url) {
    const ws = new WebSocket(url); const c = new Cdp(ws)
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej })
    ws.onmessage = (ev) => {
      let m; try { m = JSON.parse(ev.data) } catch { return }
      if (m.id && c.waiting.has(m.id)) { const { resolve, reject } = c.waiting.get(m.id); c.waiting.delete(m.id); m.error ? reject(new Error(JSON.stringify(m.error))) : resolve(m.result) }
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
  const pages = (await getJson(`http://127.0.0.1:${PORT}/json/list`)).filter((t) => t.type === 'page')
  const page = pages.find((p) => p.url.includes('member.bilibili.com'))
  if (!page) throw new Error('没找到投稿页')
  const cdp = await Cdp.connect(page.webSocketDebuggerUrl)
  await cdp.send('DOM.enable'); await cdp.send('Runtime.enable')

  // 1. 找「添加封面」并点它
  const clicked = await cdp.send('Runtime.evaluate', {
    expression: `(() => {
      const cands = [...document.querySelectorAll('div,span,button,a')]
        .filter(e => (e.innerText || '').trim() === '添加封面')
      if (!cands.length) return 'not-found'
      const el = cands[0]
      el.click()
      const r = el.getBoundingClientRect()
      return 'clicked@' + Math.round(r.x) + ',' + Math.round(r.y)
    })()`, returnByValue: true,
  })
  console.log('点击封面区:', clicked.result.value)
  await sleep(2000)

  // 2. 等 image 类型的 file input 出现
  let nodeId = 0
  for (let i = 0; i < 15; i++) {
    const doc = await cdp.send('DOM.getDocument', { depth: -1, pierce: true })
    const all = await cdp.send('DOM.querySelectorAll', { nodeId: doc.root.nodeId, selector: 'input[type=file]' })
    const ids = all.nodeIds || []
    for (const id of ids) {
      const attrs = await cdp.send('DOM.getAttributes', { nodeId: id })
      const a = attrs.attributes || []
      const idx = a.indexOf('accept')
      const accept = idx >= 0 ? a[idx + 1] : ''
      if (/image|\.png|\.jpg|\.jpeg/i.test(accept)) { nodeId = id; break }
    }
    if (nodeId) break
    await sleep(800)
  }
  if (!nodeId) throw new Error('没找到图片 input（封面对话框没弹出？）')

  await cdp.send('DOM.setFileInputFiles', { nodeId, files: [cover] })
  console.log('封面已设置:', cover)
  await sleep(3000)

  const state = await cdp.send('Runtime.evaluate', {
    expression: `(() => {
      const imgs = [...document.querySelectorAll('img')].filter(i => (i.src||'').startsWith('http') && i.naturalWidth > 100)
      return JSON.stringify({ 大图数量: imgs.length, 第一张: imgs[0] ? imgs[0].src.slice(0, 80) : '' })
    })()`, returnByValue: true,
  })
  console.log('页面状态:', state.result.value)
  setTimeout(() => process.exit(0), 200)
}

main().catch((e) => { console.error('失败:', e.message); process.exit(1) })
