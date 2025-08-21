from fastapi import FastAPI, Depends,HTTPException,Request, Response
from fastapi.middleware.cors import CORSMiddleware  # 导入跨域中间件
from fastapi.staticfiles import StaticFiles
import requests
import json
import uuid
import jwt
from datetime import datetime, timedelta
# from config import settings  # 导入配置对象
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import SessionLocal, engine
import models
from jwt_token import init_user, refresh_access_token
from dependencies import get_current_user
from models import User, SessionToken,ConsultationRecord

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
def call_ark_api(question, user_id,image_url=None,db=None):
    #将问题保存到问答表中，角色是用户
    if image_url:
        db_con=ConsultationRecord(user_id=user_id, role=1, content_text=question,img_b64=image_url)
        db.add(db_con)
        db.commit()
    else:
        db_con = ConsultationRecord(user_id=user_id, role=1, content_text=question)
        db.add(db_con)
        db.commit()
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
        # 将获取的回答保存到问答表中，角色是ai
        db_con = ConsultationRecord(user_id=user_id, role=2, content_text=answer)
        db.add(db_con)
        db.commit()
        return answer

    except Exception as e:
        return f"调用失败：{str(e)}"

# 获取回答的接口（GET请求、POST请求）
@app.api_route("/call_ark_api", methods=["GET", "POST"])
def call_ark(question: str, img_b64: str=None,user_id: str = Depends(get_current_user),db: Session = Depends(get_db)):
    answer = call_ark_api(question,user_id,img_b64,db)
    return answer
# 挂载静态文件目录（将 /templates 路径映射到 ./templates 文件夹）
app.mount("/templates", StaticFiles(directory="templates"), name="templates")
# 将/img映射到img文件夹
app.mount("/img", StaticFiles(directory="img"), name="img")
#前端页面接口
@app.get("/")
def index():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/templates/index.html")

# 初始化用户接口（首次访问）
@app.post("/init")
def init_new_user(db: Session = Depends(get_db)):
    """创建新用户并返回Token（无需登录），包括用户id和长期token的保存"""
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

