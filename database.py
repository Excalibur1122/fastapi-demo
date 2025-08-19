from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 从环境变量获取数据库连接信息
DATABASE_USER = os.getenv("MYSQL_USER", "root")
DATABASE_PASSWORD = os.getenv("MYSQL_PASSWORD", "SH3VcG7r28M5w1QP4NW0Z9YbdnAR6TyL")
DATABASE_HOST = os.getenv("MYSQL_HOST", "sjc1.clusters.zeabur.com")
DATABASE_PORT = os.getenv("MYSQL_PORT", "30112")
DATABASE_NAME = os.getenv("MYSQL_DATABASE", "zeabur")

# 构建连接 URL（已包含 charset=utf8mb4）
DATABASE_URL = f"mysql+pymysql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}?charset=utf8mb4"

# 创建引擎（移除 encoding 参数，字符编码通过 URL 中的 charset 指定）
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"charset": "utf8mb4", "ssl": False}
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基础模型类
Base = declarative_base()

# 依赖：获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
