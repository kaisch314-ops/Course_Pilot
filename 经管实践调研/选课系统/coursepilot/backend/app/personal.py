"""Personal recommendation application service. No external AI API required."""
import math
import re
from datetime import datetime, timezone
from typing import Protocol, Literal
from uuid import UUID, uuid4
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from .models import StudentProfile, Session
from .repository import StudentRepository, Conflict
from . import solver
from .calibration import calibrate
from .iteration import iterate, invalidate, state, install_routes

def now(): return datetime.now(timezone.utc).isoformat()

class DialogueProvider(Protocol):
    def extract(self, text: str, profile: StudentProfile, courses: dict) -> tuple[StudentProfile, list[str], list[dict]]: ...

class RuleDialogueProvider:
    def extract(self, text, profile, courses):
        p = profile.model_copy(deep=True)
        changes, feedback = [], []
        tags = {t for c in courses.values() for t in c.tags}
        for clause in re.split(r'[，。；！？,;!?\n]',text):
            negative = bool(re.search('不想|不喜欢|没兴趣|不要|取消',clause))
            if re.search('喜欢|想学|兴趣|量化|数据分析',clause):
                matched = sorted(t for t in tags if t in clause or ('数据分析' in clause and t in ['计量','实证','量化']))
                for tag in matched:
                    if negative: p.interests=[t for t in p.interests if t!=tag]
                    elif tag not in p.interests: p.interests.append(tag)
                if matched: changes.append(('暂不考虑' if negative else '关注')+'、'.join(matched))
            for pattern,field,value,description in [
                ('想轻松|降低负荷|时间紧张|实习很忙','challenge',.2,'减轻本学期负担'),
                ('愿意挑战|提高难度','challenge',.8,'增加课程挑战'),
                ('成绩优先|重视绩点','focus',.2,'更重视成绩'),
                ('能力优先|学到东西','focus',.8,'更重视能力提升'),
                ('不要早八|不想早八','avoid_early',True,'尽量避开早八'),
                ('可以早八','avoid_early',False,'允许早八')]:
                if re.search(pattern,clause): setattr(p,field,value);changes.append(description)
            match=re.search(r'(?:周|星期)([一二三四五六日])(上午|下午|晚上)',clause)
            if match and re.search('不能|没空|实习|实践|取消禁排',clause):
                day='一二三四五六日'.index(match[1])+1
                start,end={'上午':(1,4),'下午':(5,9),'晚上':(10,14)}[match[2]]
                p.blocked=[s for s in p.blocked if (s.day,s.start,s.end)!=(day,start,end)]
                if '取消禁排' not in clause:p.blocked.append(Session(day=day,start=start,end=end,location='个人安排'))
                changes.append(('恢复' if '取消禁排' in clause else '避开')+match[0])
            for c in courses.values():
                if c.name in clause and '喜欢' in clause:
                    feedback.append({'id':str(uuid4()),'course':c.code,'tags':c.tags,'reason':'interest','direction':-1 if negative else 1,'time':now(),'source':clause})
                    changes.append('记下你对'+c.name+'的反馈')
        return p,changes,feedback

def learned_profile(base, feedback, gain=1.0):
    p=StudentProfile(**base)
    evidence={}; load=0; growth=0
    latest={}
    for item in feedback:latest[(item['course'],item['reason'])]=item
    for f in latest.values():
        if f['reason']=='interest':
            for tag in f['tags']:evidence[tag]=evidence.get(tag,0)+f['direction']
        elif f['reason']=='load':load+=f['direction']
        elif f['reason']=='growth':growth+=f['direction']
    p.affinity={tag:math.tanh(gain*v/3) for tag,v in evidence.items()}
    p.challenge=max(0,min(1,p.challenge+.25*math.tanh((growth-load)/3)))
    return p

class Revision(BaseModel):
    revision: int = Field(ge=1)
class Chat(Revision):
    text: str = Field(min_length=1,max_length=600)
class FeedbackInput(Revision):
    course: str
    reason: Literal['interest','load','growth']
    direction: Literal[-1,1]
class Recommend(Revision):
    # Temporary workbench constraints, never a client-provided learned model.
    locked: list[str] = Field(default_factory=list,max_length=100)
    excluded: list[str] = Field(default_factory=list,max_length=100)
class ProfileEdit(Revision):
    interests: list[str] = Field(max_length=100)
    goal: str = Field(max_length=300)
    focus: float = Field(ge=0,le=1)
    challenge: float = Field(ge=0,le=1)
    exploration: float = Field(ge=0,le=1)



