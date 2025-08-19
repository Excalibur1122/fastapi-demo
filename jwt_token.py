import uuid
from datetime import datetime, timedelta
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os

from models import User, SessionToken

# 加载配置
load_dotenv()
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dsaodhoiioj")  # 生产环境需更换
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 短期Token有效期（1小时）
LONG_TOKEN_EXPIRE_DAYS = 7  # 长期Token有效期（7天）

#根据user_id生成短期access_token或长期long_token
def create_token(user_id: str, is_long: bool = False) -> str:
    """生成Token（短期access_token或长期long_token）"""
    expire = datetime.utcnow() + (
        timedelta(days=LONG_TOKEN_EXPIRE_DAYS) if is_long
        else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode = {"sub": user_id, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

#验证传来的token是否在有效时间内
def verify_token(token: str) -> str:
    """验证Token并返回user_id"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]  # 返回user_id
    except (JWTError, KeyError):
        raise ValueError("无效的Token")

#新用户初始化
def init_user(db: Session) -> tuple[str, str, str]:
    """初始化新用户：创建user+long_token+access_token"""
    # 1. 生成唯一user_id（UUID）
    user_id = str(uuid.uuid4())

    # 2. 创建用户记录（时间自动填充）
    db_user = User(user_id=user_id)
    db.add(db_user)
    db.commit()

    # 3. 生成Token
    access_token = create_token(user_id, is_long=False)
    long_token = create_token(user_id, is_long=True)

    # 4. 存储长期Token（时间自动填充）
    db_token = SessionToken(user_id=user_id, long_token=long_token)
    db.add(db_token)
    db.commit()

    return user_id, access_token, long_token

#用长期token刷新短期token
def refresh_access_token(db: Session, long_token: str) -> str:
    """用长期Token刷新短期access_token"""
    # 1. 验证长期Token
    try:
        user_id = verify_token(long_token)
    except ValueError:
        raise ValueError("长期Token无效")

    # 2. 在有效时间内，检查Token是否存在于数据库
    db_token = db.query(SessionToken).filter(
        SessionToken.user_id == user_id,
        SessionToken.long_token == long_token
    ).first()
    if not db_token:
        raise ValueError("长期Token未注册")

    # 3. 通过验证，生成新的短期Token
    return create_token(user_id, is_long=False)