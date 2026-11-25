"""Bounded, auditable preference-policy iteration. Never edits code or academic rules."""
import hashlib
import json
import math
from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, Field

def stamp(): return datetime.now(timezone.utc).isoformat()
def state(doc):
    return doc.setdefault('iteration',{'active_gain':1.0,'active_version':'baseline','versions':[],'evaluations':[]})
def affinity(feedback,gain=1.0):
    evidence={}
    for f in feedback:
        if f['reason']=='interest':
            for tag in f['tags']:evidence[tag]=evidence.get(tag,0)+f['direction']
    return {t:math.tanh(gain*v/3) for t,v in evidence.items()}
def loss(train,test,gain):
    scores=affinity(train,gain)
    return sum(((1+sum(scores.get(t,0) for t in f['tags'])/max(1,len(f['tags'])))/2-(f['direction']+1)/2)**2 for f in test)/len(test)
def iterate(doc):
    policy=state(doc)
    # Latest explicit interest response per course; retries/repeated comments cannot inflate N.
    unique={}
    for f in doc['feedback']:
        if f['reason']=='interest' and f['tags']:unique[f['course']]=f
    events=sorted(unique.values(),key=lambda f:(f['time'],f['id']))
    fingerprint=hashlib.sha256(json.dumps(events,sort_keys=True).encode()).hexdigest()
    if any(e['fingerprint']==fingerprint for e in policy['evaluations']):return
    audit={'id':str(uuid4()),'time':stamp(),'fingerprint':fingerprint,'samples':len(events),'status':'insufficient_data','reason':'至少需要 10 门不同课程的明确兴趣反馈；不把落选或退课视为不喜欢。'}
    if len(events)>=10:
        # Train / validation / untouched chronological test. Tune only on validation.
        split=int(len(events)*.6);mid=int(len(events)*.8)
        train,validation,test=events[:split],events[split:mid],events[mid:]
        used=set(policy.get('tested_courses',[]))
        if len(test)<2 or any(f['course'] in used for f in test):
            audit.update(status='waiting_new_test',reason='等待至少两门未用于测试的新课程反馈，避免重复使用测试集。')
            policy['evaluations'].append(audit)
            return
        policy['tested_courses']=sorted(used|{f['course'] for f in test})
        current=policy['active_gain']
        candidates=[.5,1.0,1.5]
        gain=min(candidates,key=lambda g:(loss(train,validation,g),abs(g-current)))
        baseline=loss(train,test,current);candidate=loss(train,test,gain)
        audit.update(status='rejected',reason='独立测试分数未达到最小改进幅度，保留当前策略。',train_count=len(train),validation_count=len(validation),test_count=len(test),baseline_brier=baseline,candidate_brier=candidate,candidate_gain=gain)
        if gain!=current and baseline-candidate>=.01:
            version={'id':str(uuid4()),'time':stamp(),'gain':gain,'previous_gain':current,'source':fingerprint,'evaluation_id':audit['id']}
            policy['versions'].append(version);policy['active_gain']=gain;policy['active_version']=version['id']
            audit.update(status='promoted',reason='离线测试 Brier 误差至少降低 0.01，采用有界偏好强度。')
    policy['evaluations'].append(audit)
    policy['evaluations']=policy['evaluations'][-100:]

def invalidate(doc):
    policy=state(doc)
    policy['active_gain']=1.0;policy['active_version']='baseline'
    policy['evaluations'].append({'id':str(uuid4()),'time':stamp(),'fingerprint':str(uuid4()),'status':'invalidated','reason':'反馈撤回后回到基线，旧评价仅保留审计记录。'})

class Outcome(BaseModel):
    revision:int=Field(ge=1)
    offering_id:str
    status:Literal['not_selected','enrolled','dropped','completed']
    actual_weekly_hours:float|None=Field(default=None,ge=0,le=100)
    expectation:Literal['matches','lighter','heavier','unknown']='unknown'
    note:str=Field(default='',max_length=600)
class Rollback(BaseModel):
    revision:int=Field(ge=1)
    version_id:str='baseline'

def install_routes(router,check,save,courses,offerings,seed):
    @router.post('/{student_id}/outcomes')
    def outcome(student_id:UUID,request:Outcome):
        doc=check(student_id,request.revision)
        offering=next((o for o in offerings if o.id==request.offering_id),None)
        if offering is None:raise HTTPException(422,'未知教学班')
        if request.status=='not_selected' and request.actual_weekly_hours is not None:raise HTTPException(422,'未选上不能提交实际修读负荷')
        key=seed['term']+':'+offering.code
        records=doc.setdefault('outcomes',{})
        event={**request.model_dump(exclude={'revision'}),'course':offering.code,'term':seed['term'],'id':str(uuid4()),'time':stamp(),'source':'student_report','predicted_weekly_hours':courses[offering.code].profile.weekly_hours}
        records[key]=event
        doc.setdefault('outcome_history',[]).append(event)
        return save(student_id,doc,request.revision)
    @router.delete('/{student_id}/outcomes/{course_code}')
    def remove(student_id:UUID,course_code:str,revision:int):
        doc=check(student_id,revision);key=seed['term']+':'+course_code
        if key not in doc.get('outcomes',{}):raise HTTPException(404,'反馈不存在')
        del doc['outcomes'][key]
        doc['outcome_history']=[e for e in doc.get('outcome_history',[]) if not(e['course']==course_code and e['term']==seed['term'])]
        return save(student_id,doc,revision)
    @router.get('/{student_id}/iteration')
    def inspect(student_id:UUID,revision:int):
        doc=check(student_id,revision)
        records=list(doc.get('outcomes',{}).values())
        observed=[r for r in records if r['status'] in ['enrolled','completed'] and r['actual_weekly_hours'] is not None]
        return {'policy':state(doc),'outcomes':records,'metrics':{'student_reported_courses':len(records),'observed_load_samples':len(observed),'load_mae':sum(abs(r['actual_weekly_hours']-r['predicted_weekly_hours']) for r in observed)/len(observed) if observed else None,'official_satisfaction_rate':None},'notice':'仅本人自报反馈；未接官方结果，无全体需求分母，不计算正式满足率。'}
    @router.post('/{student_id}/iterate')
    def run(student_id:UUID,request:Rollback):
        doc=check(student_id,request.revision);iterate(doc);return save(student_id,doc,request.revision)
    @router.post('/{student_id}/iteration/rollback')
    def rollback(student_id:UUID,request:Rollback):
        doc=check(student_id,request.revision);policy=state(doc)
        # Always safe baseline; historic promoted versions may depend on withdrawn data.
        if request.version_id!='baseline':raise HTTPException(422,'仅支持回退基线，历史版本需用当前反馈重新评估')
        invalidate(doc)
        return save(student_id,doc,request.revision)
