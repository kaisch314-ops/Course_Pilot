import asyncio, os, tempfile
from pathlib import Path
import httpx
async def run():
 with tempfile.TemporaryDirectory() as folder:
  os.environ['COURSEPILOT_AUTH_FILE']=str(Path(folder)/'auth.db')
  os.environ['COURSEPILOT_STUDENT_DIR']=str(Path(folder)/'students')
  from app.main import app
  from app.academic import AcademicDataset
  from app.llm_gateway import LLMConfiguration
  assert 'secret' not in repr(LLMConfiguration(token='secret'))
  transport=httpx.ASGITransport(app=app)
  async with httpx.AsyncClient(transport=transport,base_url='http://test') as c:
   assert (await c.get('/api/bootstrap')).status_code==401
   for name in ['student_a','student_b']:
    assert (await c.post('/api/auth/register',json={'username':name,'password':'testing-password-123'})).status_code==201
   assert (await c.post('/api/auth/login',json={'username':'student_a','password':'incorrect-pass'})).status_code==401
   assert (await c.post('/api/auth/login',json={'username':'student_a','password':'testing-password-123'})).status_code==200
   assert (await c.get('/api/bootstrap')).status_code==200
   a=(await c.post('/api/students')).json()
   assert (await c.post('/api/students')).json()['id']==a['id']
   assert (await c.post('/api/auth/logout',headers={'origin':'http://evil'})).status_code==403
   await c.post('/api/auth/logout')
   assert (await c.get('/api/students/'+a['id'])).status_code==401
   await c.post('/api/auth/login',json={'username':'student_b','password':'testing-password-123'})
   assert (await c.get('/api/students/'+a['id'])).status_code==403
   b=(await c.post('/api/students')).json();assert a['id']!=b['id']
   await c.post('/api/auth/logout')
 print('PASS: authentication, account isolation, session revocation, origin check, token redaction')
asyncio.run(run())
