"""Optional local Ollama preference extraction. The client confirms all fields."""
import json
import os
from urllib.request import Request, urlopen

from fastapi import HTTPException
from pydantic import BaseModel, Field


class PreferenceText(BaseModel):
    text: str = Field(min_length=1, max_length=600)


def extract_preference(request: PreferenceText, tags: set[str]) -> dict:
    model = os.getenv("COURSEPILOT_MODEL")
    if not model:
        raise HTTPException(503, "未配置本地模型")
    schema = {"type":"object","properties":{
        "day":{"type":"integer","minimum":0,"maximum":7},
        "period":{"enum":["上午","下午","晚上"]},
        "interests":{"type":"array","items":{"type":"string","enum":sorted(tags)}}},
        "required":["day","period","interests"]}
    prompt = "从学生原话提取明确不可上课的一个时段（周一为1，未指定为0），以及正向兴趣标签。只返回符合格式的 JSON。原话：" + request.text
    payload = {"model":model,"prompt":prompt,"format":schema,"stream":False}
    req = Request("http://127.0.0.1:11434/api/generate", data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"})
    try:
        with urlopen(req, timeout=12) as response:
            fields = json.loads(json.load(response)["response"])
        if fields["day"] not in range(8) or fields["period"] not in schema["properties"]["period"]["enum"]:
            raise ValueError("invalid period")
        return {**fields, "interests":sorted(tags.intersection(fields["interests"]))}
    except (OSError, KeyError, ValueError, TypeError) as error:
        raise HTTPException(503, "本地模型不可用") from error
