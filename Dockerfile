FROM python:3.11-slim

RUN mkdir /app

WORKDIR /app

ADD src .
ADD run.py .
ADD requirements.txt .

RUN pip install -r requirements.txt