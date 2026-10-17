/**
 * 给已上传的 B 站投稿页补：封面、标题、简介（Quill 编辑器）。
 * 仍然**不点发布** —— 最后一步留给人。
 *
 * 用法：
 *   node tools/bili-fill.mjs --cover "C:\...\cover.png" --title "标题" --desc "简介" [--descFile 文件]
 */
import http from 'node:http'
import { readFileSync } from 'node:fs'

const PORT = Number(process.env.CDP_PORT || 9222)
const args = process.argv.slice(2)
const opt = { cover: '', title: '', desc: '', descFile: '', tags: '' }
for (let i = 0; i < args.length; i++) {
  const a = args[i]
  if (a === '--cover') opt.cover = args[++i]
  else if (a === '--title') opt.title = args[++i]
  else if (a === '--desc') opt.desc = args[++i]
  else if (a === '--descFile') opt.descFile = args[++i]
  else if (a === '--tags') opt.tags = args[++i]
}
if (opt.descFile) opt.desc = readFileSync(opt.descFile, 'utf8').replace(/^\uFEFF/, '')

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
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
  const pages = (await getJson(`http://127.0.0.1:${PORT}/json/list`)).filter((t) => t.type === 'page')
  const page = pages.find((p) => p.url.includes('member.bilibili.com')) || pages[pages.length - 1]
  if (!page) throw new Error('没找到投稿页')
  const cdp = await Cdp.connect(page.webSocketDebuggerUrl)
  await cdp.send('DOM.enable')
  await cdp.send('Runtime.enable')

  // ---- 封面（第二个 file input 一般是封面）----
  if (opt.cover) {
    const doc = await cdp.send('DOM.getDocument', { depth: -1, pierce: true })
    const all = await cdp.send('DOM.querySelectorAll', { nodeId: doc.root.nodeId, selector: 'input[type=file]' })
    const ids = all.nodeIds || []
    console.log('file input 数量:', ids.length)
    if (ids.length >= 2) {
      await cdp.send('DOM.setFileInputFiles', { nodeId: ids[1], files: [opt.cover] })
      console.log('封面已设置:', opt.cover)
      await sleep(4000)
    } else {
      console.log('!! 没找到第二个 file input，封面跳过')
    }
  }

  // ---- 标题 ----
  if (opt.title) {
    const r = await cdp.send('Runtime.evaluate', {
      expression: `(() => {
        const el = [...document.querySelectorAll('input[type=text]')].find(e => (e.placeholder||'').includes('标题'))
        if (!el) return 'no-title-input'
        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set
        setter.call(el, ${JSON.stringify(opt.title)})
        el.dispatchEvent(new Event('input', { bubbles: true }))
        el.dispatchEvent(new Event('change', { bubbles: true }))
        return 'ok:' + el.value
      })()`, returnByValue: true,
    })
    console.log('标题:', r.result.value)
  }

  // ---- 简介（Quill 编辑器：先 focus 再 insertText）----
  if (opt.desc) {
    const focus = await cdp.send('Runtime.evaluate', {
      expression: `(() => {
        const eds = [...document.querySelectorAll('.ql-editor')]
        if (!eds.length) return 'no-editor'
        eds[0].focus()
        eds[0].innerHTML = ''
        return 'focused:' + eds.length
      })()`, returnByValue: true,
    })
    console.log('编辑器:', focus.result.value)
    await sleep(300)
    // 分段输入（保留换行）
    for (const line of opt.desc.split('\n')) {
      await cdp.send('Input.insertText', { text: line })
      await cdp.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 })
      await cdp.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 })
    }
    const check = await cdp.send('Runtime.evaluate', {
      expression: `document.querySelector('.ql-editor') ? document.querySelector('.ql-editor').innerText.slice(0,60) : 'none'`,
      returnByValue: true,
    })
    console.log('简介写入:', JSON.stringify(check.result.value))
  }

  console.log('')
  console.log('请检查：封面、标题、简介、分区 → 然后你自己按「发布」')
  setTimeout(() => process.exit(0), 200)
}

main().catch((e) => { console.error('失败:', e.message); process.exit(1) })
