from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # 导入跨域中间件
import requests
import json

# 初始化 FastAPI 应用
app = FastAPI()

# 添加跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源访问（生产环境建议指定具体域名）
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有请求头
)

# 根据用户提出的问题调用豆包ai返回相应的结果
def call_ark_api(question, image_url=None):
    """
    调用火山方舟 API，发送问题（可附带图片）并返回结果
    :param question: 控制台输入的问题（字符串）
    :param image_url: 图片 URL（可选，无需图片时传 None）
    :return: API 响应结果中的回答文本
    """
    # API 接口地址
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

    # 请求头（包含身份验证和数据格式）
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
        return answer

    except Exception as e:
        return f"调用失败：{str(e)}"

# 获取回答的接口（GET请求、POST请求）
@app.api_route("/call_ark_api", methods=["GET", "POST"])
def call_ark(question: str, img_b64: str=None):
    answer = call_ark_api(question, img_b64)
    return answer

# 你的自定义方法（替换成你的实际逻辑）
def add_numbers(a: int, b: int) -> int:
    return a + b

# 将方法包装为 API 接口（GET 请求）
@app.get("/add")
def api_add(a: int, b: int):
    result = add_numbers(a, b)
    return {"result": result}

# 可选：再添加一个接口示例（POST 请求）
from pydantic import BaseModel

class Data(BaseModel):
    text: str

@app.post("/uppercase")
def api_uppercase(data: Data):
    return {"original": data.text, "uppercase": data.text.upper()}
