"""Local authentication adapter. School SSO can replace identity verification later."""
from contextlib import contextmanager
import hashlib
import hmac
import secrets
import sqlite3
import time
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

class Credentials(BaseModel):
    username: str = Field(pattern=r'^[A-Za-z0-9_一-鿿-]{2,40}$')
    password: str = Field(min_length=10,max_length=128)

class LocalIdentityStore:
    def __init__(self,path:Path):
        self.path=path;path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, salt TEXT NOT NULL, digest TEXT NOT NULL, student_id TEXT UNIQUE, role TEXT NOT NULL DEFAULT \'student\', teacher_name TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, username TEXT NOT NULL, expires REAL NOT NULL)')
            # 旧版表（student_id NOT NULL、无 role）在线迁移
            cols={row[1] for row in db.execute('PRAGMA table_info(users)')}
            if 'role' not in cols:
                db.execute('ALTER TABLE users RENAME TO users_legacy')
                db.execute('CREATE TABLE users (username TEXT PRIMARY KEY, salt TEXT NOT NULL, digest TEXT NOT NULL, student_id TEXT UNIQUE, role TEXT NOT NULL DEFAULT \'student\', teacher_name TEXT)')
                db.execute('INSERT INTO users (username,salt,digest,student_id,role) SELECT username,salt,digest,student_id,\'student\' FROM users_legacy')
                db.execute('DROP TABLE users_legacy')
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path)
        try:
            with db:yield db
        finally:db.close()
    def hash_password(self,password,salt):return hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
    def register(self,username,password):
        salt=secrets.token_hex(16)
        try:
            with self.connect() as db:db.execute('INSERT INTO users (username,salt,digest,student_id,role) VALUES (?,?,?,?,?)',(username,salt,self.hash_password(password,salt),str(uuid4()),'student'))
        except sqlite3.IntegrityError:raise HTTPException(409,'用户名已存在')
    def register_teacher(self,username,password,teacher_name):
        """预置教师账号：仅服务端初始化调用，不对外暴露注册接口。"""
        salt=secrets.token_hex(16)
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO users (username,salt,digest,student_id,role,teacher_name) VALUES (?,?,?,NULL,?,?)',(username,salt,self.hash_password(password,salt),'teacher',teacher_name))
    def login(self,username,password):
        with self.connect() as db:
            row=db.execute('SELECT salt,digest FROM users WHERE username=?',(username,)).fetchone()
            actual=self.hash_password(password,row[0] if row else '00'*16)
            if not row or not hmac.compare_digest(actual,row[1]):raise HTTPException(401,'用户名或密码不正确')
            token=secrets.token_urlsafe(32)
            db.execute('DELETE FROM sessions WHERE expires < ?',(time.time(),))
            db.execute('INSERT INTO sessions VALUES (?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),username,time.time()+86400))
            return token
    def resolve(self,token):
        if not token:return None
        with self.connect() as db:
            row=db.execute('SELECT u.username,u.student_id,u.role,u.teacher_name FROM sessions s JOIN users u ON u.username=s.username WHERE token_hash=? AND expires>?',(hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone()
            return {'username':row[0],'student_id':row[1],'role':row[2],'teacher_name':row[3]} if row else None
    def logout(self,token):
        with self.connect() as db:db.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256((token or '').encode()).hexdigest(),))

def auth_router(store,secure=False):
    router=APIRouter(prefix='/api/auth',tags=['local authentication'])
    @router.post('/register',status_code=201)
    def register(body:Credentials):store.register(body.username,body.password);return {'created':True}
    @router.post('/login')
    def login(body:Credentials,response:Response):
        token=store.login(body.username,body.password)
        response.set_cookie('coursepilot_session',token,httponly=True,samesite='strict',secure=secure,max_age=86400)
        return store.resolve(token)
    @router.get('/me')
    def me(request:Request):
        identity=store.resolve(request.cookies.get('coursepilot_session'))
        if not identity:raise HTTPException(401,'请先登录')
        return identity
    @router.post('/logout')
    def logout(request:Request,response:Response):store.logout(request.cookies.get('coursepilot_session'));response.delete_cookie('coursepilot_session');return {'ok':True}
    return router


# School integration port: implement with the school's documented SSO protocol.
# The return value must be server-verified; never trust a browser-supplied username.
from typing import Protocol
class SchoolIdentityProvider(Protocol):
    def authorization_url(self, state: str, redirect_uri: str) -> str: ...
    def verify_callback(self, code: str, state: str, redirect_uri: str) -> dict: ...
