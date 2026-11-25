import CourseAssistant from './components/CourseAssistant'
import Community from './components/Community'
import { QABoard, TeacherIntro } from './components/TeacherCorner'
import { useEffect, useRef, useState } from 'react'
import { getBootstrap, solve, swap } from './api'
import type { Bootstrap, Schedule, Session, SolveResponse, StudentProfile } from './types'
import Timetable, { weekLabel } from './components/Timetable'

const days = '一二三四五六日'
const periods: Record<string, number[]> = { 上午: [1, 4], 下午: [5, 9], 晚上: [10, 14] }
const dayLabel = (day: number) => '周' + days[day - 1]
function difference(old: Schedule, next: Schedule) {
  const changed = (a: Schedule, b: Schedule) => a.items.filter(i => !b.items.some(j => j.offering_id === i.offering_id)).map(i => i.name + ' ' + i.offering_id).join('、') || '无'
  return '移出 ' + changed(old, next) + '；加入 ' + changed(next, old) + '。课外投入变化 ' + (next.total_weekly_hours - old.total_weekly_hours).toFixed(1) + ' 小时/周。'
}
export default function App() {
  const [boot, setBoot] = useState<Bootstrap>()
  const [profile, setProfile] = useState<StudentProfile>()
  const [result, setResult] = useState<SolveResponse>()
  const [index, select] = useState(0)
  const [busy, setBusy] = useState(false)
  const [message, say] = useState('')
  const [previous, remember] = useState<Schedule>()
  const [sentence, write] = useState('周三下午有实践，想学数据分析')
  const [day, setDay] = useState(0)
  const [start, setStart] = useState(5)
  const [end, setEnd] = useState(9)
  const [slots, setSlots] = useState<Session[]>([])
  const [interest, setInterest] = useState('')
  const [codes, setCodes] = useState('')
  const [preview,setPreview] = useState<{p:StudentProfile,r:SolveResponse,id:string}>()
  const [editor,setEditor] = useState(()=>window.innerWidth>800)
  const previewBox = useRef<HTMLElement>(null)
  useEffect(() => { if (preview) previewBox.current?.focus() }, [preview])
  const serial = useRef(0)
  async function run(p: StudentProfile) {
    const id = ++serial.current
    setBusy(true); say(''); setPreview(undefined)
    try {
      const r = await solve(p)
      if (id !== serial.current) return
      if (r.schedules.length || !current) {
        setResult(r); setProfile(p); select(0)
      } else say(r.diagnostics.join('；') + '。仍显示原课表。')
    } catch (e) { if (id === serial.current) say('请求失败，条件尚未应用。'+String(e)) }
    finally { if (id === serial.current) setBusy(false) }
  }
  useEffect(() => {
    let live = true
    getBootstrap().then(b => {
      if (!live) return
      setBoot(b); setProfile(b.default_profile); setInterest(b.default_profile.interests.join('、')); setCodes(b.completed.join(', ')); setSlots(b.default_profile.blocked); void run(b.default_profile)
    }).catch(e => { if (live) say(String(e)) })
    return () => { live = false; serial.current++ }
  }, [])
  const current = result?.schedules[index]
  function addSlot(d = day, s = start, e = end) {
    if (!d) return
    const slot = { day: d, start: Math.min(s, e), end: Math.max(s, e), location: '' }
    setSlots((prev) => prev.some((x) => x.day === slot.day && x.start === slot.start && x.end === slot.end) ? prev : [...prev, slot])
  }
  async function parse() {
    try {
      const response = await fetch('/api/preferences', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:sentence})})
      if (response.ok) {
        const fields = await response.json()
        if (fields.day) addSlot(fields.day, periods[fields.period][0], periods[fields.period][1])
        setInterest(fields.interests.join('、'))
        say('本地模型已提取偏好，请核对后确认。')
        return
      }
    } catch { /* Local extraction also works without a model service. */ }
    const match = sentence.match(/(?:星期|周)([一二三四五六日])(上午|下午|晚上)/)
    if (match) addSlot(days.indexOf(match[1]) + 1, periods[match[2]][0], periods[match[2]][1])
    const tags = [...new Set(boot?.courses.flatMap(c => c.tags) || [])].filter(t => sentence.includes(t))
    if (sentence.includes('数据分析')) tags.push('计量', '实证', '量化')
    setInterest([...new Set(tags)].join('、'))
    say('本地解析完成。请核对下方时段与兴趣，未识别的要求需手动调整。')
  }
  function apply() {
    if (!profile || !boot) return
    const completed = [...new Set(codes.split(/[\s,，、]+/).filter(Boolean))]
    const known = new Set([...boot.completed, ...boot.courses.map(c => c.code)])
    const unknown = completed.filter(c => !known.has(c))
    if (unknown.length) { say('未匹配课号，请核对：' + unknown.join('、')); return }
    remember(undefined)
    void run({...profile, completed, interests: interest.split(/[\s,，、]+/).filter(Boolean), blocked: slots})
  }
  function download() {
    if (!current || !boot) return
    const lines = [boot.term, boot.notice, ...current.items.map(i => [i.offering_id,i.name,i.teacher,...i.sessions.map(s => dayLabel(s.day) + ' 第' + s.start + '–' + s.end + '节 ' + s.location+' '+weekLabel(s))].join(' | '))]
    const url = URL.createObjectURL(new Blob(['\uFEFF'+lines.join('\r\n')],{type:'text/plain;charset=utf-8'}))
    const link = document.createElement('a'); link.href=url; link.download='选课清单.txt'; link.click(); setTimeout(()=>URL.revokeObjectURL(url),1000)
  }
  async function markFull(id:string) {
    if (!profile || !current || !boot) return
    setBusy(true); say(''); setPreview(undefined)
    const p={...profile,excluded:[...profile.excluded,id]}
    const source=current.items.find(i=>i.offering_id===id)!
    try {
      for (const alt of boot.offerings.filter(o=>o.code===source.code && !p.excluded.includes(o.id))) {
        if (alt.sessions.some(s=>p.blocked.some(b=>b.day===s.day&&b.start<=s.end&&s.start<=b.end))) continue
        const reply=await swap({offering_ids:current.items.map(i=>i.offering_id),target:id,replacement:alt.id,profile:p})
        if(reply.ok && reply.schedule){
          setPreview({p,id,r:{schedules:[reply.schedule],frontier:[],diagnostics:[]}}); return
        }
      }
      const r=await solve(p)
      const cost=(s:Schedule)=>current.items.filter(i=>!s.items.some(j=>i.offering_id===j.offering_id)).length+s.items.filter(i=>!current.items.some(j=>i.offering_id===j.offering_id)).length
      r.schedules.sort((a,b)=>Number(!a.items.some(i=>i.code===source.code))-Number(!b.items.some(i=>i.code===source.code)) || cost(a)-cost(b))
      setPreview({p,r,id})
    } catch(e) {say('备选请求失败，原课表已保留。'+String(e))}
    finally {setBusy(false)}
  }
  const words=(v:string)=>v.split(/[\s,，、]+/).filter(Boolean)
  const changed=profile && (JSON.stringify(slots)!==JSON.stringify(profile.blocked) || words(interest).join()!==profile.interests.join() || words(codes).join()!==profile.completed.join())
  function title(s:Schedule,base:Schedule) {
    if(s===base)return '当前首选'
    if(s.used_days<base.used_days)return '少到校 '+(base.used_days-s.used_days)+' 天'
    if(s.total_weekly_hours<base.total_weekly_hours)return '周投入少 '+(base.total_weekly_hours-s.total_weekly_hours).toFixed(1)+' 小时'
    return s.items.find(i=>!base.items.some(j=>j.code===i.code))?.name || '同课程 · 不同班次'
  }
  return <div className="desk"><nav className="mast"><strong><i aria-hidden="true">▦</i> CoursePilot</strong><div><a href="#calendar">学期课表</a><a href="#courses">选课清单</a></div></nav>
    <header className="cover"><div><small>上海交通大学　/　{boot?.major || '选课工作台'}</small><h1>我的学期课表</h1></div><p>{boot?.term} <span>演示数据</span></p></header>
    {message && <p role="status">{message}</p>}
    {boot && profile && <div className="workspace"><aside><button aria-expanded={editor} onClick={()=>setEditor(!editor)}>选课条件　{editor?"收起":"展开"}</button>{editor && <><label>用一句话描述偏好<textarea value={sentence} onChange={e=>write(e.target.value)}/></label><button onClick={parse}>解析偏好</button>
    <label>不可上课的时段（可添加多段）<select value={day} onChange={e=>setDay(+e.target.value)}><option value={0}>选择星期</option>{[...days].map((d,i)=><option key={d} value={i+1}>周{d}</option>)}</select></label>
    <div style={{display:'flex',alignItems:'center',gap:6}}><span style={{flexShrink:0}}>第</span><select className="period-select" aria-label="开始节" value={start} onChange={e=>setStart(+e.target.value)}>{Array.from({length:14},(_,i)=><option key={i+1} value={i+1}>{i+1}</option>)}</select><span style={{flexShrink:0}}>节 到 第</span><select className="period-select" aria-label="结束节" value={end} onChange={e=>setEnd(+e.target.value)}>{Array.from({length:14},(_,i)=><option key={i+1} value={i+1}>{i+1}</option>)}</select><span style={{flexShrink:0}}>节</span></div>
    <button disabled={!day} onClick={()=>{addSlot();setDay(0)}}>＋ 添加该时段</button>
    {slots.map((s,i)=><p key={s.day+'-'+s.start+'-'+s.end} className="slot-row">{dayLabel(s.day)} 第{s.start}–{s.end}节<button aria-label="删除该时段" onClick={()=>setSlots(slots.filter((_,j)=>j!==i))}>×</button></p>)}
    <label>兴趣标签<input value={interest} onChange={e=>setInterest(e.target.value)} placeholder="计量、实证、量化"/></label>
    <details><summary>导入或修改已修课号</summary><p>文本或单列 CSV，每行一个课号，无表头。</p><input type="file" accept=".txt,.csv" onChange={async e=>{const f=e.target.files?.[0]; if(f)setCodes(await f.text())}}/><textarea aria-label="已修课号" value={codes} onChange={e=>setCodes(e.target.value)}/></details>
    <button className="primary" disabled={busy} onClick={apply}>应用条件并生成课表</button>
    <details><summary>修读进度与培养依据</summary>{boot.plan.filter(r=>r.module==='必修').map(r=><p key={r.code}>{boot.courses.find(c=>c.code===r.code)?.name} · {profile.completed.includes(r.code)?'已修':'待修'}<br/><small>毕业必修 · 建议第 {r.suggest_term} 学期</small></p>)}
    <small>依据：本地示例培养计划及已确认课号</small></details></>}
    </aside><main id="calendar"><CourseAssistant profile={profile} courses={boot.courses} offerings={boot.offerings} busy={busy} onApply={(p,r)=>{setInterest(p.interests.join('、'));setSlots(p.blocked);setDay(0);setProfile(p);setResult(r);select(0);setPreview(undefined);remember(undefined)}}/><h2>课表方案</h2>{busy && <p>正在计算，原课表保留供核对…</p>}
    <div className="active-rules"><b>已采用条件</b><span>{profile.blocked.map(b=>dayLabel(b.day)+'第'+b.start+'–'+b.end+'节禁排').join('、') || '无禁排时段'}</span><span>兴趣 · {profile.interests.join('、')||'不限'}</span><span>锁定 {profile.locked.length} 班</span></div>
    {changed && <p className="change-note">条件已修改，等待重新排课</p>}
    {/展示|汇报/.test(sentence)&&<p>对展示或汇报的偏好尚未参与排序，可核对各课考核方式。</p>}
    {profile.excluded.map(id=><button key={id} disabled={busy} onClick={()=>{setProfile({...profile,excluded:profile.excluded.filter(x=>x!==id)});setPreview(undefined)}}>撤销 {id} 满员记录</button>)}
    {preview && <section className="review" role="status" ref={previewBox} tabIndex={-1}><h3>{preview.r.schedules.length?'备选预览':'未找到可用备选'}</h3><p>本次满员班次：{preview.id}</p>
    {preview.r.schedules[0] && current ? <><p>{difference(current,preview.r.schedules[0])}</p><p>保留锁定班：{profile.locked.join('、')||'无'}。{profile.blocked.map(b=>dayLabel(b.day)+'第'+b.start+'–'+b.end+'节仍空闲').join('、')}</p>
    <button className="primary" onClick={()=>{remember(current);setProfile(preview.p);setResult(preview.r);select(0);setPreview(undefined)}}>采用备选</button></>:<p>{preview.r.diagnostics.join('；')}。仍显示原课表。</p>}
    <button onClick={()=>setPreview(undefined)}>撤销本次满员标记</button></section>}
    {result?.diagnostics.map(d=><p key={d}>{d}</p>)}
    {result?.schedules.map((s,i)=><button disabled={busy || !!preview} key={s.id} aria-pressed={index===i} onClick={()=>select(i)}>{title(s,result.schedules[0])} · {s.total_credits} 学分</button>)}
    {current && <><div className="metrics">{[[current.total_credits,'学分'],[current.items.length,'门课程'],[current.total_weekly_hours,'小时 / 周 · 模拟值'],[current.used_days,'天有课']].map(([n,label])=><div key={label}><b>{n}</b><small>{label}</small></div>)}</div>
    {(previous || index>0) && <p>{difference(previous || result!.schedules[0],current)}</p>}
    <div className="calendar-scroll"><Timetable items={current.items} blocked={profile.blocked} locked={profile.locked}/></div><div className="section-head" id="courses"><h2>选课清单</h2><button onClick={download}>↓ 下载离线清单</button></div>
    {current.items.map(i=>{const c=boot.courses.find(c=>c.code===i.code)!; const locked=profile.locked.includes(i.offering_id)
    return <article id={"class-"+i.offering_id} key={i.offering_id}><h3>{i.name} <small>{i.category}</small></h3><p><code>{i.offering_id}</code> <button onClick={async()=>{try{await navigator.clipboard.writeText(i.offering_id);say("已复制 "+i.offering_id)}catch{say("请手动复制 "+i.offering_id)}}}>复制班号</button> · {i.teacher} · {i.credits} 学分</p>
    <p>{i.sessions.map(s=>dayLabel(s.day)+' '+s.start+'–'+s.end+'节 · '+s.location+' · '+weekLabel(s)).join(' / ')}</p>
    <button disabled={busy || !!preview} onClick={()=>{setProfile({...profile,locked:locked?profile.locked.filter(x=>x!==i.offering_id):[...profile.locked,i.offering_id]});setResult({...result!,schedules:[current]});select(0)}}>{locked?'🔒 已锁定 · 解除':'已选上，锁定此班'}</button>
    <button disabled={busy || locked || !!preview} onClick={()=>void markFull(i.offering_id)}>标记满员</button>
    {i.tags.some(t=>profile.interests.includes(t))&&<p>匹配兴趣：{i.tags.filter(t=>profile.interests.includes(t)).join('、')}</p>}
    <Community name={i.name}/><TeacherIntro code={i.code}/><QABoard code={i.code} teachers={[...new Set(boot.offerings.filter(o=>o.code===i.code).map(o=>o.teacher))]}/><details><summary>工作量与评价依据</summary><p>{i.summary}</p><p>示例周均 {i.weekly_hours} 小时 · 示例难度 {i.difficulty} · 教师示例评分 {i.teacher_rating}</p><p>{Object.entries(c.profile.assessment).map(([k,v])=>k+' '+v+'%').join(' / ')}</p><small>来源：本地 seed.json 模拟画像，样本量字段 {c.profile.sample_size}。真实反馈与用时分布暂无数据。</small></details></article>})}</>}
    <p><small>{boot.notice}</small></p></main></div>}</div>
}



