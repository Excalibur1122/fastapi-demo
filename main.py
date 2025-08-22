from fastapi import UploadFile, File,Form,FastAPI, Depends,HTTPException,Request, Response
from fastapi.middleware.cors import CORSMiddleware  # 导入跨域中间件
from fastapi.staticfiles import StaticFiles
import requests
import json
import uuid
import jwt
from datetime import datetime, timedelta
from config import *
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
import logging
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse

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

# --------------------------
# 1. 配置详细错误日志
# --------------------------
# 创建日志器
logger = logging.getLogger("app")
logger.setLevel(logging.ERROR)  # 只记录错误及以上级别

# 定义日志格式（包含时间、模块、错误级别、消息、完整堆栈）
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s\n"
    "Traceback:\n%(exc_info)s\n"  # 关键：记录完整堆栈信息
)

# 日志输出到文件（生产环境推荐）
file_handler = logging.FileHandler("app_errors.log")
file_handler.setFormatter(formatter)

# 同时输出到控制台（方便实时查看）
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# 添加处理器到日志器
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# --------------------------
# 2. 初始化 FastAPI 应用
# --------------------------
app = FastAPI()

# 跨域配置（根据你的需求调整）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------
# 3. 全局异常捕获中间件
#    捕获所有未处理的异常并记录日志
# --------------------------
@app.middleware("http")
async def catch_all_exceptions(request: Request, call_next):
    try:
        # 执行请求处理
        response = await call_next(request)
        return response
    except Exception as e:
        # 记录错误详情：包含请求路径、方法、参数和完整堆栈
        try:
            # 获取请求参数（GET为查询参数，POST为表单/JSON数据）
            if request.method == "GET":
                params = dict(request.query_params)
            else:
                params = await request.json()  # 适用于JSON请求
        except:
            params = "无法解析请求参数"

        # 记录错误日志
        logger.error(
            f"请求失败：方法={request.method}，路径={request.url.path}，参数={params}",
            exc_info=True  # 强制记录完整堆栈（核心）
        )

        # 向客户端返回安全的错误信息（不暴露细节）
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": "服务器内部错误，请稍后重试"}
        )

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

    # 分页查询指定用户的记录，按创建时间正序排序
    records = db.query(ConsultationRecord).filter(
        ConsultationRecord.user_id == user_id
    ).order_by(
        ConsultationRecord.created_at.asc()
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
            "img_url": "https://bean-bun-ai.zeabur.app/" + record.img_url if record.img_url else None,
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

# 根据用户提出的问题调用豆包ai返回相应的结果
import json
import requests


# 根据用户提出的问题调用豆包ai返回相应的结果
def call_ark_api(question: str, user_id: str, image_path: str = None, db: Session = None) -> str:
    """调用火山方舟API获取回答并保存记录"""
    # 保存用户提问记录
    if db:
        record_data = {
            "user_id": user_id,
            "role": 1,  # 1表示用户
            "content_text": question
        }
        if image_path:
            record_data["img_url"] = image_path

        db.add(ConsultationRecord(**record_data))
        db.commit()

    # 构建API请求内容
    content = [{"type": "text", "text": question}]
    if image_path:
        full_image_url = f"{API_BASE_URL}/{image_path}"
        content.insert(0, {
            "type": "image_url",
            "image_url": {"url": full_image_url}
        })

    # 发送请求到ARK API
    try:
        response = requests.post(
            ARK_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": ARK_API_KEY
            },
            data=json.dumps({
                "model": "doubao-1-5-thinking-vision-pro-250428",
                "messages": [{"role": "user", "content": content}]
            })
        )
        response.raise_for_status()
        result = response.json()
        answer = result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"API调用失败: {str(e)}"

    # 保存AI回答记录
    if db:
        db.add(ConsultationRecord(
            user_id=user_id,
            role=2,  # 2表示AI
            content_text=answer
        ))
        db.commit()

    return answer


# 工具函数：图片处理
def process_image_file(file: UploadFile) -> str:
    """处理上传的图片文件，返回相对路径"""
    # 验证文件名和扩展名
    if not file.filename or "." not in file.filename:
        raise ValueError("无效的图片文件名")

    ext = file.filename.rsplit(".", 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的图片格式，允许格式: {ALLOWED_EXTENSIONS}")

    # 生成唯一文件名
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = uuid.uuid4().hex[:10]
    new_filename = f"{timestamp}_{unique_id}.{ext}"

    # 保存文件
    file_path = os.path.join(UPLOAD_DIR, new_filename)
    try:
        with open(file_path, "wb") as buffer:
            content = file.file.read()
            buffer.write(content)
    except Exception as e:
        raise IOError(f"图片保存失败: {str(e)}")

    # 返回相对路径
    return f"{UPLOAD_DIR}/{new_filename}"

# 获取回答的接口（GET请求、POST请求）
@app.post("/call_ark_api", response_model=dict)
def handle_ark_request(
        question: str = Form(..., description="用户的问题文本"),
        file: UploadFile = File(None, description="可选的图片文件"),
        user_id: str = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """处理用户的提问（可附带图片），返回AI回答"""
    # 处理图片（如果有）
    image_path = None
    if file:
        try:
            image_path = process_image_file(file)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    # 调用业务逻辑获取回答
    answer = call_ark_api(question, user_id, image_path, db)
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
#微信验证
@app.get("/10f810fe2c20ef9d4e8ae13ab05b12b4.txt")
def serve_verification_file():
    # 文件路径：根目录下的认证文件
    file_path = "templates/10f810fe2c20ef9d4e8ae13ab05b12b4.txt"  # 直接写文件名（因为在根目录）

    # 检查文件是否存在
    if not os.path.exists(file_path):
        return {"error": "认证文件不存在"}, 404

    # 返回文件内容（MIME类型自动设为text/plain，符合txt文件要求）
    return FileResponse(path=file_path)
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

#获取指定用户对话记录的接口，采用了分页查询
@app.api_route("/get_conversation_transcript", methods=["GET", "POST"])
def get_conversation(
        page: int = 1,
        page_size: int = 20,
        user_id: str = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    try:
        result = get_conversation_transcript(page, page_size, user_id, db)
        return {
            "code": 200,
            "message": "查询成功",
            "data": result
        }
    except ValueError as e:
        # 记录参数错误日志（可选，因通常是客户端问题）
        logger.warning(f"参数错误: {str(e)}, user_id={user_id}, page={page}, page_size={page_size}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # 关键：记录未知异常的完整堆栈
        logger.error(
            f"查询对话记录失败: user_id={user_id}, page={page}, page_size={page_size}",
            exc_info=True  # 强制记录完整堆栈
        )
        # 向客户端返回安全的错误信息（不暴露细节）
        raise HTTPException(status_code=500, detail="查询失败，请稍后重试")
