/**
 * 在 B 站视频页发评论（CDP：真实聚焦 + Input.insertText 输入 + 点发送）。
 *
 * 用法：node bili-comment.mjs --bvid BV... --text-file 文本.txt
 *
 * 边界：只发一条；失败不重试；发完读接口复核并打印。
 */
import { readFileSync } from 'node:fs'

const PORT = 9222
const argv = process.argv.slice(2)
const arg = (k, d = '') => {
  const i = argv.indexOf('--' + k)
  return i >= 0 && argv[i + 1] ? argv[i + 1] : d
}
const bvid = arg('bvid')
const text = arg('text-file') ? readFileSync(arg('text-file'), 'utf8').trim() : ''
if (!bvid || !text) {
  console.error('用法：node bili-comment.mjs --bvid BV... --text-file a.txt')
  process.exit(2)
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function page() {
  const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()
  const p = list.find((x) => x.type === 'page' && x.url.includes(bvid))
  if (!p) throw new Error('找不到视频页')
  return p
}

function connect(wsUrl) {
  const ws = new WebSocket(wsUrl)
  let id = 0
  const pending = new Map()
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data)
    if (m.id && pending.has(m.id)) {
      const { res, rej } = pending.get(m.id)
      pending.delete(m.id)
      m.error ? rej(new Error(m.error.message)) : res(m.result)
    }
  }
  const ready = new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej })
  const call = (method, params = {}) => new Promise((res, rej) => {
    const myId = ++id
    pending.set(myId, { res, rej })
    ws.send(JSON.stringify({ id: myId, method, params }))
  })
  const evaluate = async (expression) => {
    const r = await call('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.text || 'eval failed')
    return r.result && r.result.value
  }
  return { ready, call, evaluate, close: () => ws.close() }
}

async function main() {
  const p = await page()
  const c = connect(p.webSocketDebuggerUrl)
  await c.ready
  await c.call('Runtime.enable')

  // 1) 滚到评论区并聚焦编辑器
  const focused = await c.evaluate(`(async () => {
    const sleep=(ms)=>new Promise(r=>setTimeout(r,ms));
    const all=(root,acc=[])=>{ for(const el of root.querySelectorAll('*')){ acc.push(el); if(el.shadowRoot) all(el.shadowRoot,acc); } return acc; };
    window.scrollTo(0, document.body.scrollHeight);
    await sleep(1800);
    const els = all(document);
    const eds = els.filter(e => e.isContentEditable && e.offsetParent !== null);
    if (!eds.length) return 'no-editor';
    const ed = eds[0];
    ed.scrollIntoView({block:'center'});
    ed.click();
    ed.focus();
    await sleep(400);
    return 'focused';
  })()`)
  console.log('聚焦:', focused)
  if (focused !== 'focused') throw new Error('没能聚焦评论框')

  // 2) 先清空编辑器（上一次残留会把两条粘在一起 —— 2026-10-18 踩过）
  const key = (type, opts) => c.call('Input.dispatchKeyEvent', Object.assign({
    type, modifiers: 0, key: '', code: '', windowsVirtualKeyCode: 0, nativeVirtualKeyCode: 0,
  }, opts))
  await key('keyDown', { key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65, nativeVirtualKeyCode: 65, modifiers: 2 })
  await key('keyUp', { key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65, nativeVirtualKeyCode: 65, modifiers: 2 })
  await sleep(200)
  await key('keyDown', { key: 'Delete', code: 'Delete', windowsVirtualKeyCode: 46, nativeVirtualKeyCode: 46 })
  await key('keyUp', { key: 'Delete', code: 'Delete', windowsVirtualKeyCode: 46, nativeVirtualKeyCode: 46 })
  await sleep(300)
  const cleared = await c.evaluate(`(() => {
    const all=(root,acc=[])=>{ for(const el of root.querySelectorAll('*')){ acc.push(el); if(el.shadowRoot) all(el.shadowRoot,acc); } return acc; };
    const eds = all(document).filter(e => e.isContentEditable && e.offsetParent !== null);
    return eds.length ? (eds[0].innerText || '').length : -1;
  })()`)
  console.log('清空后长度:', cleared)

  // 3) 真实输入
  await c.call('Input.insertText', { text })
  await sleep(600)
  const typed = await c.evaluate(`(() => {
    const all=(root,acc=[])=>{ for(const el of root.querySelectorAll('*')){ acc.push(el); if(el.shadowRoot) all(el.shadowRoot,acc); } return acc; };
    const eds = all(document).filter(e => e.isContentEditable && e.offsetParent !== null);
    return eds.length ? (eds[0].innerText || '').slice(0, 60) : '';
  })()`)
  console.log('输入框内容:', JSON.stringify(typed))
  if (!typed || typed.length < 4) throw new Error('输入没进去')

  // 4) 点「发布」
  const clicked = await c.evaluate(`(async () => {
    const sleep=(ms)=>new Promise(r=>setTimeout(r,ms));
    const all=(root,acc=[])=>{ for(const el of root.querySelectorAll('*')){ acc.push(el); if(el.shadowRoot) all(el.shadowRoot,acc); } return acc; };
    const btns = all(document).filter(e => e.offsetParent !== null && (e.tagName === 'BUTTON' || e.getAttribute('role') === 'button'));
    const send = btns.find(b => { const t = (b.textContent||'').replace(/\\s+/g,''); return t === '发布' || t === '发送'; });
    if (!send) return 'no-button:' + btns.slice(0,6).map(b=>((b.textContent||'').trim().slice(0,6))).join('|');
    send.click();
    await sleep(2500);
    return 'clicked';
  })()`)
  console.log('发送按钮:', clicked)

  if (String(clicked).startsWith('no-button')) {
    // 兜底：Ctrl+Enter 发送（B 站评论框支持）
    console.log('改用 Ctrl+Enter …')
    const key = (type, extra) => c.call('Input.dispatchKeyEvent', Object.assign({
      type, modifiers: 2, key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13,
    }, extra))
    await key('keyDown', {})
    await key('char', { text: '\r' })
    await key('keyUp', {})
    await sleep(2500)
    console.log('Ctrl+Enter 已发送')
  }
  c.close()

  // 4) 复核
  await sleep(2500)
  const j = await (await fetch(`https://api.bilibili.com/x/web-interface/view?bvid=${bvid}`,
    { headers: { 'User-Agent': 'Mozilla/5.0', Referer: 'https://www.bilibili.com/' } })).json()
  if (j.code === 0) {
    const c2 = await (await fetch(`https://api.bilibili.com/x/v2/reply?type=1&oid=${j.data.aid}&sort=0&ps=30`,
      { headers: { 'User-Agent': 'Mozilla/5.0', Referer: 'https://www.bilibili.com/' } })).json()
    const replies = c2.data?.replies || []
    const probe = text.slice(0, 10)
    const hit = replies.find((x) => (x.content.message || '').includes(probe))
    console.log('复核:', hit ? `已出现（rpid ${hit.rpid}）` : '接口暂未看到（可能审核中）')
    console.log('评论总数:', c2.data?.page?.count)
  }
}

main().catch((e) => { console.error('失败:', e.message); process.exit(1) })
