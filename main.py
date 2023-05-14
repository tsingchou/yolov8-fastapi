import base64
import os
import sqlite3
import urllib
import uuid
from datetime import datetime
from datetime import timedelta
# import aioredis
import cv2
import jwt
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from model import User, ImageToPredict
from ultralytics import YOLO


load_dotenv()

project_dir = os.path.dirname(os.path.abspath(__file__))
# DOWNLOAD_IMG_BASE_DIR为项目目录所在文件夹拼接os.getenv("DOWNLOAD_IMG_BASE_DIR")
DOWNLOAD_IMG_BASE_DIR = os.path.join(project_dir, os.getenv("DOWNLOAD_IMG_BASE_DIR"))
PREDICT_BASE_DIR = os.path.join(project_dir, os.getenv("PREDICT_BASE_DIR"))
MODEL_PATH = os.path.join(project_dir, os.getenv("MODEL_PATH"))

yolo = YOLO(MODEL_PATH, task="detect")

# JWT 相关设置
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_TIME_MINUTES = int(os.getenv("JWT_EXPIRATION_TIME_MINUTES"))

# FastAPI 应用
app = FastAPI(
    title=os.getenv("APP_NAME"),
    description=os.getenv("APP_DESC"),
    version=os.getenv("APP_VERSION"),
)

app.mount('/public', StaticFiles(directory="data"), 'data')

app.add_middleware(
    CORSMiddleware,
    # 允许跨域的源列表，例如 ["http://www.example.org"] 等等，["*"] 表示允许任何源
    allow_origins=["*"],
    # 跨域请求是否支持 cookie，默认是 False，如果为 True，allow_origins 必须为具体的源，不可以是 ["*"]
    allow_credentials=False,
    # 允许跨域请求的 HTTP 方法列表，默认是 ["GET"]
    allow_methods=["*"],
    # 允许跨域请求的 HTTP 请求头列表，默认是 []，可以使用 ["*"] 表示允许所有的请求头
    # 当然 Accept、Accept-Language、Content-Language 以及 Content-Type 总之被允许的
    allow_headers=["*"],
    # 可以被浏览器访问的响应头, 默认是 []，一般很少指定
    # expose_headers=["*"]
    # 设定浏览器缓存 CORS 响应的最长时间，单位是秒。默认为 600，一般也很少指定
    # max_age=1000
)

# OAuth2 密码模式
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

#
# # 创建 Redis 连接池
# async def get_redis_pool():
#     redis_host = os.getenv("REDIS_HOST")
#     redis_port = os.getenv("REDIS_PORT")
#     redis = await aioredis.from_url(f"redis://{redis_host}:{redis_port}", encoding="utf-8", decode_responses=True)
#     return redis


# 获取用户信息
def get_user(username: str):
    with sqlite3.connect("sysuser.sqlite") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        system_user = cursor.fetchone()
    if system_user:
        user = User(username=system_user[0], password=system_user[1])
        return user
    else:
        return None


# 验证密码
def authenticate_user(user: User, password: str):
    if not user:
        return False
    if user.password != password:
        return False
    return user


# 创建 JWT token
def create_jwt_token(username: str):
    expiration_time = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_TIME_MINUTES)
    token = jwt.encode({"sub": username,  "exp": expiration_time}, JWT_SECRET,
                       algorithm=JWT_ALGORITHM)
    return token


# 验证 JWT token
def verify_jwt_token(request: Request):
    try:
        token = request.headers.get("Authorization", "").split(" ")[-1]
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        return get_user(username)
    except:
        return None


# 路由：获取 token
@app.post("/token")
async def login(login_data: dict):
    username = login_data.get("username")
    password = login_data.get("password")
    user = authenticate_user(get_user(username), password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误！",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_jwt_token(user.username)
    return {"access_token": token, "token_type": "bearer"}


# 请求钩子：更新 JWT token 过期时间
@app.middleware("http")
async def refresh_jwt_token(request, call_next):
    user = verify_jwt_token(request)
    if user:
        new_token = create_jwt_token(user.username)
        response = await call_next(request)
        response.headers["Authorization"] = f"Bearer {new_token}"
        return response
    return await call_next(request)


def download_img(url, date):
    img_path = os.path.join(DOWNLOAD_IMG_BASE_DIR, date)
    if not os.path.exists(img_path):
        os.makedirs(img_path)
    img_name = url.split("/")[-1]
    img_path = os.path.join(img_path, img_name)
    urllib.request.urlretrieve(url, img_path)
    return img_path


def base64_to_img(base64_str, date):
    img_path = os.path.join(DOWNLOAD_IMG_BASE_DIR, date)
    if not os.path.exists(img_path):
        os.makedirs(img_path)
    img_name = str(uuid.uuid4()) + ".jpg"
    img_path = os.path.join(img_path, img_name)
    with open(img_path, "wb") as f:
        f.write(base64.b64decode(base64_str))
    return img_path


@app.post("/predict")
async def predict(user: User = Depends(verify_jwt_token), imageToPredict: ImageToPredict = dict):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误！",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if imageToPredict.date:
        date = imageToPredict.date.replace("-", "")
    else:
        date = datetime.now().strftime("%Y%m%d")
    if imageToPredict.type == "url":
        # 从 url 下载图片并保存到本地DOWNLOAD_IMG_BASE_DIR
        img_path = download_img(imageToPredict.url, date)
    elif imageToPredict.type == "base64":
        # 将 base64 编码的图片保存到本地DOWNLOAD_IMG_BASE_DIR
        img_path = base64_to_img(imageToPredict.base64, date)
    result = yolo(
        source=img_path,
        conf=0.25,
        # device="cpu",
    )
    names = result[0].names
    # 将预测结果中的图片和标签保存到本地PREDICT_BASE_DIR
    predict_path = os.path.join(PREDICT_BASE_DIR, date)
    if not os.path.exists(predict_path):
        os.makedirs(predict_path)
    predict_name = img_path.split("/")[-1]
    predict_path = os.path.join(predict_path, predict_name)
    # 将result中的BOXES描绘到原图上，并保存到本地
    img = result[0].plot(font="Arial", line_width=2, font_size=15)
    for i in range(len(result[0].boxes.data)):
        classname = names[int(result[0].boxes.cls[i].item())]
        confidence = float(result[0].boxes.conf[i].item())
        label = f"{classname} {confidence:.2f}"
        xywh = result[0].boxes.xywh[i].tolist()
        # x1,y1分别是左上角的坐标，x2,y2分别是右下角的坐标
        x1 = int(xywh[0] - xywh[2] / 2)
        y1 = int(xywh[1] - xywh[3] / 2) - 15
        # 使用PIL将label写到图片上x1,y1的位置
        img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img)
        draw.text((x1, y1), label, (255, 255, 255), font=ImageFont.truetype("./SimHei.ttf", 14))
        img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
    # 保存图片
    cv2.imwrite(predict_path, img)
    # 将预测结果中的标签保存到predict_path同文件夹，后缀改成.json
    image_format = predict_path.split(".")[-1]
    label_path = predict_path.replace(image_format, "json")
    with open(label_path, "w") as f:
        f.write(result[0].tojson())
    data = {
        "original_img": img_path.replace(DOWNLOAD_IMG_BASE_DIR, ""),
        "predict_img": predict_path.replace(PREDICT_BASE_DIR, ""),
        "result": result[0].tojson()
    }
    return {"code": 200, "msg": "success", "data": data}

