FROM python:3.10-slim

ENV PYTHONUNBUFFERED=True \
    PORT=9099

WORKDIR /app
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . ./

RUN  sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list
RUN  sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list
RUN  apt-get update
RUN  apt-get install ffmpeg libsm6 libxext6  -y

RUN mkdir -p /root/.config/Ultralytics/
RUN cp ./Arial.Unicode.ttf  /root/.config/Ultralytics/Arial.Unicode.ttf

CMD exec uvicorn main:app --reload --host 0.0.0.0 --port $PORT