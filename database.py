from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 部署以后从zeabur中直接获取，没有的情况下使用默认值
DATABASE_USER = os.getenv("MYSQL_USER", "root")
DATABASE_PASSWORD = os.getenv("MYSQL_PASSWORD", "SH3VcG7r28M5w1QP4NW0Z9YbdnAR6TyL")
DATABASE_HOST = os.getenv("MYSQL_HOST", "sjc1.clusters.zeabur.com")
DATABASE_PORT = os.getenv("MYSQL_PORT", "30112")
DATABASE_NAME = os.getenv("MYSQL_DATABASE", "zeabur")

# 构建连接 URL
DATABASE_URL = f"mysql+pymysql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}?charset=utf8mb4"

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    encoding="utf8mb4",
    pool_pre_ping=True,
    connect_args={"charset": "utf8mb4", "ssl": False}
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基础模型类
Base = declarative_base()