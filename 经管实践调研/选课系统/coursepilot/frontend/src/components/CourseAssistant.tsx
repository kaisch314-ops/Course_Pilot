import { useEffect, useRef, useState } from 'react'
import type { StudentProfile, Course, Offering, SolveResponse } from '../types'
type Props = { profile: StudentProfile; courses: Course[]; offerings: Offering[]; busy: boolean; onApply: (p: StudentProfile, result: SolveResponse) => void }
type Student = {id:string; revision:number; messages:{role:string;text:string}[]; draft:StudentProfile|null}
async function request(path:string,method='GET',body?:unknown){
 const r=await fetch('/api/students'+path,{method,headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)})
 if(!r.ok){const e=await r.json().catch(()=>({}));throw new Error(e.detail||'请求失败，请重试')}
 return r.json()
}
let initializing:Promise<Student>|undefined
function initialize(){if(!initializing)initializing=request('','POST').catch(e=>{initializing=undefined;throw e});return initializing}
export default function CourseAssistant({profile,courses,offerings,busy:parentBusy,onApply}:Props){
 const [student,setStudent]=useState<Student>()
 const [pending,setPending]=useState(false)
 const busy=parentBusy||pending||!student
 const [open,setOpen]=useState(false)
 const [text,setText]=useState('')
 const [showFeedback,setShowFeedback]=useState(false)
 const [offeringId,setOfferingId]=useState(offerings[0]?.id||'')
 const [outcome,setOutcome]=useState('enrolled')
 const [hours,setHours]=useState('')
 const [note,setNote]=useState('')
 const [feedbackMessage,setFeedbackMessage]=useState('')
 async function submitOutcome(){const ok=await mutate('outcomes','POST',{offering_id:offeringId,status:outcome,actual_weekly_hours:outcome==='not_selected'||hours===''?null:Number(hours),note});if(ok){setFeedbackMessage('已保存，谢谢你的反馈。你可以随时修改或撤回。');setShowFeedback(false)}}

 const [error,setError]=useState('')
 const messages=student?.messages||[]
 const draft=student?.draft
 const end=useRef<HTMLDivElement>(null),launcher=useRef<HTMLButtonElement>(null),input=useRef<HTMLTextAreaElement>(null)
 useEffect(()=>{let live=true;initialize().then(s=>{if(live)setStudent(s)}).catch(e=>{if(live)setError(String(e))});return()=>{live=false}},[])
 useEffect(()=>{if(open){input.current?.focus();end.current?.scrollIntoView({block:'nearest'})}},[open,messages])
 function close(){setOpen(false);launcher.current?.focus()}
 async function mutate(action:string,method='POST',extra:object={}){
  if(!student||pending)return
  setPending(true);setError('')
  try{const path='/'+student.id+'/'+action+(method==='DELETE'?'?revision='+student.revision:'');const data=await request(path,method,method==='DELETE'?undefined:{revision:student.revision,...extra});if(action==='recommend'){setStudent(data.student);if(data.result.schedules.length)onApply(data.profile,data.result)}else setStudent(data);return true}
  catch(e){setError(String(e));try{setStudent(await request('/'+student.id))}catch{}return false}
  finally{setPending(false)}
 }
 async function send(value=text){if(!value.trim()||busy)return;if(await mutate('chat','POST',{text:value}))setText('')}
 function recommend(){void mutate('recommend','POST',{locked:profile.locked,excluded:profile.excluded})}
  return <div className="consultation-root">
    {open&&<section className="consultation-panel" role="dialog" aria-label="选课咨询" onKeyDown={e=>{if(e.key==='Escape')close()}}>
      <header className="consultation-header"><div><span className="consultation-mark">C</span><div><strong>选课咨询</strong><small>一起安排更适合你的学期</small></div></div><button aria-label="收起选课咨询" onClick={close}>×</button></header>
      <div className="consultation-body"><div className="consultation-welcome"><small>YOUR SEMESTER, YOUR WAY</small><h3>这学期，想怎么安排？</h3><p>聊聊想学的课程、最近的计划，或选课时的纠结。</p></div>
      {!messages.length&&<div className="consultation-suggestions">{['我想学数据分析','周三下午要实习','这学期想轻松一点'].map(v=><button disabled={busy} key={v} onClick={()=>send(v)}>{v}<span>↗</span></button>)}</div>}
      <div aria-live="polite">{messages.map((m,i)=><div key={i} className={'consultation-message '+(m.role==='我'?'from-me':'from-advisor')}>{m.text}</div>)}</div>
      {draft&&<div className="consultation-action"><button disabled={busy} onClick={recommend}>{busy?'正在更新…':'按这个安排更新课表'} <span>→</span></button><button disabled={busy} onClick={()=>void mutate("draft","DELETE")}>暂不调整</button></div>}
      <button onClick={()=>setShowFeedback(!showFeedback)}>反馈选课与修读情况</button>
      {showFeedback&&<form className="course-outcome" onSubmit={e=>{e.preventDefault();void submitOutcome()}}><label>教学班<select value={offeringId} onChange={e=>setOfferingId(e.target.value)}>{offerings.map(o=><option key={o.id} value={o.id}>{courses.find(c=>c.code===o.code)?.name} · {o.teacher} · {o.id}</option>)}</select></label><label>目前情况<select value={outcome} onChange={e=>setOutcome(e.target.value)}><option value="not_selected">没选上</option><option value="enrolled">已选上，正在修读</option><option value="dropped">选上后退课</option><option value="completed">已完成修读</option></select></label>{outcome!=='not_selected'&&<label>每周课外投入（小时，可不填）<input type="number" min="0" max="100" step="0.5" value={hours} onChange={e=>setHours(e.target.value)}/></label>}<label>想补充的情况<textarea maxLength={600} value={note} onChange={e=>setNote(e.target.value)}/></label><p>自愿反馈，不影响选课资格。选课结果以学校系统为准。</p><button disabled={busy}>保存反馈</button><button type="button" disabled={busy} onClick={async()=>{const code=offerings.find(o=>o.id===offeringId)?.code;if(code&&await mutate('outcomes/'+code,'DELETE')){setFeedbackMessage('已撤回这门课的反馈');setShowFeedback(false)}}}>撤回该课程反馈</button></form>}
      {feedbackMessage&&<p role="status">{feedbackMessage}</p>}
      {error&&<p role="status">{error}</p>}<div ref={end}/></div>
      <form className="consultation-compose" onSubmit={e=>{e.preventDefault();send()}}><textarea ref={input} aria-label="咨询内容" maxLength={600} value={text} onChange={e=>setText(e.target.value)} placeholder="说说你的选课想法…" onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();if(text.trim()&&!busy)send()}}}/><button aria-label="发送消息" disabled={busy||!text.trim()}>↑</button></form>
      <footer className="consultation-footer"><span>Enter 发送 · Shift + Enter 换行</span><button onClick={()=>{void mutate("messages","DELETE")}}>清空对话</button></footer>
    </section>}
    <button ref={launcher} className="consultation-launcher" aria-expanded={open} aria-label="打开选课咨询" onClick={()=>setOpen(!open)}><svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M20 11.5a8 8 0 0 1-8 8H5l-3 2v-10a9 9 0 0 1 18 0Z"/><path d="M7 10h8M7 14h5"/></svg><span>选课咨询</span></button>
  </div>
}
