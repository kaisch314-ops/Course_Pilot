/** Replaceable dialogue boundary. The demo provider does not call a model. */
export interface DialogueProvider { name: string; clauses(text: string): string[] }
export const dialogueProvider: DialogueProvider = {
  name: '本地规则模拟器',
  clauses: text => text.split(/[，。；！？,;!?\n]/).filter(Boolean),
}
export type Feedback = { id: string; course: string; name: string; tags: string[]; reason: 'interest'|'load'|'growth'; direction: number; time: string }
export function learn(feedback: Feedback[]) {
  const affinity: Record<string,number> = {}
  let load = 0, growth = 0
  for(const f of feedback) {
    if(f.reason==='interest')for(const t of f.tags)affinity[t]=(affinity[t]||0)+f.direction
    if(f.reason==='load')load+=f.direction
    if(f.reason==='growth')growth+=f.direction
  }
  // Bounded evidence accumulation; deleting feedback recomputes from scratch.
  return { affinity:Object.fromEntries(Object.entries(affinity).map(([t,v])=>[t,Math.tanh(v/3)])), challengeDelta:.25*Math.tanh((growth-load)/3) }
}
