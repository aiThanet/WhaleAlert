# syntax=docker/dockerfile:1

FROM python:3.10.1-slim-buster

WORKDIR /app

ENV TZ=Asia/Bangkok

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY . .

CMD ["python3", "-u", "main.py"]