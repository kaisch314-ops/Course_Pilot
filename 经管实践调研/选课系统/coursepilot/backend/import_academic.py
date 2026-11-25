"""Validate and copy a school export without overwriting the demo seed."""
import argparse
import json
from pathlib import Path
from app.academic import JsonAcademicDataSource
parser=argparse.ArgumentParser()
parser.add_argument('source',type=Path)
parser.add_argument('destination',type=Path)
args=parser.parse_args()
data=JsonAcademicDataSource(args.source).load()
if args.destination.exists():parser.error('目标已存在；请使用新的版本文件名')
args.destination.parent.mkdir(parents=True,exist_ok=True)
with args.destination.open('x',encoding='utf-8') as stream:json.dump(data,stream,ensure_ascii=False,indent=2)
print('Validated academic dataset imported. Configure COURSEPILOT_ACADEMIC_FILE and restart.')
