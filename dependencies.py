from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from models import User
from jwt_token import verify_token

# 从请求头提取Token（Authorization: Bearer <token>）
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token/refresh")

#解析token中的user_id
def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
) -> str:
    """验证Token并返回当前用户user_id"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token无效或已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # 1. 调用token中的方法验证Token并解析user_id
        user_id = verify_token(token)
        # 2. 检查用户是否存在（防止用户记录被删除）
        if not db.query(User).filter(User.user_id == user_id).first():
            raise credentials_exception
        return user_id
    except ValueError:
        raise credentials_exception