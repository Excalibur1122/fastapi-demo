# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 从 .env 文件读取配置（没有则用默认值，生产环境必须通过.env设置）
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    #本地配置
    secret_key: str = "sdsasssssssss"  # 核心密钥
    access_expire_hours: int = 2  # Access Token有效期
    refresh_expire_days: int = 7  # Refresh Token有效期


# 实例化配置对象，供main.py导入
settings = Settings()