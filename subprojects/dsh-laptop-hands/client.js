/**
 * dsh-laptop-hands v0.1 — 大肥鱼的「手和眼」
 *
 * 干什么：在 DSH 界面右下角放一个小面板，显示笔记本的实时状态 + 最新截图，
 * 并且能一键让它截屏 / 鼠标点击 / 键盘打字。
 *
 * 数据从哪来：本机 127.0.0.1:7891 上的 video-inbox 服务
 *   GET  /agent/state        队列 + 最新截图信息
 *   GET  /agent/latest-shot  最新截图（png）
 *   POST /agent/push         { cmd } 推一条命令给笔记本 worker
 *
 * 设计原则（稳定性优先）：
 *   1. 所有 DOM / fetch 全部 try-catch，插件永远不会把 GUI 弄崩
 *   2. 不注入 DSH 的 React 树，只用独立 DOM 面板 + 内联样式
 *   3. 服务不可达时只把状态显示成「离线」，不抛错
 */
window.__ModuleLoader__.load({
  id: 'dsh-laptop-hands',
  factory: (require) => {
    var module = { exports: {} }
    var exports = module.exports

    const VERSION = '0.1.0'
    const BASE = 'http://127.0.0.1:7891'
    const POLL_MS = 3000

    const log = (...args) => {
      try { console.log('[laptop-hands]', ...args) } catch (e) {}
    }

    const el = (tag, style, text) => {
      const n = document.createElement(tag)
      if (style) n.setAttribute('style', style)
      if (text !== undefined) n.textContent = text
      return n
    }

    const pushTask = async (cmd) => {
      const res = await fetch(BASE + '/agent/push', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cmd }),
      })
      if (!res.ok) throw new Error('push HTTP ' + res.status)
      return res.json()
    }

    const state = {
      panel: null,
      body: null,
      statusEl: null,
      img: null,
      timer: null,
      minimized: false,
      lastShotAt: 0,
    }

    const cssPanel =
      'position:fixed;right:16px;bottom:16px;z-index:2147483000;width:300px;' +
      'background:rgba(10,14,24,.94);color:#e6eeff;border:1px solid #2a3a5c;border-radius:12px;' +
      'font:12px/1.5 system-ui,"Microsoft YaHei",sans-serif;box-shadow:0 8px 30px rgba(0,0,0,.45);' +
      'backdrop-filter:blur(6px);overflow:hidden'

    const cssHeader =
      'display:flex;align-items:center;gap:8px;padding:8px 10px;background:#131c2e;' +
      'border-bottom:1px solid #22304c;cursor:move;user-select:none'

    const cssBtn =
      'background:#16233a;color:#cfe3ff;border:1px solid #2b3f60;border-radius:8px;' +
      'padding:4px 8px;font-size:12px;cursor:pointer'

    const cssInput =
      'background:#0e1523;color:#e6eeff;border:1px solid #2b3f60;border-radius:6px;' +
      'padding:3px 6px;font-size:12px;width:100%;box-sizing:border-box'

    const btn = (label, onClick) => {
      const b = el('button', cssBtn, label)
      b.addEventListener('click', async () => {
        try { await onClick() } catch (e) { setStatus('失败：' + (e && e.message ? e.message : e), true) }
      })
      return b
    }

    const setStatus = (text, isError) => {
      try {
        if (!state.statusEl) return
        state.statusEl.textContent = text
        state.statusEl.style.color = isError ? '#ff9ec7' : '#8fd8b0'
      } catch (e) {}
    }

    const refresh = async () => {
      try {
        const res = await fetch(BASE + '/agent/state', { cache: 'no-store' })
        if (!res.ok) throw new Error('state HTTP ' + res.status)
        const s = await res.json()
        const shotInfo = s.shot
        let txt = '在线 · 队列 ' + s.pending + ' 跑中 ' + s.running
        if (shotInfo) {
          const age = Math.max(0, Math.round((Date.now() - shotInfo.at) / 1000))
          txt += ' · 截图 ' + age + 's 前'
        } else {
          txt += ' · 还没截图'
        }
        setStatus(txt, false)
        if (shotInfo && shotInfo.at !== state.lastShotAt) {
          state.lastShotAt = shotInfo.at
          if (state.img) state.img.src = BASE + '/agent/latest-shot?t=' + shotInfo.at
        }
      } catch (e) {
        setStatus('离线（7891 没响应）', true)
      }
    }

    const buildPanel = () => {
      const panel = el('div', cssPanel)
      const header = el('div', cssHeader)
      const title = el('div', 'flex:1;font-weight:600;color:#6ee6eb', '🖐 笔记本手眼')
      const ver = el('div', 'color:#5f7292;font-size:11px', 'v' + VERSION)
      const minBtn = el('button', cssBtn, '—')
      minBtn.addEventListener('click', () => {
        state.minimized = !state.minimized
        state.body.style.display = state.minimized ? 'none' : 'block'
        minBtn.textContent = state.minimized ? '+' : '—'
      })
      header.appendChild(title)
      header.appendChild(ver)
      header.appendChild(minBtn)

      const body = el('div', 'padding:10px;display:flex;flex-direction:column;gap:8px')
      const status = el('div', 'color:#8fd8b0;font-size:11px', '连接中…')

      const img = el('img', 'width:100%;border-radius:8px;border:1px solid #22304c;display:block;background:#0b1220')
      img.alt = '笔记本桌面'

      const row1 = el('div', 'display:flex;gap:6px')
      row1.appendChild(btn('📷 截屏', async () => {
        await pushTask('powershell -NoProfile -ExecutionPolicy Bypass -File D:\\DaFeiyu\\ctl.ps1 -Action shot -Name plugin-shot.png')
        setStatus('已推：截屏', false)
      }))
      row1.appendChild(btn('↻ 刷新', refresh))

      const xyRow = el('div', 'display:flex;gap:6px;align-items:center')
      const xIn = el('input', cssInput); xIn.placeholder = 'x'; xIn.value = '960'
      const yIn = el('input', cssInput); yIn.placeholder = 'y'; yIn.value = '540'
      xyRow.appendChild(xIn)
      xyRow.appendChild(yIn)
      xyRow.appendChild(btn('🖱 点击', async () => {
        const x = parseInt(xIn.value, 10); const y = parseInt(yIn.value, 10)
        if (!Number.isFinite(x) || !Number.isFinite(y)) throw new Error('坐标不合法')
        await pushTask('powershell -NoProfile -ExecutionPolicy Bypass -File D:\\DaFeiyu\\ctl.ps1 -Action click -X ' + x + ' -Y ' + y)
        setStatus('已推：点击 ' + x + ',' + y, false)
      }))

      const textRow = el('div', 'display:flex;gap:6px')
      const tIn = el('input', cssInput); tIn.placeholder = '要打的字'
      textRow.appendChild(tIn)
      textRow.appendChild(btn('⌨️ 打字', async () => {
        const t = String(tIn.value || '')
        if (!t) throw new Error('文字为空')
        await pushTask('powershell -NoProfile -ExecutionPolicy Bypass -File D:\\DaFeiyu\\ctl.ps1 -Action type -Text "' + t.replace(/"/g, '`"') + '"')
        setStatus('已推：打字', false)
      }))

      body.appendChild(status)
      body.appendChild(img)
      body.appendChild(row1)
      body.appendChild(xyRow)
      body.appendChild(textRow)
      body.appendChild(el('div', 'color:#5f7292;font-size:11px', '只在本机 7891 上工作；笔记本离线时按钮无效'))

      panel.appendChild(header)
      panel.appendChild(body)
      document.body.appendChild(panel)

      state.panel = panel
      state.body = body
      state.statusEl = status
      state.img = img
    }

    const apply = () => {
      try {
        if (typeof document === 'undefined') return
        if (window.__dshLaptopHands) return // 幂等：重复 apply 直接跳过
        buildPanel()
        state.timer = setInterval(refresh, POLL_MS)
        refresh()
        window.__dshLaptopHands = {
          version: VERSION,
          refresh,
          push: pushTask,
          panel: state.panel,
        }
        log('ready v' + VERSION)
      } catch (e) {
        log('apply failed', e)
      }
    }

    exports.apply = apply
    exports.inject = []
    return module.exports
  },
})
