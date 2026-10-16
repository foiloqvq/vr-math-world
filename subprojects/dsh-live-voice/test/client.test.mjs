/**
 * dsh-live-voice 的纯逻辑测试（node --test）。
 *
 * 不碰浏览器：用最小的 window / __ModuleLoader__ / react 桩把 client.js 装载起来，
 * 然后测断句、噪声本底、WAV 编码、会话快照解析这几块——也就是最容易静默出错的地方。
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))

// ---- 桩：window / ModuleLoader / react ----
let loaded = null
globalThis.window = {}
globalThis.window.__ModuleLoader__ = {
  load({ id, factory }) {
    loaded = { id, exports: factory((name) => {
      if (name === 'react') return { createElement: () => null, useState: (v) => [v, () => {}], useEffect: () => {}, useRef: (v) => ({ current: v }) }
      throw new Error('unexpected require: ' + name)
    }) }
  },
}

// btoa：Node 有，但为了确定性给一个明确的实现
globalThis.btoa = (bin) => Buffer.from(bin, 'binary').toString('base64')

const src = readFileSync(join(here, '..', 'client.js'), 'utf8')
// 直接执行 client.js（它就是普通 ESM 语法 + 一个全局 load 调用）
await import('data:text/javascript,' + encodeURIComponent(src))

const t = loaded && loaded.exports && loaded.exports.__test
assert.ok(t, 'client.js 应该通过 __ModuleLoader__ 导出 __test')

// 一秒 16kHz 的样本数
const SR = 16000
const blocks = (ms) => Math.round(ms / 16)

const silence = (ms) => new Float32Array((16 * Math.round(ms / 16)))
const tone = (ms, amp) => {
  const n = 16 * Math.round(ms / 16)
  const a = new Float32Array(n)
  for (let i = 0; i < n; i++) a[i] = Math.sin((2 * Math.PI * 220 * i) / SR) * amp
  return a
}

test('rmsOf：静音 ≈ 0，正弦有能量', () => {
  assert.equal(t.rmsOf(silence(16)), 0)
  const r = t.rmsOf(tone(16, 0.2))
  assert.ok(r > 0.1 && r < 0.2, 'RMS 应接近 0.2/√2≈0.141，实际 ' + r)
})

test('噪声本底：校准期只采样，之后缓慢跟随', () => {
  const nf = t.createNoiseFloor({ blockMs: 16, calibrationMs: 32 })
  nf.feed(0.01)
  const c1 = nf.feed(0.01)
  assert.equal(c1.calibrating, false, '两个块之后应校准完成')
  assert.ok(Math.abs(nf.floor - 0.01) < 1e-9)
  // 之后一格静音：本底向下跟随（只降一点）
  nf.feed(0.02)
  assert.ok(nf.floor > 0.01 && nf.floor < 0.02, '本底应朝 0.02 走一小步，实际 ' + nf.floor)
})

test('断句：说话 → 静音 700ms → end，并把整句内容拼齐', () => {
  const ep = t.createEndpointer({ blockMs: 16, silenceMs: 700, minSpeechMs: 250 })
  const floor = 0.002
  const events = []
  // 300ms 说话
  for (let i = 0; i < blocks(300); i++) events.push(ep.feed(0.05, floor, false).event)
  // 700ms 静音
  for (let i = 0; i < blocks(700); i++) events.push(ep.feed(0.001, floor, false).event)
  assert.equal(events.filter((e) => e === 'start').length, 1, '刚好一次 start')
  assert.equal(events[events.length - 1], 'end', '静音够久后应 end')
  assert.equal(events.filter((e) => e === 'end').length, 1)
})

test('断句：太短的咔哒声被丢掉（drop）', () => {
  const ep = t.createEndpointer({ blockMs: 16, silenceMs: 700, minSpeechMs: 250 })
  const floor = 0.002
  let last = 'none'
  for (let i = 0; i < blocks(64); i++) last = ep.feed(0.05, floor, false).event   // 64ms 说话
  for (let i = 0; i < blocks(700); i++) last = ep.feed(0.001, floor, false).event
  assert.equal(last, 'drop', '64ms 太短，应 drop 而不是 end')
})

test('断句：屏蔽期间丢句，且不判 start', () => {
  const ep = t.createEndpointer({ blockMs: 16 })
  const floor = 0.002
  const before = ep.feed(0.05, floor, false)
  assert.equal(before.event, 'start')
  const during = ep.feed(0.05, floor, true)   // 大肥鱼开始说话 → 背压
  assert.equal(during.event, 'drop', '屏蔽时正在进行的句子要丢')
  const after = ep.feed(0.05, floor, true)
  assert.equal(after.event, 'blocked')
  assert.equal(ep.speaking, false)
})

test('断句：单句超长会被强制切（后端有 20s 上限）', () => {
  const ep = t.createEndpointer({ blockMs: 16, maxUtteranceMs: 160 })
  const floor = 0.002
  const events = []
  // 只喂到刚过上限一点：第 1 块 start，第 10 块（=160ms）触发强制切
  for (let i = 0; i < blocks(176); i++) events.push(ep.feed(0.05, floor, false).event)
  assert.equal(events.filter((e) => e === 'end').length, 1, '160ms 上限下应恰好切一次')
  // 实测：0-based 第 9 块触发（start 在第 0 块，之后再数 10 块 = 160ms）
  assert.equal(events.indexOf('end'), 9, '切点应在 10 个说话块之后（0-based 第 9 块）')
})

test('encodeWav：44 字节头 + 16bit 样本，长度自洽', () => {
  const pcm = new Float32Array(1600)   // 100ms
  pcm[0] = 1
  pcm[1] = -1
  pcm[2] = 0.5
  const buf = t.encodeWav(pcm)
  assert.equal(buf.byteLength, 44 + 1600 * 2)
  const v = new DataView(buf)
  assert.equal(String.fromCharCode(v.getUint8(0), v.getUint8(1), v.getUint8(2), v.getUint8(3)), 'RIFF')
  assert.equal(v.getUint32(24, true), 16000, '采样率 16k')
  assert.equal(v.getUint16(22, true), 1, '单声道')
  assert.equal(v.getUint16(34, true), 16, '16bit')
  assert.equal(v.getInt16(44, true), 32767, '满幅 1 → 0x7fff')
  assert.equal(v.getInt16(46, true), -32768, '负满幅 → -0x8000')
})

test('toBase64：往返正确', () => {
  const bytes = new Uint8Array([1, 2, 3, 250, 251])
  const b64 = t.toBase64(bytes.buffer)
  assert.equal(Buffer.from(b64, 'base64').toString('hex'), '010203fafb')
})

test('会话快照解析：找到最新 assistant 文本与忙碌状态', () => {
  const snaps = [
    { name: 'useSession', snap: { running: true, nodes: [] } },
    {
      name: 'useConversation',
      snap: {
        chat: {
          messages: [
            { role: 'user', text: '你好' },
            { role: 'assistant', content: [{ type: 'text', text: '第一条回复' }] },
            { role: 'assistant', text: '第二条回复' },
          ],
        },
      },
    },
  ]
  const st = t.readSessionState(snaps)
  assert.equal(st.active, true, 'running 应判定为忙')
  assert.equal(st.latest, '第二条回复', '取最新的 assistant 文本')
})

test('会话快照解析：没有 assistant 节点时不误判', () => {
  const st = t.readSessionState([
    { name: 'useChat', snap: { nodes: [{ role: 'user', text: '只说了话' }] } },
  ])
  assert.equal(st.active, false)
  assert.equal(st.latest, '')
})

test('extractAssistantText：只取正文，跳过 reasoning / tool 块（实机踩过）', () => {
  const node = {
    role: 'assistant',
    content: [
      { type: 'reasoning', text: 'Need to fix the host from serving stale bundles' },
      { type: 'tool-call', name: 'bash', arguments: '{"command":"powershell ..."}' },
      { type: 'text', text: '这是真正的回复。' },
      { type: 'tool-result', content: [{ type: 'text', text: '命令输出：OK' }] },
      { type: 'text', text: '第二段正文。' },
    ],
  }
  assert.equal(t.extractAssistantText(node), '这是真正的回复。\n第二段正文。')
})

test('extractAssistantText：没有 content 数组时退回 text 字段；只有思考则返回空', () => {
  assert.equal(t.extractAssistantText({ role: 'assistant', text: '  正文  ' }), '正文')
  assert.equal(t.extractAssistantText({ role: 'assistant', content: '直接字符串' }), '直接字符串')
  assert.equal(t.extractAssistantText({ role: 'assistant', content: [{ type: 'reasoning', text: '只有思考' }] }), '')
})

test('extractNodeText：认得字符串/数组/嵌套 blocks', () => {
  assert.equal(t.extractNodeText('直接字符串'), '直接字符串')
  assert.equal(t.extractNodeText([{ text: 'a' }, 'b']), 'a\nb')
  assert.equal(t.extractNodeText({ content: { blocks: [{ text: '深一层' }] } }), '深一层')
  assert.equal(t.extractNodeText(null), '')
})

test('synthSpeech：POST 到本机 TTS，拿回音频字节', async () => {
  const calls = []
  const fakeFetch = async (url, init) => {
    calls.push({ url, body: JSON.parse(init.body) })
    return { ok: true, status: 200, arrayBuffer: async () => new Uint8Array(2048).buffer }
  }
  const out = await t.synthSpeech('测试一句话', fakeFetch)
  assert.equal(calls.length, 1)
  assert.equal(calls[0].url, 'http://127.0.0.1:7880/api/v1/tts/tasks')
  assert.equal(calls[0].body.text, '测试一句话')
  assert.equal(out.buffer.byteLength, 2048)
  assert.equal(out.mime, 'audio/wav')
})
