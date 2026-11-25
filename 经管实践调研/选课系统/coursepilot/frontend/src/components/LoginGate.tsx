import { useEffect, useState, type ReactNode } from 'react'
export default function LoginGate({children}:{children:ReactNode}){
 const [user,setUser]=useState<string>(),[loading,setLoading]=useState(true),[working,setWorking]=useState(false),[register,setRegister]=useState(false),[error,setError]=useState(''),[name,setName]=useState(''),[password,setPassword]=useState(''),[role,setRole]=useState<'student'|'teacher'>('student')
 useEffect(()=>{fetch('/api/auth/me').then(async r=>{if(r.ok)setUser((await r.json()).username)}).catch(()=>setError('无法连接服务')).finally(()=>setLoading(false))},[])
 async function submit(){setWorking(true);setError('');try{const body=JSON.stringify({username:name,password});if(register){const r=await fetch('/api/auth/register',{method:'POST',headers:{'Content-Type':'application/json'},body});if(!r.ok)throw new Error((await r.json()).detail||'创建失败')}
 const r=await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body});if(!r.ok)throw new Error((await r.json()).detail||'登录失败');window.location.reload()
 }catch(e){setError(String(e))}finally{setWorking(false)}}
 if(loading)return <p>正在读取选课账户…</p>
 if(user)return <><div className="account-bar"><span>{user}</span><button onClick={async()=>{await fetch('/api/auth/logout',{method:'POST'});window.location.reload()}}>退出登录</button></div>{children}</>
 return <div className="login-shell"><form className="login-card" onSubmit={e=>{e.preventDefault();void submit()}}><small>COURSEPILOT</small><h1>开启你的学期规划</h1>
 <div role="tablist" aria-label="登录身份" style={{display:'flex',gap:'0.5rem'}}>
 <button type="button" role="tab" aria-selected={role==='student'} className={role==='student'?'primary':''} onClick={()=>{setRole('student');setError('')}}>我是学生</button>
 <button type="button" role="tab" aria-selected={role==='teacher'} className={role==='teacher'?'primary':''} onClick={()=>{setRole('teacher');setRegister(false);setError('')}}>我是教师</button></div>
 <p>{role==='student'?'登录后继续你的课程咨询与选课方案。':'登录后查看选课社区反馈、填写课程简介并回复学生提问。'}</p>
 <label>用户名<input required autoComplete="username" title={role==='teacher'?'教师请使用姓名登录':'3–40 位字母、数字、下划线或连字符'} value={name} onChange={e=>setName(e.target.value)}/></label><label>密码<input type="password" required minLength={10} maxLength={128} autoComplete={register?'new-password':'current-password'} value={password} onChange={e=>setPassword(e.target.value)}/></label>
 <small>{role==='teacher'?'教师账号由教务预置，用户名为教师姓名，初始密码由教务下发。':'用户名 3–40 位字母或数字等，密码至少 10 位。'}</small>{error&&<p role="alert">{error}</p>}<button className="primary" disabled={working}>{working?'请稍候…':register?'创建账户并登录':role==='teacher'?'教师登录':'登录'}</button>{role==='student'&&<button type="button" disabled={working} onClick={()=>{setRegister(!register);setError('')}}>{register?'已有账户，去登录':'首次使用，创建账户'}</button>}<p><small>本地项目账户，暂未接入学校统一身份认证。请勿使用学校账户密码。</small></p></form></div>
}
