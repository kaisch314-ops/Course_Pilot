from tempfile import TemporaryDirectory
from pathlib import Path
from fastapi import FastAPI
import asyncio
import httpx
class TestClient:
 def __init__(self,app):self.app=app
 def call(self,method,url,**kwargs):
  async def run():
   async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url='http://test') as client:return await client.request(method,url,**kwargs)
  return asyncio.run(run())
 def post(self,url,**kwargs):return self.call('POST',url,**kwargs)
 def get(self,url,**kwargs):return self.call('GET',url,**kwargs)
 def delete(self,url,**kwargs):return self.call('DELETE',url,**kwargs)
from app.main import COURSES,OFFERINGS,SEED,bootstrap
from app.models import StudentProfile
from app.personal import create_router
from app.repository import JsonStudentRepository
with TemporaryDirectory() as folder:
 repo=JsonStudentRepository(Path(folder));app=FastAPI();app.include_router(create_router(repo,COURSES,OFFERINGS,SEED,StudentProfile(**bootstrap()['default_profile'])))
 c=TestClient(app);a=c.post('/api/students').json();b=c.post('/api/students').json();url='/api/students/'+a['id']
 r=c.post(url+'/chat',json={'revision':a['revision'],'text':'我想学数据分析，周三下午要实习'});assert r.status_code==200,r.text;a=r.json()
 assert a['draft']['blocked'][0]['day']==3
 assert c.post(url+'/chat',json={'revision':1,'text':'想轻松'}).status_code==409
 assert not c.get('/api/students/'+b['id']).json()['messages']
 assert JsonStudentRepository(Path(folder)).get(a['id'])['messages']
 course=next(v for v in COURSES.values() if v.tags)
 a=c.post(url+'/feedback',json={'revision':a['revision'],'course':course.code,'reason':'interest','direction':1}).json();fid=a['feedback'][0]['id']
 response=c.post(url+'/recommend',json={'revision':a['revision']});assert response.status_code==200,response.text
 data=response.json();assert data['result']['schedules'];assert data['profile']['affinity'];a=data['student']
 a=c.delete(url+'/feedback/'+fid,params={'revision':a['revision']}).json()
 data=c.post(url+'/recommend',json={'revision':a['revision']}).json();assert data['profile']['affinity']=={};a=data['student']
 assert c.post(url+'/feedback',json={'revision':a['revision'],'course':'fake','reason':'interest','direction':1}).status_code==422
 offering=OFFERINGS[0]
 a=c.post(url+'/outcomes',json={'revision':a['revision'],'offering_id':offering.id,'status':'completed','actual_weekly_hours':8}).json()
 metrics=c.get(url+'/iteration',params={'revision':a['revision']}).json()['metrics'];assert metrics['observed_load_samples']==1 and metrics['official_satisfaction_rate'] is None
 bad=c.post(url+'/outcomes',json={'revision':a['revision'],'offering_id':offering.id,'status':'not_selected','actual_weekly_hours':8});assert bad.status_code==422
 a=c.post(url+'/outcomes',json={'revision':a['revision'],'offering_id':offering.id,'status':'not_selected'}).json()
 assert c.get(url+'/iteration',params={'revision':a['revision']}).json()['metrics']['observed_load_samples']==0
 a=c.delete(url+'/outcomes/'+offering.code,params={'revision':a['revision']}).json();assert a['outcomes']=={} and a['outcome_history']==[]
 a=c.delete(url+'/messages',params={'revision':a['revision']}).json();assert not a['messages']
 assert c.delete(url,params={'revision':a['revision']}).status_code==200
 assert c.get(url).status_code==404
print('PASS: persistence, isolation, revision conflict, chat, feedback, recommendation, withdrawal, validation, deletion')

