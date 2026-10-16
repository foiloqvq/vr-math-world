/**
 * dsh-live-voice —— 宿主半边。
 *
 * 这个插件全部逻辑都在浏览器半边（client.js）：麦克风、断句、提交、播报。
 * 宿主侧不需要 service、路由或工具，所以这里只留 name/inject 并导出一个空 apply，
 * 保证 loader 能正常挂载这一行（不再有第二份实现，避免两处逻辑漂移）。
 */
export const name = 'dsh-live-voice'
export const inject = []
export function apply() {}
