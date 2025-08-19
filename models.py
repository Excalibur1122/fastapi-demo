from sqlalchemy import Text,Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base

# 对应已创建的 user_table 表
class User(Base):
    __tablename__ = "user_table"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(50), unique=True, nullable=False, index=True)  # 唯一用户标识
    creation_time = Column(DateTime, default=func.now(), nullable=False)  # 创建时间（自动生成）
    update_time = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)  # 更新时间（自动更新）

class ConsultationRecord(Base):
    """咨询记录表模型（包含用户关联字段）"""
    __tablename__ = "consultation_records"  # 对应数据库表名

    # 自增主键
    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="自增主键")
    # 关联的用户ID（新增字段）
    user_id = Column(String(255), nullable=False, comment="关联的用户ID（字符串类型）")
    # 角色（1：用户，2：AI）
    role = Column(Integer, nullable=False, comment="角色（1：用户，2：AI）")
    # 发送的内容（长文本）
    content_text = Column(Text, nullable=False, comment="发送的内容")
    # 创建时间（自动生成）
    created_at = Column(DateTime, default=func.now(), nullable=False, comment="创建时间")
    # 修改时间（自动更新）
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, comment="修改时间")

class SessionToken(Base):
    """会话token记录表模型"""
    __tablename__ = "session_token"  # 对应数据库表名

    # 自增主键
    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="自增主键")
    # 关联的用户ID（新增字段）
    user_id = Column(String(255), nullable=False, comment="关联的用户ID（字符串类型）")
    # 长期token（唯一）
    long_token = Column(String(255), unique=True, nullable=False, comment="长期token（字符串类型）")
    # 创建时间（自动生成）
    created_at = Column(DateTime, default=func.now(), nullable=False, comment="创建时间")
    # 修改时间（自动更新）
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, comment="修改时间")
