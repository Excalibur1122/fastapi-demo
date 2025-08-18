from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base

# 对应已创建的 user_table 表
class User(Base):
    __tablename__ = "user_table"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(50), unique=True, nullable=False, index=True)  # 唯一用户标识
    creation_time = Column(DateTime, default=func.now(), nullable=False)  # 创建时间（自动生成）
    update_time = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)  # 更新时间（自动更新）