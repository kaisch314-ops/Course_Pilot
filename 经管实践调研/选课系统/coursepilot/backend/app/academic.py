"""Validated offline academic-data adapter; no school endpoint assumed."""
import json
from pathlib import Path
from typing import Protocol
from pydantic import BaseModel, Field, model_validator
from .models import Course, Offering

class StudentAcademicRecord(BaseModel):
    completed: list[str]
    major: str
    grade: int
    earned: dict[str, float] = Field(default_factory=dict)

class AcademicDataset(BaseModel):
    term:str
    major:str
    grade:int
    college:str=''
    notice:str='导入数据，请核对来源与适用学期'
    completed:list[str]=Field(default_factory=list)
    graduation:dict=Field(default_factory=dict)
    earned:dict=Field(default_factory=dict)
    plan:list[dict]
    requirements:list[dict]
    students:dict[str,StudentAcademicRecord]=Field(default_factory=dict)
    courses:list[Course]
    offerings:list[Offering]
    @model_validator(mode='after')
    def references(self):
        codes=[c.code for c in self.courses];ids=[o.id for o in self.offerings]
        if len(codes)!=len(set(codes)) or len(ids)!=len(set(ids)):raise ValueError('课程或班次编号重复')
        if any(o.code not in codes for o in self.offerings):raise ValueError('教学班关联了不存在的课程')
        if any(p.get('code') not in codes for p in self.plan):raise ValueError('培养计划关联了不存在的课程')
        for o in self.offerings:
            if not o.sessions:raise ValueError('教学班缺少时间')
            if any(s.end<s.start or any(w<1 or w>60 for w in s.weeks) for s in o.sessions):raise ValueError('课程时段或周次无效')
        return self

class AcademicDataSource(Protocol):
    def load(self)->dict: ...
class JsonAcademicDataSource:
    def __init__(self,path:Path):self.path=path
    def load(self):return AcademicDataset.model_validate_json(self.path.read_text(encoding='utf-8-sig')).model_dump()
