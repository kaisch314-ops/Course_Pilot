﻿﻿﻿import { useState } from 'react'
import type { ScheduleItem, Session } from '../types'

export const CATEGORY_COLOR: Record<string,string> = {必修:'var(--must)',专业选修:'var(--major)',通识:'var(--ge)'}
const days = ['周一','周二','周三','周四','周五','周六','周日']
export function weekLabel(s:Session) {
  const w = s.weeks
  if (!w?.length) return '第1–16周'
  if (w.length===1) return '第'+w[0]+'周'
  if (w.every((n,i)=>n===w[0]+i)) return '第'+w[0]+'–'+w[w.length-1]+'周'
  return '第'+w.join('、')+'周'
}
export default function Timetable({items,blocked,locked}:{items:ScheduleItem[],blocked:Session[],locked:string[]}) {
  const [week,setWeek]=useState(1)
  const [day,setDay]=useState(1)
  const blocks=items.flatMap(item=>item.sessions.map((s,i)=>({...s,item,key:item.offering_id+i})))
  const count=Math.max(5,...blocks.map(b=>b.day),...blocked.map(b=>b.day))
  const visible=(s:Session)=>!s.weeks || s.weeks.includes(week)
  return <section><div className="calendar-tools"><label>教学周 <select value={week} onChange={e=>setWeek(+e.target.value)}>{Array.from({length:Math.max(16,...blocks.flatMap(b=>b.weeks||[]))},(_,i)=><option key={i} value={i+1}>第 {i+1} 周</option>)}</select></label>
  <label className="mobile-day">按天查看 <select value={day} onChange={e=>setDay(+e.target.value)}>{days.slice(0,count).map((d,i)=><option key={d} value={i+1}>{d}</option>)}</select></label></div>
  <div className="week-grid" style={{gridTemplateColumns:'32px repeat('+count+',minmax(0,1fr))'}}><small>节次</small>{days.slice(0,count).map(d=><strong key={d}>{d}</strong>)}
  {Array.from({length:14},(_,i)=><small key={i} style={{gridColumn:1,gridRow:i+2}}>{i+1}</small>)}
  {blocked.filter(visible).map((s,i)=><div className="blocked-slot" key={i} style={{gridColumn:s.day+1,gridRow:(s.start+1)+' / '+(s.end+2)}}>禁排</div>)}
  {blocks.filter(visible).map(b=><a className="class-slot" key={b.key} href={'#class-'+b.item.offering_id} style={{gridColumn:b.day+1,gridRow:(b.start+1)+' / '+(b.end+2),borderColor:CATEGORY_COLOR[b.item.category]}}><b>{b.item.name}</b><small>{locked.includes(b.item.offering_id)?'🔒 已锁定':b.item.teacher} · {weekLabel(b)}</small></a>)}</div>
  <div className="daily-list">{!blocks.some(b=>visible(b)&&b.day===day)&&<p>当天没有排课</p>}{blocked.filter(s=>visible(s)&&s.day===day).map(s=><p key={s.start}>第 {s.start}–{s.end} 节 · 禁排</p>)}{blocks.filter(b=>visible(b)&&b.day===day).sort((a,b)=>a.start-b.start).map(b=><a key={b.key} href={'#class-'+b.item.offering_id}>第 {b.start}–{b.end} 节　{b.item.name}　{locked.includes(b.item.offering_id)?'🔒 已锁定':b.item.teacher}</a>)}</div></section>
}
