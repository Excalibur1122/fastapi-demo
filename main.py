from fastapi import FastAPI

# 初始化 FastAPI 应用
app = FastAPI()

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