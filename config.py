# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

# 配置常量
UPLOAD_DIR = "img"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
API_BASE_URL = "https://bean-bun-ai.zeabur.app"
ARK_API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
ARK_API_KEY = "Bearer 1c99f808-f87f-4312-86d6-e8f4fbe1250e"

