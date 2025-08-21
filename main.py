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
import base64
import os
from typing import List, Dict, Any

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
    # 确保img文件夹存在
    if not os.path.exists('img'):
        os.makedirs('img')
    # 图片路径
    saved_img_url = None
    if image_url:
        try:
            # 生成随机不重复的图片名称（使用UUID+时间戳确保唯一性）
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            unique_id = uuid.uuid4().hex
            img_filename = f"{timestamp}_{unique_id}.png"
            img_path = os.path.join('img', img_filename)

            # 解码base64并保存图片
            # 注意：base64编码通常以'data:image/png;base64,'开头，需要先去除
            if image_url.startswith('data:image'):
                # 分割base64头部和实际编码内容
                base64_data = image_url.split(',')[1]
            else:
                base64_data = image_url

            # 解码并写入文件
            with open(img_path, 'wb') as f:
                f.write(base64.b64decode(base64_data))

            # 构建存储到数据库的URL路径
            saved_img_url = f"img/{img_filename}"

        except Exception as e:
            print(f"图片保存失败: {str(e)}")
            # 可以根据需要决定是否抛出异常或继续执行
    # 将记录保存到数据库
    if saved_img_url:
        db_con = ConsultationRecord(
            user_id=user_id,
            role=1,
            content_text=question,
            img_url=saved_img_url  # 这里使用修改后的字段名img_url
        )
    else:
        db_con = ConsultationRecord(
            user_id=user_id,
            role=1,
            content_text=question
        )
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


def get_conversation_transcript(page: int, page_size: int, user_id: str, db: Session) -> Dict[str, Any]:
    """
    获取指定用户的对话记录，支持分页和按创建时间倒序排序

    参数:
        page: 页码（从1开始）
        page_size: 每页记录数
        user_id: 要查询的用户ID
        db: 数据库会话

    返回:
        包含分页数据和元信息的字典
    """
    # 验证分页参数有效性
    if page < 1:
        raise ValueError("页码必须大于等于1")
    if page_size < 1 or page_size > 100:  # 限制最大页大小，防止一次请求过多数据
        raise ValueError("每页记录数必须在1到100之间")

    # 计算偏移量
    offset = (page - 1) * page_size

    # 查询总记录数（用于计算总页数）
    total_records = db.query(ConsultationRecord).filter(
        ConsultationRecord.user_id == user_id
    ).count()

    # 分页查询指定用户的记录，按创建时间倒序排序（最新的在前）
    records = db.query(ConsultationRecord).filter(
        ConsultationRecord.user_id == user_id
    ).order_by(
        ConsultationRecord.created_at.desc()
    ).offset(offset).limit(page_size).all()

    # 计算总页数
    total_pages = (total_records + page_size - 1) // page_size  # 向上取整

    # 格式化返回数据
    formatted_records = []
    for record in records:
        formatted_records.append({
            "id": record.id,
            "user_id": record.user_id,
            "role": record.role,
            "content_text": record.content_text,
            "img_url": record.img_url,
            "created_at": record.created_at.isoformat(),  # 转换为ISO格式字符串
            "updated_at": record.updated_at.isoformat()
        })

    return {
        "data": formatted_records,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_records": total_records,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


@app.api_route("/get_conversation_transcript", methods=["GET", "POST"])
def get_conversation(
        page: int = 1,
        page_size: int = 20,  # 默认为20条每页
        user_id: str = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    接口：获取当前用户的对话记录，支持分页

    查询参数:
        page: 页码，默认为1
        page_size: 每页记录数，默认为20，最大100
        user_id: 由依赖项get_current_user提供的当前用户ID
    """
    try:
        # 调用数据查询方法
        result = get_conversation_transcript(page, page_size, user_id, db)
        return {
            "code": 200,
            "message": "查询成功",
            "data": result
        }
    except ValueError as e:
        # 处理参数错误
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # 处理其他异常
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

