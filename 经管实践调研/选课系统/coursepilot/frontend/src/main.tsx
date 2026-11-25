import React, { useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import LoginGate from './components/LoginGate'
import TeacherApp from './components/TeacherApp'
import { getMe } from './api'
import type { Identity } from './types'
import './styles.css'

function Root() {
  const [identity, setIdentity] = useState<Identity>()
  useEffect(() => {
    getMe().then(setIdentity).catch(() => setIdentity(undefined))
  }, [])
  if (!identity) return <p>正在识别账户身份…</p>
  return identity.role === 'teacher' ? <TeacherApp /> : <App />
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <LoginGate>
      <Root />
    </LoginGate>
  </React.StrictMode>,
)
