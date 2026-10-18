/**
 * 在 B 站视频页发一条评论 / 回复（CDP 驱动，复用已登录的 dsh-see-profile）。
 *
 * 用法：
 *   node bili-reply.mjs --bvid BV1X5ng6KEbD --text "要说的话"
 *   node bili-reply.mjs --bvid ... --text "..." --reply-to 317427685873   # 回复某条
 *
 * 安全边界（写在代码里，别改歪）：
 *   · 只在**自己账号能看到的页面**操作；不翻墙、不批量刷
 *   · 发完立刻重新读评论接口，把结果打印出来（可核对）
 *   · 失败不重试（防重复发）
 */
import { spawn } from 'node:child_process'
import { existsSync, mkdirSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import process from 'node:process'

const PORT = 9222
const CHROME = [
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
].find((p) => existsSync(p))
const PROFILE = path.join(os.homedir(), 'AppData', 'Local', 'dsh-see-profile')

const argv = process.argv.slice(2)
const arg = (k, d = '') => {
  const i = argv.indexOf('--' + k)
  return i >= 0 && argv[i + 1] ? argv[i + 1] : d
}
const bvid = arg('bvid')
const text = arg('text')
const replyTo = arg('reply-to')

if (!bvid || !text) {
  console.error('用法：node bili-reply.mjs --bvid BV... --text "内容" [--reply-to rpid]')
  process.exit(2)
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function listTargets() {
  const res = await fetch(`http://127.0.0.1:${PORT}/json/list`)
  return res.json()
}

async function ensureChrome() {
  try {
    const t = await listTargets()
    if (t && t.length) return
  } catch (e) {
    /* 没在跑 */
  }
  if (!CHROME) throw new Error('找不到 chrome.exe')
  if (!existsSync(PROFILE)) mkdirSync(PROFILE, { recursive: true })
  console.log('启动 Chrome（调试端口 + 已登录配置）…')
  spawn(CHROME, [
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${PROFILE}`,
    '--no-first-run',
    '--no-default-browser-check',
    `https://www.bilibili.com/video/${bvid}/`,
  ], { detached: true, stdio: 'ignore' }).unref()
  for (let i = 0; i < 40; i++) {
    await sleep(500)
    try {
      const t = await listTargets()
      if (t.find((x) => x.type === 'page' && x.url.includes(bvid))) return
    } catch (e) {}
  }
  throw new Error('Chrome 没起来')
}

async function pickPage() {
  const t = await listTargets()
  const page = t.find((x) => x.type === 'page' && x.url.includes(bvid))
  if (!page) throw new Error('找不到视频页（可能被登录窗口占用）')
  return page
}

async function evalIn(page, expression, awaitPromise = true) {
  const ws = new WebSocket(page.webSocketDebuggerUrl)
  await new Promise((res, rej) => {
    ws.onopen = res
    ws.onerror = rej
  })
  let id = 0
  const call = (method, params) => new Promise((res, rej) => {
    const myId = ++id
    const onMsg = (ev) => {
      const m = JSON.parse(ev.data)
      if (m.id === myId) {
        ws.removeEventListener('message', onMsg)
        if (m.error) rej(new Error(m.error.message))
        else res(m.result)
      }
    }
    ws.addEventListener('message', onMsg)
    ws.send(JSON.stringify({ id: myId, method, params }))
  })
  const r = await call('Runtime.evaluate', {
    expression, awaitPromise, returnByValue: true,
  })
  ws.close()
  return r.result && r.result.value
}

const SCRIPT = `(async () => {
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  // 找准输入框：B 站评论框是 contenteditable 或 textarea
  function findBox() {
    const sels = [
      '.reply-box .bili-rich-textarea__inner',
      'div.bili-rich-textarea__inner',
      '.reply-box textarea',
      'textarea[placeholder*="善语"]',
      '.reply-box [contenteditable="true"]',
      'div[contenteditable="true"]'
    ];
    for (const s of sels) {
      const el = document.querySelector(s);
      if (el && el.offsetParent !== null) return el;
    }
    return null;
  }
  let box = findBox();
  if (!box) {
    // 先点一下"发一条友善的评论"占位，激活编辑器
    const ph = [...document.querySelectorAll('div,span')].find(e => (e.textContent||'').includes('善语结善缘') || (e.textContent||'').includes('发一条友善的评论'));
    if (ph) { ph.click(); await sleep(600); }
    box = findBox();
  }
  if (!box) return { ok: false, why: 'no-input' };
  box.focus();
  if (box.tagName === 'TEXTAREA' || box.tagName === 'INPUT') {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
    setter.call(box, __TEXT__);
    box.dispatchEvent(new Event('input', { bubbles: true }));
  } else {
    box.innerHTML = '';
    const p = document.createElement('p');
    p.textContent = __TEXT__;
    box.appendChild(p);
    box.dispatchEvent(new InputEvent('input', { bubbles: true }));
  }
  await sleep(500);
  // 找发送按钮
  const btns = [...document.querySelectorAll('button,div[role="button"],span')];
  const send = btns.find(b => {
    const t = (b.textContent || '').trim();
    return (t === '发布' || t === '发送' || t === '评论') && b.offsetParent !== null
      && !b.disabled;
  });
  if (!send) return { ok: false, why: 'no-send-button' };
  send.click();
  await sleep(2500);
  return { ok: true, clicked: (send.textContent || '').trim() };
})()`

async function main() {
  await ensureChrome()
  await sleep(2500)
  const page = await pickPage()
  console.log('页面:', page.url.slice(0, 80))

  // 若是回复某条评论，先滚到那条
  if (replyTo) {
    await evalIn(page, `(() => { const el = document.querySelector('[data-rpid="${replyTo}"]'); if (el) { el.scrollIntoView({block:'center'}); return 'scrolled'; } return 'not-found'; })()`)
    await sleep(1200)
  }

  const script = SCRIPT.replace('__TEXT__', JSON.stringify(text))
  const r = await evalIn(page, script)
  console.log('发送结果:', JSON.stringify(r))

  // 复核：读评论接口，看有没有出现这句话
  await sleep(2000)
  const j = await (await fetch(
    `https://api.bilibili.com/x/web-interface/view?bvid=${bvid}`,
    { headers: { 'User-Agent': 'Mozilla/5.0', Referer: 'https://www.bilibili.com/' } },
  )).json()
  if (j.code === 0) {
    const aid = j.data.aid
    const c = await (await fetch(
      `https://api.bilibili.com/x/v2/reply?type=1&oid=${aid}&sort=0&ps=20`,
      { headers: { 'User-Agent': 'Mozilla/5.0', Referer: 'https://www.bilibili.com/' } },
    )).json()
    const hit = (c.data?.replies || []).find((x) => (x.content.message || '').includes(text.slice(0, 8)))
    console.log('复核:', hit ? `已出现在评论区（rpid ${hit.rpid}）` : '评论区接口还没看到（可能有审核延迟）')
    console.log('当前评论数:', c.data?.page?.count)
  }
}

main().catch((e) => {
  console.error('失败:', e.message)
  process.exit(1)
})