def create_router(repository: StudentRepository, courses, offerings, seed, default_profile, provider: DialogueProvider | None = None):
    router=APIRouter(prefix='/api/students',tags=['personal recommendation'])
    provider=provider or RuleDialogueProvider()
    def read(student_id):
        doc=repository.get(str(student_id))
        if doc is None:raise HTTPException(404,'档案不存在')
        return doc
    def check(student_id, revision):
        doc=read(student_id)
        if doc['revision']!=revision:raise HTTPException(409,'档案已更新，请重新加载后重试')
        return doc
    def save(student_id,doc,revision):
        doc['updated_at']=now()
        try:return repository.save(str(student_id),doc,revision)
        except Conflict as e:raise HTTPException(409,str(e))
    @router.post('',status_code=201)
    def create(request:Request):
        identity=getattr(request.state,'identity',None)
        sid=identity['student_id'] if identity else str(uuid4())
        existing=repository.get(sid)
        record=seed.get('students',{}).get(identity['username'],{}) if identity else {}
        initial=default_profile.model_copy(deep=True)
        for field in ('completed','major','grade'):
            if field in record:setattr(initial,field,record[field])
        if existing:
            if record:
                for field in ('completed','major','grade'):
                    existing['profile'][field]=getattr(initial,field)
                    if existing['draft']:existing['draft'][field]=getattr(initial,field)
                return save(sid,existing,existing['revision'])
            return existing
        return save(sid,{'id':sid,'profile':initial.model_dump(),'draft':None,'messages':[],'feedback':[],'evidence':[],'created_at':now()},0)
    @router.get('/{student_id}')
    def get(student_id:UUID):return read(student_id)
    @router.post('/{student_id}/chat')
    def chat(student_id:UUID,request:Chat):
        if not request.text.strip():raise HTTPException(422,'请输入内容')
        doc=check(student_id,request.revision)
        base=StudentProfile(**(doc['draft'] or doc['profile']))
        p,changes,feedback=provider.extract(request.text,base,courses)
        if changes:doc['draft']=p.model_dump()
        doc['feedback'].extend(feedback)
        if feedback:iterate(doc)
        reply='好的，我会'+ '、'.join(changes)+'。可以按这些安排更新课表。' if changes else '我还不太确定你的意思。你可以告诉我想学的方向，或具体哪天不能上课。'
        doc['messages'].extend([{'role':'我','text':request.text,'time':now()},{'role':'选课咨询','text':reply,'time':now()}])
        doc['evidence'].append({'source':request.text,'changes':changes,'time':now(),'provider':'local-rules'})
        return save(student_id,doc,request.revision)
    @router.post('/{student_id}/feedback')
    def feedback(student_id:UUID,request:FeedbackInput):
        doc=check(student_id,request.revision)
        if request.course not in courses:raise HTTPException(422,'未知课程')
        doc['feedback'].append({'id':str(uuid4()),'course':request.course,'tags':courses[request.course].tags,'reason':request.reason,'direction':request.direction,'time':now(),'source':'explicit'})
        iterate(doc)
        return save(student_id,doc,request.revision)
    @router.delete('/{student_id}/feedback/{feedback_id}')
    def withdraw(student_id:UUID,feedback_id:UUID,revision:int):
        doc=check(student_id,revision)
        if not any(f['id']==str(feedback_id) for f in doc['feedback']):raise HTTPException(404,'反馈不存在')
        doc['feedback']=[f for f in doc['feedback'] if f['id']!=str(feedback_id)]
        invalidate(doc)
        return save(student_id,doc,revision)
    @router.put('/{student_id}/profile')
    def edit(student_id:UUID,request:ProfileEdit):
        doc=check(student_id,request.revision)
        doc['profile'].update(request.model_dump(exclude={'revision'}));doc['draft']=None
        return save(student_id,doc,request.revision)
    @router.post('/{student_id}/recommend')
    def recommend(student_id:UUID,request:Recommend):
        doc=check(student_id,request.revision)
        base=doc['draft'] or doc['profile']
        p=learned_profile(base,doc['feedback'],state(doc)['active_gain']);p.locked=request.locked;p.excluded=request.excluded
        personal_courses,calibration=calibrate(doc,courses,seed['term'])
        result=solver.solve(personal_courses,offerings,seed['plan'],p,seed.get('requirements'))
        if result.schedules:
            doc['profile']=base;doc['draft']=None
            doc['messages'].append({'role':'选课咨询','text':'课表已更新，你可以在课表区域比较方案。','time':now()})
        else:doc['messages'].append({'role':'选课咨询','text':'暂时没有找到满足条件的方案，原课表已保留。可以放宽时间安排后再试。','time':now()})
        doc.setdefault('recommendation_history',[]).append({'time':now(),'policy_version':state(doc)['active_version'],'gain':state(doc)['active_gain'],'calibration':calibration,'feasible':bool(result.schedules),'schedule_ids':[s.id for s in result.schedules]})
        saved=save(student_id,doc,request.revision)
        return {'student':saved,'profile':p.model_dump(),'result':result.model_dump(),'calibration':calibration}
    @router.delete('/{student_id}/draft')
    def discard(student_id:UUID,revision:int):
        doc=check(student_id,revision);doc['draft']=None
        return save(student_id,doc,revision)
    @router.delete('/{student_id}/messages')
    def clear(student_id:UUID,revision:int):
        doc=check(student_id,revision);doc['messages']=[];doc['evidence']=[];doc['draft']=None
        return save(student_id,doc,revision)
    @router.delete('/{student_id}')
    def delete(student_id:UUID,revision:int):
        check(student_id,revision)
        try:repository.delete(str(student_id),revision)
        except Conflict as e:raise HTTPException(409,str(e))
        return {'deleted':True}
    install_routes(router,check,save,courses,offerings,seed)
    return router
