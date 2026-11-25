"""Storage port. DB adapter must implement atomic compare-and-swap semantics."""
import json
import os
from pathlib import Path
from threading import RLock
from typing import Protocol

class Conflict(Exception):
    pass

class StudentRepository(Protocol):
    def get(self, student_id: str) -> dict | None: ...
    def save(self, student_id: str, document: dict, expected_revision: int) -> dict: ...
    def delete(self, student_id: str, expected_revision: int) -> None: ...

class JsonStudentRepository:
    """Local single-process adapter; not a multi-worker production database."""
    def __init__(self, directory: Path):
        self.directory = directory
        self.lock = RLock()
    def path(self, key):
        from uuid import UUID
        return self.directory / (str(UUID(key)) + '.json')
    def get(self, student_id):
        with self.lock:
            path = self.path(student_id)
            return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
    def save(self, student_id, document, expected_revision):
        with self.lock:
            current = self.get(student_id)
            if (current or {}).get('revision', 0) != expected_revision:
                raise Conflict('档案已更新，请重新加载后重试')
            self.directory.mkdir(parents=True, exist_ok=True)
            result = {**document, 'revision': expected_revision + 1}
            path = self.path(student_id)
            temporary = path.with_suffix('.tmp')
            temporary.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
            os.replace(temporary,path)
            return result
    def delete(self, student_id, expected_revision):
        with self.lock:
            current = self.get(student_id)
            if current is None or current['revision'] != expected_revision: raise Conflict('档案已更新')
            self.path(student_id).unlink()
