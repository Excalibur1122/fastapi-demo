from fastapi import FastAPI, Depends,HTTPException,Request, Response
from fastapi.middleware.cors import CORSMiddleware  # 导入跨域中间件
import requests
import json
import uuid
import jwt
from datetime import datetime, timedelta
from config import settings  # 导入配置对象
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import SessionLocal, engine
import models
from token import init_user, refresh_access_token
from dependencies import get_current_user

# 初始化 FastAPI 应用
app = FastAPI()

# 添加跨域配置
app.add_middleware(
    CORSMiddleware,
    # allow_origins=["http://127.0.0.1:5500","https://www.htmlgo.cn","https://weixin.qq.com"],  # 允许所有来源访问（生产环境建议指定具体域名）
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有请求头
)
# 数据库会话依赖：获取数据库连接
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 根据用户提出的问题调用豆包ai返回相应的结果
def call_ark_api(question, user_id,image_url=None):
    """
    调用火山方舟 API，发送问题（可附带图片）并返回结果
    :param question: 控制台输入的问题（字符串）
    :param image_url: 图片 URL（可选，无需图片时传 None）
    :return: API 响应结果中的回答文本
    """
    # API 接口地址
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

    # 请求头（包含身份验证和数据格式）//
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer 1c99f808-f87f-4312-86d6-e8f4fbe1250e"  # 替换为实际 token
    }

    # 构建消息内容（支持文字+图片混合输入）
    content = [{"type": "text", "text": question}]
    if image_url:
        content.insert(0, {"type": "image_url", "image_url": {"url": image_url}})

    # 请求体参数
    payload = {
        "model": "doubao-1-5-thinking-vision-pro-250428",  # 指定模型
        "messages": [{"role": "user", "content": content}]  # 用户消息
    }

    try:
        # 发送 POST 请求
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # 检查请求是否成功（非 200 状态码会抛异常）

        # 解析响应结果
        result = response.json()
        # 提取 AI 回答（从响应的 choices 中获取）
        answer = result["choices"][0]["message"]["content"]
        return answer

    except Exception as e:
        return f"调用失败：{str(e)}"


# 获取密钥和过期时间配置
SECRET_KEY = settings.secret_key
ACCESS_EXPIRE_HOURS = settings.access_expire_hours
REFRESH_EXPIRE_DAYS = settings.refresh_expire_days


def new_user(db: Session = Depends(get_db)):
    # 生成用户唯一ID
    unique_id = str(uuid.uuid4())  # 转换为字符串以便存储和传输
    #将生成的用户唯一ID保存到数据库
    new_user = models.User(user_id=unique_id)
    # 计算短期Token(access token)过期时间
    short_expiry = datetime.utcnow() + timedelta(hours=ACCESS_EXPIRE_HOURS)
    # 构建短期Token payload
    short_payload = {
        "user_id": unique_id,
        "exp": short_expiry,  # 过期时间
        "type": "access"  # 标识Token类型
    }
    # 生成短期Token
    short_token = jwt.encode(short_payload, SECRET_KEY, algorithm="HS256")

    # 计算长期Token(refresh token)过期时间
    long_expiry = datetime.utcnow() + timedelta(days=REFRESH_EXPIRE_DAYS)
    # 构建长期Token payload
    long_payload = {
        "user_id": unique_id,
        "exp": long_expiry,  # 过期时间
        "type": "refresh"  # 标识Token类型
    }
    # 生成长期Token
    long_token = jwt.encode(long_payload, SECRET_KEY, algorithm="HS256")
    #将生成的长期token保存到数据库
    new_SessionToken = models.SessionToken(long_token=long_token)
    # 返回生成的用户ID和两个Token
    return {
        "short_token": short_token,
        "long_token": long_token
    }

#查找指定的用户id是否存在（目前废弃）
@app.api_route("/users/exists", methods=["GET", "POST"])
def check_user_exists(user_id: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    return {
        "user_id": user_id,
        "exists": True if user else False,
        "id": user.id if user else None  # 若存在，返回对应的自增 id
    }

#生成user_id，创建short_token和long_token返回（目前废弃）
@app.api_route("/new_user", methods=["GET", "POST"])
def newUser():
    return new_user()


# 获取回答的接口（GET请求、POST请求）
@app.api_route("/call_ark_api", methods=["GET", "POST"])
def call_ark(question: str, img_b64: str=None,user_id: str = Depends(get_current_user)):
    answer = call_ark_api(question,user_id,img_b64)
    return answer

# 初始化用户接口（首次访问）
@app.post("/init")
def init_new_user(db: Session = Depends(get_db)):
    """创建新用户并返回Token（无需登录）"""
    try:
        user_id, access_token, long_token = init_user(db)
        return {
            "access_token": access_token,
            "long_token": long_token,
            "token_type": "bearer"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"初始化失败：{str(e)}")

# 使用接收的长期Token刷新短期Token
class RefreshRequest(BaseModel):
    long_token: str
@app.post("/token/refresh")
def refresh_token(
    req: RefreshRequest,
    db: Session = Depends(get_db)
):
    """用长期Token获取新的access_token"""
    try:
        new_access_token = refresh_access_token(db, req.long_token)
        return {"access_token": new_access_token, "token_type": "bearer"}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

