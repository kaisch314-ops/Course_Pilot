import { useState } from 'react'

type Course = {id:number,name:string,code:string,teacher:string|null,count:number|null,average:number|null}
type Detail = Course & {term:string|null,reviews:{id:number,term:string|null,text:string}[]}
const topics: Record<string,RegExp> = {小组展示:/小组|展示|汇报|答辩|pre\b/i,课外投入:/小时|作业|课后|每周/,考试方式:/考试|开卷|闭卷|论文/}
async function query<T>(path:string):Promise<T>{
  const response=await fetch('/api/community/'+path)
  if (!response.ok) {
    const error=await response.json().catch(()=>({}))
    throw new Error(error.detail || '查询失败，请确认新版后端已启动')
  }
  return response.json()
}
export default function Community({name}:{name:string}){
  const [keyword,edit]=useState(name)
  const [rows,list]=useState<Course[]>()
  const [detail,show]=useState<Detail>()
  const [topic,choose]=useState('小组展示')
  const [busy,wait]=useState(false)
  const [error,report]=useState('')
  async function load(id?:number){
    wait(true);report('');show(undefined)
    try{
      if(id!==undefined)show(await query<Detail>('courses/'+id))
      else {list(undefined);list(await query<Course[]>('search?q='+encodeURIComponent(keyword.trim())))}
    }catch(e){report(e instanceof Error?e.message:'查询失败')}finally{wait(false)}
  }
  const hits=detail?.reviews.filter(r=>topics[topic].test(r.text)) || []
  return <details><summary>查看选课社区评价</summary><p>按真实课程与教师核对，当前课表使用演示班号。</p>
  <label>社区课程名或课号<input value={keyword} onChange={e=>edit(e.target.value)}/></label>
  <button disabled={busy||!keyword.trim()} onClick={()=>void load()}>搜索社区课程</button>
  {busy&&<p role="status">正在查询社区…</p>}{error&&<p role="alert">{error}</p>}
  {rows?.length===0&&<p>未找到匹配课程，请修改关键词。</p>}
  {rows?.map(r=><button disabled={busy} key={r.id} onClick={()=>void load(r.id)}>{r.name} · {r.code} · {r.teacher||'教师未提供'}</button>)}
  {detail&&<section><h4>{detail.name} · {detail.teacher||'教师未提供'}</h4>
  <p>{detail.term||'学期未知'} · 社区评分 {detail.count ? detail.average?.toFixed(1) ?? '未知':'暂无'} · {detail.count??'未知'} 人评分</p>
  <label>想了解什么？<select value={topic} onChange={e=>choose(e.target.value)}>{Object.keys(topics).map(t=><option key={t}>{t}</option>)}</select></label>
  <p>最近读取的 {detail.reviews.length} 条评价中，{hits.length} 条提到相关关键词。</p>
  {(hits.length?hits:detail.reviews).map(r=><details key={r.id}><summary>{r.term||'学期未知'} · 评价 #{r.id}</summary><p>{r.text||'无文字评价'}</p></details>)}
  <a href={'https://course.sjtu.plus/course/'+detail.id} target="_blank" rel="noreferrer">在 jCourse 查看来源</a></section>}</details>
}
