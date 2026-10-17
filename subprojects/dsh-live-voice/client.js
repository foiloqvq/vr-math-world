/**
 * dsh-live-voice —— 语音通话模式（一直听着 → 说完自动提交 → 回复读完继续听）
 *
 * 把「点击录音」的语音输入变成打电话那种体感。
 *
 * 本文件是 DSH 客户端插件模块（模块加载器格式），但写法是标准 ESM，
 * 所以 __test 里的纯逻辑可以直接 node --test 跑。
 *
 * 排障：所有关键步骤都写进 window.__dshLiveVoice.diag（环形缓冲，最多 200 条），
 *       并同步 console.log 一行 [live-voice] diag …，
 *       所以「到哪一步断了」在控制台里是可见的，不用靠猜。
 */
window.__ModuleLoader__.load({
  id: 'dsh-live-voice',
  factory: (require) => {
    var module = { exports: {} }
    var exports = module.exports
    Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' })
    const react = require('react')

    // =====================================================================
    // 一、纯逻辑（可单测）
    // =====================================================================

    /** 一块 PCM 的 RMS（0..1）。 */
    const rmsOf = (frames) => {
      let sum = 0
      for (let i = 0; i < frames.length; i++) sum += frames[i] * frames[i]
      return frames.length ? Math.sqrt(sum / frames.length) : 0
    }

    /** 自适应噪声本底：先校准，之后静音缓慢跟随。 */
    const createNoiseFloor = (opts) => {
      const o = opts || {}
      const blockMs = o.blockMs === undefined ? 16 : o.blockMs
      const calibrationMs = o.calibrationMs === undefined ? 600 : o.calibrationMs
      const calibrateBlocks = Math.max(1, Math.round(calibrationMs / blockMs))
      const followUp = o.followUp === undefined ? 0.02 : o.followUp
      const followDown = o.followDown === undefined ? 0.08 : o.followDown
      const samples = []
      let floor = null
      const feed = (rms) => {
        if (floor === null) {
          samples.push(rms)
          if (samples.length >= calibrateBlocks) {
            const sorted = samples.slice().sort((a, b) => a - b)
            floor = sorted[Math.floor(sorted.length / 2)]
          }
          return { floor, calibrating: floor === null }
        }
        const rate = rms > floor ? followUp : followDown
        floor = floor + (rms - floor) * rate
        return { floor, calibrating: false }
      }
      return { feed, get floor() { return floor }, get calibrating() { return floor === null } }
    }

    /**
     * 断句器：把连续 16ms 块切成「一句」。
     * 事件：none / start / end（成了）/ drop（太短或超长丢）/ blocked（被屏蔽）
     */
    const createEndpointer = (opts) => {
      const o = opts || {}
      const blockMs = o.blockMs === undefined ? 16 : o.blockMs
      const silenceMs = o.silenceMs === undefined ? 700 : o.silenceMs
      const minSpeechMs = o.minSpeechMs === undefined ? 250 : o.minSpeechMs
      const maxUtteranceMs = o.maxUtteranceMs === undefined ? 20000 : o.maxUtteranceMs
      const threshold = o.threshold === undefined ? 3 : o.threshold
      const absFloor = o.absFloor === undefined ? 0.006 : o.absFloor
      const silenceBlocks = Math.max(1, Math.round(silenceMs / blockMs))
      const minSpeechBlocks = Math.max(1, Math.round(minSpeechMs / blockMs))
      const maxBlocks = Math.max(2, Math.round(maxUtteranceMs / blockMs))

      let speaking = false
      let speechBlocks = 0
      let quietBlocks = 0

      const feed = (rms, noiseFloor, blocked) => {
        if (blocked) {
          const wasSpeaking = speaking
          speaking = false; speechBlocks = 0; quietBlocks = 0
          return { event: wasSpeaking ? 'drop' : 'blocked', level: 0 }
        }
        const floor = noiseFloor === null || noiseFloor === undefined ? 0 : noiseFloor
        const gate = Math.max(floor * threshold, absFloor)
        const loud = rms >= gate

        if (!speaking) {
          if (!loud) return { event: 'none', level: 0 }
          speaking = true; speechBlocks = 1; quietBlocks = 0
          return { event: 'start', level: 1 }
        }
        if (loud) { speechBlocks++; quietBlocks = 0 } else { quietBlocks++ }
        if (speechBlocks >= maxBlocks) {
          const blocks = speechBlocks
          speaking = false; speechBlocks = 0; quietBlocks = 0
          return { event: 'end', level: 0, reason: 'max', blocks }
        }
        if (quietBlocks >= silenceBlocks) {
          const blocks = speechBlocks
          speaking = false; speechBlocks = 0; quietBlocks = 0
          return { event: blocks >= minSpeechBlocks ? 'end' : 'drop', level: 0, blocks }
        }
        return { event: 'none', level: 1 }
      }

      return {
        feed,
        get speaking() { return speaking },
        get speechBlocks() { return speechBlocks },
      }
    }

    // =====================================================================
    // 二、音频工具
    // =====================================================================

    /** Float32(16k) → WAV(mono/16bit) 的 ArrayBuffer。 */
    const encodeWav = (pcm16k) => {
      const n = pcm16k.length
      const buf = new ArrayBuffer(44 + n * 2)
      const v = new DataView(buf)
      const put = (off, s) => { for (let i = 0; i < s.length; i++) v.setUint8(off + i, s.charCodeAt(i)) }
      put(0, 'RIFF'); v.setUint32(4, 36 + n * 2, true); put(8, 'WAVE')
      put(12, 'fmt '); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true)
      v.setUint32(24, 16000, true); v.setUint32(28, 32000, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true)
      put(36, 'data'); v.setUint32(40, n * 2, true)
      let off = 44
      for (let i = 0; i < n; i++) {
        const s = Math.max(-1, Math.min(1, pcm16k[i]))
        v.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7fff, true)
        off += 2
      }
      return buf
    }

    const toBase64 = (arrayBuffer) => {
      const bytes = new Uint8Array(arrayBuffer)
      let bin = ''
      const CH = 0x8000
      for (let i = 0; i < bytes.length; i += CH) {
        bin += String.fromCharCode.apply(null, bytes.subarray(i, i + CH))
      }
      return btoa(bin)
    }

    /** 从任意节点形状里抽文字（防御式）。 */
    const extractNodeText = (n) => {
      if (!n) return ''
      if (typeof n === 'string') return n
      if (Array.isArray(n)) return n.map(extractNodeText).filter(Boolean).join('\n')
      if (typeof n !== 'object') return ''
      if (typeof n.text === 'string' && n.text) return n.text
      if (typeof n.markdown === 'string' && n.markdown) return n.markdown
      if (n.content !== undefined) {
        const t = extractNodeText(n.content)
        if (t) return t
      }
      for (const k of ['blocks', 'parts', 'children', 'message', 'node']) {
        if (n[k] !== undefined) {
          const t = extractNodeText(n[k])
          if (t) return t
        }
      }
      return ''
    }

    /**
     * 只取「要给用户看的正文」。
     *
     * 为什么单独写一个：2026-10-17 实机把 reasoning（我的思考）和诊断文本当正文念了出来，
     * 用户听到的是 "Need to fix the host from serving…" 这种英文日志。
     * 所以这里**严格**按 content 数组里的块类型过滤：只要 type === 'text'，
     * 跳过 reasoning / tool-call / tool-result / thinking 等所有其它块。
     */
    const extractAssistantText = (node) => {
      if (!node || typeof node !== 'object') return ''
      const content = node.content
      if (typeof content === 'string') return content.trim()
      if (Array.isArray(content)) {
        const parts = []
        for (const part of content) {
          if (!part) continue
          if (typeof part === 'string') { parts.push(part); continue }
          if (typeof part !== 'object') continue
          const type = String(part.type || part.kind || '').toLowerCase()
          if (type === 'text' || type === 'markdown' || type === 'output_text') {
            const t = typeof part.text === 'string' ? part.text : (typeof part.markdown === 'string' ? part.markdown : '')
            if (t && t.trim()) parts.push(t.trim())
            continue
          }
          // 明确的非正文块：跳过 reasoning / thinking / tool-call / tool-result / image 等
          if (/reason|think|tool|call|result|image|attachment|file|error/.test(type)) continue
          if (typeof part.text === 'string' && part.text.trim()) parts.push(part.text.trim())
        }
        if (parts.length) return parts.join('\n').trim()
        return ''
      }
      // 有些快照直接把正文放在 node.text / node.markdown 上（没有 content 数组）
      if (typeof node.text === 'string' && node.text.trim()) return node.text.trim()
      if (typeof node.markdown === 'string' && node.markdown.trim()) return node.markdown.trim()
      return ''
    }

    /** 快照里找节点数组（不同 hook 形状不同）。 */
    const pickNodeList = (snap) => {
      if (!snap || typeof snap !== 'object') return null
      const keys = ['nodes', 'messages', 'timeline', 'entries', 'eventNodes', 'items', 'transcript']
      for (const k of keys) if (Array.isArray(snap[k])) return snap[k]
      for (const k of ['conversation', 'chat', 'projection', 'trajectory', 'view', 'data']) {
        const v = snap[k]
        if (v && typeof v === 'object') {
          for (const k2 of keys) if (Array.isArray(v[k2])) return v[k2]
        }
      }
      return null
    }

    const isAssistantNode = (n) => {
      if (!n || typeof n !== 'object') return false
      const role = n.kind !== undefined ? n.kind : (n.role !== undefined ? n.role : n.type)
      if (role === undefined || role === null) return false
      const s = String(role).toLowerCase()
      return s === 'assistant' || s === 'agent' || s === 'model' || s === 'ai' || s.indexOf('assistant') >= 0
    }

    /** 从一组快照读「最新 assistant 文本」与「agent 是否在干活」。 */
    const readSessionState = (snaps) => {
      let latest = ''
      let active = false
      for (const entry of snaps || []) {
        const s = entry && entry.snap
        if (!s || typeof s !== 'object') continue
        if (s.running === true) active = true
        for (const k of ['queue', 'pendingSubmissions', 'steering']) {
          if (Array.isArray(s[k]) && s[k].length) active = true
        }
        if (s.partial !== undefined && s.partial !== null) active = true
        const nodes = pickNodeList(s)
        if (!nodes) continue
        for (let i = nodes.length - 1; i >= 0; i--) {
          const n = nodes[i]
          if (isAssistantNode(n)) {
            const t = extractAssistantText(n)
            if (t) { latest = t; break }
          }
        }
      }
      return { latest, active }
    }

    // =====================================================================
    // 三、浏览器侧运行时
    // =====================================================================

    const AUDIO_WORKLET_SOURCE = [
      'class PcmTap extends AudioWorkletProcessor {',
      '  process(inputs) {',
      '    const ch = inputs && inputs[0] && inputs[0][0]',
      '    if (ch && ch.length) {',
      '      const copy = new Float32Array(ch.length)',
      '      copy.set(ch)',
      '      this.port.postMessage(copy, [copy.buffer])',
      '    }',
      '    return true',
      '  }',
      '}',
      "registerProcessor('dsh-live-voice-tap', PcmTap)",
    ].join('\n')

    const createRuntime = (opts) => {
      const o = opts || {}
      const onEvent = o.onEvent || (() => {})
      const onUtterance = o.onUtterance || (() => {})
      const blockMs = 16
      const framesPerBlock = Math.round((16000 * blockMs) / 1000)

      const floorTracker = createNoiseFloor({ blockMs, calibrationMs: o.calibrationMs })
      const endpointer = createEndpointer({
        blockMs,
        silenceMs: o.silenceMs,
        minSpeechMs: o.minSpeechMs,
        maxUtteranceMs: o.maxUtteranceMs,
        threshold: o.threshold,
        absFloor: o.absFloor,
      })

      let actx = null
      let stream = null
      let node = null
      let source = null
      let running = false
      let blocked = false
      let pcm = []
      let pending = []
      let pendingLen = 0
      const stats = { blocks: 0, utterances: 0, drops: 0, blockedDrops: 0, peak: 0, lastRms: 0, floor: null, lastVoiceAt: 0 }

      const handleBlock = (frames) => {
        stats.blocks++
        const rms = rmsOf(frames)
        stats.lastRms = rms
        if (rms > stats.peak) stats.peak = rms
        const fl = floorTracker.feed(rms)
        stats.floor = fl.floor
        const res = endpointer.feed(rms, fl.floor, blocked)
        if (res.event === 'start') {
          pcm = []
          stats.lastVoiceAt = Date.now()
          onEvent({ type: 'speech-start' })
        }
        if (endpointer.speaking) {
          stats.lastVoiceAt = Date.now()
          for (let i = 0; i < frames.length; i++) pcm.push(frames[i])
        }
        if (res.event === 'end') {
          stats.utterances++
          const samples = pcm
          pcm = []
          onEvent({ type: 'speech-end', samples: samples.length })
          if (samples.length) onUtterance(samples)
        } else if (res.event === 'drop') {
          if (res.blocks !== undefined) { stats.drops++ } else { stats.blockedDrops++ }
          pcm = []
          onEvent({ type: 'speech-drop', reason: res.reason || 'too-short', blocks: res.blocks })
        }
      }

      const start = async () => {
        if (running) return
        if (!navigator || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          throw new Error('当前环境不支持麦克风')
        }
        const audioConstraints = {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
        }
        // 指定设备（App 侧会尽量挑掉"虚拟音频设备/立体声混音"这类没有声音的输入）
        if (o.deviceId) audioConstraints.deviceId = { exact: o.deviceId }
        stream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints })
        const AC = window.AudioContext || window.webkitAudioContext
        actx = new AC({ sampleRate: 16000 })
        if (actx.state === 'suspended') { try { await actx.resume() } catch (e) {} }
        const url = URL.createObjectURL(new Blob([AUDIO_WORKLET_SOURCE], { type: 'application/javascript' }))
        await actx.audioWorklet.addModule(url)
        URL.revokeObjectURL(url)
        source = actx.createMediaStreamSource(stream)
        node = new AudioWorkletNode(actx, 'dsh-live-voice-tap')
        node.port.onmessage = (ev) => {
          const frames = ev.data
          if (!frames || !frames.length) return
          for (let i = 0; i < frames.length; i++) pending.push(frames[i])
          pendingLen += frames.length
          while (pendingLen >= framesPerBlock) {
            const block = new Float32Array(framesPerBlock)
            for (let i = 0; i < framesPerBlock; i++) block[i] = pending[i]
            pending = pending.slice(framesPerBlock)
            pendingLen -= framesPerBlock
            handleBlock(block)
          }
        }
        source.connect(node)   // 不接 destination：不听自己
        running = true
        onEvent({
          type: 'listening',
          sampleRate: actx.sampleRate,
          state: actx.state,
          trackLabel: (stream.getAudioTracks()[0] || {}).label || '',
        })
      }

      const stop = async () => {
        running = false
        try { if (node) node.port.onmessage = null } catch (e) {}
        try { if (source) source.disconnect() } catch (e) {}
        try { if (node) node.disconnect() } catch (e) {}
        try { if (actx) await actx.close() } catch (e) {}
        try { if (stream) stream.getTracks().forEach((t) => t.stop()) } catch (e) {}
        actx = null; stream = null; node = null; source = null
        pcm = []; pending = []; pendingLen = 0
        onEvent({ type: 'idle' })
      }

      return {
        start, stop,
        setBlocked: (v) => { blocked = !!v },
        get running() { return running },
        get blocked() { return blocked },
        stats,
      }
    }

    /** 本机八千代 TTS 合成 → 音频字节（调用方包成 blob 播）。 */
    const synthSpeech = async (text, fetchImpl, url) => {
      const f = fetchImpl || fetch
      const res = await f(url || 'http://127.0.0.1:7880/api/v1/tts/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
      if (!res.ok) throw new Error('TTS HTTP ' + res.status)
      const buf = await res.arrayBuffer()
      if (!buf || buf.byteLength < 100) throw new Error('TTS 返回过小')
      return { buffer: buf, mime: 'audio/wav' }
    }

    // =====================================================================
    // 四、客户端插件
    // =====================================================================

    /**
     * 构建戳：**每次改动都必须改这个字符串**。
     * 为什么：客户端模块会被浏览器/loader 缓存，出问题时分不清"跑的是哪版代码"，
     * 就变成瞎猜（2026-10-17 就吃过这个亏：按钮还显示英文 error，说明新代码没生效）。
     * **2026-10-17 起按钮上不再显示它**（foilo 嫌占地方）——只出现在 title / 控制台 / 报错条里。
     */
    const BUILD = '2026-10-17.10'

    // 依赖声明（照 app 内部的写法：`inject = ['remote', 'remote.job']`）：
    // - 'slots'           ：输入行的 slot 注册
    // - 'remote'          ：Remote 服务本体
    // - 'remote.speech'   ：语音识别命名空间 —— **必须单独声明**，
    //                       少了它取 ctx.remote.speech 就是抛错
    //                       （2026-10-17 报 "cannot get property \"remote.speech\" without inject"）
    const inject = ['slots', 'remote', 'remote.speech', 'remote.session']

    /** 默认参数；可在 window.__dshLiveVoiceConfig 上覆盖（调试用）。 */
    const DEFAULTS = {
      // 判停：说完多久没声音就算一句说完。
      // 2026-10-17 从 700 提到 1200 —— foilo 说话时"想一想"的停顿被当成说完，
      // 于是发出去的句子全是半截（"呃，就是我的。"）。宁可多等半秒，也别切人话。
      silenceMs: 1200,
      minSpeechMs: 300,
      maxUtteranceMs: 20000,
      calibrationMs: 600,
      // 触发门限：相对噪声本底的倍数 + 绝对下限。
      // 2026-10-17 实测：3.0 对耳麦偏保守（正常说话会不过阈值被丢），降到 2.0；
      // 绝对下限 0.006 对音量小的耳机也太高，降到 0.003。
      threshold: 2,
      absFloor: 0.003,
      providerId: 'sensevoice-local',
      language: 'auto',
      ttsUrl: 'http://127.0.0.1:7880/api/v1/tts/tasks',
      verbose: true,
    }
    const readConfig = () => {
      try {
        if (typeof window !== 'undefined' && window.__dshLiveVoiceConfig) {
          return Object.assign({}, DEFAULTS, window.__dshLiveVoiceConfig)
        }
      } catch (e) {}
      return Object.assign({}, DEFAULTS)
    }

    // 阶段文案：尽量短（按钮要小，foilo 2026-10-17 提的）
    const PHASES = {
      off: '通话',
      arming: '准备…',
      listening: '听…',
      thinking: '识别…',
      speaking: '说…',
      error: '出错',
    }

    // =====================================================================
    // 诊断面板（固定定位，不依赖输入行容器）
    //
    // 教训：一开始做成输入行里的绝对定位浮层，被输入行容器裁掉了、看不见，
    // 于是"屏幕上没有任何信息"。现在用 position:fixed 钉在左下角，
    // 出错时**强制展开**，并且把错误全文摆最上面。
    // =====================================================================
    const PANEL_CSS = [
      '.dsh-lv-panel{position:fixed;left:12px;bottom:96px;z-index:2147483000;width:min(680px,92vw);max-height:52vh;overflow:auto;background:#16161a;color:#e8e8ea;border:1px solid rgba(255,255,255,.18);border-radius:12px;padding:10px 12px;box-shadow:0 18px 50px rgba(0,0,0,.55);font:11px/1.6 ui-monospace,Consolas,"Cascadia Mono",monospace;text-align:left}',
      '.dsh-lv-panel h4{margin:0 0 6px;font-size:12px;font-weight:600;display:flex;justify-content:space-between;gap:10px;align-items:center}',
      '.dsh-lv-panel .dsh-lv-actions{display:flex;gap:8px}',
      '.dsh-lv-panel button{cursor:pointer;background:#2a2a31;color:#e8e8ea;border:1px solid rgba(255,255,255,.2);border-radius:7px;padding:2px 8px;font-size:11px}',
      '.dsh-lv-err{color:#ff8a8a;background:rgba(255,80,80,.10);border-left:3px solid #ff6b6b;padding:5px 7px;border-radius:4px;margin-bottom:6px;word-break:break-all;white-space:pre-wrap}',
      '.dsh-lv-line{white-space:pre-wrap;word-break:break-all}',
      '.dsh-lv-key{color:#8ab4ff}',
      '.dsh-lv-muted{color:#9a9aa2}',
    ].join('\n')

    const apply = (ctx) => {
      // 兜底：任何未捕获错误也进报错条（不然用户只看到"不好使"）
      try {
        if (typeof window !== 'undefined' && !window.__dshLiveVoiceErrHook) {
          window.__dshLiveVoiceErrHook = true
          const grab = (msg) => {
            try {
              const api = window.__dshLiveVoice
              if (api && typeof api.__setError === 'function') api.__setError(String(msg).slice(0, 300))
            } catch (e) {}
          }
          window.addEventListener('error', (ev) => {
            const m = ev && ev.message ? ev.message : (ev && ev.error && ev.error.message) || 'window.onerror'
            // ResizeObserver 这类浏览器噪声不是我们的错，别报（2026-10-17 它把红条占满了）
            if (/ResizeObserver loop|ResizeObserver loop completed/i.test(m)) return
            grab('页面错误：' + m)
          })
          window.addEventListener('unhandledrejection', (ev) => {
            const r = ev && ev.reason
            const m = r && r.message ? r.message : String(r)
            if (/ResizeObserver loop/i.test(m)) return
            grab('未处理的 Promise：' + m)
          })
        }
      } catch (e) {}
      const slots = ctx.slots || (typeof ctx.get === 'function' ? ctx.get('slots') : undefined)
      if (!slots) throw new Error('[dsh-live-voice] slots service unavailable')
      try { console.info('[live-voice] client loaded build=' + BUILD) } catch (e) {}

      const state = { enabled: false, phase: 'off', caption: '', error: '', lastHeard: '' }
      const listeners = new Set()
      const diag = []          // 环形诊断缓冲
      const history = []       // 听到/说了什么
      let panelOpen = false    // 诊断面板是否手动展开
      let forceTick = () => {} // 由组件注册的强制重渲染
      let deviceInfo = '(还没查)'

      const pushDiag = (kind, detail) => {
        const rec = { t: Date.now(), kind, detail: detail === undefined ? '' : detail }
        diag.push(rec)
        if (diag.length > 200) diag.shift()
        if (readConfig().verbose) {
          try { console.log('[live-voice] diag ' + kind + (rec.detail ? ' ' + rec.detail : '')) } catch (e) {}
        }
      }

      const emit = () => { for (const l of listeners) { try { l(Object.assign({}, state)) } catch (e) {} } }
      const patch = (p) => { Object.assign(state, p); emit() }
      const subscribe = (l) => { listeners.add(l); return () => listeners.delete(l) }

      /**
       * 安全取 Remote 命名空间。
       * 为什么不能直接写 ctx.remote.speech：DSH 对没 inject 的路径**抛错**，
       * 而且会变成未处理 Promise（实机两次都是这个坑）。
       * 这里三层兜底：属性 → ctx.get('remote.x') → null，并把结论写进诊断。
       */
      const remoteNs = (name) => {
        const report = { api: false, err: '' }
        try {
          const r = ctx.remote
          if (r && r[name]) { report.api = true; return { api: r[name], report } }
        } catch (e) { report.err = 'ctx.remote 抛错：' + (e && e.message ? e.message : String(e)) }
        try {
          if (typeof ctx.get === 'function') {
            const v = ctx.get('remote.' + name)
            if (v) { report.api = true; return { api: v, report } }
          }
        } catch (e2) { report.err += ' ctx.get 抛错：' + (e2 && e2.message ? e2.message : String(e2)) }
        return { api: null, report }
      }

      /** 启动自检：把 remote 命名空间能不能用，一次性说清楚。 */
      const checkApis = () => {
        for (const name of ['speech', 'session']) {
          const { api, report } = remoteNs(name)
          pushDiag('api-' + name, api
            ? '可用' + (api.transcribe || api.prompt ? '（有方法）' : '（无方法）')
            : '不可用 ' + (report.err || '未声明/未挂载'))
          if (name === 'speech' && !api) speechApiError = report.err || 'remote.speech 命名空间不可用'
        }
      }

      /** 失败自检：列出音频输入设备，并把结论写进 deviceInfo（面板上直接显示）。 */
      const micSelfCheck = async () => {
        const out = []
        try {
          if (!navigator.mediaDevices) {
            deviceInfo = '没有 navigator.mediaDevices（非安全上下文？）'
            out.push(deviceInfo)
            return out
          }
          const devs = await navigator.mediaDevices.enumerateDevices()
          const mics = devs.filter((d) => d.kind === 'audioinput')
          deviceInfo = '音频输入 ' + mics.length + ' 个' +
            (mics.length ? '：' + mics.map((m) => m.label || '(无名称)').slice(0, 3).join(' / ') : '')
          out.push('音频输入设备 ' + mics.length + ' 个')
          if (!mics.length) out.push('系统里没有可用麦克风')
          else if (mics.every((m) => !m.label)) out.push('设备名为空：麦克风权限还没批')
        } catch (e) {
          const msg = 'enumerateDevices 失败：' + (e && e.message ? e.message : String(e))
          deviceInfo = msg
          out.push(msg)
        }
        return out
      }

      /**
       * 挑一个"真的在收音"的麦克风。
       *
       * 为什么需要：Windows 上常有一堆假输入 —— 「立体声混音」「虚拟音频设备」「CABLE」，
       * 浏览器默认可能偏偏选中它们，于是永远是 0 电平（foilo 说的"一直静音"）。
       * 这里按标签排除这些，取第一个看起来是真的。
       */
      const pickMicDevice = async () => {
        try {
          if (!navigator.mediaDevices) return ''
          const devs = await navigator.mediaDevices.enumerateDevices()
          const mics = devs.filter((d) => d.kind === 'audioinput' && d.deviceId)
          const bad = /虚拟|virtual|立体声混音|stereo mix|loopback|cable|vb-audio|voicemeeter|obs/i
          const good = mics.filter((m) => m.label && !bad.test(m.label))
          const pick = good[0] || mics.find((m) => m.deviceId === 'default') || mics[0]
          if (!pick) return ''
          micDeviceId = pick.deviceId || ''
          micLabel = pick.label || '(无名称)'
          pushDiag('mic-pick', micLabel + (good.length ? '' : '（没找到明显真实的，退回第一个）'))
          return micDeviceId
        } catch (e) {
          pushDiag('mic-pick-error', e && e.message ? e.message : String(e))
          return ''
        }
      }

      let runtime = null
      let audio = null
      let lastReply = ''
      let busy = false
      let micDeviceId = ''
      let micLabel = ''
      let actionsRef = { inputActions: null }
      let activeSessionId = ''
      let speakChain = Promise.resolve()
      let stallTimer = null
      let speechApiError = ''
      let blockedSince = 0

      const record = (kind, text) => {
        history.push({ at: Date.now(), kind, text: String(text || '').slice(0, 300) })
        if (history.length > 80) history.shift()
      }

      const stopAudio = () => {
        if (!audio) return
        try { audio.pause() } catch (e) {}
        audio = null
      }

      /** 回到「听」。调用方自己判条件：通话开着、且不在播报中。 */
      const resumeListening = () => {
        if (!state.enabled) return
        if (audio) return
        if (state.phase === 'listening') return
        patch({ phase: 'listening', caption: '' })
      }

      const setBlocked = (v) => {
        if (busy === v) return
        busy = !!v
        if (v) blockedSince = Date.now()
        if (runtime) runtime.setBlocked(v)
        if (v) stopAudio()
        pushDiag('blocked', String(v))
        // 不忙了 → 回到聆听。
        // （这里以前漏了：只改标志位不改阶段，界面就永远停在"大肥鱼在说"）
        if (!v) resumeListening()
      }

      const speakReply = (text) => {
        if (!text || !text.trim()) return
        speakChain = speakChain.then(async () => {
          try {
            patch({ phase: 'speaking', caption: text.slice(0, 100) })
            pushDiag('tts-request', text.length + ' 字')
            const { buffer } = await synthSpeech(text, undefined, readConfig().ttsUrl)
            pushDiag('tts-ok', buffer.byteLength + ' 字节')
            const url = URL.createObjectURL(new Blob([buffer], { type: 'audio/wav' }))
            const a = new Audio(url)
            audio = a
            a.onended = () => {
              try { URL.revokeObjectURL(url) } catch (e) {}
              if (audio === a) audio = null
              pushDiag('tts-ended')
              // 播报结束就回到聆听：**不要**用 busy 当判据
              //（会话的"忙"和"音频播完"是两件事，实机就卡在这里再也不听）
              resumeListening()
            }
            a.onerror = () => {
              try { URL.revokeObjectURL(url) } catch (e) {}
              if (audio === a) audio = null
              pushDiag('tts-play-error')
            }
            await a.play()
            record('speak', text)
            pushDiag('tts-playing')
          } catch (err) {
            const msg = err && err.message ? err.message : String(err)
            pushDiag('tts-fail', msg)
            patch({ error: '播报失败：' + msg })
            if (state.enabled && !busy) patch({ phase: 'listening' })
          }
        })
      }

      const transcribe = async (samples) => {
        const cfg = readConfig()
        const wav = encodeWav(samples)
        const audioBase64 = toBase64(wav)
        pushDiag('transcribe-send', (Math.round(samples.length / 160) / 100) + ' 秒 / ' + wav.byteLength + ' 字节 WAV')
        const { api, report } = remoteNs('speech')
        if (!api || typeof api.transcribe !== 'function') {
          pushDiag('transcribe-no-api', report.err || 'speech 命名空间不可用')
          throw new Error('语音识别服务不可用（remote.speech 未挂载；看诊断里的 api-speech 行）')
        }
        let result
        try {
          result = await api.transcribe({
            audioBase64,
            providerId: cfg.providerId,
            language: cfg.language,
          })
        } catch (err) {
          pushDiag('transcribe-throw', err && err.message ? err.message : String(err))
          throw err
        }
        pushDiag('transcribe-reply', result && result.ok === false
          ? 'ERROR ' + JSON.stringify(result.error).slice(0, 300)
          : JSON.stringify(result && result.value).slice(0, 300))
        if (result && result.ok && result.value) return String(result.value.text || '')
        if (result && result.ok === false) {
          const e = result.error
          throw new Error(e && e.message ? e.message : '识别失败')
        }
        return ''
      }

      // ===================================================================
      // 提交：优先直接走会话控制器（干净），拿不到就退回「写进输入框 + 回车」
      // ===================================================================

      const newRequestId = () => {
        try { if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID() } catch (e) {}
        return 'lv-' + Date.now() + '-' + Math.random().toString(16).slice(2)
      }

      const promptRemote = async (sessionId, text) => {
        const { api: S, report } = remoteNs('session')
        if (!S || typeof S.prompt !== 'function') {
          pushDiag('submit-remote-unavailable', report.err || 'session 命名空间不可用')
          return { ok: false, reason: 'no-api' }
        }
        if (!sessionId) {
          pushDiag('submit-remote-no-session', '没拿到 sessionId')
          return { ok: false, reason: 'no-session' }
        }
        try {
          const res = await S.prompt({
            requestId: newRequestId(),
            sessionId,
            mode: 'queue',
            content: [{ type: 'text', text }],
            clientTimeZone: (() => { try { return Intl.DateTimeFormat().resolvedOptions().timeZone } catch (e) { return undefined } })(),
          })
          const ok = !!(res && (res.ok === true || res.accepted === true))
          pushDiag('submit-remote', ok ? '会话已接受' : ('未接受 ' + JSON.stringify(res).slice(0, 200)))
          return { ok, reason: ok ? 'accepted' : 'rejected' }
        } catch (err) {
          pushDiag('submit-remote-throw', err && err.message ? err.message : String(err))
          return { ok: false, reason: 'throw', error: err }
        }
      }

      /** 兜底：把文字写进输入框，再补一个 Enter 事件。 */
      const submitViaComposer = (text) => {
        const ia = actionsRef.inputActions
        if (!ia || typeof ia.insertText !== 'function') {
          pushDiag('submit-no-actions', ia ? 'inputActions 缺 insertText' : '还没拿到 inputActions')
          return false
        }
        try {
          const span = typeof ia.captureInsertion === 'function' ? ia.captureInsertion() : undefined
          const inserted = ia.insertText(text, span)
          pushDiag('submit-insert', inserted === false ? '被拒（版本冲突/编辑器不可编辑）' : '已写入输入框')
          if (inserted === false) return false
          record('heard', text)
          queueMicrotask(() => {
            try {
              const target = document.activeElement || document.body
              const opts = { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true, composed: true }
              for (const type of ['keydown', 'keypress', 'keyup']) {
                target.dispatchEvent(new KeyboardEvent(type, opts))
              }
              pushDiag('submit-enter', '已派发 Enter 到 ' + (target.tagName || '?'))
            } catch (e) {
              pushDiag('submit-enter-error', e && e.message ? e.message : String(e))
            }
          })
          return true
        } catch (err) {
          pushDiag('submit-throw', err && err.message ? err.message : String(err))
          patch({ error: '提交失败：' + (err && err.message ? err.message : String(err)) })
          return false
        }
      }

      const submitTranscript = async (text) => {
        const direct = await promptRemote(activeSessionId, text)
        if (direct.ok) { record('heard', text); return true }
        pushDiag('submit-fallback', '改走输入框兜底')
        return submitViaComposer(text)
      }

      const handleUtterance = async (samples) => {
        if (!state.enabled) return
        if (busy) { patch({ phase: 'speaking' }); pushDiag('utterance-dropped-busy'); return }
        try {
          patch({ phase: 'thinking' })
          pushDiag('utterance', Math.round(samples.length / 16) + 'ms')
          const text = await transcribe(samples)
          if (!text || !text.trim()) {
            pushDiag('transcribe-empty')
            patch({ phase: 'listening', caption: '' })
            return
          }
          patch({ lastHeard: text })
          pushDiag('transcribe-text', text)
          const ok = await submitTranscript(text)
          if (!ok) {
            patch({ phase: 'error', error: '发不出去：会话提交和输入框兜底都没成功，点右边 ⚠ 复制诊断给我' })
            pushDiag('submit-failed', text)
          }
        } catch (err) {
          const msg = err && err.message ? err.message : String(err)
          pushDiag('utterance-error', msg)
          patch({ phase: 'error', error: msg })
        }
      }

      const start = async () => {
        patch({ phase: 'arming', error: '', caption: '' })
        const cfg = readConfig()
        pushDiag('start', JSON.stringify({
          silenceMs: cfg.silenceMs,
          threshold: cfg.threshold,
          providerId: cfg.providerId,
          remoteSpeech: !!(ctx.remote && ctx.remote.speech),
        }))
        clearTimeout(stallTimer)
        stallTimer = setTimeout(() => {
          if (state.phase === 'arming') {
            pushDiag('mic-stalled', 'getUserMedia 超过 3 秒未返回：检查系统「隐私 → 麦克风」和输入设备')
            patch({ error: '麦克风没响应：检查系统「隐私 → 麦克风」和输入设备' })
          }
        }, 3000)
        // 先摸一遍设备情况，面板上一开始就能看到"系统里有没有麦克风"。
        // 注意：必须限时——enumerateDevices 在某些环境下会挂住不返回，
        // 那会把整个 start() 卡在 'arming'（实机就出现过：phase=arming / enabled=false）。
        const withTimeout = (p, ms, fallback) => Promise.race([
          p,
          new Promise((resolve) => setTimeout(() => resolve(fallback), ms)),
        ])
        try {
          await withTimeout(micSelfCheck(), 1500, ['设备查询超时（继续启动麦克风）'])
        } catch (e) {}
        // 挑一个真的在收音的麦克风（排除"立体声混音/虚拟音频设备"这类 0 电平的假输入）
        let pickedDevice = ''
        try {
          pickedDevice = await withTimeout(pickMicDevice(), 1500, '')
        } catch (e) {}
        try {
          if (!runtime) {
            runtime = createRuntime({
              silenceMs: cfg.silenceMs,
              minSpeechMs: cfg.minSpeechMs,
              maxUtteranceMs: cfg.maxUtteranceMs,
              calibrationMs: cfg.calibrationMs,
              threshold: cfg.threshold,
              absFloor: cfg.absFloor,
              deviceId: pickedDevice,
              onEvent: (ev) => {
                if (ev.type === 'listening') {
                  pushDiag('listening', 'rate=' + ev.sampleRate + ' state=' + ev.state + ' track=' + ev.trackLabel)
                } else if (ev.type === 'speech-start') {
                  patch({ phase: 'listening', caption: '…' })
                  pushDiag('vad-start')
                } else if (ev.type === 'speech-end') {
                  patch({ phase: 'thinking' })
                  pushDiag('vad-end', ev.samples + ' 样本')
                } else if (ev.type === 'speech-drop') {
                  pushDiag('vad-drop', (ev.reason || '') + ' blocks=' + ev.blocks)
                }
              },
              onUtterance: handleUtterance,
            })
          }
          state.enabled = true
          await runtime.start()
          clearTimeout(stallTimer)
          if (state.phase === 'arming') patch({ phase: 'listening' })
          pushDiag('mic-ok')
        } catch (err) {
          clearTimeout(stallTimer)
          state.enabled = false
          try { if (runtime) await runtime.stop() } catch (e) {}
          runtime = null
          const msg = err && err.message ? err.message : String(err)
          pushDiag('mic-error', msg)
          const hints = await micSelfCheck()
          for (const h of hints) pushDiag('mic-check', h)
          patch({ phase: 'error', error: '麦克风失败：' + msg + '（' + hints.join('；') + '）' })
        }
      }

      const stop = async () => {
        state.enabled = false
        clearTimeout(stallTimer)
        patch({ phase: 'off', caption: '', error: '' })
        pushDiag('stop')
        stopAudio()
        if (runtime) { try { await runtime.stop() } catch (e) {} runtime = null }
      }

      // ---- 样式（随 fiber 卸载） ----
      const style = document.createElement('style')
      style.setAttribute('data-dsh-live-voice', '1')
      style.textContent = [
        '.dsh-live-voice{display:inline-flex;align-items:center;gap:6px;max-width:360px}',
        '.dsh-live-voice-btn{cursor:pointer;border:1px solid var(--dsw-alias-border-l1,rgba(127,127,127,.35));background:transparent;color:inherit;border-radius:7px;padding:2px 7px;font-size:11px;line-height:1.35;white-space:nowrap}',
        '.dsh-live-voice-btn.on{border-color:var(--dsw-alias-brand-primary,#4f8cff);color:var(--dsw-alias-brand-primary,#4f8cff)}',
        '.dsh-live-voice-btn.bad{border-color:#ff6b6b;color:#ff6b6b}',
        '.dsh-live-voice[data-phase="listening"] .dsh-live-voice-btn{box-shadow:0 0 0 2px rgba(79,140,255,.25)}',
        '.dsh-live-voice[data-phase="speaking"] .dsh-live-voice-btn{opacity:.6}',
        '.dsh-live-voice-err{color:#e5484d;font-size:12px;cursor:pointer;text-decoration:underline}',
        '.dsh-lv-banner{display:block;flex-basis:100%;width:100%;margin-top:6px;padding:5px 9px;border-radius:7px;background:rgba(229,72,77,.14);border:1px solid rgba(229,72,77,.5);color:#ff9b9b;font-size:11px;line-height:1.5;cursor:pointer;word-break:break-all}',
        PANEL_CSS,
      ].join('\n')
      document.head.appendChild(style)
      ctx.effect(() => () => style.remove(), 'dsh-live-voice styles')

      // ---- 会话输入行里的通话开关 ----
      const CallButton = (props) => {
        const [, force] = react.useState(0)
        forceTick = () => force((n) => n + 1)
        react.useEffect(() => subscribe(() => force((n) => n + 1)), [])

        const ia = props && (props.inputActions || props.actions || (props.input && props.input.actions))
        if (ia && typeof ia.insertText === 'function' && actionsRef.inputActions !== ia) {
          actionsRef.inputActions = ia
          pushDiag('actions-bound', '拿到 inputActions')
        }
        // 会话 id：优先 slot props，其次从 location 里挖
        const sid = (props && (props.sessionId || (props.session && props.session.sessionId))) ||
          (() => {
            try {
              const m = /session[-_/]([0-9a-f-]{36})/i.exec(String(window.location && window.location.href || ''))
              return m ? m[1] : ''
            } catch (e) { return '' }
          })()
        if (sid && sid !== activeSessionId) {
          activeSessionId = sid
          pushDiag('session-bound', sid)
        }

        const snaps = []
        for (const name of ['useSession', 'useConversation', 'useChat', 'useTrajectory', 'useProjection']) {
          const h = props && props[name]
          if (typeof h !== 'function') continue
          try { snaps.push({ name, snap: h((v) => v) }) } catch (e) {}
        }
        const sessionState = readSessionState(snaps)
        react.useEffect(() => {
          setBlocked(sessionState.active)
          if (sessionState.latest && sessionState.latest !== lastReply) {
            lastReply = sessionState.latest
            pushDiag('new-reply', sessionState.latest.slice(0, 60))
            if (state.enabled) speakReply(lastReply)
          }
        })

        const onClick = () => {
          pushDiag('click', '按钮被点了，enabled=' + state.enabled + ' phase=' + state.phase)
          try {
            if (state.enabled) stop(); else start()
          } catch (e) {
            pushDiag('click-throw', e && e.message ? e.message : String(e))
            patch({ error: '点击处理出错：' + (e && e.message ? e.message : String(e)) })
          }
        }
        const onCopyDiag = async () => {
          const payload = JSON.stringify({
            state: Object.assign({}, state),
            diag: diag.slice(-40),
            history: history.slice(-20),
            stats: runtime ? runtime.stats : null,
          }, null, 1)
          let copied = false
          try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
              await navigator.clipboard.writeText(payload)
              copied = true
            }
          } catch (e) {}
          if (!copied) {
            try {
              const ta = document.createElement('textarea')
              ta.value = payload
              document.body.appendChild(ta)
              ta.select()
              document.execCommand('copy')
              ta.remove()
              copied = true
            } catch (e) {}
          }
          patch({ error: copied ? '诊断已复制到剪贴板，粘贴发我即可' : '复制失败，请按 F12 手动复制 window.__dshLiveVoice.dump()' })
          pushDiag('copy-diag', copied ? 'ok' : 'failed')
        }
        const active = state.enabled
        const label = PHASES[state.phase] || state.phase

        // ---- 全部诊断塞进 title（不需要点任何东西） ----
        const deviceOk = /音频输入\s*[1-9]/.test(deviceInfo)
        const fullTitle = [
          'dsh-live-voice 构建 ' + BUILD,
          state.error ? '错误：' + state.error : (active ? '正在通话' : '点一下开始通话'),
          '阶段：' + state.phase,
          '设备：' + deviceInfo,
          micLabel ? ('当前麦克风：' + micLabel) : '',
          deviceOk ? '' : '⚠ 这台机器上没查到麦克风',
          state.level ? ('电平：rms=' + Number(state.level.rms).toFixed(4) + ' 说话中=' + (state.level.voiceNow ? '是' : '否')) : '',
          '',
          '最近步骤：',
          ...diag.slice(-12).map((d) => '· ' + d.kind + ' ' + String(d.detail).slice(0, 160)),
          '',
          '全量：控制台 window.__dshLiveVoice.status()',
        ].filter(Boolean).join('\n')

        // 说话时按钮上加一个极短提示：不用猜"到底有没有进来声音"
        const voiceHint = active && state.level
          ? (audio || busy ? ' · 我说' : (state.level.voiceNow ? ' · 有声' : ' · 静音'))
          : ''

        // 按钮尽量小：正常态只显示「📞 通话」；通话中显示「🎙 听… · 有声」；出错才带红点。
        // 构建戳不上按钮（foilo 嫌占地方）——只在 title 和控制台里。
        const text = (state.error ? '🔴 ' : (active ? '🎙 ' : '📞 ')) + label + voiceHint

        return react.createElement(react.Fragment, null,
          react.createElement('div', { className: 'dsh-live-voice', 'data-phase': state.phase },
            react.createElement('button', {
              type: 'button',
              className: 'dsh-live-voice-btn' + (active ? ' on' : '') + (state.error ? ' bad' : ''),
              title: fullTitle,
              'aria-pressed': active ? 'true' : 'false',
              onClick,
            }, text),
          ),
          // 报错条：屏幕上常驻、纯文本、点一下复制。修好之后可以删掉这一段。
          state.error ? react.createElement('div', {
            className: 'dsh-lv-banner',
            title: fullTitle,
            onClick: onCopyDiag,
          }, '❌ live-voice [' + BUILD + '] ' + String(state.error).slice(0, 220) + '（点此复制诊断）') : null,
        )
      }

      ctx.effect(() => slots.inject('conversation.input.left', () => slots.register(
        { name: 'conversation.input.left', key: 'live-voice', id: 'live-voice', order: 30 },
        CallButton,
      )), 'dsh-live-voice call button')

      // -------------------------------------------------------------------
      // 启动就自检一次：把结论直接挂到按钮上（不依赖任何面板/点击）
      // 这一步就是为了证明"插件确实加载了、机器上到底有几个麦克风"。
      // -------------------------------------------------------------------
      const runBootCheck = async () => {
        try {
          checkApis()
          const hints = await micSelfCheck()
          pushDiag('boot', '插件已加载 · ' + deviceInfo)
          for (const h of hints) pushDiag('boot-check', h)
        } catch (e) {
          pushDiag('boot-error', e && e.message ? e.message : String(e))
        }
        try { forceTick() } catch (e) {}
      }
      runBootCheck()

      // ---- 遥测：既做 2 秒一条的日志，也让按钮实时显示「有声音/静音」 ----
      let lastTick = 0
      const tickTimer = setInterval(() => {
        if (!state.enabled || !runtime) return
        const s = runtime.stats
        const now = Date.now()
        // 卡死自救：被标成"忙"太久还没有音频在播 → 强制回到聆听
        // （会话的忙状态可能残留，不能让麦克风一直被关着）
        if (busy && !audio && blockedSince && now - blockedSince > 30000) {
          pushDiag('blocked-timeout', '忙状态超过 30 秒且没有音频，强制恢复聆听')
          busy = false
          blockedSince = 0
          if (runtime) runtime.setBlocked(false)
          resumeListening()
        }
        const voiceNow = (now - (s.lastVoiceAt || 0)) < 600
        // 显示用的"有声"判据比断句门限更低：门限是"算一句"的标准，显示是"我确实看到电平了"。
        // 分开之后，用户能立刻区分"麦克风没声音"和"门限太高"（2026-10-17 foilo 报"一直静音"）。
        const floorNow = s.floor === null || s.floor === undefined ? 0 : s.floor
        const displayVoice = voiceNow || s.lastRms > Math.max(floorNow * 1.4, 0.0012)
        // 轻量刷新（只更新界面用的电平/是否检测到说话），不写日志
        patch({ level: { rms: s.lastRms, peak: s.peak, floor: s.floor, voiceNow: displayVoice, at: now } })
        if (now - lastTick < 2000) return
        lastTick = now
        pushDiag('level', 'rms=' + s.lastRms.toFixed(4) + ' peak=' + s.peak.toFixed(4) +
          ' floor=' + (s.floor === null ? 'null' : s.floor.toFixed(4)) +
          ' 说话中=' + (voiceNow ? '是' : '否') +
          ' blocks=' + s.blocks + ' 句=' + s.utterances + ' 丢=' + s.drops + ' 屏蔽丢=' + s.blockedDrops)
      }, 400)
      if (typeof ctx.effect === 'function') ctx.effect(() => () => clearInterval(tickTimer), 'dsh-live-voice telemetry')

      // ---- 调试把手 ----
      try {
        window.__dshLiveVoice = {
          get state() { return Object.assign({}, state) },
          get history() { return history.slice() },
          get diag() { return diag.slice() },
          get stats() { return runtime ? Object.assign({}, runtime.stats) : null },
          get devices() { return deviceInfo },
          /** 一行行纯文本，方便复制给我的那种（没有表格、没有对象）。 */
          status() {
            const lines = [
              'live-voice 状态',
              '插件：已加载 构建 ' + BUILD,
              '阶段：' + state.phase + (state.enabled ? '（通话中）' : '（空闲）'),
              '设备：' + deviceInfo,
              '错误：' + (state.error || '无'),
              '最近步骤：',
            ]
            for (const d of diag.slice(-16)) lines.push('  ' + d.kind + ' ' + String(d.detail).slice(0, 200))
            const out = lines.join('\n')
            try { console.log(out) } catch (e) {}
            return out
          },
          /** 复制 status() 到剪贴板。 */
          async copy() {
            let text = ''
            try { text = this.status() } catch (e) {}
            try {
              await navigator.clipboard.writeText(text)
              return '已复制'
            } catch (e) {
              try {
                const ta = document.createElement('textarea')
                ta.value = text
                document.body.appendChild(ta)
                ta.select()
                document.execCommand('copy')
                ta.remove()
                return '已复制（兜底路径）'
              } catch (e2) { return '复制失败：' + (e2 && e2.message ? e2.message : String(e2)) }
            }
          },
          dump() { try { console.table(diag.slice(-40)) } catch (e) { console.log(diag.slice(-40)) } },
          /** 全局错误钩子往里塞错误用的内部口子。 */
          __setError(msg) {
            try { pushDiag('global-error', msg); patch({ error: String(msg) }) } catch (e) {}
          },
          start, stop,
          runtime: () => runtime,
          config: readConfig,
        }
        console.info('[live-voice] ready build=' + BUILD + ' — 控制台 window.__dshLiveVoice.status() 看诊断')
      } catch (e) {}
    }

    exports.apply = apply
    exports.inject = inject
    exports.__test = {
      rmsOf, createNoiseFloor, createEndpointer, encodeWav, toBase64,
      extractNodeText, extractAssistantText, pickNodeList, isAssistantNode, readSessionState, synthSpeech, PHASES,
    }
    return module.exports
  },
})
