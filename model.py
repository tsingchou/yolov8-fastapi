from pydantic import BaseModel
from pydantic.typing import List


# 用户模型
class User(BaseModel):
    username: str
    password: str


# 传入图片模型
class ImageToPredict(BaseModel):
    type: str = 'url'
    url: str = None
    base64: str = None
    date: str = None


# 返回结果模型
class Result(BaseModel):
    code: int = 0
    msg: str = 'success'
    data: List[dict] = []
