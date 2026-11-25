"""Read-only jCourse client. Credentials stay in the local backend."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/community")
BASE = "https://course.sjtu.plus/api"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def fetch(path, **params):
    key = os.environ.get("JCOURSE_API_KEY", "").strip()
    if not key:
        raise HTTPException(401, "请在启动后端的终端配置 JCOURSE_API_KEY，再重启服务。")
    req = Request(BASE + path + "?" + urlencode(params), headers={"Authorization": "Bearer " + key})
    try:
        with build_opener(NoRedirect()).open(req, timeout=10) as res:
            return json.load(res)
    except HTTPError as exc:
        errors = {401:"社区密钥无效或已过期",403:"社区拒绝了本次访问",404:"课程已不存在",429:"查询过于频繁，请稍后再试"}
        raise HTTPException(exc.code if exc.code in errors else 502, errors.get(exc.code,"社区服务暂不可用")) from exc
    except (URLError, OSError, ValueError) as exc:
        raise HTTPException(502, "无法读取社区响应，请稍后再试") from exc


def course(row):
    rating = row.get("rating") or {}
    return {"id":row["id"], "name":row["name"], "code":row.get("code"), "teacher":(row.get("main_teacher") or {}).get("name"), "count":rating.get("count"), "average":rating.get("avg")}


@router.get("/search")
def search(q: str = Query(min_length=1,max_length=100)):
    data = fetch("/course/", q=q, page_size=10)
    return [course(row) for row in data["items"]]


@router.get("/courses/{course_id}")
def evidence(course_id:int):
    detail = fetch(f"/course/{course_id}")
    data = fetch(f"/course/{course_id}/review", order_by="created_at",page_size=10)
    reviews = [{"id":r["id"],"term":r.get("semester"),"text":(r.get("content") or "")[:2000]} for r in data["items"]]
    return {**course(detail),"term":detail.get("last_semester"),"reviews":reviews}
